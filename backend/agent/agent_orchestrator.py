# backend/agent/agent_orchestrator.py
# Atlas 7.0 - Agent Orchestrator (Smart Router)

import re
from typing import Dict, Any, List

# Import all agents
from .pc_agent import PCAgent
from .file_agent import FileAgent
from .web_agent import WebAgent
from .media_agent import MediaAgent
from .productivity_agent import ProductivityAgent
from .security_agent import SecurityAgent
from .app_agent import AppAgent
from .terminal_agent import TerminalAgent
from .agent_registry import agent_registry
from .coding_agent import coding_agent
from .screen_rpa_agent import screen_rpa_agent
from .research_pro_agent import research_pro_agent
from .doc_intel_agent import doc_intel_agent
from .exam_coach_agent import exam_coach_agent
from .yt_learn_agent import yt_learn_agent
from .report_builder_agent import report_builder_agent
from .email_triage_agent import email_triage_agent
from .meeting_autopilot_agent import meeting_autopilot_agent
from .finance_agent import finance_agent
from .security_sentinel_agent import security_sentinel_agent
from .privacy_guardian_agent import privacy_guardian_agent
from backend.communication.whatsapp_call_agent import whatsapp_call_agent
from backend.communication.call_receptionist_agent import call_receptionist_agent


