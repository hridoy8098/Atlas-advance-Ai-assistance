# backend/study/spaced_repetition.py — SM-2 scheduling on top of flashcards

import threading
from datetime import date, timedelta

import config
from backend.core.domain_db import init, now

_DB = config.DATA_DIR / "atlas_study.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS srs (
    card_id INTEGER PRIMARY KEY,
    ease REAL NOT NULL DEFAULT 2.5,
    interval_days REAL NOT NULL DEFAULT 0,
    reps INTEGER NOT NULL DEFAULT 0,
    due TEXT NOT NULL,
    last_review TEXT
);
"""


class SpacedRepetition:
    def __init__(self):
        self._lock = threading.Lock()
        self._conn = init(_DB, _SCHEMA)

    def due(self, limit: int = 20):
        today = date.today().isoformat()
        with self._lock:
            rows = self._conn.execute(
                "SELECT c.id, c.question, c.answer, c.deck, s.due, s.reps "
                "FROM flashcards c LEFT JOIN srs s ON s.card_id = c.id "
                "WHERE s.card_id IS NULL OR s.due <= ? ORDER BY s.due IS NULL DESC, s.due LIMIT ?",
                (today, limit),
            ).fetchall() if self._has_cards() else []
        return [dict(r) for r in rows]

    def review(self, card_id: int, quality: int):
        quality = max(0, min(5, int(quality)))
        with self._lock:
            row = self._conn.execute(
                "SELECT ease, interval_days, reps FROM srs WHERE card_id = ?", (card_id,)
            ).fetchone()
            ease = row["ease"] if row else 2.5
            interval = row["interval_days"] if row else 0.0
            reps = row["reps"] if row else 0

            if quality < 3:
                reps = 0
                interval = 1
            else:
                reps += 1
                if reps == 1:
                    interval = 1
                elif reps == 2:
                    interval = 6
                else:
                    interval = round(interval * ease)
                ease = max(1.3, ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))

            due = (date.today() + timedelta(days=max(interval, 1))).isoformat()
            self._conn.execute(
                "INSERT INTO srs (card_id, ease, interval_days, reps, due, last_review) "
                "VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(card_id) DO UPDATE SET ease=excluded.ease, interval_days=excluded.interval_days, "
                "reps=excluded.reps, due=excluded.due, last_review=excluded.last_review",
                (card_id, ease, interval, reps, due, now()),
            )
            self._conn.commit()
        return {"card_id": card_id, "quality": quality, "reps": reps,
                "interval_days": interval, "ease": round(ease, 2), "due": due}

    def stats(self):
        today = date.today().isoformat()
        with self._lock:
            total_cards = self._count("flashcards") if self._has_cards() else 0
            row = self._conn.execute(
                "SELECT COUNT(*) AS due FROM flashcards c LEFT JOIN srs s ON s.card_id = c.id "
                "WHERE s.card_id IS NULL OR s.due <= ?", (today,)
            ).fetchone() if total_cards else None
            reviewed_today = self._conn.execute(
                "SELECT COUNT(*) FROM srs WHERE substr(last_review, 1, 10) = ?", (today,)
            ).fetchone()[0]
            avg_ease = self._conn.execute("SELECT AVG(ease) FROM srs").fetchone()[0] or 2.5
        return {
            "total_cards": total_cards,
            "due_today": row["due"] if row else 0,
            "reviewed_today": reviewed_today,
            "avg_ease": round(float(avg_ease), 2),
        }

    def _has_cards(self):
        try:
            return bool(self._conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='flashcards'"
            ).fetchone())
        except Exception:
            return False

    def _count(self, table):
        try:
            return self._conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        except Exception:
            return 0


spaced_repetition = SpacedRepetition()
