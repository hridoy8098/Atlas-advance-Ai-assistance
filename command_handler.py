# backend/command_handler.py — Atlas 7.0 Agent Command Handler
# এটি AgentOrchestrator এর সাথে কানেক্ট করে

import re
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Any

import config
from backend.agent.agent_orchestrator import agent_orchestrator
from backend.agent.smart_planner import plan_command
from backend.core.weather import get_weather as fetch_weather
from backend.core.ai_engine import ai_engine
from backend.core.memory import memory_manager
from backend.core.language import language_detector
from backend.core.intent_classifier import classify_intent


def handle_agent_command(command: str, parsed: Dict, return_result: bool = False):
    """
    Agent Orchestrator এর মাধ্যমে কমান্ড হ্যান্ডেল করে।

    return_result=True হলে (message, agent_result) ফেরত দেয়, যাতে
    phone bridge / mobile app structured action (whatsapp_call_native,
    deep_link, contact, call) পেতে পারে।
    """
    intent = parsed.get('intent', '')
    entities = parsed.get('entities', {})
    original_command = command.strip()

    print(f"🤖 Agent Handler → Intent: {intent} | Command: {original_command}")

    # Orchestrator এ পাঠানো
    result = agent_orchestrator.execute(intent, entities, original_command)
    agent_result: Dict[str, Any] = result if isinstance(result, dict) else {}

    # The planner decided this is ordinary conversation, not an action.
    if result.get("handled") is False or result.get("action") in ("chat", "chat_fallback"):
        return (handle_ai_fallback(command), {}) if return_result else handle_ai_fallback(command)

    if result.get("success", False):
        message = result.get("message", "Command executed successfully.")
    # An agent that simply does not implement this intent should not leak a
    # raw "Command not supported" string into the voice reply.
    elif "not supported" in str(result.get("message", "")).lower():
        message = handle_ai_fallback(command)
        agent_result = {}
    # A registered agent may intentionally return a helpful failure
    # (disabled toggle, missing contact, setup needed). Don't hide it
    # behind the generic AI fallback.
    elif result.get("agent") or result.get("action") not in (None, "unknown"):
        message = result.get("message", "কমান্ডটি সম্পন্ন করা যায়নি।")
    else:
        message = handle_ai_fallback(command)
        agent_result = {}

    if return_result:
        return message, agent_result
    return message


def _language_prompt(command: str) -> str:
    """User যে ভাষায় কথা বলেছে, সেই ভাষায় reply করার instruction তৈরি করে।"""
    try:
        detected = language_detector.detect(command)
    except Exception:
        detected = "unknown"

    hints = {
        "bn": "The user is speaking Bengali (বাংলা). Reply in Bengali.",
        "banglish": "The user is speaking Banglish (romanized Bengali). Reply in Bengali (বাংলা).",
        "en": "The user is speaking English. Reply in English.",
        "mixed": "The user mixed languages. Reply in the same mix, keeping Bengali parts in Bengali.",
    }
    hint = hints.get(detected, "")

    return (
        "You are Atlas, a helpful voice assistant.\n"
        "LANGUAGE RULE (highest priority): Detect the language of the user's message and reply in that exact same language and script.\n"
        "- Bengali (বাংলা) or Banglish → reply in Bengali (বাংলা).\n"
        "- English → reply in English.\n"
        "- Hindi, Urdu, Arabic, or any other language → reply in that same language.\n"
        "Never switch to English unless the user wrote in English. Never translate unless asked.\n"
        f"{hint}\n"
        "Keep the reply concise, friendly, and practical. Reply with natural language only."
    )


def handle_ai_fallback(command: str) -> str:
    """AI দিয়ে সাধারণ উত্তর — user এর ভাষাতেই reply দেয়"""
    try:
        response = ai_engine.chat(
            f"User said: {command}\nBe helpful and practical.",
            system_prompt=_language_prompt(command)
        )
        return response
    except:
        try:
            lang = language_detector.get_response_language(command)
        except Exception:
            lang = "en"
        if lang == "bn":
            return "দুঃখিত, এই কমান্ডটি এখনো প্রসেস করতে পারছি না।"
        return "Sorry, I can't process this command right now."


