# backend/analytics/productivity_score.py — 0-100 productivity from real usage data

import config
from backend.core.domain_db import clamp, connect, since

_DB = config.DB_ANALYTICS
_DISTRACTIONS = ("youtube", "facebook", "instagram", "tiktok", "netflix", "discord", "twitter", "reddit")


def _sum(conn, sql, params):
    try:
        row = conn.execute(sql, params).fetchone()
        return float(row[0] or 0)
    except Exception:
        return 0.0


class ProductivityScore:
    def __init__(self):
        self._conn = connect(_DB)

    def score(self, days: int = 7):
        start = since(days)
        study_min = _sum(self._conn, "SELECT SUM(minutes) FROM study_sessions WHERE ts >= ?", (start,))
        usage = self._conn.execute(
            "SELECT app, SUM(minutes) AS m FROM app_usage WHERE ts >= ? GROUP BY app", (start,)
        ).fetchall() if self._table_exists("app_usage") else []
        distraction = sum(float(r["m"]) for r in usage if any(d in str(r["app"]).lower() for d in _DISTRACTIONS))
        habit_days = _sum(self._conn, "SELECT COUNT(DISTINCT name || day) FROM habit_logs WHERE ts >= ?", (start,))

        study_component = clamp(study_min / (days * 120.0) * 60)
        distraction_component = clamp(40 - distraction / (days * 240.0) * 40)
        habit_component = clamp(habit_days / max(days * 2.0, 1) * 20)
        total = round(clamp(study_component + distraction_component * 0.5 + habit_component))
        return {
            "score": total,
            "study_component": round(study_component),
            "distraction_component": round(distraction_component),
            "habit_component": round(habit_component),
            "study_hours": round(study_min / 60.0, 2),
            "distraction_minutes": round(distraction, 1),
        }

    def _table_exists(self, name):
        try:
            return bool(self._conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
            ).fetchone())
        except Exception:
            return False


productivity_score = ProductivityScore()
