# backend/analytics/app_tracker.py — app usage tracking

import threading
import time
from datetime import datetime

import config
from backend.core.domain_db import connect, init, now, since

_DB = config.DB_ANALYTICS

_SCHEMA = """
CREATE TABLE IF NOT EXISTS app_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    app TEXT NOT NULL,
    title TEXT,
    minutes REAL NOT NULL DEFAULT 0,
    ts TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_app_usage_ts ON app_usage(ts);
"""


class AppTracker:
    def __init__(self):
        self._lock = threading.Lock()
        self._conn = init(_DB, _SCHEMA)
        self._running = False
        self._started = 0.0
        self._app = ""

    def log(self, app, title=None, minutes=None):
        minutes = float(minutes) if minutes is not None else 1.0
        with self._lock:
            self._conn.execute(
                "INSERT INTO app_usage (app, title, minutes, ts) VALUES (?, ?, ?, ?)",
                (str(app), title, minutes, now()),
            )
            self._conn.commit()
            total = self._conn.execute(
                "SELECT COALESCE(SUM(minutes), 0) FROM app_usage WHERE app = ? AND ts >= ?",
                (str(app), since(1)),
            ).fetchone()[0]
        return {"app": app, "minutes": minutes, "today_minutes": round(total, 1)}

    def usage(self, days: int = 1):
        with self._lock:
            rows = self._conn.execute(
                "SELECT app, ROUND(SUM(minutes), 1) AS minutes, COUNT(*) AS sessions "
                "FROM app_usage WHERE ts >= ? GROUP BY app ORDER BY minutes DESC",
                (since(days),),
            ).fetchall()
        return [dict(r) for r in rows]

    def start(self, app: str):
        self._running = True
        self._app = str(app)
        self._started = time.time()
        return {"tracking": self._app}

    def stop(self):
        if not self._running:
            return {"tracking": None}
        minutes = (time.time() - self._started) / 60.0
        app = self._app
        self._running = False
        self._app = ""
        if minutes >= 0.1:
            self.log(app, minutes=round(minutes, 1))
        return {"tracked": app, "minutes": round(minutes, 1)}

    def is_running(self) -> bool:
        return self._running

    def daily(self, days: int = 7):
        with self._lock:
            rows = self._conn.execute(
                "SELECT substr(ts, 1, 10) AS day, ROUND(SUM(minutes), 1) AS minutes "
                "FROM app_usage WHERE ts >= ? GROUP BY day ORDER BY day",
                (since(days),),
            ).fetchall()
        return [dict(r) for r in rows]


app_tracker = AppTracker()
