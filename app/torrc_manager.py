"""Read the torrc and extract a few common settings.

Writing goes through :func:`app.system_control.save_torrc` (privileged helper
that validates the configuration before installing it).
"""

from __future__ import annotations

from .config import settings

# Directives presented as "quick" fields in the UI.
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
    """Return the raw torrc content (empty string if absent)."""
    try:
        with open(settings.torrc_path, "r", encoding="utf-8") as fh:
            return fh.read()
    except FileNotFoundError:
        return ""
    except PermissionError:
        return "# (Lecture impossible : permissions insuffisantes sur le torrc)"


def parse_quick_values(content: str) -> dict[str, str]:
    """Extract the last value of each "quick" directive."""
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
