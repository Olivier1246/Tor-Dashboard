"""Interface avec le démon Tor via le ControlPort (bibliothèque stem).

Cette couche est volontairement défensive : chaque information est récupérée
dans son propre try/except afin qu'une métrique indisponible n'empêche pas
les autres de s'afficher. Si Tor est arrêté, get_metrics() renvoie
simplement ``{"online": False}``.
"""

from __future__ import annotations

import threading
import time
from collections import Counter
from typing import Any

import stem
from stem.control import Controller

from .config import settings
from .countries import country_name, flag_emoji


class TorController:
    """Connexion paresseuse et thread-safe au ControlPort de Tor."""

    def __init__(self) -> None:
        self._controller: Controller | None = None
        self._lock = threading.Lock()
        # Cache fingerprint → adresse IP du consensus (évite N allers-retours)
        self._consensus: dict[str, str] = {}
        self._consensus_ts = 0.0

    # -- gestion de connexion ------------------------------------------------
    def _connect(self) -> Controller:
        controller = Controller.from_port(port=settings.tor_control_port)
        if settings.tor_control_password:
            controller.authenticate(password=settings.tor_control_password)
        else:
            controller.authenticate()  # cookie auth
        return controller

    def _get(self) -> Controller:
        """Renvoie un contrôleur authentifié, en se reconnectant si besoin."""
        if self._controller is not None and self._controller.is_alive():
            return self._controller
        if self._controller is not None:
            try:
                self._controller.close()
            except Exception:
                pass
        self._controller = self._connect()
        return self._controller

    def close(self) -> None:
        with self._lock:
            if self._controller is not None:
                try:
                    self._controller.close()
                except Exception:
                    pass
                self._controller = None

    # -- helpers -------------------------------------------------------------
    @staticmethod
    def _safe(fn, default=None):
        try:
            return fn()
        except Exception:
            return default

    # -- métriques -----------------------------------------------------------
    def get_metrics(self) -> dict[str, Any]:
        """Collecte un instantané des métriques du relais."""
        with self._lock:
            try:
                c = self._get()
            except Exception as exc:
                return {"online": False, "error": str(exc)}

            m: dict[str, Any] = {"online": True}

            # Identité
            m["nickname"] = self._safe(lambda: c.get_conf("Nickname", "Unnamed"))
            m["fingerprint"] = self._safe(lambda: c.get_info("fingerprint"))
            ver = self._safe(lambda: str(c.get_version()))
            m["version"] = ver

            # Bootstrap (% de démarrage)
            boot = self._safe(lambda: c.get_info("status/bootstrap-phase"), "")
            m["bootstrap"] = self._parse_bootstrap(boot)

            # Uptime (secondes) — dispo sur Tor récents
            up = self._safe(lambda: c.get_info("uptime"))
            m["uptime"] = int(up) if up and up.isdigit() else None

            # Trafic cumulé depuis le démarrage (octets)
            m["read_total"] = self._safe(
                lambda: int(c.get_info("traffic/read")), 0
            )
            m["written_total"] = self._safe(
                lambda: int(c.get_info("traffic/written")), 0
            )

            # Bande passante configurée (octets/s)
            m["rate"] = self._safe(lambda: c.get_effective_rate())
            m["burst"] = self._safe(lambda: c.get_effective_rate(burst=True))

            # Drapeaux du consensus (Guard, Fast, Stable, Exit, Running…)
            fp = m.get("fingerprint")
            flags = None
            if fp:
                flags = self._safe(
                    lambda: list(c.get_network_status(fp).flags)
                )
            m["flags"] = flags or []

            # Politique de sortie (résumé)
            m["exit_policy"] = self._safe(
                lambda: str(c.get_exit_policy()), ""
            )

            # Circuits & connexions OR ouvertes
            # (orconn-status passe par le ControlPort : fiable quel que soit
            #  l'utilisateur, contrairement à get_connections() qui doit lire
            #  les sockets du process Tor via /proc.)
            m["circuits"] = self._safe(lambda: len(c.get_circuits()), 0)
            oc = self._safe(lambda: c.get_info("orconn-status"))
            m["connections"] = (
                len([ln for ln in oc.splitlines() if ln.strip()])
                if oc else None
            )

            # Comptabilité de bande passante (AccountingMax)
            m["accounting"] = self._get_accounting(c)

            # Adresse onion du dashboard
            m["onion"] = self._read_onion_address()

            return m

    def _get_accounting(self, c: Controller) -> dict[str, Any] | None:
        enabled = self._safe(lambda: c.get_info("accounting/enabled"))
        if enabled != "1":
            return None
        info: dict[str, Any] = {"enabled": True}
        info["hibernating"] = self._safe(
            lambda: c.get_info("accounting/hibernating")
        )
        used = self._safe(lambda: c.get_info("accounting/bytes"))
        left = self._safe(lambda: c.get_info("accounting/bytes-left"))
        if used:
            r, w = used.split()
            info["read_used"], info["written_used"] = int(r), int(w)
        if left:
            r, w = left.split()
            info["read_left"], info["written_left"] = int(r), int(w)
        info["interval_end"] = self._safe(
            lambda: c.get_info("accounting/interval-end")
        )
        return info

    @staticmethod
    def _parse_bootstrap(line: str) -> int:
        for tok in line.split():
            if tok.startswith("PROGRESS="):
                try:
                    return int(tok.split("=", 1)[1])
                except ValueError:
                    return 0
        return 0

    @staticmethod
    def _read_onion_address() -> str | None:
        try:
            with open(settings.onion_hostname_file, "r", encoding="utf-8") as fh:
                return fh.read().strip()
        except Exception:
            return None

    # -- connexions par pays -------------------------------------------------
    def _consensus_map(self, c: Controller) -> dict[str, str]:
        """Carte fingerprint → adresse IP du consensus, mise en cache 5 min."""
        now = time.time()
        if self._consensus and now - self._consensus_ts < 300:
            return self._consensus
        mapping: dict[str, str] = {}
        try:
            for desc in c.get_network_statuses():
                if desc.fingerprint and desc.address:
                    mapping[desc.fingerprint] = desc.address
        except Exception:
            return self._consensus  # garde l'ancien cache si échec
        self._consensus = mapping
        self._consensus_ts = now
        return mapping

    @staticmethod
    def _parse_orconn_fingerprints(orconn: str) -> list[str]:
        """Extrait les empreintes des connexions OR (lignes ``$FP~nick STATE``)."""
        fps: list[str] = []
        for line in orconn.splitlines():
            line = line.strip()
            if not line:
                continue
            target = line.split()[0]
            if target.startswith("$"):
                target = target[1:]
            # Sépare l'empreinte d'un éventuel ~nick ou =nick
            for sep in ("~", "="):
                if sep in target:
                    target = target.split(sep, 1)[0]
            fps.append(target.upper())
        return fps

    def connections_by_country(self, max_relays: int = 1500) -> dict[str, Any]:
        """Agrège les connexions OR du relais par pays (via le ControlPort).

        Ne nécessite aucun accès aux sockets système : on liste les pairs via
        ``orconn-status``, on résout leur IP dans le consensus, puis le pays
        via ``GETINFO ip-to-country`` (base GeoIP de Tor).
        """
        with self._lock:
            try:
                c = self._get()
            except Exception as exc:
                return {"online": False, "error": str(exc)}

            orconn = self._safe(lambda: c.get_info("orconn-status"))
            if not orconn:
                return {"online": True, "total": 0, "resolved": 0, "countries": []}

            fps = self._parse_orconn_fingerprints(orconn)[:max_relays]
            mapping = self._consensus_map(c)

            counter: Counter[str] = Counter()
            ip_country: dict[str, str] = {}
            unresolved = 0
            for fp in fps:
                ip = mapping.get(fp)
                if not ip:
                    unresolved += 1
                    continue
                code = ip_country.get(ip)
                if code is None:
                    code = self._safe(
                        lambda: c.get_info(f"ip-to-country/{ip}"), "??"
                    ) or "??"
                    code = code.upper()
                    ip_country[ip] = code
                counter[code] += 1

            total = len(fps)
            countries = [
                {
                    "code": code,
                    "name": country_name(code) if code != "??" else "Inconnu",
                    "flag": flag_emoji(code) if code != "??" else "🏴",
                    "count": n,
                    "percent": round(n * 100 / total, 1) if total else 0,
                }
                for code, n in counter.most_common()
            ]
            return {
                "online": True,
                "total": total,
                "resolved": total - unresolved,
                "unresolved": unresolved,
                "countries": countries,
            }

    # -- signaux -------------------------------------------------------------
    def signal(self, sig: str) -> None:
        """Envoie un signal Tor (RELOAD, NEWNYM, …) via le ControlPort."""
        with self._lock:
            c = self._get()
            c.signal(getattr(stem.Signal, sig))


# Instance partagée
tor = TorController()
