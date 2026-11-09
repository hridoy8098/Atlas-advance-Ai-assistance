# backend/analytics/goal_probability.py — goal tracking with success probability

import threading
from datetime import date, datetime

import config
from backend.core.domain_db import init, now

_DB = config.DB_ANALYTICS

_SCHEMA = """
CREATE TABLE IF NOT EXISTS goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    target REAL NOT NULL,
    progress REAL NOT NULL DEFAULT 0,
    deadline TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT
);
"""


class GoalTracker:
    def __init__(self):
        self._lock = threading.Lock()
        self._conn = init(_DB, _SCHEMA)

    def add(self, title: str, target: float, deadline: str = None):
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO goals (title, target, progress, deadline, created_at) VALUES (?, ?, 0, ?, ?)",
                (str(title), float(target), deadline, now()),
            )
            self._conn.commit()
        return {"goal_id": cur.lastrowid, "title": title, "target": float(target), "deadline": deadline}

    def update_progress(self, goal_id: int, progress: float):
        with self._lock:
            row = self._conn.execute("SELECT target FROM goals WHERE id = ?", (goal_id,)).fetchone()
            if row is None:
                raise ValueError(f"goal {goal_id} not found")
            self._conn.execute(
                "UPDATE goals SET progress = ?, updated_at = ? WHERE id = ?", (float(progress), now(), goal_id)
            )
            self._conn.commit()
        percent = round(min(100.0, progress / row["target"] * 100), 1) if row["target"] else 0.0
        return {"goal_id": goal_id, "progress": progress, "percent": percent}

    def estimate(self, goal_id: int):
        with self._lock:
            row = self._conn.execute(
                "SELECT title, target, progress, deadline, created_at FROM goals WHERE id = ?", (goal_id,)
            ).fetchone()
        if row is None:
            raise ValueError(f"goal {goal_id} not found")
        target = max(row["target"], 0.001)
        done = min(row["progress"] / target, 1.0)
        if not row["deadline"]:
            return {"goal_id": goal_id, "title": row["title"], "percent": round(done * 100, 1), "probability": None}
        try:
            deadline = datetime.strptime(str(row["deadline"])[:10], "%Y-%m-%d").date()
            created = datetime.fromisoformat(row["created_at"]).date()
        except ValueError:
            return {"goal_id": goal_id, "title": row["title"], "percent": round(done * 100, 1), "probability": None}
        total_days = max((deadline - created).days, 1)
        elapsed = max((date.today() - created).days, 0)
        expected = min(1.0, elapsed / total_days)
        if elapsed >= total_days:
            probability = round(done * 100)
        else:
            pace = (done - expected) / max(1 - expected, 0.1)
            probability = round(max(0.0, min(1.0, 0.5 + pace * 0.5)) * 100)
        return {
            "goal_id": goal_id,
            "title": row["title"],
            "percent": round(done * 100, 1),
            "days_left": max((deadline - date.today()).days, 0),
            "probability": probability,
        }

    def list(self):
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, title, target, progress, deadline FROM goals ORDER BY id DESC"
            ).fetchall()
        return [dict(r) for r in rows]


goal_tracker = GoalTracker()
