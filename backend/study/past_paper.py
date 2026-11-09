# backend/study/past_paper.py — archive past papers and extract recurring topics

import re
import threading
from collections import Counter
from pathlib import Path

import config
from backend.core.domain_db import init, now

_DB = config.DATA_DIR / "atlas_study.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS past_papers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL,
    path TEXT NOT NULL,
    added_at TEXT NOT NULL
);
"""

_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "what", "which", "when", "your",
    "answer", "question", "marks", "write", "short", "long", "explain", "define", "describe",
    "are", "was", "were", "has", "have", "not", "you", "all", "any", "following",
}


class PastPapers:
    def __init__(self):
        self._lock = threading.Lock()
        self._conn = init(_DB, _SCHEMA)

    def add(self, file_path: str, subject: str = "General"):
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"file not found: {file_path}")
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO past_papers (subject, path, added_at) VALUES (?, ?, ?)",
                (subject or "General", str(path), now()),
            )
            self._conn.commit()
        return {"paper_id": cur.lastrowid, "subject": subject, "path": str(path)}

    def list(self):
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, subject, path, added_at FROM past_papers ORDER BY id DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def analyze(self, paper_id: int, top_n: int = 10):
        with self._lock:
            row = self._conn.execute(
                "SELECT subject, path FROM past_papers WHERE id = ?", (paper_id,)
            ).fetchone()
        if row is None:
            raise ValueError(f"paper {paper_id} not found")

        text = self._read(Path(row["path"]))
        if not text:
            return {"paper_id": paper_id, "subject": row["subject"], "topics": [],
                    "message": "could not read text from this paper"}
        words = [w for w in re.findall(r"[A-Za-z][A-Za-z-]{3,}", text.lower()) if w not in _STOPWORDS]
        topics = [{"topic": word, "count": count} for word, count in Counter(words).most_common(top_n)]
        return {"paper_id": paper_id, "subject": row["subject"], "topics": topics,
                "word_count": len(words)}

    @staticmethod
    def _read(path: Path):
        try:
            if path.suffix.lower() == ".pdf":
                try:
                    from pypdf import PdfReader
                    return "\n".join((page.extract_text() or "") for page in PdfReader(str(path)).pages)
                except Exception:
                    return ""
            return path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""


past_papers = PastPapers()
