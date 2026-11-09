# backend/agent/exam_coach_agent.py — Exam Prep Coach Agent
# Study plans, AI quizzes with weak-topic tracking, flashcards and spaced repetition.
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List

from backend.study.exam_prep import exam_prep
from backend.study.flashcard import flashcards
from backend.study.spaced_repetition import spaced_repetition
from .advanced_common import (
    ask_json,
    clean_text,
    data_file,
    extract_after,
    fail,
    ok,
    read_json,
    write_json,
)

STATE_FILE = data_file("exam_coach.json")


class ExamCoachAgent:
    name = "Exam Prep Coach Agent"

    def get_capabilities(self) -> List[str]:
        return [
            "exam_plan", "exam_quiz", "exam_flashcards", "exam_due",
            "exam_review", "exam_weak_topics", "exam_mock_test",
        ]

    def handle(self, intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        entities = entities or {}
        command = str(entities.get("_command", ""))
        intent_lower = str(intent or "").lower()
        lower = command.lower()

        try:
            if "review" in intent_lower or "review" in lower:
                card_id = int(entities.get("card_id") or self._first_int(command) or 0)
                quality = int(entities.get("quality") or 4)
                return self.review_card(card_id, quality)
            if "due" in intent_lower or "due" in lower:
                return self.due_cards(int(entities.get("limit") or 20))
            if "flashcard" in intent_lower or "flashcard" in lower or "কার্ড" in command:
                return self.make_flashcards(
                    self._subject(command, entities),
                    int(entities.get("count") or 8),
                )
            if "weak" in intent_lower or "weak" in lower or "দুর্বল" in command:
                return self.weak_topics(self._subject(command, entities))
            if "plan" in intent_lower or "plan" in lower or "রুটিন" in command:
                return self.plan(
                    self._subject(command, entities),
                    str(entities.get("exam_date") or self._exam_date(command) or ""),
                    float(entities.get("hours_per_day") or 2),
                )
            if "grade" in intent_lower or "answer" in intent_lower:
                return self.grade(entities.get("answers") or [])
            return self.quiz(
                self._subject(command, entities),
                int(entities.get("count") or 5),
                str(entities.get("level") or "medium"),
                bool(entities.get("show_answers")),
            )
        except Exception as exc:
            return fail("exam_coach", f"Exam Coach error: {exc}")

    # ---------------- plan ----------------
    def plan(self, subject: str, exam_date: str = "", hours_per_day: float = 2.0) -> Dict[str, Any]:
        subject = clean_text(subject) or "General"
        result = exam_prep.plan(subject, exam_date or None, hours_per_day)
        state = read_json(STATE_FILE, {"plans": [], "results": [], "last_quiz": None})
        state.setdefault("plans", []).append({"ts": datetime.now().isoformat(timespec="seconds"), **result})
        state["plans"] = state["plans"][-20:]
        write_json(STATE_FILE, state)
        return ok(
            "exam_coach",
            f"📚 {subject}-এর {result['days_left']} দিনের study plan তৈরি হয়েছে।",
            plan=result,
        )

    # ---------------- quiz ----------------
    def quiz(self, subject: str, count: int = 5, level: str = "medium", show_answers: bool = False) -> Dict[str, Any]:
        subject = clean_text(subject) or "General Knowledge"
        count = max(1, min(int(count), 15))
        data = ask_json(
            f"Create {count} {level} multiple-choice questions on '{subject}' for exam practice. "
            'Reply JSON only: {"questions":[{"q":"...","options":["a","b","c","d"],"answer":0,"topic":"..."}]} '
            "where answer is the zero-based index of the correct option.",
            system_prompt="You are an exam question writer. Reply with JSON only.",
            fallback=None,
        )
        questions = (data or {}).get("questions") if isinstance(data, dict) else None
        if not questions:
            return fail("exam_coach", "AI quiz এখন তৈরি করা যাচ্ছে না। একটু পরে আবার চেষ্টা করুন।", subject=subject)

        cleaned = []
        for item in questions[:count]:
            options = [str(option) for option in (item.get("options") or [])][:4]
            if len(options) < 2 or not item.get("q"):
                continue
            try:
                answer = int(item.get("answer", 0))
            except Exception:
                answer = 0
            answer = max(0, min(answer, len(options) - 1))
            cleaned.append({
                "q": clean_text(item.get("q")),
                "options": options,
                "answer": answer,
                "topic": clean_text(item.get("topic") or subject),
            })
        if not cleaned:
            return fail("exam_coach", "AI quiz format ঠিক ছিল না; আবার চেষ্টা করুন।")

        state = read_json(STATE_FILE, {"plans": [], "results": [], "last_quiz": None})
        state["last_quiz"] = {
            "subject": subject,
            "ts": datetime.now().isoformat(timespec="seconds"),
            "questions": cleaned,
        }
        write_json(STATE_FILE, state)

        public = [
            {"q": item["q"], "options": item["options"], **({"answer": item["answer"]} if show_answers else {})}
            for item in cleaned
        ]
        return ok(
            "exam_coach",
            f"📝 {len(public)} question-এর {subject} quiz তৈরি। উত্তর জমা দিলে grade করব।",
            subject=subject,
            questions=public,
            show_answers=show_answers,
            grade_hint="answers=[1,0,2,...] পাঠান।",
        )

    def grade(self, answers: List[Any]) -> Dict[str, Any]:
        state = read_json(STATE_FILE, {"plans": [], "results": [], "last_quiz": None})
        quiz = state.get("last_quiz") or {}
        questions = quiz.get("questions") or []
        if not questions:
            return fail("exam_coach", "Grade করার জন্য আগে quiz তৈরি করুন।")
        if not isinstance(answers, list) or len(answers) != len(questions):
            return fail("exam_coach", f"{len(questions)}টি উত্তর দরকার (answers list)।")

        correct = 0
        wrong_topics: List[str] = []
        detail = []
        for index, (question, given) in enumerate(zip(questions, answers)):
            try:
                picked = int(given)
            except Exception:
                picked = -1
            is_correct = picked == question["answer"]
            correct += int(is_correct)
            if not is_correct:
                wrong_topics.append(question.get("topic") or quiz.get("subject") or "general")
            detail.append({
                "question": question["q"],
                "your_answer": picked,
                "correct_answer": question["answer"],
                "correct": is_correct,
                "topic": question.get("topic"),
            })

        total = len(questions)
        score = round(correct / total * 100, 1)
        result = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "subject": quiz.get("subject"),
            "correct": correct,
            "total": total,
            "score": score,
            "weak_topics": sorted(set(wrong_topics)),
        }
        state.setdefault("results", []).append(result)
        state["results"] = state["results"][-50:]
        write_json(STATE_FILE, state)

        return ok(
            "exam_coach",
            f"🎯 Score: {correct}/{total} ({score}%).",
            result=result,
            detail=detail,
            advice=(
                "দুর্বল topic: " + ", ".join(result["weak_topics"]) + "। ওগুলো নিয়ে flashcards বানান।"
                if result["weak_topics"] else "চমৎকার — সব সঠিক! এখন spaced repetition চালিয়ে যান।"
            ),
        )

    # ---------------- flashcards ----------------
    def make_flashcards(self, subject: str, count: int = 8) -> Dict[str, Any]:
        subject = clean_text(subject) or "General"
        count = max(1, min(int(count), 20))
        data = ask_json(
            f"Create {count} high-quality study flashcards on '{subject}'. "
            'Reply JSON only: {"cards":[{"question":"...","answer":"..."}]}',
            system_prompt="You are an expert tutor. Reply with JSON only.",
            fallback=None,
        )
        cards = (data or {}).get("cards") if isinstance(data, dict) else None
        if not cards:
            return fail("exam_coach", "Flashcard তৈরি করা যায়নি (AI unavailable)।", subject=subject)

        added = []
        for card in cards[:count]:
            question = clean_text(card.get("question"))
            answer = clean_text(card.get("answer"))
            if question and answer:
                added.append(flashcards.add(question, answer, deck=subject))
        return ok(
            "exam_coach",
            f"🃏 {len(added)}টি flashcard যোগ হয়েছে (deck: {subject}).",
            cards=added,
            deck=subject,
            due_hint="“due cards” বললে আজকের কার্ড দেখাব।",
        )

    def due_cards(self, limit: int = 20) -> Dict[str, Any]:
        due = spaced_repetition.due(limit=max(1, min(limit, 50)))
        stats = spaced_repetition.stats()
        return ok("exam_coach", f"🃏 {len(due)}টি card আজ due.", cards=due, stats=stats)

    def review_card(self, card_id: int, quality: int = 4) -> Dict[str, Any]:
        if not card_id:
            return fail("exam_coach", "card_id দিন (due list থেকে)।")
        result = spaced_repetition.review(card_id, quality)
        return ok("exam_coach", f"✅ Card {card_id} reviewed (quality {quality}).", review=result)

    # ---------------- weak topics ----------------
    def weak_topics(self, subject: str = "") -> Dict[str, Any]:
        state = read_json(STATE_FILE, {"plans": [], "results": [], "last_quiz": None})
        results = state.get("results") or []
        if subject:
            results = [item for item in results if (item.get("subject") or "").lower() == subject.lower()]
        if not results:
            return ok("exam_coach", "এখনো কোনো quiz result নেই; আগে একটি quiz দিন।", weak_topics=[])

        counts: Dict[str, int] = {}
        total_correct = total_questions = 0
        for item in results:
            total_correct += int(item.get("correct") or 0)
            total_questions += int(item.get("total") or 0)
            for topic in item.get("weak_topics") or []:
                counts[topic] = counts.get(topic, 0) + 1

        ranked = sorted(counts.items(), key=lambda pair: pair[1], reverse=True)[:8]
        return ok(
            "exam_coach",
            f"📉 Weak areas: {', '.join(topic for topic, _ in ranked) or 'none'}",
            weak_topics=[{"topic": topic, "misses": miss} for topic, miss in ranked],
            average_score=round(total_correct / max(total_questions, 1) * 100, 1),
            attempts=len(results),
        )

    def test(self) -> Dict[str, Any]:
        state = read_json(STATE_FILE, {"plans": [], "results": [], "last_quiz": None})
        srs = spaced_repetition.stats()
        return {
            "success": True,
            "agent": "exam_coach",
            "plans": len(state.get("plans") or []),
            "attempts": len(state.get("results") or []),
            "srs": srs,
            "message": "Exam Coach ready.",
        }

    # ---------------- parsing ----------------
    @staticmethod
    def _subject(command: str, entities: Dict[str, Any]) -> str:
        value = entities.get("subject") or entities.get("topic")
        if value:
            return clean_text(value)
        return extract_after(
            command,
            ["exam for", "exam on", "পরীক্ষা", "subject", "topic", "for", "on", "about", "plan for"],
        )

    @staticmethod
    def _exam_date(command: str) -> str:
        match = re.search(r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{4})\b", command)
        return match.group(1) if match else ""

    @staticmethod
    def _first_int(command: str) -> int:
        match = re.search(r"\d+", command)
        return int(match.group(0)) if match else 0


exam_coach_agent = ExamCoachAgent()