def is_agent_command(parsed: Dict) -> bool:
    """Return True only for concrete actions the planner recognizes.

    Ordinary questions ("how do I open a bank account", "tell me about
    black holes") are intentionally not agent commands; they go to AI chat.
    """
    if not parsed:
        return False

    command = str(parsed.get("original_command") or "").strip()
    if command:
        try:
            return plan_command(command) is not None
        except Exception:
            pass

    # Structured callers without a natural command (phone bridge, tests).
    intent = str(parsed.get("intent") or "").lower()
    try:
        return intent in agent_orchestrator._intent_map()
    except Exception:
        return False


def _clean_location(value: Any) -> str:
    """Normalize a weather slot that Whisper may have over-filled.

    "What is the weather like today? I am speaking English." used to put the
    whole tail into the location slot, which then got geocoded as a city.
    """
    location = str(value or "").strip(" ?.,!।")
    location = re.split(r"[?।!]", location, maxsplit=1)[0].strip()
    for prefix in ("in ", "at ", "of ", "for "):
        if location.lower().startswith(prefix):
            location = location[len(prefix):].strip(" ?.,!।")
    location = re.sub(
        r"\b(?:like|today|now|currently|outside|weather|speaking)\b",
        " ",
        location,
        flags=re.IGNORECASE,
    )
    return " ".join(location.split()).strip(" ?.,!।")


def handle_info_command(intent: str, command: str, entities: Dict[str, Any]) -> str:
    """Answer time/date/weather locally.

    These used to be routed to WebAgent, which has no info handler and returned
    a raw "Command not supported" string. A direct answer is faster and works on
    the free cloud instance, where a browser cannot be opened.
    """
    try:
        lang = language_detector.detect(command)
    except Exception:
        lang = "en"
    bengali = lang in ("bn", "banglish", "mixed")

    tz_name = getattr(config, "TIMEZONE", "Asia/Dhaka") or "Asia/Dhaka"
    try:
        now = datetime.now(ZoneInfo(tz_name))
    except Exception:
        now = datetime.now()

    if intent == "info_time":
        if bengali:
            hour, minute = now.hour, now.minute
            if 4 <= hour < 6:
                period = "ভোর"
            elif 6 <= hour < 12:
                period = "সকাল"
            elif 12 <= hour < 16:
                period = "দুপুর"
            elif 16 <= hour < 18:
                period = "বিকাল"
            elif 18 <= hour < 20:
                period = "সন্ধ্যা"
            else:
                period = "রাত"
            hour12 = hour % 12 or 12
            if minute == 0:
                return f"এখন {period} {hour12}টা বাজে।"
            return f"এখন {period} {hour12}টা {minute} মিনিট।"
        clock = now.strftime("%I:%M %p").lstrip("0")
        return f"It's {clock}."

    if intent == "info_date":
        if bengali:
            days = ["সোমবার", "মঙ্গলবার", "বুধবার", "বৃহস্পতিবার", "শুক্রবার", "শনিবার", "রবিবার"]
            months = [
                "জানুয়ারি", "ফেব্রুয়ারি", "মার্চ", "এপ্রিল", "মে", "জুন",
                "জুলাই", "আগস্ট", "সেপ্টেম্বর", "অক্টোবর", "নভেম্বর", "ডিসেম্বর",
            ]
            return f"আজ {days[now.weekday()]}, {now.day} {months[now.month - 1]} {now.year}।"
        date_text = now.strftime("%A, %d %B %Y")
        return f"Today is {date_text}."

    if intent != "info_weather":
        return ""

    default_city = getattr(config, "DEFAULT_CITY", "Dhaka") or "Dhaka"
    location = _clean_location(entities.get("location"))

    city_aliases = {
        "ঢাকা": "Dhaka", "ঢাকায়": "Dhaka", "ঢাকার": "Dhaka",
        "লন্ডন": "London", "লন্ডনে": "London", "লন্ডনের": "London",
        "কলকাতা": "Kolkata", "কলকাতায়": "Kolkata", "কলকাতার": "Kolkata",
        "দিল্লি": "Delhi", "দিল্লিতে": "Delhi", "দিল্লির": "Delhi",
        "চট্টগ্রাম": "Chittagong", "সিলেট": "Sylhet",
    }
    for alias, english in city_aliases.items():
        if alias in command:
            location = english
            break
    if location.lower() in ("", "today", "now", "এখন", "আজ", "আমার", "my"):
        location = ""
    if location:
        entities["location"] = location
    else:
        entities.pop("location", None)

    candidates = [location, default_city] if location and location.lower() != default_city.lower() else [default_city]
    for city in candidates:
        weather = fetch_weather(city)
        if not weather:
            continue

        temp = weather["temp"]
        feels = weather["feels_like"]
        humidity = weather["humidity"]
        city_name = weather["city"]
        if bengali:
            city_bn = {
                "Dhaka": "ঢাকায়", "Chittagong": "চট্টগ্রামে", "Sylhet": "সিলেটে",
                "Kolkata": "কলকাতায়", "Delhi": "দিল্লিতে", "London": "লন্ডনে",
                "New York": "নিউইয়র্কে", "Tokyo": "টোকিওতে", "Dubai": "দুবাইয়ে",
            }
            place = city_bn.get(city_name, f"{city_name}-এ")
            return (
                f"{place} এখন {temp}°C, {weather['desc_bn']}। "
                f"অনুভূত হচ্ছে {feels}°C, আর্দ্রতা {humidity}%।"
            )
        return (
            f"It's {temp}°C in {city_name} with {weather['desc'].lower()}. "
            f"Feels like {feels}°C, humidity {humidity}%."
        )

    return ""


