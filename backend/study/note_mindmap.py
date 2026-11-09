# backend/study/note_mindmap.py — mindmap from a note's text (keyword frequency)

import re
from collections import Counter

_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for", "with", "is", "are",
    "was", "were", "be", "been", "this", "that", "these", "those", "it", "as", "at", "by",
    "from", "has", "have", "had", "not", "no", "can", "will", "would", "should", "which",
    "when", "what", "how", "why", "who", "their", "there", "then", "than", "into", "also",
}


class NoteMindmap:
    def from_note(self, text: str, title: str = "Note", max_nodes: int = 8):
        text = (text or "").strip()
        if not text:
            raise ValueError("note text is required")

        words = [w for w in re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", text.lower()) if w not in _STOPWORDS]
        top = [word for word, _ in Counter(words).most_common(max_nodes)]

        nodes = [{"id": "root", "label": title}] + [
            {"id": f"n{i}", "label": word} for i, word in enumerate(top, start=1)
        ]
        edges = [{"source": "root", "target": f"n{i}", "label": ""} for i in range(1, len(top) + 1)]

        sentences = [s.strip() for s in re.split(r"[.!?\n]+", text) if s.strip()]
        return {
            "title": title,
            "nodes": nodes,
            "edges": edges,
            "summary": sentences[0] if sentences else "",
            "sentences": len(sentences),
        }


note_mindmap = NoteMindmap()
