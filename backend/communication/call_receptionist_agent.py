# backend/communication/call_receptionist_agent.py
# Agent #2 — AI Call Receptionist (simulator first, real telephony later).
#
# Real calls: telephony provider -> media stream -> STT -> LLM -> TTS -> caller.
# This module gives the product a working call inbox, busy mode, AI script and
# callback queue while the Twilio/SIP adapter is wired in the next phase.

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import config

STATE_FILE = config.DATA_DIR / "receptionist_state.json"
MAX_CALLS = 300


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _default_state() -> Dict[str, Any]:
    return {
        "busy": False,
        "mode": "manual",
        "provider": "simulator",
        "consent_disclosure": True,
        "recording_enabled": False,
        "updated_at": _now(),
        "calls": [],
    }


def _load_state() -> Dict[str, Any]:
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return _default_state()
        state = _default_state()
        state.update(data)
        if not isinstance(state.get("calls"), list):
            state["calls"] = []
        return state
    except Exception:
        return _default_state()


def _save_state(state: Dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["calls"] = state.get("calls", [])[-MAX_CALLS:]
    tmp = STATE_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    tmp.replace(STATE_FILE)


def _telephony_status() -> Dict[str, Any]:
    provider = ""
    number = ""
    if os.getenv("TWILIO_ACCOUNT_SID") and os.getenv("TWILIO_AUTH_TOKEN"):
        provider = "twilio"
        number = os.getenv("TWILIO_PHONE_NUMBER", "")
    elif os.getenv("ATLAS_VIRTUAL_NUMBER"):
        provider = "sip"
        number = os.getenv("ATLAS_VIRTUAL_NUMBER", "")
    try:
        with open(config.DATA_DIR / "telephony.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and data.get("provider"):
            provider = data["provider"]
            number = data.get("number", number)
    except Exception:
        pass
    masked = ("•" * max(0, len(number) - 4) + number[-4:]) if number else ""
    return {
        "configured": bool(provider),
        "provider": provider or "simulator",
        "number": masked,
        "real_calls": bool(provider),
    }


class CallReceptionistAgent:
    name = "AI Call Receptionist"

    def get_capabilities(self) -> list:
        return [
            "call_receptionist", "busy_mode", "take_message",
            "call_summary", "notify_owner", "callback", "call_inbox",
        ]

    # ---------------- command router ----------------
    def handle(self, intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        entities = entities or {}
        command = str(entities.get("_command", "")).lower()
        intent_lower = str(intent or "").lower()

        if any(k in intent_lower for k in ("simulate", "test_call")) or "simulate" in command:
            return self.simulate_call(
                caller_name=str(entities.get("caller_name", "Test Caller")),
                caller_number=str(entities.get("caller_number", "+8801000000000")),
                message=str(entities.get("message", "Test message from the receptionist simulator.")),
                urgency=str(entities.get("urgency", "normal")),
            )
        if "callback" in intent_lower or "callback" in command:
            return self.callback(
                str(entities.get("call_id", "")),
                platform=str(entities.get("platform", "desktop")),
            )
        if any(k in intent_lower for k in ("busy_off", "disable", "stop")) or re.search(r"\b(busy|বিজি)\b.*\b(off|বন্ধ)\b", command):
            return self.set_busy(False)
        if any(k in intent_lower for k in ("busy_on", "enable")) or re.search(r"\b(busy|বিজি)\b.*\b(on|চালু)\b", command):
            return self.set_busy(True)
        if "list" in intent_lower or "inbox" in command or "calls" in command:
            return self.list_calls()
        return self.status()

    # ---------------- actions ----------------
    def set_busy(self, busy: bool) -> Dict[str, Any]:
        state = _load_state()
        state["busy"] = bool(busy)
        state["updated_at"] = _now()
        _save_state(state)
        return {
            "success": True,
            "agent": "call_receptionist",
            "busy": state["busy"],
            "message": "🔴 Busy mode ON — AI receptionist will answer." if busy else "🟢 Busy mode OFF — calls will ring normally.",
            "telephony": _telephony_status(),
        }

    def status(self) -> Dict[str, Any]:
        state = _load_state()
        calls = state.get("calls", [])
        last = calls[-1] if calls else None
        return {
            "success": True,
            "agent": "call_receptionist",
            "busy": bool(state.get("busy")),
            "mode": state.get("mode", "manual"),
            "provider": _telephony_status(),
            "calls_count": len(calls),
            "last_call": last,
            "recording_enabled": bool(state.get("recording_enabled")),
            "message": "Receptionist simulator ready." if not _telephony_status()["real_calls"] else "Receptionist ready with real telephony.",
        }

    def simulate_call(
        self,
        caller_name: str = "Test Caller",
        caller_number: str = "+8801000000000",
        message: str = "Please call me back.",
        urgency: str = "normal",
    ) -> Dict[str, Any]:
        state = _load_state()
        caller_name = str(caller_name or "Unknown").strip()[:80]
        caller_number = str(caller_number or "").strip()[:32]
        message = str(message or "").strip()[:500]
        urgency = str(urgency or "normal").lower()
        if urgency not in ("low", "normal", "urgent", "emergency"):
            urgency = "normal"

        call_id = "call_" + uuid.uuid4().hex[:12]
        transcript = [
            {"role": "ai", "text": "Hello, this is Atlas, the AI assistant. The owner is busy right now. May I know who is speaking and what the call is about?"},
            {"role": "caller", "text": f"{caller_name}: {message}"},
            {"role": "ai", "text": "Thank you. I will pass your message. Is it urgent?"},
            {"role": "caller", "text": f"Urgency: {urgency}."},
            {"role": "ai", "text": "Thank you. I will let the owner know. Goodbye."},
        ]
        summary = f"{caller_name} called from {caller_number or 'unknown number'} about: {message or 'no message'} (urgency: {urgency})."
        notification = f"📞 {caller_name} called. {message} — urgency: {urgency}."
        call = {
            "id": call_id,
            "channel": "phone",
            "direction": "incoming",
            "caller_name": caller_name,
            "caller_number": caller_number,
            "started_at": _now(),
            "ended_at": _now(),
            "status": "message_taken",
            "summary": summary,
            "urgency": urgency,
            "transcript": transcript,
            "notification": notification,
            "notified": True,
            "callback_status": "not_requested",
            "recording_path": None,
        }
        state.setdefault("calls", []).append(call)
        state["updated_at"] = _now()
        _save_state(state)
        return {
            "success": True,
            "agent": "call_receptionist",
            "action": "simulated_call",
            "call": call,
            "message": f"AI receptionist answered {caller_name}. Message saved and notification queued.",
        }

    def list_calls(self, limit: int = 50) -> Dict[str, Any]:
        state = _load_state()
        calls = list(reversed(state.get("calls", [])))[: max(1, min(limit, 200))]
        return {
            "success": True,
            "agent": "call_receptionist",
            "calls": calls,
            "count": len(calls),
            "busy": bool(state.get("busy")),
        }

    def callback(self, call_id: str = "", platform: str = "desktop") -> Dict[str, Any]:
        state = _load_state()
        calls = state.get("calls", [])
        target = None
        for call in reversed(calls):
            if call.get("id") == call_id:
                target = call
                break
        if target is None and calls:
            target = calls[-1]
        if target is None:
            return {"success": False, "agent": "call_receptionist", "message": "No call found to call back."}

        platform_name = str(platform or "desktop").lower()
        phone = str(target.get("caller_number") or "").strip()
        caller_name = str(target.get("caller_name") or phone or "caller")

        # On a phone the callback is a real outbound call through the native bridge.
        if platform_name in ("android", "ios", "phone", "mobile") and phone:
            target["callback_status"] = "dialing_on_phone"
            target["callback_requested_at"] = _now()
            state["updated_at"] = _now()
            _save_state(state)
            return {
                "success": True,
                "agent": "call_receptionist",
                "action": "phone_call_native",
                "phone": phone,
                "contact": {"name": caller_name, "phone": phone},
                "requires_bridge": True,
                "requires_manual_tap": platform_name == "ios",
                "call": target,
                "message": f"📞 {caller_name}-কে callback করা হচ্ছে ({phone})।",
            }

        target["callback_status"] = "queued"
        target["callback_requested_at"] = _now()
        state["updated_at"] = _now()
        _save_state(state)
        return {
            "success": True,
            "agent": "call_receptionist",
            "action": "callback_queued",
            "call": target,
            "message": f"Callback queued for {caller_name} ({phone}).",
            "note": "Real callback will use the telephony adapter after the virtual number is configured.",
        }

    def test(self) -> Dict[str, Any]:
        return self.status()


call_receptionist_agent = CallReceptionistAgent()
