# backend/analytics/study_analytics.py — study session logging and stats

import threading

import config
from backend.core.domain_db import init, now, since

_DB = config.DB_ANALYTICS

_SCHEMA = """
CREATE TABLE IF NOT EXISTS study_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL,
    minutes REAL NOT NULL,
    notes TEXT,
    ts TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_study_sessions_ts ON study_sessions(ts);
"""


class StudyAnalytics:
    def __init__(self):
        self._lock = threading.Lock()
        self._conn = init(_DB, _SCHEMA)

    def log_session(self, subject: str, minutes: float, notes: str = None):
        minutes = float(minutes)
        with self._lock:
            self._conn.execute(
                "INSERT INTO study_sessions (subject, minutes, notes, ts) VALUES (?, ?, ?, ?)",
                (str(subject), minutes, notes, now()),
            )
            self._conn.commit()
            today = self._conn.execute(
                "SELECT COALESCE(SUM(minutes), 0) FROM study_sessions WHERE ts >= ?",
                (since(1),),
            ).fetchone()[0]
        return {
            "subject": subject,
            "minutes": minutes,
            "today_minutes": round(today, 1),
            "today_hours": round(today / 60.0, 2),
        }

    def stats(self, days: int = 7):
        with self._lock:
            total = self._conn.execute(
                "SELECT COALESCE(SUM(minutes), 0) AS m, COUNT(*) AS c FROM study_sessions WHERE ts >= ?",
                (since(days),),
            ).fetchone()
            by_subject = self._conn.execute(
                "SELECT subject, ROUND(SUM(minutes), 1) AS minutes FROM study_sessions "
                "WHERE ts >= ? GROUP BY subject ORDER BY minutes DESC",
                (since(days),),
            ).fetchall()
            daily = self._conn.execute(
                "SELECT substr(ts, 1, 10) AS day, ROUND(SUM(minutes), 1) AS minutes "
                "FROM study_sessions WHERE ts >= ? GROUP BY day ORDER BY day",
                (since(days),),
            ).fetchall()
        return {
            "days": days,
            "total_minutes": round(total["m"], 1),
            "total_hours": round(total["m"] / 60.0, 2),
            "sessions": total["c"],
            "by_subject": [dict(r) for r in by_subject],
            "daily": [dict(r) for r in daily],
        }


study_analytics = StudyAnalytics()
