# backend/agent_handler.py — Atlas 7.0 Agent Command Handler
# এটি AgentOrchestrator এর সাথে কানেক্ট করে

from typing import Dict, Any
from backend.agent.agent_orchestrator import agent_orchestrator
from backend.core.ai_engine import ai_engine
from backend.core.memory import memory_manager


def handle_agent_command(command: str, parsed: Dict) -> str:
    """
    Agent Orchestrator এর মাধ্যমে কমান্ড হ্যান্ডেল করে
    """
    intent = parsed.get('intent', '')
    entities = parsed.get('entities', {})
    original_command = command.strip()

    print(f"🤖 Agent Handler → Intent: {intent} | Command: {original_command}")

    # Orchestrator এ পাঠানো
    result = agent_orchestrator.execute(intent, entities, original_command)

    if result.get("success", False):
        message = result.get("message", "Command executed successfully.")
        return message
    else:
        # যদি কোনো Agent না মিলে তাহলে AI এর কাছে পাঠাবে
        return handle_ai_fallback(command)


def handle_ai_fallback(command: str) -> str:
    """AI দিয়ে সাধারণ উত্তর"""
    try:
        response = ai_engine.chat(f"User said: {command}\nBe helpful and practical.")
        return response
    except:
        return "দুঃখিত, এই কমান্ডটি এখনো প্রসেস করতে পারছি না।"


def is_agent_command(parsed: Dict) -> bool:
    """চেক করে এটা Agent এর কমান্ড কিনা"""
    if not parsed or 'intent' not in parsed:
        return False
    
    intent = parsed.get('intent', '').lower()
    command = parsed.get('original_command', '').lower() if 'original_command' in parsed else ""

    agent_keywords = [
        "open", "youtube", "chrome", "vscode", "gmail", "github",
        "optimize", "clean", "battery", "shutdown", "lock",
        "organize", "downloads", "file", "folder", "search",
        "research", "pomodoro", "task", "privacy", "security"
    ]

    return any(keyword in intent or keyword in command for keyword in agent_keywords)


def get_agent_status() -> Dict:
    """Agent System এর স্ট্যাটাস"""
    try:
        capabilities = agent_orchestrator.get_all_capabilities()
        return {
            "status": "active",
            "agents_loaded": list(agent_orchestrator.agents.keys()),
            "total_agents": len(agent_orchestrator.agents),
            "capabilities": capabilities
        }
    except:
        return {"status": "error", "message": "Agent system not loaded"}


print("✅ Agent Handler Loaded Successfully")