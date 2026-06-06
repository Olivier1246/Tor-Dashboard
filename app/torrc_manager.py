"""Read the torrc and extract a few common settings.

Writing goes through :func:`app.system_control.save_torrc` (privileged helper
that validates the configuration before installing it).
"""

from __future__ import annotations

from .config import settings

# Directives presented as "quick" fields in the UI.
QUICK_KEYS = [
    ("Nickname", "Relay name"),
    ("ContactInfo", "Contact (email)"),
    ("ORPort", "OR port"),
    ("RelayBandwidthRate", "Average rate (e.g. 10 MBytes)"),
    ("RelayBandwidthBurst", "Burst rate (e.g. 20 MBytes)"),
    ("AccountingMax", "Traffic quota (e.g. 1 TBytes)"),
    ("AccountingStart", "Period start (e.g. month 1 00:00)"),
    ("ExitRelay", "Exit relay (0/1)"),
]


def read_torrc() -> str:
    """Return the raw torrc content (empty string if absent)."""
    try:
        with open(settings.torrc_path, "r", encoding="utf-8") as fh:
            return fh.read()
    except FileNotFoundError:
        return ""
    except PermissionError:
        return "# (Cannot read: insufficient permissions on the torrc)"


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
