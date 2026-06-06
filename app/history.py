"""Historique persistant des métriques (SQLite).

On enregistre périodiquement les compteurs cumulés de trafic ; les débits
sont recalculés à la lecture à partir des deltas entre échantillons. Stocker
les compteurs bruts (plutôt que les débits) permet de rester juste même en
cas de redémarrage de Tor (remise à zéro des compteurs → on coupe la courbe).
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

    # -- écriture ------------------------------------------------------------
    def add(self, m: dict[str, Any]) -> None:
        """Enregistre un échantillon si le relais est en ligne."""
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

    # -- lecture -------------------------------------------------------------
    def series(self, seconds: int, max_points: int = 400) -> list[dict[str, Any]]:
        """Renvoie les débits (octets/s) sur la fenêtre demandée.

        ``down``/``up`` valent ``None`` quand un delta est négatif (compteur
        remis à zéro par un redémarrage de Tor) : la courbe est alors coupée.
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


# Instance partagée
history = History(settings.history_path)
