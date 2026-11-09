# backend/agent/agent_registry.py — Atlas 7.0 Agent Registry
# Central metadata + on/off persistence + health checks for every agent.

from __future__ import annotations

import importlib.util
import json
import os
import platform
import shutil
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import config

SETTINGS_FILE = config.DATA_DIR / "agent_settings.json"
AUDIT_FILE = config.LOGS_DIR / "agents.log"
CONTACTS_FILE = config.DATA_DIR / "contacts.json"

_lock = threading.RLock()


# ============================================================
# Agent catalog
# ============================================================
AGENTS: List[Dict[str, Any]] = [
    # ---------------- Core 8 ----------------
    {
        "id": "pc",
        "name": "PC Control Agent",
        "description": "System status, shutdown, restart, lock, battery, WiFi and safe cleanup.",
        "category": "core",
        "platforms": ["pc"],
        "execution": "pc",
        "risk": "confirm",
        "default": True,
        "requires": [],
        "steps": ["check", "preview", "confirm", "execute", "report"],
        "icon": "🖥️",
    },
    {
        "id": "file",
        "name": "File Agent",
        "description": "Search, create, copy, move, rename and safely organize files.",
        "category": "core",
        "platforms": ["pc"],
        "execution": "pc",
        "risk": "confirm",
        "default": True,
        "requires": [],
        "steps": ["locate", "preview", "confirm", "move", "report"],
        "icon": "📁",
    },
    {
        "id": "web",
        "name": "Web Research Agent",
        "description": "Web search, page reading, summaries, translation and bookmarks.",
        "category": "core",
        "platforms": ["pc", "cloud"],
        "execution": "cloud",
        "risk": "safe",
        "default": True,
        "requires": [],
        "steps": ["search", "read", "verify", "summarize", "cite"],
        "icon": "🌐",
    },
    {
        "id": "media",
        "name": "Media Agent",
        "description": "YouTube, music, video, images, memes and downloads.",
        "category": "core",
        "platforms": ["pc", "phone"],
        "execution": "pc",
        "risk": "safe",
        "default": True,
        "requires": [],
        "steps": ["parse", "search", "play", "verify", "report"],
        "icon": "🎬",
    },
    {
        "id": "productivity",
        "name": "Productivity Agent",
        "description": "Tasks, reminders, notes, calendar, pomodoro and alarms.",
        "category": "core",
        "platforms": ["pc", "phone", "cloud"],
        "execution": "cloud",
        "risk": "safe",
        "default": True,
        "requires": [],
        "steps": ["parse", "schedule", "save", "remind", "report"],
        "icon": "🗓️",
    },
    {
        "id": "security",
        "name": "Security Agent",
        "description": "Privacy mode, password checks, breach checks and malware scan.",
        "category": "core",
        "platforms": ["pc", "phone"],
        "execution": "pc",
        "risk": "confirm",
        "default": True,
        "requires": [],
        "steps": ["scan", "rank", "preview", "fix", "report"],
        "icon": "🛡️",
    },
    {
        "id": "app",
        "name": "App Agent",
        "description": "Open and control desktop and phone applications.",
        "category": "core",
        "platforms": ["pc", "phone"],
        "execution": "pc",
        "risk": "safe",
        "default": True,
        "requires": [],
        "steps": ["resolve_app", "launch", "focus", "verify"],
        "icon": "🚀",
    },
    {
        "id": "terminal",
        "name": "Terminal Agent",
        "description": "Safe shell commands, git and package operations.",
        "category": "core",
        "platforms": ["pc"],
        "execution": "pc",
        "risk": "danger",
        "default": True,
        "requires": ["git"],
        "steps": ["validate", "preview", "confirm", "run", "report"],
        "icon": "⌨️",
    },

    # ---------------- Call agents (new #1, #2) ----------------
    {
        "id": "whatsapp_call",
        "name": "WhatsApp Call Agent",
        "description": "Resolve a saved contact by name and start a WhatsApp voice call.",
        "category": "call",
        "platforms": ["android", "ios", "web", "pc"],
        "execution": "phone",
        "risk": "confirm",
        "default": False,
        "requires": ["contacts", "whatsapp"],
        "steps": ["resolve_contact", "open_chat", "place_call", "verify", "log"],
        "icon": "📞",
    },
    {
        "id": "call_receptionist",
        "name": "AI Call Receptionist",
        "description": "Answer while busy, take a message, notify you and optionally call back.",
        "category": "call",
        "platforms": ["android", "ios", "cloud"],
        "execution": "cloud",
        "risk": "danger",
        "default": False,
        "requires": ["virtual_number", "stt", "tts", "consent"],
        "steps": ["detect_busy", "answer", "collect", "summarize", "notify", "callback"],
        "icon": "🤖",
    },

    # ---------------- Advanced 12 ----------------
    {
        "id": "coding",
        "name": "Coding Copilot Agent",
        "description": "Scan a repo, plan a fix, edit files, run tests and summarize the diff.",
        "category": "advanced",
        "platforms": ["pc", "cloud"],
        "execution": "pc",
        "risk": "danger",
        "default": False,
        "requires": ["git"],
        "steps": ["scan", "plan", "edit", "test", "diff"],
        "icon": "🧑‍💻",
    },
    {
        "id": "screen_rpa",
        "name": "Screen Vision RPA Agent",
        "description": "Read the screen, detect fields and perform repetitive click/type workflows.",
        "category": "advanced",
        "platforms": ["pc"],
        "execution": "pc",
        "risk": "danger",
        "default": False,
        "requires": ["pyautogui"],
        "steps": ["capture", "detect", "act", "verify", "repeat"],
        "icon": "🖱️",
    },
    {
        "id": "research_pro",
        "name": "Deep Research Agent",
        "description": "Multi-source research with claim cross-checking and cited reports.",
        "category": "study",
        "platforms": ["pc", "cloud"],
        "execution": "cloud",
        "risk": "confirm",
        "default": True,
        "requires": ["requests", "beautifulsoup4"],
        "steps": ["query", "search", "read", "cross_check", "cite"],
        "icon": "🔎",
    },
    {
        "id": "doc_intel",
        "name": "Document Intelligence Agent",
        "description": "Read PDFs/DOCX, index chunks and answer questions with page citations.",
        "category": "study",
        "platforms": ["pc", "cloud"],
        "execution": "cloud",
        "risk": "safe",
        "default": True,
        "requires": ["pypdf"],
        "steps": ["ingest", "chunk", "index", "answer", "export"],
        "icon": "📄",
    },
    {
        "id": "exam_coach",
        "name": "Exam Prep Coach Agent",
        "description": "Build a study plan, find weak topics, make flashcards and run mock tests.",
        "category": "study",
        "platforms": ["pc", "phone", "cloud"],
        "execution": "cloud",
        "risk": "safe",
        "default": True,
        "requires": [],
        "steps": ["syllabus", "quiz", "weak_topics", "plan", "mock_test"],
        "icon": "🎓",
    },
    {
        "id": "yt_learn",
        "name": "YouTube Learning Agent",
        "description": "Search a video, play it, fetch the transcript, summarize and quiz.",
        "category": "study",
        "platforms": ["pc", "phone", "cloud"],
        "execution": "pc",
        "risk": "safe",
        "default": True,
        "requires": ["yt-dlp", "playwright"],
        "steps": ["search", "pick", "transcript", "notes", "quiz"],
        "icon": "▶️",
    },
    {
        "id": "report_builder",
        "name": "Presentation Builder Agent",
        "description": "Create outlines, charts, slide content and export PPTX/PDF.",
        "category": "productivity",
        "platforms": ["pc", "cloud"],
        "execution": "cloud",
        "risk": "confirm",
        "default": True,
        "requires": ["python-pptx", "matplotlib"],
        "steps": ["outline", "content", "charts", "design", "export"],
        "icon": "📊",
    },
    {
        "id": "email_triage",
        "name": "Email Triage Agent",
        "description": "Fetch inbox, classify urgency, summarize and draft replies for approval.",
        "category": "productivity",
        "platforms": ["pc", "cloud"],
        "execution": "cloud",
        "risk": "danger",
        "default": False,
        "requires": ["gmail"],
        "steps": ["fetch", "classify", "summarize", "draft", "confirm_send"],
        "icon": "📧",
    },
    {
        "id": "meeting_autopilot",
        "name": "Meeting Autopilot Agent",
        "description": "Find a free slot, create the event, invite people and prepare an agenda.",
        "category": "productivity",
        "platforms": ["pc", "phone", "cloud"],
        "execution": "cloud",
        "risk": "confirm",
        "default": False,
        "requires": ["calendar"],
        "steps": ["parse", "find_slot", "create", "invite", "remind"],
        "icon": "📅",
    },
    {
        "id": "finance",
        "name": "Personal Finance Agent",
        "description": "Categorize expenses, check budgets, detect anomalies and build reports.",
        "category": "productivity",
        "platforms": ["pc", "phone", "cloud"],
        "execution": "cloud",
        "risk": "confirm",
        "default": True,
        "requires": ["pandas"],
        "steps": ["import", "categorize", "budget", "alert", "report"],
        "icon": "💰",
    },
    {
        "id": "security_sentinel",
        "name": "Security Sentinel Agent",
        "description": "Malware, network and breach checks with risk ranking and quarantine.",
        "category": "security",
        "platforms": ["pc", "cloud"],
        "execution": "pc",
        "risk": "danger",
        "default": False,
        "requires": [],
        "steps": ["scan", "network", "breach", "risk", "quarantine"],
        "icon": "🚨",
    },
    {
        "id": "privacy_guardian",
        "name": "Privacy Guardian Agent",
        "description": "Detect sensitive screen/clipboard data, blur it and audit privacy events.",
        "category": "security",
        "platforms": ["pc", "phone"],
        "execution": "pc",
        "risk": "confirm",
        "default": True,
        "requires": [],
        "steps": ["detect", "blur", "privacy_mode", "audit", "report"],
        "icon": "🕵️",
    },
]

