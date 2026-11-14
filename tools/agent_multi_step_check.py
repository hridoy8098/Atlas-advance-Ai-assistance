"""Atlas 7.0 — full agent + multi-step verification harness.

Run:  python -X utf8 tools/agent_multi_step_check.py

It checks:
  1. deterministic routing for all 22 registered agents,
  2. multi-step planning for English / Banglish / Bengali compounds,
  3. real sequential execution with browser launches stubbed out,
  4. each agent's own self-test / health result.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.agent.agent_orchestrator import agent_orchestrator
from backend.agent.agent_registry import agent_registry
from backend.agent.media_agent import media_agent
from backend.agent.smart_planner import plan_command, plan_sequence
from command_handler import is_agent_command


ROUTING = {
    "battery status": ("pc", "pc_battery"),
    "open youtube": ("app", "open_app"),
    "find file config.py": ("file", "file_search"),
    "translate hello to Bengali": ("web", "web_translate"),
    "play lofi beats": ("media", "media_youtube_play"),
    "show my tasks": ("productivity", "productivity_show_tasks"),
    "generate password": ("security", "security_password"),
    "git status": ("terminal", "git_status"),
    "whatsapp call mom": ("whatsapp_call", "whatsapp_call"),
    "call receptionist status": ("call_receptionist", "call_receptionist"),
    "code review backend/agent/base_agent.py": ("coding", "coding_review"),
    "screenshot": ("screen_rpa", "screen_capture"),
    "deep research on AI in healthcare": ("research_pro", "deep_research"),
    "list documents": ("doc_intel", "doc_list"),
    "due cards": ("exam_coach", "exam_due_cards"),
    "youtube summary https://youtu.be/abc12345678": ("yt_learn", "yt_learn"),
    "make presentation on AI in education": ("report_builder", "presentation_build"),
    "check email": ("email_triage", "email_triage"),
    "meeting list": ("meeting_autopilot", "meeting_list"),
    "add expense 500 lunch": ("finance", "finance_add"),
    "scan malware": ("security_sentinel", "security_scan"),
    "privacy status": ("privacy_guardian", "privacy_audit"),
}

CHAT = [
    "how do I open a bank account",
    "tell me about black holes",
    "what is the weather today",
    "thanks",
    "hello",
]

SEQUENCES = [
    (
        "open youtube and search lofi beats and play",
        [("app", "open_app"), ("media", "media_youtube_play")],
        "lofi beats",
    ),
    (
        "youtube open kore lofi beats search kore play koro",
        [("media", "media_youtube_play")],
        "lofi beats",
    ),
    (
        "ইউটিউব খুলে লফি বিটস সার্চ করে চালাও",
        [("app", "open_app"), ("media", "media_youtube_play")],
        "লফি বিটস",
    ),
    ("battery status and system status", [("pc", "pc_battery"), ("pc", "pc_status")], ""),
    ("find file config.py and list documents", [("file", "file_search"), ("doc_intel", "doc_list")], ""),
    ("check email and list meetings", [("email_triage", "email_triage"), ("meeting_autopilot", "meeting_list")], ""),
    (
        "add task buy milk and show tasks",
        [("productivity", "productivity_task"), ("productivity", "productivity_show_tasks")],
        "",
    ),
    ("git status and battery status", [("terminal", "git_status"), ("pc", "pc_battery")], ""),
    (
        "play lofi beats and show my tasks",
        [("media", "media_youtube_play"), ("productivity", "productivity_show_tasks")],
        "",
    ),
    (
        "translate hello to Bengali and battery status",
        [("web", "web_translate"), ("pc", "pc_battery")],
        "",
    ),
    ("open youtube and play music", [("app", "open_app"), ("media", "media_youtube_play")], "music"),
    ("open youtube and search lofi beats", [("app", "open_app"), ("media", "media_youtube")], "lofi beats"),
    ("open youtube and search rock and roll", [("app", "open_app"), ("media", "media_youtube")], "rock and roll"),
    ("play rock and roll", [("media", "media_youtube_play")], "rock and roll"),
    ("check email then list meetings then battery status", [("email_triage", "email_triage"), ("meeting_autopilot", "meeting_list"), ("pc", "pc_battery")], ""),
]


failures = []


def report(ok, label, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {label}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        failures.append(label)


print("\n=== 1. SINGLE-COMMAND ROUTING (all 22 agents) ===")
for command, (agent, intent) in ROUTING.items():
    plan = plan_command(command)
    ok = bool(plan and plan.agent == agent and plan.intent == intent)
    report(ok, f"{command!r}", f"{plan.agent}/{plan.intent}" if plan else "no plan")
    if not is_agent_command({"original_command": command}):
        report(False, f"is_agent_command({command!r})", "returned False")

print("\n=== 2. CHAT GUARD ===")
for command in CHAT:
    plans = plan_sequence(command)
    report(not plans, f"chat: {command!r}", f"{len(plans)} plan(s)" if plans else "AI chat")

print("\n=== 3. MULTI-STEP PLANNING ===")
for command, expected, query in SEQUENCES:
    plans = plan_sequence(command)
    actual = [(plan.agent, plan.intent) for plan in plans]
    ok = actual == expected
    report(ok, f"{command!r}", f"{actual}" if not ok else f"{len(plans)} steps")
    if ok and query:
        queries = [str(plan.entities.get("query") or "") for plan in plans]
        report(any(query == value for value in queries), f"query preserved: {query!r}", f"{queries}")

print("\n=== 4. REAL SEQUENTIAL EXECUTION (browser launch stubbed) ===")
# Do not open real browser windows during verification. The agents still build
# real URLs, resolve real YouTube results and return real messages.
import backend.agent.app_agent as app_module

real_webbrowser_open = app_module.webbrowser.open
real_media_open = media_agent._open
opened_urls = []


def fake_webbrowser_open(url, *args, **kwargs):
    opened_urls.append(url)
    return True


app_module.webbrowser.open = fake_webbrowser_open
media_agent._open = lambda url: (opened_urls.append(url) or True)

EXECUTE = [
    ("open youtube and search lofi beats and play", 2),
    ("battery status and system status", 2),
    ("find file config.py and list documents", 2),
    ("git status and battery status", 2),
    ("play lofi beats and show my tasks", 2),
]

try:
    for command, expected_steps in EXECUTE:
        result = agent_orchestrator.execute("", {}, command)
        steps = result.get("steps") or []
        ok = (
            result.get("multi_step") is True
            and len(steps) == expected_steps
            and bool(result.get("success"))
        )
        report(
            ok,
            f"execute: {command!r}",
            f"steps={len(steps)} success={result.get('success')} "
            f"agents={[s.get('agent') for s in steps]}",
        )
        message = str(result.get("message") or "")
        duplicate_icons = re.search(r"(?:✅|⚠️)\s+\d+\.\s+(?:✅|⚠️)", message)
        report(
            not duplicate_icons,
            f"format: {command!r}",
            "double status icon" if duplicate_icons else "",
        )
        for step in steps:
            if not step.get("success"):
                report(False, f"  step {step['step']} {step['agent']}/{step['intent']}", step.get("message", "")[:160])
finally:
    app_module.webbrowser.open = real_webbrowser_open
    media_agent._open = real_media_open

print(f"\nURLs prepared by agents: {len(opened_urls)}")
for url in opened_urls:
    print(f"  {url[:140]}")

print("\n=== 5. AGENT SELF-TESTS (22) ===")
agents = agent_registry.list_agents()
for info in agents:
    agent_id = info["id"]
    result = agent_registry.test(agent_id)
    success = bool(result.get("success"))
    health = info["health"]["status"]
    expected_failure = health in ("setup", "missing", "disabled")
    label = f"{agent_id:20} enabled={str(info['enabled']):5} health={health:8}"
    if success:
        print(f"PASS  {label} {str(result.get('message') or '')[:120]}")
    elif expected_failure:
        missing = ", ".join(info["health"].get("missing") or []) or health
        print(f"SETUP {label} {missing} — {str(result.get('message') or result.get('error') or '')[:100]}")
    else:
        report(False, label, str(result.get("message") or result.get("error") or "")[:160])

print("\n=== SUMMARY ===")
print(f"Agents registered: {len(agents)}")
print(f"Unexpected failures: {len(failures)}")
for failure in failures:
    print(f"  - {failure}")
sys.exit(1 if failures else 0)
