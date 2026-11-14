# backend/agent/agent_orchestrator.py
# Atlas 7.0 - Agent Orchestrator (Smart Router)
#
# Routing is deterministic: smart_planner.plan_command() decides whether a
# message is a concrete action and which agent/entities it belongs to. Ordinary
# questions return handled=False so command_handler sends them to AI chat.
# There is no substring keyword fallback anymore ("wa" -> WhatsApp, "open" in a
# question -> app launcher, etc.).

from __future__ import annotations

import re
from typing import Any, Dict, List

import config

# Import all agents
from .pc_agent import PCAgent
from .file_agent import FileAgent
from .web_agent import WebAgent
from .media_agent import MediaAgent
from .productivity_agent import ProductivityAgent
from .security_agent import SecurityAgent
from .app_agent import AppAgent
from .terminal_agent import TerminalAgent
from .agent_i18n import is_bengali
from .agent_registry import agent_registry
from .smart_planner import plan_command, plan_sequence
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

# Agents that only make sense on the user's own machine. When the cloud server
# is handling a command without a relayed laptop connector, they return setup
# instructions instead of touching the Render container.
PC_ONLY_AGENTS = {"pc", "screen_rpa"}

CONNECTOR_COMMAND = (
    "python connector/atlas_laptop.py "
    "--server https://atlas-7-api.onrender.com --token <pair-code>"
)

# Agents already prefix their message with a status icon (✅ / ⚠️ / ➡️ ...).
# In a multi-step list the step number supplies that status, so strip the inner
# prefix to avoid "✅ 1. ✅ Opened YouTube.".
_STATUS_PREFIX_RE = re.compile(r"^\s*(?:✅|⚠️|⚠|❌|❎|➡️|➡|✔️|✔|☑️|☑)+\s*")