AGENT_MAP: Dict[str, Dict[str, Any]] = {a["id"]: a for a in AGENTS}
DEFAULT_SETTINGS: Dict[str, bool] = {a["id"]: bool(a["default"]) for a in AGENTS}

# Lazy imports for agents that expose a test()/status() method.
AGENT_TEST_TARGETS: Dict[str, tuple] = {
    "coding": ("backend.agent.coding_agent", "coding_agent"),
    "screen_rpa": ("backend.agent.screen_rpa_agent", "screen_rpa_agent"),
    "research_pro": ("backend.agent.research_pro_agent", "research_pro_agent"),
    "doc_intel": ("backend.agent.doc_intel_agent", "doc_intel_agent"),
    "exam_coach": ("backend.agent.exam_coach_agent", "exam_coach_agent"),
    "yt_learn": ("backend.agent.yt_learn_agent", "yt_learn_agent"),
    "report_builder": ("backend.agent.report_builder_agent", "report_builder_agent"),
    "email_triage": ("backend.agent.email_triage_agent", "email_triage_agent"),
    "meeting_autopilot": ("backend.agent.meeting_autopilot_agent", "meeting_autopilot_agent"),
    "finance": ("backend.agent.finance_agent", "finance_agent"),
    "security_sentinel": ("backend.agent.security_sentinel_agent", "security_sentinel_agent"),
    "privacy_guardian": ("backend.agent.privacy_guardian_agent", "privacy_guardian_agent"),
}
CATEGORY_ORDER = ["core", "call", "study", "productivity", "security", "advanced"]


