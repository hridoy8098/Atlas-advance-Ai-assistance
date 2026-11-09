# backend/study/exam_prep.py — study plan + AI quiz

from datetime import date, datetime, timedelta

from backend.core.ai_text import ask_json

_PHASES = [
    ("Learn core concepts", 0.35),
    ("Practice problems", 0.3),
    ("Mock test", 0.2),
    ("Revision", 0.15),
]


class ExamPrep:
    def plan(self, subject: str, exam_date: str = None, hours_per_day: float = 2.0):
        subject = (subject or "General").strip()
        hours_per_day = max(0.5, float(hours_per_day or 2))
        target = self._parse_date(exam_date) or (date.today() + timedelta(days=14))
        days_left = max((target - date.today()).days, 1)
        plan_days = min(days_left, 14)

        schedule = []
        for offset in range(plan_days):
            ratio = offset / max(plan_days - 1, 1)
            if ratio < 0.35:
                phase = _PHASES[0]
            elif ratio < 0.65:
                phase = _PHASES[1]
            elif ratio < 0.85:
                phase = _PHASES[2]
            else:
                phase = _PHASES[3]
            day = date.today() + timedelta(days=offset)
            schedule.append({
                "date": day.isoformat(),
                "day": day.strftime("%a"),
                "focus": phase[0],
                "hours": round(hours_per_day * phase[1] * 1.8, 1),
            })

        return {
            "subject": subject,
            "exam_date": target.isoformat(),
            "days_left": days_left,
            "hours_per_day": hours_per_day,
            "schedule": schedule,
            "advice": "Start with weak topics, test yourself daily, and sleep before the exam.",
        }

    def quiz(self, subject: str, count: int = 5, level: str = "medium"):
        count = max(1, min(int(count), 15))
        prompt = (
            f"Create {count} {level} multiple-choice questions on '{subject}'. "
            'Reply JSON only: {"questions":[{"q":"...","options":["a","b","c","d"],"answer":0}]} '
            "where answer is the index of the correct option."
        )
        data = ask_json(prompt, system_prompt="You write exam questions. Reply with JSON only.")
        questions = data.get("questions") if isinstance(data, dict) else None
        if not questions:
            return {"subject": subject, "questions": [], "message": "AI quiz unavailable right now"}
        return {"subject": subject, "questions": questions}

    @staticmethod
    def _parse_date(value):
        if not value:
            return None
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(str(value)[:10], fmt).date()
            except ValueError:
                continue
        return None


exam_prep = ExamPrep()
