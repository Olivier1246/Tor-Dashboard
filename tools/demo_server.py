"""Demo server with realistic MOCK data, only to produce README screenshots.

Not part of the application. Run from the project root:
    .venv/Scripts/python.exe tools/demo_server.py
"""
from __future__ import annotations

import json
import math
import os
import random
import sqlite3
import sys
import time
from pathlib import Path

import pyotp

# Point the config at sample/demo files BEFORE importing the app.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
# Display a realistic path in the UI; the content is read from the sample file
# via a monkeypatch below.
os.environ["TORRC_PATH"] = "/etc/tor/torrc"
os.environ["USERS_FILE"] = str(ROOT / "tools" / "demo_users.json")
os.environ["HISTORY_DB"] = str(ROOT / "tools" / "demo_history.db")
os.environ["SECRET_KEY"] = "demo-secret-key-not-for-production-use-only"

from app.auth import hash_password  # noqa: E402
from app.config import settings  # noqa: E402

DEMO_TOTP = "XKGR62XMKXIKGAGHUM6RMRZOIWUGJP3J"
DEMO_PASS = "Demo1234567"

# --- demo account ----------------------------------------------------------
settings.users_path.write_text(
    json.dumps(
        {"admin": {"password_hash": hash_password(DEMO_PASS), "totp_secret": DEMO_TOTP}},
        indent=2,
    ),
    encoding="utf-8",
)

# --- seed 24h of history ---------------------------------------------------
db = sqlite3.connect(str(settings.history_path))
db.execute(
    """CREATE TABLE IF NOT EXISTS samples (
        ts INTEGER PRIMARY KEY, read_total INTEGER, written_total INTEGER,
        circuits INTEGER, connections INTEGER)"""
)
db.execute("DELETE FROM samples")
now = int(time.time())
read, written = 4_800_000_000, 3_600_000_000
rows = []
for i in range(24 * 60, 0, -1):
    ts = now - i * 60
    base = 9_000_000 + 5_000_000 * math.sin(i / 110)
    dr = int(max(0, base + random.uniform(-1_500_000, 1_500_000))) * 60
    dw = int(dr * 0.72)
    read += dr
    written += dw
    circ = 130 + int(40 * math.sin(i / 80)) + random.randint(0, 12)
    conn = 280 + int(70 * math.sin(i / 60)) + random.randint(0, 25)
    rows.append((ts, read, written, circ, conn))
db.executemany("INSERT OR REPLACE INTO samples VALUES (?,?,?,?,?)", rows)
db.commit()
db.close()

# --- mock the Tor controller -----------------------------------------------
from app import tor_controller  # noqa: E402

_state = {"t": time.time(), "r": float(read), "w": float(written)}


def fake_metrics():
    nowt = time.time()
    dt = nowt - _state["t"]
    _state["t"] = nowt
    rate = 9_000_000 + 5_000_000 * math.sin(nowt / 4) + random.uniform(-1_000_000, 1_000_000)
    _state["r"] += rate * dt
    _state["w"] += rate * 0.72 * dt
    return {
        "online": True,
        "nickname": "NebulaGuard",
        "fingerprint": "A1B2C3D4E5F6A7B8C9D0E1F2A3B4C5D6E7F8A9B0",
        "version": "0.4.9.9",
        "bootstrap": 100,
        "uptime": 18 * 86400 + 7 * 3600 + 42 * 60,
        "read_total": int(_state["r"]),
        "written_total": int(_state["w"]),
        "rate": 12_582_912,
        "burst": 25_165_824,
        "flags": ["Fast", "Guard", "Running", "Stable", "V2Dir", "Valid"],
        "exit_policy": "reject *:*",
        "circuits": 147,
        "connections": 312,
        "accounting": {
            "enabled": True,
            "hibernating": "awake",
            "read_used": 612_000_000_000,
            "written_used": 440_000_000_000,
            "read_left": 388_000_000_000,
            "written_left": 560_000_000_000,
            "interval_end": "2026-07-01 00:00:00",
        },
        "onion": "nebulaguarddashb0ardexampleonionaddrxyz23q.onion",
    }


def fake_connections(max_relays=1500):
    data = [
        ("DE", "Germany", "\U0001F1E9\U0001F1EA", 71),
        ("US", "United States", "\U0001F1FA\U0001F1F8", 54),
        ("FR", "France", "\U0001F1EB\U0001F1F7", 33),
        ("NL", "Netherlands", "\U0001F1F3\U0001F1F1", 28),
        ("FI", "Finland", "\U0001F1EB\U0001F1EE", 19),
        ("GB", "United Kingdom", "\U0001F1EC\U0001F1E7", 16),
        ("SE", "Sweden", "\U0001F1F8\U0001F1EA", 14),
        ("CH", "Switzerland", "\U0001F1E8\U0001F1ED", 11),
        ("CA", "Canada", "\U0001F1E8\U0001F1E6", 9),
        ("RU", "Russia", "\U0001F1F7\U0001F1FA", 7),
    ]
    total = 312
    resolved = sum(c[3] for c in data)
    countries = [
        {"code": c, "name": n, "flag": f, "count": k, "percent": round(k * 100 / total, 1)}
        for c, n, f, k in data
    ]
    return {
        "online": True,
        "total": total,
        "resolved": resolved,
        "unresolved": total - resolved,
        "countries": countries,
    }


tor_controller.tor.get_metrics = fake_metrics
tor_controller.tor.connections_by_country = fake_connections

# main.py imported service_status/service_action into its namespace
import app.main as main  # noqa: E402

main.service_status = lambda: "active"
main.tor.get_metrics = fake_metrics
main.tor.connections_by_country = fake_connections

_sample_torrc = (ROOT / "tools" / "sample_torrc").read_text(encoding="utf-8")
main.read_torrc = lambda: _sample_torrc

if __name__ == "__main__":
    import uvicorn

    print("TOTP now:", pyotp.TOTP(DEMO_TOTP).now())
    uvicorn.run(main.app, host="127.0.0.1", port=8096, log_level="warning")
