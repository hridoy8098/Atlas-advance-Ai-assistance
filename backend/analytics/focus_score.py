# backend/analytics/focus_score.py — focus/deep-work score from study vs distraction

import config
from backend.core.domain_db import clamp, connect, since

_DB = config.DB_ANALYTICS
_DISTRACTIONS = ("youtube", "facebook", "instagram", "tiktok", "netflix", "discord", "twitter", "reddit")


class FocusScore:
    def __init__(self):
        self._conn = connect(_DB)

    def score(self, days: int = 1):
        start = since(days)
        try:
            study_min = float(self._conn.execute(
                "SELECT COALESCE(SUM(minutes), 0) FROM study_sessions WHERE ts >= ?", (start,)
            ).fetchone()[0])
        except Exception:
            study_min = 0.0
        try:
            rows = self._conn.execute(
                "SELECT app, SUM(minutes) AS m FROM app_usage WHERE ts >= ? GROUP BY app", (start,)
            ).fetchall()
        except Exception:
            rows = []
        distraction = sum(float(r["m"]) for r in rows if any(d in str(r["app"]).lower() for d in _DISTRACTIONS))
        focused = sum(float(r["m"]) for r in rows) - distraction
        denom = study_min + distraction + focused
        if denom <= 0:
            return {"score": 0, "deep_minutes": 0.0, "distraction_minutes": 0.0, "focused_minutes": 0.0}
        score = round(clamp((study_min + focused * 0.6) / denom * 100))
        return {
            "score": score,
            "deep_minutes": round(study_min, 1),
            "focused_minutes": round(max(focused, 0), 1),
            "distraction_minutes": round(distraction, 1),
        }


focus_score = FocusScore()
