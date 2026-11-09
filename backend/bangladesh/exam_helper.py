# backend/bangladesh/exam_helper.py — BCS / admission / school exam help

from backend.core.ai_text import ask

_SYSTEM = (
    "You help Bangladeshi students with BCS, university admission and school exams. "
    "Answer in Bangla unless the user writes English. Be accurate and concise."
)


class ExamHelper:
    def ask(self, question: str):
        question = (question or "").strip()
        if not question:
            raise ValueError("question required")
        answer = ask(question, system_prompt=_SYSTEM)
        return {"question": question, "answer": answer.strip() if answer else "", "available": bool(answer)}

    def tips(self, exam: str = "BCS"):
        exam = (exam or "BCS").strip()
        prompt = (
            f"Give 6 short, practical preparation tips for the {exam} exam in Bangladesh: "
            "syllabus coverage, time management, practice, and revision."
        )
        text = ask(prompt, system_prompt=_SYSTEM)
        return {"exam": exam, "tips": text.strip(), "available": bool(text)}


exam_helper = ExamHelper()
