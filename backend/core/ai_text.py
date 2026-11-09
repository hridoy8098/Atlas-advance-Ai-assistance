# backend/core/ai_text.py — small helpers for domain modules that need AI text/JSON

import json
import re


def ask(prompt: str, system_prompt: str = None) -> str:
    try:
        from backend.core.ai_engine import ai_engine
        return ai_engine.chat(prompt, system_prompt=system_prompt, use_history=False) or ""
    except Exception as e:
        print(f"⚠️ ai_text.ask: {e}")
        return ""


def ask_json(prompt: str, system_prompt: str = None, fallback=None):
    text = ask(prompt, system_prompt=system_prompt)
    if not text:
        return fallback
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    candidates = [cleaned]
    for opener, closer in (("{", "}"), ("[", "]")):
        start, end = cleaned.find(opener), cleaned.rfind(closer)
        if start != -1 and end > start:
            candidates.append(cleaned[start:end + 1])
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except Exception:
            continue
    return fallback