class AgentOrchestrator:
    def __init__(self):
        self.agents = {
            "pc": PCAgent(),
            "file": FileAgent(),
            "web": WebAgent(),
            "media": MediaAgent(),
            "productivity": ProductivityAgent(),
            "security": SecurityAgent(),
            "app": AppAgent(),
            "terminal": TerminalAgent(),
            "whatsapp_call": whatsapp_call_agent,
            "call_receptionist": call_receptionist_agent,
            "coding": coding_agent,
            "screen_rpa": screen_rpa_agent,
            "research_pro": research_pro_agent,
            "doc_intel": doc_intel_agent,
            "exam_coach": exam_coach_agent,
            "yt_learn": yt_learn_agent,
            "report_builder": report_builder_agent,
            "email_triage": email_triage_agent,
            "meeting_autopilot": meeting_autopilot_agent,
            "finance": finance_agent,
            "security_sentinel": security_sentinel_agent,
            "privacy_guardian": privacy_guardian_agent,
        }
        print(f"✅ Agent Orchestrator Loaded with {len(self.agents)} agents")

    def execute(self, intent: str, entities: Dict, original_command: str = "") -> Dict:
        """
        Smart Agent Routing Logic - Intent-based routing with keyword fallback
        """
        if not intent and not original_command:
            return {"success": False, "message": "No command detected"}

        intent_lower = intent.lower()
        cmd_lower = original_command.lower()
        entities = dict(entities or {})
        entities["_command"] = original_command

        # ========== CALL AGENTS (must run before generic app routing) ==========
        if ("whatsapp" in cmd_lower or "হোয়াটসঅ্যাপ" in cmd_lower or "wa " in cmd_lower) and any(
            word in cmd_lower for word in ("call", "কল", "dial", "ফোন")
        ):
            return self._run_agent("whatsapp_call", intent, entities)

        if any(word in cmd_lower for word in (
            "receptionist", "রিসেপশনিস্ট", "busy mode", "বিজি মোড",
            "call ধর", "কল ধর", "ai call", "ai কল", "call inbox",
            "simulate call", "test call", "call summary", "call list",
            "কল সামারি", "কল লিস্ট",
        )):
            return self._run_agent("call_receptionist", intent, entities)

        # ========== ADVANCED AGENTS (specific commands first) ==========
        advanced_agent = self._advanced_route(cmd_lower)
        if advanced_agent:
            return self._run_agent(advanced_agent, intent, entities)

        # ========== DIRECT INTENT MAPPING (Primary) ==========
        intent_map = {
            # Advanced agents
            "coding_review": "coding",
            "coding_scan": "coding",
            "coding_explain": "coding",
            "coding_fix": "coding",
            "coding_test": "coding",
            "screen_capture": "screen_rpa",
            "screen_analyze": "screen_rpa",
            "screen_click": "screen_rpa",
            "screen_type": "screen_rpa",
            "screen_hotkey": "screen_rpa",
            "deep_research": "research_pro",
            "research_report": "research_pro",
            "cite_sources": "research_pro",
            "doc_ingest": "doc_intel",
            "doc_ask": "doc_intel",
            "doc_list": "doc_intel",
            "exam_plan": "exam_coach",
            "exam_quiz": "exam_coach",
            "exam_flashcards": "exam_coach",
            "exam_weak_topics": "exam_coach",
            "yt_learn": "yt_learn",
            "yt_summarize": "yt_learn",
            "yt_transcript": "yt_learn",
            "presentation_build": "report_builder",
            "report_build": "report_builder",
            "email_triage": "email_triage",
            "email_inbox": "email_triage",
            "email_draft": "email_triage",
            "meeting_schedule": "meeting_autopilot",
            "meeting_list": "meeting_autopilot",
            "meeting_cancel": "meeting_autopilot",
            "finance_add": "finance",
            "finance_summary": "finance",
            "finance_budget": "finance",
            "security_scan": "security_sentinel",
            "malware_scan": "security_sentinel",
            "network_scan": "security_sentinel",
            "breach_check": "security_sentinel",
            "privacy_audit": "privacy_guardian",
            "privacy_mode": "privacy_guardian",
            "clipboard_check": "privacy_guardian",
            "blur_faces": "privacy_guardian",

            # Call agents
            "whatsapp_call": "whatsapp_call",
            "whatsapp_voice_call": "whatsapp_call",
            "call_whatsapp": "whatsapp_call",
            "call_contact_on_whatsapp": "whatsapp_call",
            "call_receptionist": "call_receptionist",
            "receptionist_status": "call_receptionist",
            "busy_mode_on": "call_receptionist",
            "busy_mode_off": "call_receptionist",
            "simulate_call": "call_receptionist",
            "list_calls": "call_receptionist",
            "callback": "call_receptionist",

            # App Agent
            "open_app": "app",
            "app_open": "app",

            # PC Agent
            "pc_optimize": "pc",
            "pc_clean": "pc",
            "pc_shutdown": "pc",
            "pc_restart": "pc",
            "pc_lock": "pc",
            "pc_sleep": "pc",
            "pc_battery": "pc",
            "pc_status": "pc",
            "pc_wifi": "pc",
            "pc_bluetooth": "pc",
            "process_manager": "pc",
            "startup_apps": "pc",

            # File Agent
            "file_organize": "file",
            "file_search": "file",
            "file_create": "file",
            "file_delete": "file",
            "file_copy": "file",
            "file_move": "file",
            "file_rename": "file",
            "file_backup": "file",

            # Web Agent
            "web_search": "web",
            "web_research": "web",
            "web_summarize": "web",
            "web_translate": "web",
            "web_bookmark": "web",
            "web_history": "web",
            "open_url": "web",
            "open_website": "web",

            # Media Agent
            "media_youtube": "media",
            "media_music": "media",
            "media_video": "media",
            "media_image": "media",
            "media_meme": "media",
            "media_download": "media",
            "media_subtitle": "media",
            "media_convert": "media",
            "youtube": "media",
            "play_youtube": "media",
            "play_music": "media",
            "generate_image": "media",
            "generate_meme": "media",

            # Productivity Agent
            "productivity_task": "productivity",
            "productivity_show_tasks": "productivity",
            "productivity_pomodoro": "productivity",
            "productivity_reminder": "productivity",
            "productivity_calendar": "productivity",
            "productivity_note": "productivity",
            "productivity_alarm": "productivity",
            "add_task": "productivity",
            "new_task": "productivity",
            "show_tasks": "productivity",
            "pomodoro": "productivity",
            "focus_mode": "productivity",
            "task": "productivity",
            "todo": "productivity",
            "reminder": "productivity",

            # Security Agent
            "security_lock": "security",
            "security_privacy": "security",
            "security_breach": "security",
            "security_password": "security",
            "security_scan": "security",
            "security_firewall": "security",
            "privacy_mode": "security",
            "enable_privacy": "security",
            "check_breach": "security",

            # Terminal Agent
            "terminal_run": "terminal",
            "terminal_git": "terminal",
            "terminal_pip": "terminal",
            "terminal_npm": "terminal",
            "git_status": "terminal",
            "git_pull": "terminal",
            "git_push": "terminal",
            "git_commit": "terminal",
            "pip_install": "terminal",
            "npm_install": "terminal",
        }

        # Try direct intent mapping first
        if intent_lower in intent_map:
            agent_key = intent_map[intent_lower]
            return self._run_agent(agent_key, intent, entities)

        # ========== KEYWORD FALLBACK (Secondary) ==========

        # ==================== APP / OPEN COMMANDS ====================
        app_keywords = [
            "open ", "launch ", "start ", "run ", "load ",
            "youtube", "chrome", "vscode", "gmail", "github", 
            "facebook", "whatsapp", "chatgpt", "spotify", "discord",
            "notion", "slack", "zoom", "teams", "excel", "word",
            "খোল", "চালু", "ওপেন", "লঞ্চ", "শুরু"
        ]
        if any(word in cmd_lower for word in app_keywords):
            return self._run_agent("app", intent, entities)

        # ==================== PC COMMANDS ====================
        pc_keywords = [
            "optimize", "clean", "boost", "speed", "tune",
            "shutdown", "turn off", "power off",
            "restart", "reboot", "reload",
            "lock", "screen lock",
            "sleep", "hibernate",
            "battery", "charge", "power",
            "system status", "pc status", "diagnostics", "health",
            "wifi", "internet", "network",
            "bluetooth", "pair",
            "process", "task manager", "kill ",
            "startup", "boot",
            "ফাস্ট", "পরিষ্কার", "শাটডাউন", "বন্ধ", "রিস্টার্ট",
            "লক", "ব্যাটারি", "সিস্টেম", "ওয়াইফাই"
        ]
        if any(word in cmd_lower for word in pc_keywords):
            return self._run_agent("pc", intent, entities)

        # ==================== FILE COMMANDS ====================
        file_keywords = [
            "organize", "sort", "arrange", "tidy",
            "downloads", "desktop", "documents",
            "file", "folder", "directory",
            "search file", "find file", "locate",
            "create file", "new file", "make file",
            "delete file", "remove file", "trash",
            "copy file", "duplicate", "clone",
            "move file", "transfer", "relocate",
            "rename", "change name",
            "backup", "save copy", "export",
            "গোছাও", "সাজাও", "ফাইল", "ফোল্ডার",
            "খুঁজ", "তৈরি", "ডিলিট", "কপি", "মুভ"
        ]
        if any(word in cmd_lower for word in file_keywords):
            return self._run_agent("file", intent, entities)

        # ==================== WEB / RESEARCH ====================
        web_keywords = [
            "research", "learn about", "tell me about", "explain",
            "search google", "search web", "google", "look up",
            "summarize", "summary", "tl;dr",
            "translate", "translation",
            "bookmark", "save page", "favorite",
            "history", "browsing",
            "খুঁজ", "জানতে", "ব্যাখ্যা", "সার্চ",
            "সারাংশ", "ট্রান্সলেট", "বুকমার্ক"
        ]
        if any(word in cmd_lower for word in web_keywords):
            return self._run_agent("web", intent, entities)

        # ==================== MEDIA ====================
        media_keywords = [
            "youtube", "video", "watch", "stream",
            "music", "song", "audio", "playlist", "spotify",
            "movie", "film", "clip",
            "image", "picture", "photo", "generate image",
            "meme", "funny image", "joke",
            "download video", "save song",
            "subtitle", "caption", "transcribe",
            "convert", "mp3", "mp4",
            "গান", "ভিডিও", "ছবি", "মিম", "ডাউনলোড",
            "সাবটাইটেল", "কনভার্ট"
        ]
        if any(word in cmd_lower for word in media_keywords):
            return self._run_agent("media", intent, entities)

        # ==================== PRODUCTIVITY ====================
        productivity_keywords = [
            "pomodoro", "focus", "concentrate", "timer", "study mode",
            "task", "todo", "to-do", "add task", "new task",
            "show tasks", "my tasks", "task list", "what to do",
            "remind", "reminder", "alert", "notify", "don't forget",
            "calendar", "schedule", "event", "appointment", "meeting",
            "note", "write down", "save note", "quick note",
            "alarm", "wake me", "set alarm",
            "টাস্ক", "কাজ", "পোমোডোরো", "ফোকাস",
            "রিমাইন্ডার", "ক্যালেন্ডার", "নোট", "অ্যালার্ম"
        ]
        if any(word in cmd_lower for word in productivity_keywords):
            return self._run_agent("productivity", intent, entities)

        # ==================== SECURITY ====================
        security_keywords = [
            "privacy", "private", "incognito", "hide",
            "breach", "hack", "compromised", "leak",
            "password", "pass check", "strong password",
            "scan", "virus", "malware", "security check",
            "firewall", "block", "allow",
            "lock system", "lock computer",
            "প্রাইভেসি", "ব্রিচ", "পাসওয়ার্ড",
            "ভাইরাস", "ফায়ারওয়াল", "নিরাপত্তা"
        ]
        if any(word in cmd_lower for word in security_keywords):
            return self._run_agent("security", intent, entities)

        # ==================== TERMINAL / DEV ====================
        terminal_keywords = [
            "run command", "execute", "terminal", "cmd", "shell",
            "git ", "commit", "push", "pull", "branch", "repository",
            "pip ", "install package", "python package",
            "npm ", "node ", "install module", "yarn",
            "রান", "এক্সিকিউট", "টার্মিনাল", "গিট", "পিপ"
        ]
        if any(word in cmd_lower for word in terminal_keywords):
            return self._run_agent("terminal", intent, entities)

        # ==================== INFO / WEATHER / TIME ====================
        info_keywords = [
            "weather", "temperature", "rain", "sunny", "forecast",
            "time", "what time", "clock", "current time",
            "date", "today", "day", "what day",
            "news", "headlines", "latest", "update",
            "আবহাওয়া", "তাপমাত্রা", "সময়", "তারিখ", "খবর"
        ]
        if any(word in cmd_lower for word in info_keywords):
            # Route info commands to Web Agent for online lookup
            return self._run_agent("web", intent, entities)

        # ==================== CHAT / GREETING ====================
        chat_keywords = [
            "hello", "hi", "hey", "how are you",
            "thanks", "thank you", "goodbye", "bye",
            "help", "what can you do", "capabilities", "features",
            "হ্যালো", "হাই", "কেমন", "ধন্যবাদ", "হেল্প"
        ]
        if any(word in cmd_lower for word in chat_keywords):
            return {"success": True, "message": "👋 Hello! I'm Atlas 7.0. How can I help you today?", "action": "chat"}

        # ==================== FALLBACK ====================
        return {
            "success": False,
            "message": "🤔 I didn't understand that command. Try: 'open youtube', 'optimize pc', 'organize downloads', 'research AI', or say 'help' for more options.",
            "action": "unknown",
            "original_command": original_command
        }

    def _advanced_route(self, command: str) -> str:
        """Keyword routing for the advanced agents (checked before generic fallback)."""
        cmd = str(command or "").lower()
        if not cmd:
            return ""

        def has(*words) -> bool:
            return any(word in cmd for word in words)

        def rx(pattern: str) -> bool:
            return re.search(pattern, cmd, flags=re.I) is not None

        # Coding Copilot
        if has("code review", "review code", "fix bug", "bug fix", "code likho", "code lekho",
               "repo scan", "scan repo", "refactor", "debug", "run tests", "test run", "coding",
               "কোড", "বাগ"):
            return "coding"
        if rx(r"\b(?:code|repo|repository)\b") and has("review", "scan", "explain", "fix", "test", "summary"):
            return "coding"

        # Screen Vision RPA
        if has("screenshot", "screen capture", "screen analyze", "screen dekho", "screen size",
               "screen click", "screen type", "screen scroll", "hotkey",
               "form fill", "স্ক্রিনশট", "স্ক্রিন", "ক্লিক", "টাইপ"):
            return "screen_rpa"
        if rx(r"\b(?:click|scroll|locate)\b.*\b(?:koro|korbo|kore)\b"):
            return "screen_rpa"

        # Document Intelligence
        if has("list documents", "document list", "doc list", "documents list"):
            return "doc_intel"
        if has(".pdf", ".docx", "pdf", "docx", "document intelligence") and has(
            "ask", "question", "summary", "summarize", "analyze", "analyse", "theke",
            "from", "bolo", "index", "প্রশ্ন", "সারাংশ", "পড়",
        ):
            return "doc_intel"

        # Deep Research
        if has("deep research", "গভীর গবেষণা", "research report", "citation", "cite source",
               "তথ্যসূত্র", "cross-check", "fact check", "multi-source"):
            return "research_pro"

        # YouTube Learning
        if has("youtube", "youtu.be", "youtu") and has(
            "summary", "summarize", "transcript", "learn", "notes", "quiz",
            "সারাংশ", "ট্রান্সক্রিপ্ট", "শিখ", "নোট", "পড়",
        ):
            return "yt_learn"

        # Exam Coach
        if has("due card", "due cards", "review card", "exam", "পরীক্ষা", "syllabus", "সিলেবাস",
               "flashcard", "mock test", "মক টেস্ট", "weak topic", "দুর্বল"):
            return "exam_coach"
        if rx(r"\bquiz\b.*\b(?:on|about|for)\b"):
            return "exam_coach"

        # Report / Presentation Builder
        if has("presentation", "slide deck", "slides on", "ppt", "প্রেজেন্টেশন", "স্লাইড"):
            return "report_builder"
        if has("list report", "list presentation", "report list", "presentation list"):
            return "report_builder"
        if has("report") and has("make", "build", "create", "on", "about", "বানাও", "তৈরি"):
            return "report_builder"

        # Email Triage
        if has("inbox", "email triage", "email check", "email status", "check email", "unread email",
               "draft reply", "email draft", "ইনবক্স", "ইমেইল"):
            return "email_triage"
        if has("gmail") and has("check", "inbox", "triage", "unread"):
            return "email_triage"

        # Meeting Autopilot
        if has("meeting", "মিটিং", "appointment", "অ্যাপয়েন্টমেন্ট"):
            return "meeting_autopilot"
        if has("calendar") and has("schedule", "add", "create", "event", "ইভেন্ট"):
            return "meeting_autopilot"

        # Personal Finance
        if has("expense", "spending", "budget", "finance", "খরচ", "বাজেট", "khoroch"):
            return "finance"
        if rx(r"\d+\s*(?:taka|tk|৳)") and has("add", "spend", "khoroch", "খরচ"):
            return "finance"

        # Security Sentinel
        if has("malware", "virus scan", "security scan", "breach", "quarantine", "network scan",
               "port scan", "ম্যালওয়্যার", "ভাইরাস", "নেটওয়ার্ক স্ক্যান", "সিকিউরিটি স্ক্যান"):
            return "security_sentinel"

        # Privacy Guardian
        if has("privacy audit", "privacy scan", "privacy status", "sensitive file", "clipboard", "blur", "watermark",
               "প্রাইভেসি অডিট", "ক্লিপবোর্ড", "সংবেদনশীল", "privacy mode", "privacy on", "privacy off"):
            return "privacy_guardian"

        return ""

    def _run_agent(self, agent_key: str, intent: str, entities: Dict) -> Dict:
        """Run an agent only when its toggle is ON."""
        agent = self.agents.get(agent_key)
        if agent is None:
            return {"success": False, "action": "agent_missing", "agent": agent_key,
                    "message": f"Agent '{agent_key}' is not registered."}
        if not agent_registry.is_enabled(agent_key):
            info = agent_registry.get_agent(agent_key) or {}
            name = info.get("name", agent_key)
            return {
                "success": False,
                "action": "agent_disabled",
                "agent": agent_key,
                "message": f"⛔ {name} বন্ধ আছে। Settings-এর পাশে Agents থেকে চালু করুন।",
            }
        try:
            result = agent.handle(intent, entities)
            if isinstance(result, dict):
                result.setdefault("agent", agent_key)
                return result
            return {"success": True, "action": "agent_result", "agent": agent_key, "message": str(result)}
        except AttributeError as exc:
            return {
                "success": False,
                "action": "agent_not_implemented",
                "agent": agent_key,
                "message": f"⚠️ {agent_key} agent-এ handle() নেই: {exc}",
            }
        except Exception as exc:
            return {
                "success": False,
                "action": "agent_error",
                "agent": agent_key,
                "message": f"❌ {agent_key} agent error: {exc}",
            }

    def get_all_capabilities(self) -> Dict:
        """সব Agent এর ক্যাপাবিলিটি দেখায়"""
        result = {}
        for name, agent in self.agents.items():
            getter = getattr(agent, "get_capabilities", None)
            try:
                result[name] = getter() if callable(getter) else []
            except Exception:
                result[name] = []
        return result

    def get_agent_status(self) -> Dict:
        """Get all agent status"""
        return {
            "status": "active",
            "agents_loaded": list(self.agents.keys()),
            "total_agents": len(self.agents),
            "enabled_agents": agent_registry.enabled_ids(),
            "platform": "Atlas 7.0"
        }


# Singleton Instance
agent_orchestrator = AgentOrchestrator()