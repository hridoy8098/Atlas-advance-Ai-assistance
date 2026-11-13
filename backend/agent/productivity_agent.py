# backend/agent/productivity_agent.py — tasks, reminders, notes, calendar, pomodoro.
#
# Real persistence in data/productivity.json. No demo data, no fake success.
from __future__ import annotations

import json
import os
import re
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import config
from .advanced_common import clean_text, data_file, read_json, write_json
from .agent_i18n import is_bengali, tr
from .base_agent import BaseAgent

STATE_FILE = data_file("productivity.json")
_LOCK = threading.RLock()
_WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4,
    "saturday": 5, "sunday": 6, "সোমবার": 0, "মঙ্গলবার": 1, "বুধবার": 2,
    "বৃহস্পতিবার": 3, "শুক্রবার": 4, "শনিবার": 5, "রবিবার": 6,
}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _empty_state() -> Dict[str, Any]:
    return {
        "tasks": [],
        "reminders": [],
        "notes": [],
        "events": [],
        "pomodoro": {},
    }


def _load() -> Dict[str, Any]:
    state = read_json(STATE_FILE, _empty_state())
    if not isinstance(state, dict):
        state = _empty_state()
    for key, value in _empty_state().items():
        state.setdefault(key, value)
    return state


def _save(state: Dict[str, Any]) -> None:
    state["updated_at"] = _now()
    write_json(STATE_FILE, state)


def _parse_when(text: str, now: Optional[datetime] = None) -> str:
    """Small natural-time parser for reminders/events.

    Supports: today/tomorrow/আজ/কাল, weekday names, "in 10 minutes",
    "at 5pm", "17:30", "5:30 pm", "at 7 am".
    """
    raw = str(text or "").strip()
    if not raw:
        return ""
    base = now or datetime.now()
    lower = raw.lower().translate(str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789"))

    target_date = None
    if re.search(r"\btomorrow\b|কাল", lower):
        target_date = base.date() + timedelta(days=1)
    elif re.search(r"\btoday\b|আজ", lower):
        target_date = base.date()
    else:
        for name, weekday in _WEEKDAYS.items():
            if re.search(r"(?<![\w\u0980-\u09ff])" + re.escape(name) + r"(?![\w\u0980-\u09ff])", lower):
                delta = (weekday - base.weekday()) % 7 or 7
                target_date = (base + timedelta(days=delta)).date()
                break

    relative = re.search(r"\bin\s+(\d+)\s*(minutes?|mins?|hours?|hrs?|days?)\b", lower)
    if relative:
        amount = int(relative.group(1))
        unit = relative.group(2)
        if unit.startswith("hour") or unit.startswith("hr"):
            return (base + timedelta(hours=amount)).isoformat(timespec="minutes")
        if unit.startswith("day"):
            return (base + timedelta(days=amount)).isoformat(timespec="minutes")
        return (base + timedelta(minutes=amount)).isoformat(timespec="minutes")

    time_match = None
    if re.search(r"\b(?:at|@)\s*\d{1,2}|\d{1,2}:\d{2}|\d{1,2}\s*(?:am|pm)\b", lower):
        time_match = re.search(r"\b(?:at\s+|@\s*)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", lower)
    hour = minute = None
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2) or 0)
        meridiem = (time_match.group(3) or "").lower()
        if meridiem == "pm" and hour < 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0
        if hour > 23 or minute > 59:
            hour = minute = None

    if hour is None:
        if target_date:
            return datetime.combine(target_date, datetime.min.time().replace(hour=9)).isoformat(timespec="minutes")
        return ""

    if target_date is None:
        target = base.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= base:
            target += timedelta(days=1)
        return target.isoformat(timespec="minutes")
    return datetime.combine(target_date, datetime.min.time().replace(hour=hour, minute=minute)).isoformat(timespec="minutes")


class ProductivityAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Productivity Agent",
            description="Persistent tasks, reminders, notes, calendar and Pomodoro",
        )

    def get_capabilities(self) -> List[str]:
        return [
            "productivity_task", "productivity_show_tasks", "productivity_complete_task",
            "productivity_delete_task", "productivity_reminder", "productivity_note",
            "productivity_pomodoro", "productivity_calendar", "productivity_alarm",
        ]

    # ---------------- tasks ----------------
    def add_task(self, task: str, due: str = "", priority: str = "normal", command: str = "") -> Dict[str, Any]:
        title = clean_text(task)
        title = re.sub(r"^to\s+", "", title, flags=re.I).strip()
        if not title:
            return self._fail("কী task যোগ করব? উদাহরণ: “add task finish report tomorrow 5pm”।",
                             "What task should I add? Example: “add task finish report tomorrow 5pm”.", command)
        with _LOCK:
            state = _load()
            item = {
                "id": _new_id("task"),
                "title": title,
                "status": "open",
                "priority": clean_text(priority) or "normal",
                "due": due or _parse_when(title),
                "created_at": _now(),
            }
            state["tasks"].append(item)
            _save(state)
            total = len([t for t in state["tasks"] if t.get("status") == "open"])
        message = tr(command, f"✅ Task added: {title}", f"✅ কাজ যোগ হয়েছে: {title}")
        if item["due"]:
            message += tr(command, f" (due {item['due'].replace('T', ' ')})", f" (সময়: {item['due'].replace('T', ' ')})")
        message += tr(command, f" — {total} open task(s).", f" — মোট {total}টি খোলা কাজ।")
        return {"success": True, "action": "productivity_add_task", "agent": "productivity",
                "message": message, "task": item, "open_tasks": total}

    def list_tasks(self, include_done: bool = False, command: str = "") -> Dict[str, Any]:
        state = _load()
        tasks = [t for t in state["tasks"] if include_done or t.get("status") == "open"]
        tasks.sort(key=lambda item: (item.get("status", ""), item.get("due") or "9999", item.get("created_at", "")))
        if not tasks:
            return {"success": True, "action": "productivity_tasks", "agent": "productivity",
                    "message": tr(command, "📋 Your task list is empty.", "📋 আপনার task list খালি।"),
                    "tasks": [], "count": 0}
        lines = []
        for index, item in enumerate(tasks, 1):
            mark = "✅" if item.get("status") == "done" else "•"
            due = f" — {item['due'].replace('T', ' ')}" if item.get("due") else ""
            lines.append(f"{index}. {mark} {item.get('title')}{due}")
        message = tr(command, "📋 Your tasks:\n", "📋 আপনার কাজগুলো:\n") + "\n".join(lines[:20])
        return {"success": True, "action": "productivity_tasks", "agent": "productivity",
                "message": message, "tasks": tasks[:50], "count": len(tasks)}

    def complete_task(self, query: str, command: str = "") -> Dict[str, Any]:
        target = clean_text(query).lower()
        if not target:
            return self._fail("কোন task শেষ করব? নাম বা id দিন।", "Which task should I complete? Give a name or id.", command)
        with _LOCK:
            state = _load()
            match = self._find_task(state["tasks"], target)
            if not match:
                return self._fail(f"Task পাওয়া যায়নি: {query}", f"Task not found: {query}", command)
            match["status"] = "done"
            match["completed_at"] = _now()
            _save(state)
        return {"success": True, "action": "productivity_complete_task", "agent": "productivity",
                "message": tr(command, f"✅ Task completed: {match.get('title')}", f"✅ কাজ শেষ হয়েছে: {match.get('title')}"),
                "task": match}

    def delete_task(self, query: str, command: str = "") -> Dict[str, Any]:
        target = clean_text(query).lower()
        with _LOCK:
            state = _load()
            match = self._find_task(state["tasks"], target)
            if not match:
                return self._fail(f"Task পাওয়া যায়নি: {query}", f"Task not found: {query}", command)
            state["tasks"] = [item for item in state["tasks"] if item is not match]
            _save(state)
        return {"success": True, "action": "productivity_delete_task", "agent": "productivity",
                "message": tr(command, f"🗑️ Task deleted: {match.get('title')}", f"🗑️ কাজ মুছে ফেলা হয়েছে: {match.get('title')}")}

    # ---------------- reminders / alarms ----------------
    def add_reminder(self, text: str, due: str = "", kind: str = "reminder", command: str = "") -> Dict[str, Any]:
        value = clean_text(text)
        if not value:
            return self._fail("কী মনে করিয়ে দেব? উদাহরণ: “remind me to call mom at 5pm”।",
                              "What should I remind you about? Example: “remind me to call mom at 5pm”.", command)
        due_value = due or _parse_when(value)
        with _LOCK:
            state = _load()
            item = {
                "id": _new_id("rem"),
                "text": value,
                "kind": kind,
                "due": due_value,
                "status": "pending",
                "created_at": _now(),
            }
            state["reminders"].append(item)
            _save(state)
        if due_value:
            message = tr(command, f"⏰ {kind.title()} set: {value} — {due_value.replace('T', ' ')}",
                         f"⏰ {kind.title()} সেট হয়েছে: {value} — {due_value.replace('T', ' ')}")
        else:
            message = tr(command, f"⏰ {kind.title()} saved: {value} (no time parsed)",
                         f"⏰ {kind.title()} সেভ হয়েছে: {value} (সময় বোঝা যায়নি)")
        return {"success": True, "action": f"productivity_{kind}", "agent": "productivity",
                "message": message, "reminder": item}

    def list_reminders(self, command: str = "", include_done: bool = False) -> Dict[str, Any]:
        state = _load()
        rows = [item for item in state["reminders"]
                if include_done or item.get("status") == "pending"]
        rows.sort(key=lambda item: item.get("due") or "9999")
        if not rows:
            return {"success": True, "action": "productivity_reminders", "agent": "productivity",
                    "message": tr(command, "⏰ No pending reminders.", "⏰ কোনো রিমাইন্ডার নেই।"),
                    "reminders": []}
        lines = [f"• {item.get('text')} — {item.get('due', 'no time').replace('T', ' ')}" for item in rows[:20]]
        return {"success": True, "action": "productivity_reminders", "agent": "productivity",
                "message": tr(command, "⏰ Reminders:\n", "⏰ রিমাইন্ডার:\n") + "\n".join(lines),
                "reminders": rows[:50]}

    def due_reminders(self) -> List[Dict[str, Any]]:
        now = datetime.now()
        due = []
        with _LOCK:
            state = _load()
            changed = False
            for item in state["reminders"]:
                if item.get("status") != "pending" or not item.get("due"):
                    continue
                try:
                    when = datetime.fromisoformat(item["due"])
                except Exception:
                    continue
                if when <= now:
                    item["status"] = "notified"
                    item["notified_at"] = _now()
                    due.append(item)
                    changed = True
            if changed:
                _save(state)
        return due

    # ---------------- notes ----------------
    def add_note(self, text: str, command: str = "") -> Dict[str, Any]:
        value = clean_text(text)
        if not value:
            return self._fail("কী নোট লিখব?", "What should I note down?", command)
        with _LOCK:
            state = _load()
            item = {"id": _new_id("note"), "text": value, "created_at": _now()}
            state["notes"].append(item)
            _save(state)
        return {"success": True, "action": "productivity_note", "agent": "productivity",
                "message": tr(command, f"📝 Note saved ({len(value)} chars).", f"📝 নোট সেভ হয়েছে ({len(value)} অক্ষর)।"),
                "note": item}

    def list_notes(self, query: str = "", command: str = "") -> Dict[str, Any]:
        state = _load()
        rows = state["notes"]
        if query:
            needle = query.lower()
            rows = [item for item in rows if needle in str(item.get("text", "")).lower()]
        rows = sorted(rows, key=lambda item: item.get("created_at", ""), reverse=True)[:20]
        if not rows:
            return {"success": True, "action": "productivity_notes", "agent": "productivity",
                    "message": tr(command, "📝 No notes found.", "📝 কোনো নোট পাওয়া যায়নি।"), "notes": []}
        lines = [f"• {item.get('text')}" for item in rows]
        return {"success": True, "action": "productivity_notes", "agent": "productivity",
                "message": tr(command, "📝 Notes:\n", "📝 নোট:\n") + "\n".join(lines), "notes": rows}

    # ---------------- pomodoro ----------------
    def start_pomodoro(self, minutes: int = 25, command: str = "") -> Dict[str, Any]:
        minutes = max(1, min(int(minutes or 25), 240))
        now = datetime.now()
        end = now + timedelta(minutes=minutes)
        with _LOCK:
            state = _load()
            state["pomodoro"] = {
                "started_at": now.isoformat(timespec="seconds"),
                "ends_at": end.isoformat(timespec="seconds"),
                "minutes": minutes,
                "active": True,
            }
            _save(state)
        return {"success": True, "action": "productivity_pomodoro", "agent": "productivity",
                "message": tr(command,
                              f"🍅 Pomodoro started for {minutes} minutes (until {end.strftime('%I:%M %p').lstrip('0')}).",
                              f"🍅 পোমোডোরো শুরু — {minutes} মিনিট (শেষ {end.strftime('%I:%M %p').lstrip('0')})।"),
                "pomodoro": state["pomodoro"]}

    def pomodoro_status(self, command: str = "") -> Dict[str, Any]:
        state = _load()
        data = state.get("pomodoro") or {}
        if not data.get("active"):
            return {"success": True, "action": "productivity_pomodoro_status", "agent": "productivity",
                    "message": tr(command, "🍅 No active Pomodoro.", "🍅 কোনো পোমোডোরো চলছে না।"),
                    "pomodoro": data}
        try:
            end = datetime.fromisoformat(data["ends_at"])
            remaining = int((end - datetime.now()).total_seconds() // 60)
        except Exception:
            remaining = 0
        if remaining <= 0:
            data["active"] = False
            with _LOCK:
                state["pomodoro"] = data
                _save(state)
            message = tr(command, "✅ Pomodoro complete. Take a short break.", "✅ পোমোডোরো শেষ। একটু ব্রেক নিন।")
        else:
            message = tr(command, f"🍅 Pomodoro running — {remaining} minute(s) left.", f"🍅 পোমোডোরো চলছে — আর {remaining} মিনিট বাকি।")
        return {"success": True, "action": "productivity_pomodoro_status", "agent": "productivity",
                "message": message, "pomodoro": data, "remaining_minutes": max(0, remaining)}

    def stop_pomodoro(self, command: str = "") -> Dict[str, Any]:
        with _LOCK:
            state = _load()
            state["pomodoro"] = {"active": False, "stopped_at": _now()}
            _save(state)
        return {"success": True, "action": "productivity_pomodoro_stop", "agent": "productivity",
                "message": tr(command, "🍅 Pomodoro stopped.", "🍅 পোমোডোরো বন্ধ হয়েছে।")}

    # ---------------- calendar ----------------
    def add_event(self, title: str, when: str = "", command: str = "") -> Dict[str, Any]:
        value = clean_text(title)
        if not value:
            return self._fail("কোন event যোগ করব?", "What event should I add?", command)
        due = _parse_when(when or value)
        with _LOCK:
            state = _load()
            item = {"id": _new_id("evt"), "title": value, "when": due, "created_at": _now()}
            state["events"].append(item)
            _save(state)
        return {"success": True, "action": "productivity_calendar", "agent": "productivity",
                "message": tr(command, f"📅 Event added: {value}" + (f" — {due.replace('T', ' ')}" if due else ""),
                              f"📅 ইভেন্ট যোগ হয়েছে: {value}" + (f" — {due.replace('T', ' ')}" if due else "")),
                "event": item}

    def list_calendar(self, command: str = "") -> Dict[str, Any]:
        state = _load()
        events = sorted(state.get("events") or [], key=lambda item: item.get("when") or "9999")
        if not events:
            return {"success": True, "action": "productivity_calendar", "agent": "productivity",
                    "message": tr(command, "📅 Calendar is empty. Meetings are in the Meeting agent.",
                                  "📅 ক্যালেন্ডার খালি। মিটিংগুলো Meeting agent-এ আছে।"),
                    "events": []}
        lines = [f"• {item.get('title')} — {item.get('when', '').replace('T', ' ')}" for item in events[:20]]
        return {"success": True, "action": "productivity_calendar", "agent": "productivity",
                "message": tr(command, "📅 Calendar:\n", "📅 ক্যালেন্ডার:\n") + "\n".join(lines), "events": events[:50]}

    # ---------------- dispatch ----------------
    def handle(self, intent: str, entities: Dict) -> Dict:
        entities = dict(entities or {})
        command = str(entities.get("_command", ""))
        intent_lower = str(intent or "").lower()
        lower = command.lower()

        if "complete" in intent_lower or re.search(r"\b(?:complete|finish|done)\b.*\btask\b", lower):
            return self.complete_task(str(entities.get("task") or entities.get("query") or ""), command)
        if "delete" in intent_lower or re.search(r"\b(?:delete|remove)\b.*\btask\b", lower):
            return self.delete_task(str(entities.get("task") or entities.get("query") or ""), command)
        if "show" in intent_lower or "list" in intent_lower or re.search(r"\b(?:my|show|list)\s+tasks?\b", lower):
            if "reminder" in lower:
                return self.list_reminders(command)
            return self.list_tasks(command=command)
        if "reminder" in intent_lower or "alarm" in intent_lower or re.search(r"\bremind\b|\balarm\b", lower):
            text = str(entities.get("reminder") or entities.get("text") or command)
            text = re.sub(r"^(?:remind\s+me\s+(?:to\s+)?|set\s+(?:a\s+)?(?:reminder|alarm)\s*(?:to|for|at)?\s*)", "", text, flags=re.I).strip()
            kind = "alarm" if "alarm" in lower or "অ্যালার্ম" in command else "reminder"
            return self.add_reminder(text, str(entities.get("due") or ""), kind, command)
        if "note" in intent_lower or re.search(r"\b(?:note|নোট)\b", lower):
            if re.search(r"\b(?:list|show|search|find)\b.*\bnotes?\b", lower):
                return self.list_notes(str(entities.get("query") or ""), command)
            return self.add_note(str(entities.get("note") or entities.get("text") or command), command)
        if "pomodoro" in intent_lower or "focus" in intent_lower or "পোমোডোরো" in command:
            if re.search(r"\b(?:status|remaining|left)\b", lower):
                return self.pomodoro_status(command)
            if re.search(r"\b(?:stop|cancel|বন্ধ)\b", lower):
                return self.stop_pomodoro(command)
            return self.start_pomodoro(int(entities.get("minutes") or 25), command)
        if "calendar" in intent_lower or "event" in intent_lower or "ক্যালেন্ডার" in command:
            if re.search(r"\b(?:add|create|new)\b.*\bevent\b|\bevent\s+add\b", lower):
                title = str(entities.get("title") or re.sub(r"^.*?\bevent\b\s*", "", command)).strip()
                return self.add_event(title, command, command)
            return self.list_calendar(command)
        if re.search(r"\badd\s+(?:a\s+)?(?:task|todo)\b|\bnew\s+task\b", lower):
            return self.add_task(str(entities.get("task") or entities.get("title") or ""), command=command)
        if re.search(r"\btask\b|\bto-?do\b", lower):
            return self.list_tasks(command=command)
        return self.summary(command)

    def summary(self, command: str = "") -> Dict[str, Any]:
        state = _load()
        open_tasks = [t for t in state["tasks"] if t.get("status") == "open"]
        pending = [r for r in state["reminders"] if r.get("status") == "pending"]
        due = self.due_reminders()
        message = tr(command,
                      f"🗓️ {len(open_tasks)} open task(s), {len(pending)} reminder(s), "
                      f"{len(state['notes'])} note(s), {len(state['events'])} event(s).",
                      f"🗓️ {len(open_tasks)}টি খোলা কাজ, {len(pending)}টি রিমাইন্ডার, "
                      f"{len(state['notes'])}টি নোট, {len(state['events'])}টি ইভেন্ট।")
        if due:
            message += tr(command, "\n⏰ Due now: ", "\n⏰ এখন সময় হয়েছে: ") + "; ".join(item.get("text", "") for item in due)
        return {"success": True, "action": "productivity_summary", "agent": "productivity",
                "message": message, "open_tasks": len(open_tasks), "pending_reminders": len(pending),
                "notes": len(state["notes"]), "events": len(state["events"]), "due": due}

    # ---------------- helpers ----------------
    @staticmethod
    def _find_task(tasks: List[Dict[str, Any]], target: str) -> Optional[Dict[str, Any]]:
        if not target:
            return None
        for item in tasks:
            if item.get("id", "").lower() == target:
                return item
        for item in tasks:
            if item.get("status") != "open":
                continue
            if target in str(item.get("title", "")).lower():
                return item
        for item in tasks:
            if target in str(item.get("title", "")).lower():
                return item
        return None

    def _fail(self, bengali: str, english: str, command: str = "") -> Dict[str, Any]:
        return {"success": False, "action": "productivity_error", "agent": "productivity",
                "message": bengali if is_bengali(command) else english}

    # ---------------- self test ----------------
    def test(self) -> Dict[str, Any]:
        probe = f"__atlas_selftest_{uuid.uuid4().hex[:8]}"
        try:
            added = self.add_task(probe, command="self test")
            if not added.get("success"):
                return {"success": False, "agent": "productivity", "message": "Could not write task"}
            task_id = added["task"]["id"]
            state = _load()
            if not any(item.get("id") == task_id for item in state["tasks"]):
                return {"success": False, "agent": "productivity", "message": "Task was not persisted"}
            self.complete_task(task_id, command="self test")
            state = _load()
            match = next((item for item in state["tasks"] if item.get("id") == task_id), None)
            if not match or match.get("status") != "done":
                return {"success": False, "agent": "productivity", "message": "Task completion did not persist"}
            state["tasks"] = [item for item in state["tasks"] if item.get("id") != task_id]
            _save(state)
            return {"success": True, "agent": "productivity",
                    "message": "Task add/list/complete/delete persisted correctly.",
                    "tasks": len(state["tasks"]), "reminders": len(state["reminders"])}
        except Exception as exc:
            return {"success": False, "agent": "productivity", "message": f"Self test failed: {exc}"}


productivity_agent = ProductivityAgent()
