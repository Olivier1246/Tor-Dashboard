"""Lecture du torrc et extraction de quelques réglages courants.

L'écriture passe par :func:`app.system_control.save_torrc` (helper privilégié
qui valide la configuration avant de l'installer).
"""

from __future__ import annotations

from .config import settings

# Directives présentées comme champs « rapides » dans l'UI.
QUICK_KEYS = [
    ("Nickname", "Nom du relais"),
    ("ContactInfo", "Contact (email)"),
    ("ORPort", "Port OR"),
    ("RelayBandwidthRate", "Débit moyen (ex. 10 MBytes)"),
    ("RelayBandwidthBurst", "Débit en rafale (ex. 20 MBytes)"),
    ("AccountingMax", "Quota de trafic (ex. 1 TBytes)"),
    ("AccountingStart", "Début de période (ex. month 1 00:00)"),
    ("ExitRelay", "Relais de sortie (0/1)"),
]


def read_torrc() -> str:
    """Renvoie le contenu brut du torrc (chaîne vide si absent)."""
    try:
        with open(settings.torrc_path, "r", encoding="utf-8") as fh:
            return fh.read()
    except FileNotFoundError:
        return ""
    except PermissionError:
        return "# (Lecture impossible : permissions insuffisantes sur le torrc)"


def parse_quick_values(content: str) -> dict[str, str]:
    """Extrait la dernière valeur de chaque directive « rapide »."""
    keys = {k.lower(): k for k, _ in QUICK_KEYS}
    values: dict[str, str] = {}
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if not parts:
            continue
        key = parts[0].lower()
        if key in keys:
            values[keys[key]] = parts[1].strip() if len(parts) > 1 else ""
    return values
