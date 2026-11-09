# backend/study/flashcard.py — flashcard storage

import threading

import config
from backend.core.domain_db import init, now

_DB = config.DATA_DIR / "atlas_study.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS flashcards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    deck TEXT NOT NULL DEFAULT 'default',
    created_at TEXT NOT NULL
);
"""


class Flashcards:
    def __init__(self):
        self._lock = threading.Lock()
        self._conn = init(_DB, _SCHEMA)

    def add(self, question: str, answer: str, deck: str = "default"):
        question, answer = (question or "").strip(), (answer or "").strip()
        if not question or not answer:
            raise ValueError("question and answer are required")
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO flashcards (question, answer, deck, created_at) VALUES (?, ?, ?, ?)",
                (question, answer, deck or "default", now()),
            )
            self._conn.commit()
        return {"id": cur.lastrowid, "question": question, "answer": answer, "deck": deck}

    def list(self, deck: str = None):
        with self._lock:
            if deck:
                rows = self._conn.execute(
                    "SELECT id, question, answer, deck, created_at FROM flashcards WHERE deck = ? ORDER BY id DESC",
                    (deck,),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT id, question, answer, deck, created_at FROM flashcards ORDER BY id DESC"
                ).fetchall()
        return [dict(r) for r in rows]

    def get(self, card_id: int):
        with self._lock:
            row = self._conn.execute(
                "SELECT id, question, answer, deck FROM flashcards WHERE id = ?", (card_id,)
            ).fetchone()
        return dict(row) if row else None

    def delete(self, card_id: int):
        with self._lock:
            cur = self._conn.execute("DELETE FROM flashcards WHERE id = ?", (card_id,))
            self._conn.commit()
        return {"deleted": cur.rowcount > 0, "id": card_id}

    def decks(self):
        with self._lock:
            rows = self._conn.execute(
                "SELECT deck, COUNT(*) AS count FROM flashcards GROUP BY deck ORDER BY deck"
            ).fetchall()
        return [dict(r) for r in rows]


flashcards = Flashcards()
