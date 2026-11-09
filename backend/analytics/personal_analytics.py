# backend/analytics/personal_analytics.py — combined overview for the dashboards

from datetime import date, timedelta

import config
from backend.core.domain_db import clamp, connect, since
from backend.analytics.focus_score import focus_score
from backend.analytics.habit_predictor import habit_predictor
from backend.analytics.productivity_score import productivity_score
from backend.analytics.study_analytics import study_analytics

_DB = config.DB_ANALYTICS
_DISTRACTIONS = ("youtube", "facebook", "instagram", "tiktok", "netflix", "discord", "twitter", "reddit")


class PersonalAnalytics:
    def __init__(self):
        self._conn = connect(_DB)

    def overview(self, days: int = 7):
        study = study_analytics.stats(days=days)
        habits = habit_predictor.stats()
        prod = productivity_score.score(days=days)
        focus = focus_score.score(days=days)
        return {
            "days": days,
            "productivity": prod["score"],
            "focus": focus["score"],
            "study_hours": study["total_hours"],
            "habit_streak": habits["best_streak"],
            "series": self._series(days),
            "study_by_subject": study["by_subject"],
        }

    def _series(self, days: int):
        per_day_study = self._per_day("study_sessions", days)
        per_day_apps = self._per_day_apps(days)
        out = []
        today = date.today()
        for offset in range(days - 1, -1, -1):
            day = today - timedelta(days=offset)
            key = day.isoformat()
            study = per_day_study.get(key, 0.0)
            distraction = per_day_apps.get(key, 0.0)
            if study <= 0 and distraction <= 0:
                prod = focus = 0
            else:
                prod = round(clamp(study / 120.0 * 70 + (1 - min(distraction / 240.0, 1)) * 30))
                focus = round(clamp(study / (study + distraction + 1) * 100))
            out.append({"name": day.strftime("%a"), "date": key, "productivity": prod, "focus": focus})
        return out

    def _per_day(self, table: str, days: int):
        try:
            rows = self._conn.execute(
                f"SELECT substr(ts, 1, 10) AS day, SUM(minutes) AS m FROM {table} "
                "WHERE ts >= ? GROUP BY day",
                (since(days),),
            ).fetchall()
            return {r["day"]: float(r["m"] or 0) for r in rows}
        except Exception:
            return {}

    def _per_day_apps(self, days: int):
        try:
            rows = self._conn.execute(
                "SELECT substr(ts, 1, 10) AS day, app, SUM(minutes) AS m FROM app_usage "
                "WHERE ts >= ? GROUP BY day, app",
                (since(days),),
            ).fetchall()
        except Exception:
            return {}
        out = {}
        for r in rows:
            if any(d in str(r["app"]).lower() for d in _DISTRACTIONS):
                out[r["day"]] = out.get(r["day"], 0.0) + float(r["m"] or 0)
        return out


personal_analytics = PersonalAnalytics()
