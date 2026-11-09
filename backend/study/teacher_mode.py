# backend/study/teacher_mode.py — explanations and quizzes in a friendly teacher voice

from backend.core.ai_text import ask, ask_json

_SYSTEM = (
    "You are Atlas, a patient bilingual teacher (Bangla + English). "
    "Explain clearly with a small example, then one check-your-understanding question."
)


class TeacherMode:
    def explain(self, topic: str, level: str = "medium"):
        topic = (topic or "").strip()
        if not topic:
            raise ValueError("topic is required")
        level = level if level in ("beginner", "medium", "advanced") else "medium"
        prompt = f"Explain '{topic}' at {level} level in under 200 words."
        text = ask(prompt, system_prompt=_SYSTEM)
        if not text:
            return {"topic": topic, "level": level, "explanation": "", "available": False}
        return {"topic": topic, "level": level, "explanation": text.strip(), "available": True}

    def quiz(self, topic: str, count: int = 5):
        count = max(1, min(int(count), 15))
        prompt = (
            f"Create {count} short practice questions (with answers) about '{topic}'. "
            'Reply JSON: {"questions":[{"q":"...","a":"..."}]}'
        )
        data = ask_json(prompt, system_prompt=_SYSTEM)
        questions = data.get("questions") if isinstance(data, dict) else None
        return {"topic": topic, "questions": questions or [], "available": bool(questions)}


teacher = TeacherMode()
