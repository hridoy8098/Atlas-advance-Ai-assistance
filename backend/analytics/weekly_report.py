# backend/analytics/weekly_report.py — generated weekly summary (no AI call)

from datetime import date, timedelta

import config
from backend.analytics.app_tracker import app_tracker
from backend.analytics.habit_predictor import habit_predictor
from backend.analytics.personal_analytics import personal_analytics
from backend.analytics.spending_analytics import spending_analytics
from backend.analytics.study_analytics import study_analytics


class WeeklyReport:
    def generate(self, days: int = 7):
        overview = personal_analytics.overview(days=days)
        study = study_analytics.stats(days=days)
        habits = habit_predictor.stats()
        spending = spending_analytics.summary(days=days)
        top_apps = app_tracker.usage(days=days)[:5]

        end = date.today()
        start = end - timedelta(days=days - 1)
        lines = [
            f"Productivity {overview['productivity']}/100, focus {overview['focus']}/100.",
            f"Studied {study['total_hours']} hours across {study['sessions']} sessions.",
            f"Best habit streak: {habits['best_streak']} day(s).",
            f"Spent {spending['total']} BDT in {days} day(s).",
        ]
        if top_apps:
            lines.append("Most used app: " + top_apps[0]["app"] + ".")

        return {
            "period": {"start": start.isoformat(), "end": end.isoformat(), "days": days},
            "productivity": overview["productivity"],
            "focus": overview["focus"],
            "study_hours": study["total_hours"],
            "habit_streak": habits["best_streak"],
            "spending_total": spending["total"],
            "top_apps": top_apps,
            "study_by_subject": study["by_subject"],
            "summary": " ".join(lines),
        }


weekly_report = WeeklyReport()