# ============================================================
# Persistence
# ============================================================
def _ensure_files() -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    if not SETTINGS_FILE.exists():
        _write_json(SETTINGS_FILE, DEFAULT_SETTINGS)


def _read_json(path: Path, fallback: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return fallback


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _load_settings() -> Dict[str, bool]:
    _ensure_files()
    raw = _read_json(SETTINGS_FILE, {})
    merged = dict(DEFAULT_SETTINGS)
    if isinstance(raw, dict):
        for key, value in raw.items():
            if key in DEFAULT_SETTINGS:
                merged[key] = bool(value)
    return merged


def _save_settings(settings: Dict[str, bool]) -> None:
    _write_json(SETTINGS_FILE, settings)


def _audit(action: str, agent_id: str, extra: Optional[Dict[str, Any]] = None) -> None:
    try:
        config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "action": action,
            "agent": agent_id,
            **(extra or {}),
        }
        with open(AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ============================================================
# Health checks
# ============================================================
def _has_module(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except Exception:
        return False


def _has_contacts() -> bool:
    data = _read_json(CONTACTS_FILE, [])
    if isinstance(data, dict):
        data = data.get("contacts", [])
    if not isinstance(data, list):
        return False
    return any(str(c.get("phone", "")).strip() for c in data if isinstance(c, dict))


def _has_telephony() -> bool:
    keys = ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_PHONE_NUMBER", "ATLAS_VIRTUAL_NUMBER"]
    if any(os.getenv(k) for k in keys):
        return True
    data = _read_json(config.DATA_DIR / "telephony.json", {})
    return bool(isinstance(data, dict) and data.get("provider"))


def _has_calendar() -> bool:
    # Meeting Autopilot ships with a built-in local calendar; Google Calendar is optional.
    return True


def _has_gmail() -> bool:
    return bool(
        (config.DATA_DIR / "gmail_token.json").exists()
        or os.getenv("GMAIL_TOKEN")
        or (os.getenv("ATLAS_IMAP_HOST") and os.getenv("ATLAS_IMAP_USER") and os.getenv("ATLAS_IMAP_PASS"))
        or (os.getenv("EMAIL_HOST") and os.getenv("EMAIL_USER") and os.getenv("EMAIL_PASS"))
    )


REQUIREMENT_CHECKS = {
    "contacts": _has_contacts,
    "whatsapp": lambda: True,  # deep link / phone bridge
    "accessibility": lambda: True,  # user enables it on the phone
    "virtual_number": _has_telephony,
    "telephony": _has_telephony,
    "stt": lambda: _has_module("whisper") or bool(os.getenv("DEEPGRAM_API_KEY") or os.getenv("GROQ_KEY_1")),
    "tts": lambda: _has_module("edge_tts") or bool(os.getenv("ELEVENLABS_API_KEY")),
    "consent": lambda: True,
    "git": lambda: bool(shutil.which("git")),
    "playwright": lambda: _has_module("playwright"),
    "yt-dlp": lambda: bool(shutil.which("yt-dlp")) or _has_module("yt_dlp"),
    "pyautogui": lambda: _has_module("pyautogui"),
    "pypdf": lambda: _has_module("pypdf") or _has_module("PyPDF2"),
    "python-pptx": lambda: _has_module("pptx"),
    "matplotlib": lambda: _has_module("matplotlib"),
    "pandas": lambda: _has_module("pandas"),
    "requests": lambda: _has_module("requests"),
    "beautifulsoup4": lambda: _has_module("bs4"),
    "gmail": _has_gmail,
    "calendar": _has_calendar,
}

REQUIREMENT_LABELS = {
    "contacts": "Contacts",
    "whatsapp": "WhatsApp",
    "accessibility": "Accessibility",
    "virtual_number": "Virtual number",
    "telephony": "Telephony",
    "stt": "Speech-to-text",
    "tts": "Text-to-speech",
    "consent": "Consent policy",
    "gmail": "Gmail OAuth",
    "calendar": "Calendar OAuth",
}


def _health_for(defn: Dict[str, Any], enabled: bool) -> Dict[str, Any]:
    missing: List[str] = []
    details: List[Dict[str, Any]] = []
    for req in defn.get("requires", []):
        check = REQUIREMENT_CHECKS.get(req)
        ok = True if check is None else bool(check())
        label = REQUIREMENT_LABELS.get(req, req)
        details.append({"key": req, "label": label, "ok": ok})
        if not ok:
            missing.append(label)

    status = "ready"
    if missing:
        status = "missing"
    if defn["id"] == "whatsapp_call" and not _has_contacts():
        status = "setup"
        if "Contacts" not in missing:
            missing.append("Contacts")
    if defn["id"] == "call_receptionist" and not _has_telephony():
        status = "setup"
        if "Virtual number" not in missing:
            missing.append("Virtual number")

    if not enabled:
        status = "disabled"

    return {
        "status": status,
        "missing": missing,
        "details": details,
        "note": _health_note(defn["id"], status),
    }


def _health_note(agent_id: str, status: str) -> str:
    if agent_id == "whatsapp_call" and status == "setup":
        return "Add a contact with a phone number. Desktop opens WhatsApp chat; Android places the call automatically."
    if agent_id == "call_receptionist" and status == "setup":
        return "Simulator is ready. Add a Twilio/SIP virtual number for real phone calls."
    if status == "ready":
        return "Ready"
    if status == "disabled":
        return "Turned off"
    return "Dependency or setup missing"


# ============================================================
# Public API
# ============================================================
class AgentRegistry:
    def list_agents(self) -> List[Dict[str, Any]]:
        with _lock:
            settings = _load_settings()
            result = []
            for defn in AGENTS:
                item = dict(defn)
                enabled = bool(settings.get(defn["id"], defn["default"]))
                item["enabled"] = enabled
                item["health"] = _health_for(defn, enabled)
                result.append(item)
            return result

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        for item in self.list_agents():
            if item["id"] == agent_id:
                return item
        return None

    def is_enabled(self, agent_id: str) -> bool:
        if agent_id not in AGENT_MAP:
            return True
        return bool(_load_settings().get(agent_id, AGENT_MAP[agent_id]["default"]))

    def enabled_ids(self) -> List[str]:
        settings = _load_settings()
        return [a["id"] for a in AGENTS if settings.get(a["id"], a["default"])]

    def enabled_tools(self) -> List[str]:
        return self.enabled_ids()

    def set_enabled(self, agent_id: str, enabled: bool) -> Dict[str, Any]:
        if agent_id not in AGENT_MAP:
            return {"success": False, "error": f"Unknown agent: {agent_id}"}
        with _lock:
            settings = _load_settings()
            settings[agent_id] = bool(enabled)
            _save_settings(settings)
            _audit("toggle", agent_id, {"enabled": bool(enabled)})
        return {
            "success": True,
            "agent": agent_id,
            "enabled": bool(enabled),
            "agent_info": self.get_agent(agent_id),
        }

    def toggle(self, agent_id: str) -> Dict[str, Any]:
        if agent_id not in AGENT_MAP:
            return {"success": False, "error": f"Unknown agent: {agent_id}"}
        return self.set_enabled(agent_id, not self.is_enabled(agent_id))

    def bulk_toggle(self, enabled: bool, category: Optional[str] = None) -> Dict[str, Any]:
        with _lock:
            settings = _load_settings()
            changed = []
            for defn in AGENTS:
                if category and category != "all" and defn["category"] != category:
                    continue
                settings[defn["id"]] = bool(enabled)
                changed.append(defn["id"])
            _save_settings(settings)
            _audit("bulk_toggle", category or "all", {"enabled": bool(enabled), "count": len(changed)})
        return {"success": True, "enabled": bool(enabled), "category": category or "all", "changed": changed}

    def summary(self) -> Dict[str, Any]:
        agents = self.list_agents()
        enabled = [a for a in agents if a["enabled"]]
        categories: Dict[str, Dict[str, int]] = {}
        for a in agents:
            cat = a["category"]
            categories.setdefault(cat, {"total": 0, "enabled": 0})
            categories[cat]["total"] += 1
            if a["enabled"]:
                categories[cat]["enabled"] += 1
        return {
            "agents": agents,
            "total": len(agents),
            "enabled_count": len(enabled),
            "disabled_count": len(agents) - len(enabled),
            "categories": [{"id": c, **categories.get(c, {}), "order": i} for i, c in enumerate(CATEGORY_ORDER) if c in categories],
            "platform": platform.system(),
        }

    def health_report(self) -> Dict[str, Any]:
        agents = self.list_agents()
        return {
            "success": True,
            "ready": sum(1 for a in agents if a["health"]["status"] == "ready"),
            "setup": sum(1 for a in agents if a["health"]["status"] == "setup"),
            "missing": sum(1 for a in agents if a["health"]["status"] == "missing"),
            "agents": {a["id"]: a["health"] for a in agents},
        }

    def test(self, agent_id: str) -> Dict[str, Any]:
        if agent_id not in AGENT_MAP:
            return {"success": False, "error": f"Unknown agent: {agent_id}"}
        info = self.get_agent(agent_id) or {}
        if agent_id == "whatsapp_call":
            try:
                from backend.communication.whatsapp_call_agent import whatsapp_call_agent
                return whatsapp_call_agent.test()
            except Exception as e:
                return {"success": False, "agent": agent_id, "error": str(e), "health": info.get("health")}
        if agent_id == "call_receptionist":
            try:
                from backend.communication.call_receptionist_agent import call_receptionist_agent
                return call_receptionist_agent.status()
            except Exception as e:
                return {"success": False, "agent": agent_id, "error": str(e), "health": info.get("health")}
        target = AGENT_TEST_TARGETS.get(agent_id)
        if target:
            module_name, attr = target
            try:
                module = importlib.import_module(module_name)
                agent = getattr(module, attr)
                if hasattr(agent, "test"):
                    result = agent.test()
                    if isinstance(result, dict):
                        result.setdefault("agent", agent_id)
                        result.setdefault("health", info.get("health"))
                    return result
            except Exception as e:
                return {"success": False, "agent": agent_id, "error": str(e), "health": info.get("health")}
        return {
            "success": info.get("health", {}).get("status") == "ready",
            "agent": agent_id,
            "message": "Agent is registered and healthy.",
            "health": info.get("health"),
        }


agent_registry = AgentRegistry()
