# backend/agent/meeting_autopilot_agent.py — Meeting Autopilot Agent
# Local scheduling with conflict detection, agenda generation and .ics export.
from __future__ import annotations

import re
import uuid
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import config
from .advanced_common import (
    ask,
    clean_text,
    data_file,
    fail,
    ok,
    read_json,
    truncate,
    write_json,
)

STATE_FILE = data_file("meetings.json")
WORK_START = 9
WORK_END = 18
SLOT_MINUTES = 30
DAY_NAMES = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4,
    "saturday": 5, "sunday": 6, "সোমবার": 0, "মঙ্গলবার": 1, "বুধবার": 2,
    "বৃহস্পতিবার": 3, "শুক্রবার": 4, "শনিবার": 5, "রবিবার": 6,
}


class MeetingAutopilotAgent:
    name = "Meeting Autopilot Agent"

    def get_capabilities(self) -> List[str]:
        return ["meeting_schedule", "meeting_list", "meeting_cancel", "meeting_agenda", "meeting_ics"]

    def handle(self, intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        entities = entities or {}
        command = str(entities.get("_command", ""))
        intent_lower = str(intent or "").lower()
        lower = command.lower()

        try:
            if "list" in intent_lower or "upcoming" in lower or "meeting list" in lower:
                return self.list_upcoming()
            if "cancel" in intent_lower or "cancel" in lower:
                event_id = str(entities.get("id") or entities.get("event_id") or self._first_token(command))
                return self.cancel(event_id)

            title = str(entities.get("title") or entities.get("topic") or self._title(command) or "Meeting").strip()
            when_text = str(entities.get("when") or entities.get("time") or command)
            duration = int(entities.get("duration") or self._duration(command) or 30)
            attendees = entities.get("attendees") or self._attendees(command)
            return self.schedule(title, when_text, duration, attendees)
        except Exception as exc:
            return fail("meeting_autopilot", f"Meeting Agent error: {exc}")

    # ---------------- scheduling ----------------
    def schedule(
        self,
        title: str,
        when_text: str = "",
        duration: int = 30,
        attendees: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        title = clean_text(title) or "Meeting"
        duration = max(15, min(int(duration), 240))
        requested = self._parse_when(when_text)
        if requested is None:
            requested = self._next_slot(datetime.now())

        state = read_json(STATE_FILE, {"events": []})
        events = state.get("events") or []
        chosen, alternatives, conflict = self._find_free_slot(events, requested, duration)

        agenda = ask(
            f"Write a short meeting agenda (4-6 bullets) for: {title}. "
            f"Attendees: {', '.join(str(a) for a in (attendees or [])) or 'not specified'}. "
            "Reply in the user's language.",
            system_prompt="You are a concise meeting facilitator.",
        )
        if not agenda:
            agenda = "1. Welcome & context\n2. Progress/status\n3. Blockers\n4. Decisions needed\n5. Action items & owners"

        event_id = "mtg_" + uuid.uuid4().hex[:10]
        end = chosen + timedelta(minutes=duration)
        event = {
            "id": event_id,
            "title": title,
            "start": chosen.isoformat(timespec="minutes"),
            "end": end.isoformat(timespec="minutes"),
            "duration_minutes": duration,
            "attendees": [str(person).strip() for person in (attendees or []) if str(person).strip()],
            "agenda": agenda,
            "ics_path": "",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "status": "scheduled",
        }
        ics_path = self._write_ics(event)
        event["ics_path"] = str(ics_path)

        events.append(event)
        state["events"] = events[-500:]
        state["updated_at"] = datetime.now().isoformat(timespec="seconds")
        write_json(STATE_FILE, state)

        message = f"📅 “{title}” scheduled for {chosen.strftime('%a, %d %b %Y · %I:%M %p')}."
        if conflict:
            message += " Requested time was busy; next free slot chosen."
        return ok(
            "meeting_autopilot",
            message,
            event=event,
            alternatives=[slot.isoformat(timespec="minutes") for slot in alternatives],
            conflict=conflict,
        )

    def list_upcoming(self) -> Dict[str, Any]:
        state = read_json(STATE_FILE, {"events": []})
        now = datetime.now()
        upcoming = []
        for event in state.get("events") or []:
            if event.get("status") != "scheduled":
                continue
            try:
                start = datetime.fromisoformat(event.get("start"))
            except Exception:
                continue
            if start >= now:
                upcoming.append(event)
        upcoming.sort(key=lambda item: item.get("start", ""))
        return ok("meeting_autopilot", f"📅 {len(upcoming)} upcoming meeting(s).", events=upcoming[:20])

    def cancel(self, event_id: str) -> Dict[str, Any]:
        if not event_id:
            return fail("meeting_autopilot", "Cancel করার জন্য event id দিন।")
        state = read_json(STATE_FILE, {"events": []})
        for event in state.get("events") or []:
            if event.get("id") == event_id:
                event["status"] = "cancelled"
                event["cancelled_at"] = datetime.now().isoformat(timespec="seconds")
                write_json(STATE_FILE, state)
                return ok("meeting_autopilot", f"🗑️ “{event.get('title')}” cancelled.", event=event)
        return fail("meeting_autopilot", f"Meeting পাওয়া যায়নি: {event_id}")

    # ---------------- slot logic ----------------
    def _find_free_slot(self, events: List[Dict[str, Any]], requested: datetime, duration: int):
        if self._is_free(events, requested, duration) and self._in_work_hours(requested, duration):
            return requested, self._alternatives(events, requested, duration), False

        cursor = self._next_slot(requested)
        limit = requested + timedelta(days=7)
        alternatives: List[datetime] = []
        while cursor <= limit:
            if self._in_work_hours(cursor, duration) and self._is_free(events, cursor, duration):
                alternatives.append(cursor)
                if len(alternatives) >= 3:
                    break
            cursor += timedelta(minutes=SLOT_MINUTES)
        chosen = alternatives[0] if alternatives else self._next_slot(datetime.now())
        return chosen, alternatives[1:3], True

    def _alternatives(self, events: List[Dict[str, Any]], start: datetime, duration: int) -> List[datetime]:
        out = []
        cursor = start + timedelta(minutes=SLOT_MINUTES)
        limit = start + timedelta(days=2)
        while cursor <= limit and len(out) < 2:
            if self._in_work_hours(cursor, duration) and self._is_free(events, cursor, duration):
                out.append(cursor)
            cursor += timedelta(minutes=SLOT_MINUTES)
        return out

    @staticmethod
    def _in_work_hours(start: datetime, duration: int) -> bool:
        end = start + timedelta(minutes=duration)
        return start.weekday() < 6 and start.time() >= time(WORK_START, 0) and end.time() <= time(WORK_END, 0)

    @staticmethod
    def _is_free(events: List[Dict[str, Any]], start: datetime, duration: int) -> bool:
        end = start + timedelta(minutes=duration)
        for event in events:
            if event.get("status") != "scheduled":
                continue
            try:
                event_start = datetime.fromisoformat(event.get("start"))
                event_end = datetime.fromisoformat(event.get("end"))
            except Exception:
                continue
            if start < event_end and end > event_start:
                return False
        return True

    @staticmethod
    def _next_slot(start: datetime) -> datetime:
        candidate = start.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        if candidate.hour < WORK_START:
            candidate = candidate.replace(hour=WORK_START)
        if candidate.hour >= WORK_END:
            candidate = (candidate + timedelta(days=1)).replace(hour=WORK_START)
        return candidate

    # ---------------- parsing ----------------
    def _parse_when(self, text: str) -> Optional[datetime]:
        text = clean_text(text).lower()
        now = datetime.now()
        date_value: Optional[datetime] = None

        iso = re.search(r"(\d{4}-\d{2}-\d{2})[ t](\d{1,2}):(\d{2})", text)
        if iso:
            try:
                return datetime.strptime(f"{iso.group(1)} {int(iso.group(2))}:{iso.group(3)}", "%Y-%m-%d %H:%M")
            except Exception:
                pass

        if "tomorrow" in text or "আগামীকাল" in text:
            date_value = now + timedelta(days=1)
        elif "today" in text or "আজ" in text:
            date_value = now
        elif "next week" in text or "পরের সপ্তাহ" in text:
            date_value = now + timedelta(days=7)
        else:
            for name, weekday in DAY_NAMES.items():
                if name in text:
                    delta = (weekday - now.weekday()) % 7 or 7
                    date_value = now + timedelta(days=delta)
                    break

        time_value = self._parse_time(text)
        if time_value is None and date_value is None:
            return None
        base = date_value or now
        hour, minute = time_value or (10, 0)
        result = base.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if date_value is None and result <= now:
            result += timedelta(days=1)
        return result

    @staticmethod
    def _parse_time(text: str) -> Optional[tuple]:
        match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", text, flags=re.I)
        if match:
            hour = int(match.group(1)) % 12
            minute = int(match.group(2) or 0)
            if match.group(3).lower() == "pm":
                hour += 12
            return hour, minute
        match = re.search(r"\b(\d{1,2}):(\d{2})\b", text)
        if match:
            return int(match.group(1)), int(match.group(2))
        match = re.search(r"\b(?:at|সকাল|দুপুর|বিকাল|রাত)\s*(\d{1,2})\b", text)
        if match:
            return int(match.group(1)), 0
        return None

    @staticmethod
    def _title(command: str) -> str:
        match = re.search(r"meeting\s+(?:about|on|for)\s+(.+?)(?:\s+(?:with|at|on|tomorrow|today|আগামীকাল|আজ)\b|$)", command, flags=re.I)
        if match:
            return clean_text(match.group(1))
        match = re.search(r"(?:title|বিষয়)\s*[:\-]\s*(.+)$", command, flags=re.I)
        return clean_text(match.group(1)) if match else ""

    @staticmethod
    def _duration(command: str) -> int:
        match = re.search(r"(\d{1,3})\s*(?:min|minute|মিনিট)", command, flags=re.I)
        return int(match.group(1)) if match else 0

    @staticmethod
    def _attendees(command: str) -> List[str]:
        match = re.search(r"\bwith\s+(.+?)(?:\s+(?:at|on|tomorrow|today|আগামীকাল|আজ)\b|[.,]|$)", command, flags=re.I)
        if not match:
            return []
        return [clean_text(item) for item in re.split(r",| and | & ", match.group(1)) if clean_text(item)]

    @staticmethod
    def _first_token(command: str) -> str:
        match = re.search(r"mtg_[a-f0-9]+", command, flags=re.I)
        return match.group(0) if match else ""

    # ---------------- ics ----------------
    @staticmethod
    def _write_ics(event: Dict[str, Any]) -> Path:
        start = datetime.fromisoformat(event["start"]).astimezone(timezone.utc)
        end = datetime.fromisoformat(event["end"]).astimezone(timezone.utc)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Atlas 7.0//Meeting Autopilot//EN",
            "CALSCALE:GREGORIAN",
            "BEGIN:VEVENT",
            f"UID:{event['id']}@atlas7.local",
            f"DTSTAMP:{stamp}",
            f"DTSTART:{start.strftime('%Y%m%dT%H%M%SZ')}",
            f"DTEND:{end.strftime('%Y%m%dT%H%M%SZ')}",
            f"SUMMARY:{event['title']}",
            "DESCRIPTION:" + event.get("agenda", "").replace("\n", "\\n")[:1500],
            f"STATUS:CONFIRMED",
        ]
        for attendee in event.get("attendees", []):
            lines.append(f"ATTENDEE;CN={attendee}:mailto:{attendee}" if "@" in attendee else f"ATTENDEE;CN={attendee}:invalid:nomail")
        lines += ["END:VEVENT", "END:VCALENDAR", ""]
        folder = data_file("meetings")
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{event['id']}.ics"
        path.write_text("\r\n".join(lines), encoding="utf-8")
        return path

    def test(self) -> Dict[str, Any]:
        state = read_json(STATE_FILE, {"events": []})
        upcoming = [item for item in state.get("events") or [] if item.get("status") == "scheduled"]
        return {
            "success": True,
            "agent": "meeting_autopilot",
            "scheduled": len(upcoming),
            "message": "Meeting Autopilot ready (local calendar + .ics).",
        }


meeting_autopilot_agent = MeetingAutopilotAgent()
