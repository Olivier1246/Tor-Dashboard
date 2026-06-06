"""Persistent metrics history (SQLite).

Cumulative traffic counters are recorded periodically; rates are recomputed at
read time from the deltas between samples. Storing the raw counters (rather
than the rates) keeps things correct even when Tor restarts (the counters
reset -> we break the curve).
"""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from .config import settings


class History:
    def __init__(self, path: Path) -> None:
        self.path = str(path)
        self._lock = threading.Lock()
        self._init()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._conn() as c:
            c.execute(
                """CREATE TABLE IF NOT EXISTS samples (
                    ts            INTEGER PRIMARY KEY,
                    read_total    INTEGER,
                    written_total INTEGER,
                    circuits      INTEGER,
                    connections   INTEGER
                )"""
            )

    # -- writing -------------------------------------------------------------
    def add(self, m: dict[str, Any]) -> None:
        """Record a sample if the relay is online."""
        if not m.get("online"):
            return
        if m.get("read_total") is None or m.get("written_total") is None:
            return
        ts = int(time.time())
        with self._lock, self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO samples VALUES (?,?,?,?,?)",
                (
                    ts,
                    int(m["read_total"]),
                    int(m["written_total"]),
                    m.get("circuits"),
                    m.get("connections"),
                ),
            )

    def prune(self, max_age_seconds: int) -> None:
        cutoff = int(time.time()) - max_age_seconds
        with self._lock, self._conn() as c:
            c.execute("DELETE FROM samples WHERE ts < ?", (cutoff,))

    # -- reading -------------------------------------------------------------
    def series(self, seconds: int, max_points: int = 400) -> list[dict[str, Any]]:
        """Return the rates (bytes/s) over the requested window.

        ``down``/``up`` are ``None`` when a delta is negative (counter reset by
        a Tor restart): the curve is then broken at that point.
        """
        cutoff = int(time.time()) - seconds
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM samples WHERE ts >= ? ORDER BY ts", (cutoff,)
            ).fetchall()

        points: list[dict[str, Any]] = []
        prev: sqlite3.Row | None = None
        for r in rows:
            if prev is not None:
                dt = r["ts"] - prev["ts"]
                if dt > 0:
                    dr = r["read_total"] - prev["read_total"]
                    dw = r["written_total"] - prev["written_total"]
                    points.append(
                        {
                            "t": r["ts"],
                            "down": dr / dt if dr >= 0 else None,
                            "up": dw / dt if dw >= 0 else None,
                            "circuits": r["circuits"],
                            "connections": r["connections"],
                        }
                    )
            prev = r

        return self._downsample(points, max_points)

    @staticmethod
    def _downsample(points: list[dict], max_points: int) -> list[dict]:
        n = len(points)
        if n <= max_points:
            return points
        bucket = (n + max_points - 1) // max_points
        out: list[dict] = []
        for i in range(0, n, bucket):
            chunk = points[i : i + bucket]
            out.append(
                {
                    "t": chunk[len(chunk) // 2]["t"],
                    "down": _avg(c["down"] for c in chunk),
                    "up": _avg(c["up"] for c in chunk),
                    "circuits": _avg(c["circuits"] for c in chunk),
                    "connections": _avg(c["connections"] for c in chunk),
                }
            )
        return out


def _avg(values) -> float | None:
    nums = [v for v in values if v is not None]
    return sum(nums) / len(nums) if nums else None


# Shared instance
history = History(settings.history_path)
