# backend/analytics/habit_predictor.py — habit tracking + streak prediction

import threading
from datetime import date, datetime, timedelta

import config
from backend.core.domain_db import init, now, since

_DB = config.DB_ANALYTICS

_SCHEMA = """
CREATE TABLE IF NOT EXISTS habits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS habit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    day TEXT NOT NULL,
    ts TEXT NOT NULL,
    UNIQUE(name, day)
);
CREATE INDEX IF NOT EXISTS idx_habit_logs_name ON habit_logs(name, day);
"""


class HabitPredictor:
    def __init__(self):
        self._lock = threading.Lock()
        self._conn = init(_DB, _SCHEMA)

    def add(self, name: str):
        with self._lock:
            self._conn.execute(
                "INSERT OR IGNORE INTO habits (name, created_at) VALUES (?, ?)", (str(name), now())
            )
            self._conn.commit()
        return {"habit": name, "created": True}

    def log(self, name: str):
        today = date.today().isoformat()
        with self._lock:
            self._conn.execute(
                "INSERT OR IGNORE INTO habits (name, created_at) VALUES (?, ?)", (str(name), now())
            )
            self._conn.execute(
                "INSERT OR IGNORE INTO habit_logs (name, day, ts) VALUES (?, ?, ?)",
                (str(name), today, now()),
            )
            self._conn.commit()
            days = [r["day"] for r in self._conn.execute(
                "SELECT day FROM habit_logs WHERE name = ? ORDER BY day DESC LIMIT 400", (str(name),)
            ).fetchall()]
        streak = self._streak(days)
        return {"habit": name, "logged": True, "streak": streak, "total": len(days)}

    def stats(self):
        with self._lock:
            habits = [r["name"] for r in self._conn.execute("SELECT name FROM habits ORDER BY name").fetchall()]
            rows = self._conn.execute("SELECT name, day FROM habit_logs ORDER BY day DESC").fetchall()
        days_by_habit = {}
        for r in rows:
            days_by_habit.setdefault(r["name"], []).append(r["day"])
        out = []
        for name in habits:
            days = days_by_habit.get(name, [])
            out.append({
                "name": name,
                "streak": self._streak(days),
                "total": len(days),
                "last": days[0] if days else None,
                "completion_7d": round(len([d for d in days if d >= since(7)[:10]]) / 7.0 * 100),
            })
        best = max([h["streak"] for h in out], default=0)
        return {"habits": out, "best_streak": best, "count": len(out)}

    @staticmethod
    def _streak(days):
        if not days:
            return 0
        parsed = sorted({datetime.strptime(d, "%Y-%m-%d").date() for d in days}, reverse=True)
        today = date.today()
        if parsed[0] not in (today, today - timedelta(days=1)):
            return 0
        streak = 1
        for prev, cur in zip(parsed, parsed[1:]):
            if (prev - cur).days == 1:
                streak += 1
            else:
                break
        return streak


habit_predictor = HabitPredictor()
