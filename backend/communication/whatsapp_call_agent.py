# backend/communication/whatsapp_call_agent.py
# Agent #1 — resolve a saved contact and start a WhatsApp voice call.
#
# Android: native bridge + AccessibilityService taps the voice-call button.
# iOS: Siri/Shortcut or chat deep link + one user tap (platform limitation).
# Desktop: opens the WhatsApp chat via deep link; call button needs one tap.

from __future__ import annotations

import json
import os
import platform
import re
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import config
from backend.communication import contact_resolver

CALL_LOG = config.DATA_DIR / "call_log.json"
MAX_LOG = 200

FILLER = [
    "whatsapp", "হোয়াটসঅ্যাপ", "open", "kore", "koro", "korbo", "please", "pls",
    "ekta", "ekta", "amar", "আমার", "একটা", "diye", "দিয়ে", "jodi", "please",
    "call", "কল", "koro", "dao", "দাও", "now", "ekhon", "এখন",
]


def _clean_name(raw: str) -> str:
    text = str(raw or "").strip()
    text = re.sub(r"[\u200b-\u200d\ufeff]", "", text)
    text = re.sub(r"^(?:please|pls|ekta|amar|আমার|একটা)\s+", "", text, flags=re.I)
    text = re.sub(r"^(?:my|the)\s+", "", text, flags=re.I)
    text = re.sub(r"\s+(?:ke|কে)$", "", text, flags=re.I)
    text = re.sub(r"\s+(?:call|কল|koro|korbo|dao|দাও|please|pls)$", "", text, flags=re.I)
    text = re.sub(r"^(?:whatsapp|হোয়াটসঅ্যাপ|wa)\s+", "", text, flags=re.I)
    text = re.sub(r"^(?:open|খোল|খুলে|ওপেন)\s+", "", text, flags=re.I)
    text = re.sub(r"^(?:kore|করে)\s+", "", text, flags=re.I)
    text = re.sub(r"\s+(?:open|kore|করে)$", "", text, flags=re.I)
    return text.strip(" .,!?:;\"'")


