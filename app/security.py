"""DoS-mitigation counters parsed from Tor's periodic 'Heartbeat' log lines.

These counters (circuits killed, connections rejected, ...) are emitted at
NOTICE level in the heartbeat, NOT exposed via the control port, so we read
them from journald. The dashboard process must be allowed to read the unit's
journal (systemd-journal supplementary group).
"""

from __future__ import annotations

import re
import subprocess
import threading
import time

from .config import settings

_CACHE_TTL = 60  # seconds
_lock = threading.Lock()
_cache: dict = {"ts": 0.0, "data": None}

_DOS_RE = re.compile(r"DoS mitigation since startup:\s*(.+?)\.?\s*$")
_NUM_RE = re.compile(r"^(\d+)\s+(.*)$")


def _journal_text(unit: str, lines: int = 1500) -> str:
    proc = subprocess.run(
        ["journalctl", "-u", f"{unit}.service", "--no-pager", "-o", "cat",
         "-n", str(lines)],
        capture_output=True,
        text=True,
        timeout=20,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or "journalctl failed").strip())
    return proc.stdout


def _parse_dos(segment: str) -> dict[str, int]:
    """Parse '0 circuits killed..., 1 connections rejected, ...' into a dict."""
    stats: dict[str, int] = {}
    for part in segment.split(","):
        part = part.strip().rstrip(".")
        m = _NUM_RE.match(part)
        if m:
            stats[m.group(2).strip()] = int(m.group(1))
    return stats


def _compute(unit: str) -> dict:
    text = _journal_text(unit)
    for line in reversed(text.splitlines()):
        m = _DOS_RE.search(line)
        if m:
            return {"available": True, "dos": _parse_dos(m.group(1))}
    # journal readable but no heartbeat line yet
    return {"available": True, "dos": {}}


def get_dos_stats() -> dict:
    """Return the latest DoS-mitigation counters (cached ~60 s)."""
    now = time.time()
    with _lock:
        if _cache["data"] is not None and now - _cache["ts"] < _CACHE_TTL:
            return _cache["data"]
    try:
        data = _compute(settings.tor_service)
    except Exception as exc:
        data = {"available": False, "error": str(exc), "dos": {}}
    with _lock:
        _cache["ts"] = now
        _cache["data"] = data
    return data
