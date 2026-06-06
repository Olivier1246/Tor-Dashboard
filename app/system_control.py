"""Control the Tor service and write the torrc through a privileged helper.

The dashboard runs as an unprivileged user (e.g. ``tordash``). All sensitive
operations go through a single root binary (``tor-dashboard-helper``) allowed
without a password in sudoers. This keeps the attack surface minimal: no
arbitrary command is ever executed as root.
"""

from __future__ import annotations

import subprocess

from .config import settings

_VALID_ACTIONS = {"start", "stop", "restart", "reload", "status"}


class HelperError(RuntimeError):
    """Error returned by the privileged helper."""


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
        raise HelperError(msg or f"helper failed (code {proc.returncode})")
    return proc.stdout.strip()


def service_action(action: str) -> str:
    """Run start/stop/restart/reload on Tor's systemd unit."""
    if action not in _VALID_ACTIONS:
        raise ValueError(f"invalid action: {action}")
    return _run([action])


def service_status() -> str:
    """Return the raw systemd state: active / inactive / failed / ..."""
    try:
        return _run(["status"]) or "unknown"
    except HelperError as exc:
        # ``systemctl is-active`` returns a non-zero code when inactive
        text = str(exc).strip().lower()
        return text or "inactive"


def save_torrc(content: str) -> None:
    """Validate then install a new torrc (via ``tor --verify-config``)."""
    # Normalize line endings to \n
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    _run(["savetorrc"], input_data=normalized)
