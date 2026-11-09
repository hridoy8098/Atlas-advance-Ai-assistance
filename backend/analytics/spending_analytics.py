# backend/analytics/spending_analytics.py — expense tracking (BDT)

import threading

import config
from backend.core.domain_db import init, now, since

_DB = config.DB_ANALYTICS

_SCHEMA = """
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount REAL NOT NULL,
    category TEXT NOT NULL,
    note TEXT,
    ts TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_expenses_ts ON expenses(ts);
"""


class SpendingAnalytics:
    def __init__(self):
        self._lock = threading.Lock()
        self._conn = init(_DB, _SCHEMA)

    def add(self, amount: float, category: str = "general", note: str = None):
        amount = float(amount)
        if amount <= 0:
            raise ValueError("amount must be positive")
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO expenses (amount, category, note, ts) VALUES (?, ?, ?, ?)",
                (amount, str(category), note, now()),
            )
            self._conn.commit()
        return {"expense_id": cur.lastrowid, "amount": amount, "category": category}

    def summary(self, days: int = 30):
        with self._lock:
            total = self._conn.execute(
                "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS count FROM expenses WHERE ts >= ?",
                (since(days),),
            ).fetchone()
            by_cat = self._conn.execute(
                "SELECT category, ROUND(SUM(amount), 2) AS total FROM expenses "
                "WHERE ts >= ? GROUP BY category ORDER BY total DESC",
                (since(days),),
            ).fetchall()
            daily = self._conn.execute(
                "SELECT substr(ts, 1, 10) AS day, ROUND(SUM(amount), 2) AS total "
                "FROM expenses WHERE ts >= ? GROUP BY day ORDER BY day",
                (since(days),),
            ).fetchall()
        return {
            "currency": "BDT",
            "days": days,
            "total": round(total["total"], 2),
            "count": total["count"],
            "average_per_day": round(total["total"] / max(days, 1), 2),
            "by_category": [dict(r) for r in by_cat],
            "daily": [dict(r) for r in daily],
        }


spending_analytics = SpendingAnalytics()
