# backend/agent/advanced_common.py — shared helpers for the advanced agents
from __future__ import annotations

import json
import os
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import config

_LOCK = threading.RLock()
_BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "is", "are",
    "was", "were", "be", "been", "it", "this", "that", "with", "as", "at", "by",
    "from", "about", "into", "koro", "kore", "amar", "ami", "ekta", "please",
    "what", "how", "why", "when", "where", "which", "who", "কি", "কী", "একটা",
    "আমার", "আমি", "করে", "করো", "কেন", "কিভাবে", "কোথায়", "কখন",
}


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def data_file(name: str) -> Path:
    path = config.DATA_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def read_json(path: Path, fallback: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return fallback


def write_json(path: Path, data: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
        os.replace(tmp, path)


def ask(prompt: str, system_prompt: str = None) -> str:
    try:
        from backend.core.ai_text import ask as ai_ask
        return (ai_ask(prompt, system_prompt=system_prompt) or "").strip()
    except Exception:
        return ""


def ask_json(prompt: str, system_prompt: str = None, fallback: Any = None) -> Any:
    try:
        from backend.core.ai_text import ask_json as ai_ask_json
        return ai_ask_json(prompt, system_prompt=system_prompt, fallback=fallback)
    except Exception:
        return fallback


def bn_to_en_digits(text: str) -> str:
    return str(text or "").translate(_BN_DIGITS)


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def truncate(text: str, limit: int = 4000) -> str:
    text = str(text or "")
    return text if len(text) <= limit else text[: limit - 3] + "..."


def slugify(value: str, fallback: str = "atlas") -> str:
    text = re.sub(r"[^\w\-]+", "-", str(value or "").strip().lower(), flags=re.UNICODE)
    text = re.sub(r"-{2,}", "-", text).strip("-_")
    return text[:60] or fallback


def extract_amount(text: str) -> Optional[float]:
    text = bn_to_en_digits(text).replace(",", "")
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def extract_after(text: str, triggers: Iterable[str], limit: int = 120) -> str:
    text = clean_text(text)
    for trigger in sorted(triggers, key=len, reverse=True):
        pattern = re.escape(trigger)
        match = re.search(pattern + r"\s*[:\-]?\s*(.+)$", text, flags=re.I)
        if match:
            value = re.sub(
                r"^(?:koro|korbo|please|pls|ekta|ekhon|now|আমার|একটা|করো|এখন)\s+",
                "",
                match.group(1).strip(),
                flags=re.I,
            )
            value = re.sub(r"\s+(?:koro|korbo|please|pls|করো)$", "", value, flags=re.I)
            if value:
                return value[:limit].strip(" .,!?:;-")
    return ""


def extract_quoted(text: str) -> str:
    match = re.search(r"[\"“”']([^\"“”']{2,})[\"“”']", str(text or ""))
    return match.group(1).strip() if match else ""


def resolve_path(raw: Any, base: Optional[Path] = None) -> Optional[Path]:
    value = clean_text(raw).strip("\"'")
    if not value:
        return None
    value = os.path.expandvars(value)
    value = str(Path(value).expanduser())
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    bases = [Path(base)] if base else [Path.cwd(), Path.home(), config.BASE_DIR]
    for root in bases:
        probe = root / candidate
        if probe.exists():
            return probe
    return Path.cwd() / candidate


def find_existing_path(text: str, base: Optional[Path] = None) -> Optional[Path]:
    """Find an existing path mentioned in free text (handles spaces and quotes)."""
    quoted = extract_quoted(text)
    if quoted:
        candidate = resolve_path(quoted, base)
        if candidate and candidate.exists():
            return candidate

    raw = str(text or "")
    candidates = []
    for match in re.finditer(r"(?:[A-Za-z]:\\[^\n\"']+|(?:\.{0,2}[\\/])?[\w .\-\\/]+?\.[A-Za-z0-9]{1,8})", raw):
        value = match.group(0).strip()
        if not value:
            continue
        candidates.append(value)
        # The regex may swallow leading words ("review backend/file.py").
        # Try every whitespace-suffix so the real path wins.
        parts = value.split()
        for index in range(1, len(parts)):
            candidates.append(" ".join(parts[index:]))

    for value in candidates:
        candidate = resolve_path(value, base)
        if candidate and candidate.exists():
            return candidate
    return None


def tokenize(text: str) -> List[str]:
    return [
        token for token in re.findall(r"[a-zA-Z\u0980-\u09FF0-9_]{2,}", str(text or "").lower())
        if token not in _STOPWORDS
    ]


def score_chunks(chunks: List[Dict[str, Any]], question: str, limit: int = 4) -> List[Dict[str, Any]]:
    query_terms = set(tokenize(question))
    if not query_terms:
        return chunks[:limit]
    scored = []
    for chunk in chunks:
        terms = tokenize(chunk.get("text", ""))
        if not terms:
            continue
        overlap = len(query_terms.intersection(terms))
        density = overlap / max(len(query_terms), 1)
        scored.append((overlap, density, chunk))
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [item[2] for item in scored[:limit] if item[0] > 0] or chunks[:limit]


def human_bytes(size: float) -> str:
    size = float(size or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def mask_secret(value: str, keep: int = 4) -> str:
    text = str(value or "")
    if len(text) <= keep:
        return "•" * len(text)
    return "•" * (len(text) - keep) + text[-keep:]


def ok(agent: str, message: str, **extra: Any) -> Dict[str, Any]:
    payload = {"success": True, "agent": agent, "message": message}
    payload.update(extra)
    return payload


def fail(agent: str, message: str, **extra: Any) -> Dict[str, Any]:
    payload = {"success": False, "agent": agent, "message": message}
    payload.update(extra)
    return payload
