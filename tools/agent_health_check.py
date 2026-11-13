import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.agent.smart_planner import plan_command
from backend.agent.agent_registry import agent_registry
from backend.agent.agent_orchestrator import agent_orchestrator
from command_handler import is_agent_command


ROUTING = [
    "open youtube", "play music", "research AI", "deep research on AI in healthcare",
    "add expense 500 lunch", "how much did I spend", "schedule meeting tomorrow 3pm",
    "meeting list", "scan malware", "check email", "make presentation on AI in education",
    "code review backend/agent/base_agent.py", "screenshot", "due cards", "list documents",
    "privacy status", "password check 'abc123'", "explain quantum physics",
    "tell me about black holes", "how do I open a bank account", "open chrome",
    "youtube kholo", "optimize pc", "battery status", "system status", "find file report",
    "organize downloads", "play lofi beats", "what are my tasks", "remind me to call mom at 5pm",
    "translate hello to Bengali", "news", "git status", "summarize https://example.com",
    "open github.com", "thanks", "hello", "check my inbox", "set alarm at 7am", "lock pc",
    "youtube summary https://youtu.be/abc12345678", "close the door",
]

print("\n=== ROUTING ===")
for command in ROUTING:
    plan = plan_command(command)
    parsed = {"intent": "", "original_command": command}
    agent_cmd = is_agent_command(parsed)
    if plan:
        print(f"OK   {command!r:55} -> {plan.agent:18} {plan.intent:24} agent_cmd={agent_cmd}")
    else:
        print(f"CHAT {command!r:55} -> AI chat{' ' * 23} agent_cmd={agent_cmd}")

print("\n=== REGISTRY SELF TESTS ===")
for agent in agent_registry.list_agents():
    result = agent_registry.test(agent["id"])
    status = "PASS" if result.get("success") else "FAIL"
    message = str(result.get("message") or result.get("error") or "")[:140]
    print(f"{status} {agent['id']:20} enabled={agent['enabled']!s:5} health={agent['health']['status']:8} {message}")

print("\n=== SAFE ACTIONS ===")
SAFE = [
    "battery status",
    "system status",
    "find file config.py",
    "privacy status",
    "password check 'abc123'",
    "meeting list",
    "due cards",
    "git status",
    "list documents",
    "what are my tasks",
]
for command in SAFE:
    plan = plan_command(command)
    if not plan:
        print(f"SKIP {command!r} -> chat")
        continue
    result = agent_orchestrator.execute(plan.intent, dict(plan.entities), command)
    status = "OK  " if result.get("success") else "WARN"
    message = str(result.get("message") or "")[:180].replace("\n", " | ")
    print(f"{status} {command!r:35} -> {result.get('agent')}/{result.get('action')}: {message}")