def _strip_status_prefix(message: str) -> str:
    return _STATUS_PREFIX_RE.sub("", str(message or "")).strip()


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

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------
    def execute(self, intent: str, entities: Dict, original_command: str = "") -> Dict:
        entities = dict(entities or {})
        original = str(original_command or entities.get("_command") or "").strip()
        entities["_command"] = original
        intent_lower = str(intent or "").lower()

        # 1) Deterministic planner is the source of truth. Compound commands
        #    ("open youtube and search X and play") become an ordered sequence.
        plans = plan_sequence(original) if original else []
        if len(plans) > 1:
            return self._run_sequence(plans, original)
        if len(plans) == 1:
            plan = plans[0]
            merged = dict(entities)
            merged.update(plan.entities or {})
            merged["_command"] = original
            return self._run_agent(plan.agent, plan.intent, merged)

        # 2) Legacy direct callers (phone bridge, tests) may pass a precise
        #    agent intent without a natural-language command.
        if intent_lower in self._intent_map():
            return self._run_agent(self._intent_map()[intent_lower], intent, entities)

        # 3) Not an action: let command_handler use the AI chat path.
        return {
            "success": False,
            "action": "chat",
            "handled": False,
            "message": "",
            "original_command": original,
        }

    def _intent_map(self) -> Dict[str, str]:
        """Explicit intent -> agent map for structured callers only."""
        return {
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
            # App
            "open_app": "app",
            "app_open": "app",
            "open_folder": "app",
            # PC
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
            # File
            "file_organize": "file",
            "file_search": "file",
            "file_create": "file",
            "file_read": "file",
            "file_delete": "file",
            "file_copy": "file",
            "file_move": "file",
            "file_rename": "file",
            "file_list": "file",
            "file_info": "file",
            "disk_usage": "file",
            # Web
            "web_search": "web",
            "web_research": "web",
            "web_summarize": "web",
            "web_translate": "web",
            "web_bookmark": "web",
            "web_history": "web",
            "web_news": "web",
            "open_url": "web",
            "open_website": "web",
            "wikipedia_search": "web",
            # Media
            "media_youtube": "media",
            "media_youtube_play": "media",
            "media_music": "media",
            "media_image": "media",
            "media_meme": "media",
            "media_download": "media",
            "media_subtitle": "media",
            "media_background_remove": "media",
            "youtube": "media",
            "play_youtube": "media",
            "play_music": "media",
            "generate_image": "media",
            "generate_meme": "media",
            # Productivity
            "productivity_task": "productivity",
            "productivity_show_tasks": "productivity",
            "productivity_complete_task": "productivity",
            "productivity_delete_task": "productivity",
            "productivity_pomodoro": "productivity",
            "productivity_reminder": "productivity",
            "productivity_note": "productivity",
            "productivity_calendar": "productivity",
            "productivity_alarm": "productivity",
            "add_task": "productivity",
            "new_task": "productivity",
            "show_tasks": "productivity",
            "pomodoro": "productivity",
            "focus_mode": "productivity",
            "task": "productivity",
            "todo": "productivity",
            "reminder": "productivity",
            # Security
            "security_lock": "security",
            "security_privacy": "security",
            "security_breach": "security",
            "security_password": "security",
            "security_malware_scan": "security",
            "security_firewall": "security",
            "privacy_mode": "security",
            "enable_privacy": "security",
            "check_breach": "security",
            "breach_check": "security_sentinel",
            # Terminal
            "terminal_run": "terminal",
            "terminal_git": "terminal",
            "terminal_pip": "terminal",
            "terminal_npm": "terminal",
            "git_status": "terminal",
            "git_pull": "terminal",
            "git_push": "terminal",
            "git_commit": "terminal",
            "git_branch": "terminal",
            "pip_install": "terminal",
            "npm_install": "terminal",
            "ipconfig": "terminal",
            "ping": "terminal",
            "tasklist": "terminal",
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
            "screen_size": "screen_rpa",
            "deep_research": "research_pro",
            "research_report": "research_pro",
            "cite_sources": "research_pro",
            "doc_ingest": "doc_intel",
            "doc_ask": "doc_intel",
            "doc_list": "doc_intel",
            "exam_plan": "exam_coach",
            "exam_quiz": "exam_coach",
            "exam_flashcards": "exam_coach",
            "exam_due_cards": "exam_coach",
            "exam_weak_topics": "exam_coach",
            "exam_mock_test": "exam_coach",
            "yt_learn": "yt_learn",
            "yt_summarize": "yt_learn",
            "yt_transcript": "yt_learn",
            "yt_notes": "yt_learn",
            "yt_quiz": "yt_learn",
            "presentation_build": "report_builder",
            "report_build": "report_builder",
            "report_list": "report_builder",
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
            "password_check": "security_sentinel",
            "privacy_audit": "privacy_guardian",
            "clipboard_check": "privacy_guardian",
            "blur_faces": "privacy_guardian",
        }

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------
    def _run_agent(self, agent_key: str, intent: str, entities: Dict) -> Dict:
        """Run an agent only when its toggle is ON and the platform can run it."""
        agent = self.agents.get(agent_key)
        if agent is None:
            return {"success": False, "action": "agent_missing", "agent": agent_key,
                    "message": f"Agent '{agent_key}' is not registered."}

        if not agent_registry.is_enabled(agent_key):
            info = agent_registry.get_agent(agent_key) or {}
            name = info.get("name", agent_key)
            bengali = is_bengali(str(entities.get("_command", "")))
            message = (
                f"⛔ {name} বন্ধ আছে। Settings-এর পাশে Agents প্যানেল থেকে চালু করুন।"
                if bengali else
                f"⛔ {name} is turned off. Enable it in the Agents panel next to Settings."
            )
            return {"success": False, "action": "agent_disabled", "agent": agent_key,
                    "message": message}

        if getattr(config, "ATLAS_CLOUD", False) and agent_key in PC_ONLY_AGENTS:
            bengali = is_bengali(str(entities.get("_command", "")))
            message = (
                "🖥️ এই কাজটি আপনার ল্যাপটপে চালাতে হবে। ল্যাপটপ connector চালু করুন:\n"
                f"`{CONNECTOR_COMMAND}`\nতারপর আবার কমান্ড দিন।"
                if bengali else
                "🖥️ This is a laptop action. Start the laptop connector:\n"
                f"`{CONNECTOR_COMMAND}`\nThen ask again."
            )
            return {"success": False, "action": "needs_connector", "agent": agent_key,
                    "needs_connector": True, "connector_command": CONNECTOR_COMMAND,
                    "message": message}

        try:
            result = agent.handle(intent, entities)
            if isinstance(result, dict):
                result.setdefault("agent", agent_key)
                result.setdefault("action", str(intent or agent_key))
                return result
            return {"success": True, "action": "agent_result", "agent": agent_key, "message": str(result)}
        except AttributeError as exc:
            return {"success": False, "action": "agent_not_implemented", "agent": agent_key,
                    "message": f"⚠️ {agent_key} agent-এ handle() নেই: {exc}"}
        except Exception as exc:
            return {"success": False, "action": "agent_error", "agent": agent_key,
                    "message": f"❌ {agent_key} agent error: {exc}"}

    def _run_sequence(self, plans: list, original: str) -> Dict:
        """Execute an ordered multi-step plan and return one combined reply."""
        bengali = is_bengali(original)
        results: List[Dict] = []
        steps: List[Dict] = []

        for index, plan in enumerate(plans, 1):
            entities = dict(plan.entities or {})
            entities["_command"] = entities.get("_command") or original
            entities["_sequence_command"] = original
            entities["_step"] = index
            result = self._run_agent(plan.agent, plan.intent, entities)
            results.append(result)
            steps.append({
                "step": index,
                "agent": plan.agent,
                "intent": plan.intent,
                "action": result.get("action", plan.intent),
                "success": bool(result.get("success")),
                "message": str(result.get("message") or "").strip(),
            })

        successes = [result for result in results if result.get("success")]
        failures = [result for result in results if not result.get("success")]

        lines = []
        for step in steps:
            icon = "✅" if step["success"] else "⚠️"
            message = _strip_status_prefix(step["message"]) or (
                "সম্পন্ন হয়েছে।" if bengali and step["success"]
                else "Failed." if not step["success"] else "Done."
            )
            if len(message) > 600:
                message = message[:597].rstrip() + "..."
            lines.append(f"{icon} {step['step']}. {message}")

        header = "🧩 ধাপে ধাপে কাজ:" if bengali else "🧩 Multi-step:"
        message = header + "\n" + "\n".join(lines)

        aggregated: Dict[str, Any] = {}
        for result in reversed(results):
            for key in (
                "url", "deep_link", "phone", "contact", "requires_bridge",
                "requires_manual_tap", "call", "query",
            ):
                value = result.get(key)
                if key not in aggregated and value not in (None, "", False, []):
                    aggregated[key] = value

        if any(result.get("needs_connector") for result in results):
            aggregated["needs_connector"] = True
            connector = next(
                (result.get("connector_command") for result in results if result.get("connector_command")),
                CONNECTOR_COMMAND,
            )
            aggregated["connector_command"] = connector

        return {
            "success": not failures,
            "partial": bool(successes and failures),
            "action": "multi_step",
            "agent": "multi_step",
            "message": message,
            "multi_step": True,
            "step_count": len(steps),
            "steps": steps,
            "failed_steps": [step["step"] for step in steps if not step["success"]],
            **aggregated,
        }

    # Backward-compatible diagnostic helper. It is no longer used for routing.
    def _advanced_route(self, command: str) -> str:
        plan = plan_command(str(command or ""))
        return plan.agent if plan else ""

    def get_all_capabilities(self) -> Dict:
        result = {}
        for name, agent in self.agents.items():
            getter = getattr(agent, "get_capabilities", None)
            try:
                result[name] = getter() if callable(getter) else []
            except Exception:
                result[name] = []
        return result

    def get_agent_status(self) -> Dict:
        return {
            "status": "active",
            "agents_loaded": list(self.agents.keys()),
            "total_agents": len(self.agents),
            "enabled_agents": agent_registry.enabled_ids(),
            "platform": "Atlas 7.0"
        }


# Singleton Instance
agent_orchestrator = AgentOrchestrator()
