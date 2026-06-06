"""Contrôle du service Tor et écriture du torrc via un helper privilégié.

Le dashboard tourne en utilisateur non privilégié (ex. ``tordash``). Toutes
les opérations sensibles passent par un unique binaire racine
(``tor-dashboard-helper``) autorisé sans mot de passe dans sudoers. Cela
garde la surface d'attaque minimale : aucune commande arbitraire n'est
exécutée en root.
"""

from __future__ import annotations

import subprocess

from .config import settings

_VALID_ACTIONS = {"start", "stop", "restart", "reload", "status"}


class HelperError(RuntimeError):
    """Erreur renvoyée par le helper privilégié."""


def _run(args: list[str], input_data: str | None = None) -> str:
    proc = subprocess.run(
        ["sudo", "-n", settings.helper_path, *args],
        input=input_data,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode != 0:
        msg = (proc.stderr or proc.stdout or "").strip()
        raise HelperError(msg or f"helper a échoué (code {proc.returncode})")
    return proc.stdout.strip()


def service_action(action: str) -> str:
    """Exécute start/stop/restart/reload sur l'unité systemd de Tor."""
    if action not in _VALID_ACTIONS:
        raise ValueError(f"action invalide : {action}")
    return _run([action])


def service_status() -> str:
    """Renvoie l'état systemd brut : active / inactive / failed / ..."""
    try:
        return _run(["status"]) or "unknown"
    except HelperError as exc:
        # ``systemctl is-active`` renvoie un code != 0 quand inactif
        text = str(exc).strip().lower()
        return text or "inactive"


def save_torrc(content: str) -> None:
    """Valide puis installe un nouveau torrc (via ``tor --verify-config``)."""
    # Normalise les fins de ligne en \n
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    _run(["savetorrc"], input_data=normalized)