def get_command_response(command: str, platform: str = "desktop") -> dict:
    """
    Main entry point for processing user commands
    """
    command = command.strip()
    if not command:
        return {"response": "কিছু বলুন...", "success": False}

    started = time.perf_counter()

    # Step 1: Classify intent (local layers first, AI only when ambiguous)
    parsed = classify_intent(command)
    parsed['original_command'] = command
    entities = parsed.setdefault('entities', {})
    entities['platform'] = str(platform or "desktop").lower()

    # Step 2: Route to appropriate handler
    agent_result: Dict[str, Any] = {}
    if parsed.get("intent") in ("info_weather", "info_time", "info_date"):
        response_text = handle_info_command(parsed["intent"], command, entities)
        if not response_text:
            response_text = handle_ai_fallback(command)
    elif parsed.get("method") == "fast" or not is_agent_command(parsed):
        response_text = handle_ai_fallback(command)
    else:
        response_text, agent_result = handle_agent_command(command, parsed, return_result=True)

    # Step 3: Save to memory
    try:
        memory_manager.add_to_short_term("user", command)
        memory_manager.add_to_short_term("assistant", response_text)
    except:
        pass

    # Step 4: Detect language
    try:
        lang = language_detector.detect(command)
    except:
        lang = "unknown"

    result = {
        "response": response_text,
        "language": lang,
        "intent": parsed.get('intent', 'unknown'),
        "confidence": parsed.get('confidence', 0),
        "method": parsed.get('method', 'unknown'),
        "entities": parsed.get('entities', {}),
        "success": True,
        "latency_ms": int((time.perf_counter() - started) * 1000),
    }

    # Phone bridge needs the structured action, not only the text reply.
    if agent_result:
        result["agent_result"] = agent_result
        for key in (
            "action", "agent", "phone", "contact", "deep_link",
            "requires_bridge", "requires_manual_tap", "candidates", "call",
            "query", "hint", "needs_connector", "connector_command",
        ):
            if key in agent_result:
                result[key] = agent_result[key]

    return result


def get_agent_status() -> Dict:
    """Agent System এর স্ট্যাটাস"""
    try:
        capabilities = agent_orchestrator.get_all_capabilities()
        agent_status = agent_orchestrator.get_agent_status()
        return {
            "status": "active",
            "agents_loaded": agent_status.get("agents_loaded", []),
            "total_agents": agent_status.get("total_agents", 0),
            "capabilities": capabilities,
            "platform": "Atlas 7.0"
        }
    except Exception as e:
        return {"status": "error", "message": f"Agent system not loaded: {str(e)}"}


print("✅ Agent Handler Loaded Successfully")