# backend/communication/contact_resolver.py
# Resolve "Ammu" / "আম্মু" / "মা" to a saved contact without guessing silently.

from __future__ import annotations

import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional

import config

CONTACTS_FILE = config.DATA_DIR / "contacts.json"

# Common relationship words -> canonical search terms.
ALIASES = {
    "ammu": ["ammu", "ammi", "mom", "mommy", "mother", "maa", "ma", "আম্মু", "আম্মা", "মা"],
    "abbu": ["abbu", "abba", "dad", "daddy", "father", "baba", "আব্বু", "আব্বা", "বাবা"],
    "bhai": ["bhai", "brother", "ভাই", "ভাইয়া"],
    "apu": ["apu", "apa", "sister", "আপু", "আপা", "বোন"],
    "didi": ["didi", "sister", "দিদি"],
}

BENGALI_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", str(text or "")).strip().lower()
    text = text.translate(BENGALI_DIGITS)
    text = re.sub(r"[^\w\s\u0980-\u09FF+]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _digits(phone: str) -> str:
    phone = str(phone or "").translate(BENGALI_DIGITS)
    cleaned = re.sub(r"[^\d+]", "", phone)
    if cleaned.count("+") > 1:
        cleaned = "+" + cleaned.replace("+", "")
    return cleaned


def _ensure_file() -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not CONTACTS_FILE.exists():
        _save([])


def load_contacts() -> List[Dict[str, Any]]:
    _ensure_file()
    try:
        with open(CONTACTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data = data.get("contacts", [])
        if not isinstance(data, list):
            return []
        result = []
        for item in data:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            if not name:
                continue
            result.append({
                "name": name,
                "phone": str(item.get("phone", "")).strip(),
                "aliases": [str(a).strip() for a in item.get("aliases", []) if str(a).strip()],
                "whatsapp": bool(item.get("whatsapp", True)),
            })
        return result
    except Exception:
        return []


def _save(contacts: List[Dict[str, Any]]) -> None:
    CONTACTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = CONTACTS_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"contacts": contacts}, f, ensure_ascii=False, indent=2)
    tmp.replace(CONTACTS_FILE)


def save_contacts(contacts: List[Dict[str, Any]]) -> None:
    _save(contacts)


def add_contact(name: str, phone: str, aliases: Optional[List[str]] = None, whatsapp: bool = True) -> Dict[str, Any]:
    name = str(name or "").strip()
    phone = str(phone or "").strip()
    if not name:
        return {"success": False, "error": "Contact name is required."}
    contacts = load_contacts()
    normalized = _normalize(name)
    existing = None
    for contact in contacts:
        if _normalize(contact["name"]) == normalized:
            existing = contact
            break
        if phone and _digits(contact.get("phone", "")) == _digits(phone):
            existing = contact
            break
    if existing:
        existing.update({
            "name": name,
            "phone": phone or existing.get("phone", ""),
            "aliases": list(dict.fromkeys((existing.get("aliases") or []) + (aliases or []))),
            "whatsapp": bool(whatsapp),
        })
        action = "updated"
    else:
        contacts.append({
            "name": name,
            "phone": phone,
            "aliases": aliases or [],
            "whatsapp": bool(whatsapp),
        })
        action = "created"
    _save(contacts)
    return {"success": True, "action": action, "contact": existing or contacts[-1]}


def delete_contact(name: str) -> Dict[str, Any]:
    target = _normalize(name)
    contacts = load_contacts()
    kept = [c for c in contacts if _normalize(c["name"]) != target]
    if len(kept) == len(contacts):
        return {"success": False, "error": f"Contact not found: {name}"}
    _save(kept)
    return {"success": True, "deleted": name}


def _score(query: str, contact: Dict[str, Any]) -> float:
    q = _normalize(query)
    if not q:
        return 0.0
    terms = [_normalize(contact.get("name", ""))] + [_normalize(a) for a in contact.get("aliases", [])]
    best = 0.0
    for term in terms:
        if not term:
            continue
        if q == term:
            return 1.0
        if q in term or term in q:
            best = max(best, 0.92)
        best = max(best, SequenceMatcher(None, q, term).ratio())
    # Relationship aliases are strong hints, not automatic matches.
    for canonical, words in ALIASES.items():
        if any(_normalize(w) == q for w in words):
            for term in terms:
                if term == canonical or any(_normalize(w) == term for w in words):
                    best = max(best, 0.95)
    return round(best, 3)


def resolve(query: str) -> Dict[str, Any]:
    query = str(query or "").strip()
    if not query:
        return {"status": "not_found", "query": query, "message": "Contact name is empty."}
    contacts = load_contacts()
    if not contacts:
        return {
            "status": "not_found",
            "query": query,
            "message": "No contacts saved yet. Add a contact first.",
            "hint": "Use Settings → Agents → WhatsApp Call → Add contact.",
        }

    # Exact phone number.
    qphone = _digits(query)
    if len(qphone) >= 7:
        for contact in contacts:
            if _digits(contact.get("phone", "")) == qphone:
                return {"status": "ok", "query": query, "contact": contact, "confidence": 1.0}

    scored = sorted(
        ((_score(query, c), c) for c in contacts),
        key=lambda pair: pair[0],
        reverse=True,
    )
    matches = [(score, contact) for score, contact in scored if score >= 0.68]
    if not matches:
        return {
            "status": "not_found",
            "query": query,
            "message": f"No contact matched “{query}”.",
            "candidates": [],
        }
    if len(matches) > 1 and matches[0][0] - matches[1][0] < 0.12:
        return {
            "status": "ambiguous",
            "query": query,
            "message": f"Multiple contacts matched “{query}”. Which one?",
            "candidates": [
                {"name": c["name"], "phone": c.get("phone", ""), "score": s}
                for s, c in matches[:5]
            ],
        }
    contact = matches[0][1]
    if not _digits(contact.get("phone", "")):
        return {
            "status": "no_phone",
            "query": query,
            "contact": contact,
            "message": f"{contact['name']}-এর phone number save করা নেই।",
        }
    return {
        "status": "ok",
        "query": query,
        "contact": contact,
        "confidence": matches[0][0],
        "candidates": [
            {"name": c["name"], "phone": c.get("phone", ""), "score": s}
            for s, c in matches[:5]
        ],
    }
