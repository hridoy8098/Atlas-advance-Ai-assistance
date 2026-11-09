# backend/study/concept_map.py — AI concept map with deterministic fallback

from backend.core.ai_text import ask_json

_SYSTEM = "You build concise concept maps. Reply with JSON only."


class ConceptMap:
    def generate(self, topic: str):
        topic = (topic or "").strip()
        if not topic:
            raise ValueError("topic is required")
        prompt = (
            f'Create a concept map for: "{topic}". '
            'Reply JSON: {"nodes":[{"id":"n1","label":"..."}],"edges":[{"source":"n1","target":"n2","label":"..."}]} '
            "with 5-8 nodes. Use short labels."
        )
        data = ask_json(prompt, system_prompt=_SYSTEM)
        if isinstance(data, dict) and data.get("nodes"):
            return {
                "topic": topic,
                "nodes": data.get("nodes", []),
                "edges": data.get("edges", []),
                "source": "ai",
            }
        return self._fallback(topic)

    @staticmethod
    def _fallback(topic):
        labels = [topic, "Definition", "Key ideas", "Examples", "Applications", "Common mistakes"]
        nodes = [{"id": f"n{i + 1}", "label": label} for i, label in enumerate(labels)]
        edges = [{"source": "n1", "target": f"n{i}", "label": ""} for i in range(2, len(labels) + 1)]
        return {"topic": topic, "nodes": nodes, "edges": edges, "source": "fallback"}


concept_map = ConceptMap()