def _extract_contact(command: str, entities: Dict[str, Any]) -> str:
    for key in ("contact", "name", "person", "contact_name"):
        value = entities.get(key)
        if value:
            return _clean_name(str(value))

    text = str(command or "").strip()
    if not text:
        return ""

    patterns = [
        r"(?:whatsapp|হোয়াটসঅ্যাপ|wa)\s+(?:open\s+)?(?:kore\s+)?(.+?)\s*(?:ke|কে)\s*(?:call|কল)",
        r"(.+?)\s*(?:ke|কে)\s*(?:whatsapp|হোয়াটসঅ্যাপ|wa)\s*(?:call|কল)",
        r"(?:whatsapp|হোয়াটসঅ্যাপ|wa)\s*(?:call|কল)\s+(.+?)$",
        r"(?:call|কল)\s+(.+?)\s+(?:on|in|via|দিয়ে)\s+(?:whatsapp|হোয়াটসঅ্যাপ|wa)",
        r"(?:call|কল)\s+(.+?)(?:\s+(?:now|ekhon|এখন))?$",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            candidate = _clean_name(match.group(1))
            if candidate:
                return candidate
    return ""


def _digits(phone: str) -> str:
    phone = str(phone or "").translate(str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789"))
    cleaned = re.sub(r"[^\d+]", "", phone)
    if cleaned.count("+") > 1:
        cleaned = "+" + cleaned.replace("+", "")
    return cleaned


def _load_log() -> list:
    try:
        with open(CALL_LOG, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _append_log(entry: Dict[str, Any]) -> None:
    try:
        CALL_LOG.parent.mkdir(parents=True, exist_ok=True)
        data = _load_log()
        data.append(entry)
        data = data[-MAX_LOG:]
        tmp = CALL_LOG.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(CALL_LOG)
    except Exception:
        pass


class WhatsAppCallAgent:
    name = "WhatsApp Call Agent"

    def get_capabilities(self) -> list:
        return [
            "whatsapp_call", "call_contact_on_whatsapp", "whatsapp_voice_call",
            "resolve_contact", "open_whatsapp_chat",
        ]

    def handle(self, intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        entities = entities or {}
        command = str(entities.get("_command", ""))
        contact = _extract_contact(command, entities)
        if not contact:
            return {
                "success": False,
                "action": "whatsapp_call",
                "agent": "whatsapp_call",
                "message": "কাকে WhatsApp call করব? নাম বলুন — যেমন “আম্মুকে WhatsApp call করো”।",
            }
        return self.place_call(
            contact,
            platform_name=str(entities.get("platform", "desktop")).lower(),
        )

    def place_call(self, contact_name: str, platform_name: str = "desktop") -> Dict[str, Any]:
        resolved = contact_resolver.resolve(contact_name)
        if resolved["status"] == "ambiguous":
            names = ", ".join(c["name"] for c in resolved.get("candidates", []))
            return {
                "success": False,
                "action": "whatsapp_call_ambiguous",
                "agent": "whatsapp_call",
                "message": f"একাধিক contact পাওয়া গেছে: {names}। কোনটা বলুন।",
                "candidates": resolved.get("candidates", []),
            }
        if resolved["status"] == "not_found":
            return {
                "success": False,
                "action": "whatsapp_call_not_found",
                "agent": "whatsapp_call",
                "message": resolved.get("message", "Contact পাওয়া যায়নি।"),
                "hint": resolved.get("hint", "Settings → Agents → WhatsApp Call থেকে contact যোগ করুন।"),
                "query": contact_name,
            }
        if resolved["status"] == "no_phone":
            return {
                "success": False,
                "action": "whatsapp_call_no_phone",
                "agent": "whatsapp_call",
                "message": resolved.get("message", "Contact number is empty."),
                "contact": resolved.get("contact"),
            }

        contact = resolved["contact"]
        phone = _digits(contact.get("phone", ""))
        if not phone:
            return {
                "success": False,
                "action": "whatsapp_call_no_phone",
                "agent": "whatsapp_call",
                "message": f"{contact['name']}-এর WhatsApp number পাওয়া যায়নি।",
                "contact": contact,
            }

        link = f"whatsapp://send?phone={phone}"
        is_phone = platform_name in ("android", "ios", "phone", "mobile")
        opened = False
        error = None

        if not is_phone:
            try:
                if platform.system() == "Windows" and hasattr(os, "startfile"):
                    os.startfile(link)  # type: ignore[attr-defined]
                    opened = True
                else:
                    opened = bool(webbrowser.open(link))
            except Exception as exc:
                error = str(exc)
                try:
                    opened = bool(webbrowser.open(link))
                except Exception as exc2:
                    error = f"{error or ''} {exc2}".strip()

        status = "handoff_to_phone" if is_phone else ("chat_opened" if opened else "open_failed")
        entry = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "channel": "whatsapp",
            "contact": contact["name"],
            "phone": phone,
            "platform": platform_name,
            "status": status,
        }
        _append_log(entry)

        if is_phone:
            return {
                "success": True,
                "action": "whatsapp_call_native",
                "agent": "whatsapp_call",
                "requires_bridge": True,
                "contact": contact,
                "phone": phone,
                "deep_link": link,
                "platform": platform_name,
                "message": f"📞 {contact['name']}-কে WhatsApp call করার request phone-এ পাঠানো হয়েছে।",
                "logging": entry,
            }

        if opened:
            return {
                "success": True,
                "action": "whatsapp_call",
                "agent": "whatsapp_call",
                "contact": contact,
                "phone": phone,
                "deep_link": link,
                "requires_manual_tap": True,
                "message": f"📱 WhatsApp-এ {contact['name']}-এর chat খোলা হয়েছে। Voice call button-এ একবার tap করুন।",
                "note": "Windows/Linux-এ WhatsApp UI automate করতে Accessibility bridge লাগে; Android-এ সেটা automatic হবে।",
                "logging": entry,
            }

        return {
            "success": False,
            "action": "whatsapp_call_open_failed",
            "agent": "whatsapp_call",
            "contact": contact,
            "phone": phone,
            "deep_link": link,
            "message": f"WhatsApp খোলা যায়নি। WhatsApp installed আছে কি? {error or ''}".strip(),
            "logging": entry,
        }

    def test(self) -> Dict[str, Any]:
        contacts = contact_resolver.load_contacts()
        with_phone = [c for c in contacts if _digits(c.get("phone", ""))]
        return {
            "success": bool(with_phone),
            "agent": "whatsapp_call",
            "contacts": len(contacts),
            "contacts_with_phone": len(with_phone),
            "platform": platform.system(),
            "message": (
                f"{len(with_phone)} contact ready for WhatsApp calls."
                if with_phone else
                "No contact with a phone number. Add one in Settings → Agents → WhatsApp Call."
            ),
            "desktop_note": "Desktop opens the chat; Android places the call automatically; iOS needs one tap.",
        }


whatsapp_call_agent = WhatsAppCallAgent()
