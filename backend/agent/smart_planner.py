# backend/agent/smart_planner.py — deterministic command planning for Atlas 7.0
#
# The old orchestrator routed commands with substring keyword checks
# ("wa" matched "malware", "open" matched "how do I open a bank account").
# This module is the single, testable source of truth for action commands:
#
#   * explicit action patterns run first (with word boundaries),
#   * app names must resolve exactly in a known app registry,
#   * ordinary questions always fall through to AI chat,
#   * every plan carries intent + entities so agents receive clean input.

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .agent_i18n import is_bengali


@dataclass
class Plan:
    agent: str
    intent: str
    entities: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.9
    reason: str = ""


_BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
_URL_RE = re.compile(r"(https?://[^\s<>\"']+|www\.[^\s<>\"']+|[\w.-]+\.(?:com|org|net|io|dev|ai|edu|gov|co|bd|uk)(?:/[^\s<>\"']*)?)", re.I)
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
_PATH_RE = re.compile(r"[\"“”']([^\"“”']{3,})[\"“”']|((?:[A-Za-z]:\\[^\s]+|(?:\.{0,2}[\\/])?[\w .\-\\/]+?\.[A-Za-z0-9]{1,8}))")
_AMOUNT_RE = re.compile(r"(?:৳|tk|taka|৳\s*)?\s*(\d+(?:[.,]\d+)?)\s*(?:tk|taka|৳)?", re.I)

# Exact app aliases. A command like "scan malware" can never match an app
# because aliases are compared as whole tokens, not substrings.
APP_ALIASES: Dict[str, tuple] = {
    "youtube": ("youtube", "you tube", "ইউটিউব", "ইউটিউবে", "yt"),
    "chrome": ("chrome", "google chrome", "ক্রোম", "browser", "ব্রাউজার"),
    "edge": ("edge", "microsoft edge", "ms edge"),
    "vscode": ("vscode", "vs code", "visual studio code", "code editor", "ভিএসকোড", "এডিটর"),
    "gmail": ("gmail", "জিমেইল"),
    "github": ("github", "গিটহাব"),
    "facebook": ("facebook", "fb", "ফেসবুক"),
    "messenger": ("messenger", "মেসেঞ্জার"),
    "whatsapp": ("whatsapp", "whats app", "হোয়াটসঅ্যাপ", "হোয়াটসঅ্যাপ", "হোয়াটস্"),
    "chatgpt": ("chatgpt", "chat gpt", "gpt", "চ্যাটজিপিটি"),
    "spotify": ("spotify", "স্পটিফাই"),
    "discord": ("discord", "ডিসকর্ড"),
    "telegram": ("telegram", "টেলিগ্রাম"),
    "notion": ("notion", "নোশন"),
    "slack": ("slack", "স্ল্যাক"),
    "zoom": ("zoom", "জুম"),
    "teams": ("teams", "microsoft teams", "টিমস", "টিমস্"),
    "excel": ("excel", "spreadsheet", "এক্সেল"),
    "word": ("word", "ms word", "microsoft word", "ওয়ার্ড"),
    "powerpoint": ("powerpoint", "power point", "ppt", "পাওয়ারপয়েন্ট"),
    "calculator": ("calculator", "calc", "ক্যালকুলেটর"),
    "terminal": ("terminal", "cmd", "command prompt", "powershell", "টার্মিনাল"),
    "settings": ("settings", "control panel", "সেটিংস", "সেটিংস্"),
    "explorer": ("explorer", "file explorer", "ফাইল এক্সপ্লোরার"),
    "notepad": ("notepad", "নোটপ্যাড"),
    "paint": ("paint", "mspaint", "পেইন্ট"),
    "taskmanager": ("task manager", "taskmanager", "টাস্ক ম্যানেজার"),
    "netflix": ("netflix", "নেটফ্লিক্স"),
    "instagram": ("instagram", "insta", "ইনস্টাগ্রাম"),
    "linkedin": ("linkedin", "লিংকডইন"),
    "reddit": ("reddit", "রেডিট"),
    "twitter": ("twitter", "x.com", "টুইটার"),
    "wikipedia": ("wikipedia", "উইকিপিডিয়া"),
    "maps": ("google maps", "maps", "ম্যাপ", "ম্যাপস"),
    "drive": ("google drive", "gdrive", "ড্রাইভ"),
    "stackoverflow": ("stack overflow", "stackoverflow", "স্ট্যাকওভারফ্লো"),
    "amazon": ("amazon", "অ্যামাজন"),
    "canva": ("canva", "ক্যানভা"),
}

_APP_FILLER = {
    "the", "my", "a", "an", "app", "application", "website", "site", "page",
    "ব্রাউজার", "অ্যাপ", "অ্যাপটি", "ওয়েবসাইট",
}


def _norm(text: Any) -> str:
    value = str(text or "").translate(_BN_DIGITS).lower()
    value = value.replace("’", "'").replace("“", '"').replace("”", '"')
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _strip_polite(text: str) -> str:
    # Keep the original case: URL paths and file names can be case-sensitive.
    value = str(text or "").replace("’", "'").replace("“", '"').replace("”", '"')
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(
        r"^(?:(?:hey|hi|ok|okay|atlas|jarvis|please|pls|kindly|একটু|প্লিজ|দয়া করে)\s+)+",
        "",
        value,
        flags=re.I,
    )
    value = re.sub(
        r"^(?:(?:can|could|would|will)\s+you\s+)",
        "",
        value,
        flags=re.I,
    )
    return value.strip(" .,!?।:;-")


def _clean_query(text: str) -> str:
    value = _strip_polite(text)
    value = re.sub(
        r"\s+(?:koro|korbo|kore|koren|please|pls|করো|করুন|দিন|দাও)$",
        "",
        value,
    )
    return value.strip(" .,!?।:;-\"'")


# ---------------------------------------------------------------------------
# Multi-step commands
# ---------------------------------------------------------------------------
# "open youtube and search lofi beats and play" must become a small ordered
# plan, not one app launch that silently ignores the rest of the sentence.
# Splitting is conservative: if any piece cannot be planned, the original
# sentence is kept intact and goes through normal single-command planning.
_SEQUENCE_SPLIT_RE = re.compile(
    r"\s*(?:"
    r"\band\s+then\b|\bthen\b|\btarpor\b|\btar\s+por\b|"
    r"(?<![\u0980-\u09ff])এর\s*পর(?![\u0980-\u09ff])|"
    r"(?<![\u0980-\u09ff])তারপর(?![\u0980-\u09ff])|"
    r"(?<![\u0980-\u09ff])এরপর(?![\u0980-\u09ff])|"
    r"\bkore\b|\bkhule\b|"
    r"(?<![\u0980-\u09ff])করে(?![\u0980-\u09ff])|"
    r"(?<![\u0980-\u09ff])খুলে(?![\u0980-\u09ff])|"
    r",|;|।|"
    r"\band\b|\bar\b|"
    r"(?<![\u0980-\u09ff])আর(?![\u0980-\u09ff])|"
    r"(?<![\u0980-\u09ff])এবং(?![\u0980-\u09ff])"
    r")\s*",
    re.I,
)

_QUOTED_RE = re.compile(r'"[^"]*"|\'[^\']*\'|“[^”]*”')


def _protect_quotes(text: str) -> tuple:
    kept = []

    def hide(match):
        kept.append(match.group(0))
        return f"\u00a7Q{len(kept) - 1}\u00a7"

    return _QUOTED_RE.sub(hide, text), kept


def _restore_quotes(text: str, kept: list) -> str:
    for index, value in enumerate(kept):
        text = text.replace(f"\u00a7Q{index}\u00a7", value)
    return text


def split_steps(command: str) -> list:
    text = _strip_polite(command)
    if not text or not _SEQUENCE_SPLIT_RE.search(text):
        return [text] if text else []

    protected, kept = _protect_quotes(text)
    parts = [
        _restore_quotes(part.strip(" .,!?।:;-"), kept)
        for part in _SEQUENCE_SPLIT_RE.split(protected)
        if part.strip(" .,!?।:;-")
    ]
    if len(parts) < 2:
        return [text]
    return parts


def _step_query(plan: Plan) -> str:
    return _norm(plan.entities.get("query") or plan.entities.get("topic") or "")


def _advance_context(context: dict, plan: Plan) -> None:
    if plan.agent == "app" and plan.intent == "open_app":
        app = str(plan.entities.get("app_name") or "")
        if app:
            context["app"] = app
    if plan.agent == "media":
        if plan.intent in ("media_youtube", "media_youtube_play"):
            context["app"] = "youtube"
        query = str(plan.entities.get("query") or "")
        if query:
            context["last_query"] = query
    if plan.agent == "web" and plan.intent in ("web_search", "web_research", "wikipedia_search"):
        query = str(plan.entities.get("query") or plan.entities.get("topic") or "")
        if query:
            context["last_query"] = query


def _collapse_plans(plans: list) -> list:
    """Remove redundant steps while keeping the visible order."""
    deduped = []
    for plan in plans:
        if (
            deduped
            and deduped[-1].agent == plan.agent
            and deduped[-1].intent == plan.intent
            and _step_query(deduped[-1]) == _step_query(plan)
        ):
            continue
        deduped.append(plan)

    # "youtube search X" followed by "play" is one real action: search+play.
    collapsed = []
    for index, plan in enumerate(deduped):
        if plan.agent == "media" and plan.intent == "media_youtube":
            following = deduped[index + 1] if index + 1 < len(deduped) else None
            if (
                following
                and following.agent == "media"
                and following.intent == "media_youtube_play"
                and _step_query(plan) == _step_query(following)
            ):
                continue
        collapsed.append(plan)
    return collapsed


def _context_rules(cmd: str, context: dict) -> Optional[Plan]:
    """Resolve elliptical steps such as “search lofi” + “play”."""
    if not context or context.get("app") != "youtube":
        return None

    last_query = str(context.get("last_query") or "")

    if _m(
        r"^(?:play|start|chalao|chala|bajao|sunao|chaliye\s*chalao|"
        r"চালাও|চালিয়ে\s*চালাও|চালিয়ে|বাজাও|শোনাও)"
        r"(?:\s+(?:it|that|eta|এটা))?$",
        cmd,
    ):
        return _plan(
            "media", "media_youtube_play", "youtube play (context)",
            {"query": last_query, "_command": cmd},
        )

    play_any = _m(r"^(?:play|chalao|chala|bajao|sunao)\s+(.+)$|^(?:চালাও|বাজাও|শোনাও)\s+(.+)$", cmd)
    if play_any:
        query = _clean_query(next((group for group in play_any.groups() if group), ""))
        if query and _norm(query) not in ("it", "that", "eta", "এটা"):
            return _plan("media", "media_youtube_play", "youtube play (context)",
                         {"query": query, "_command": cmd})

    search = _m(
        r"^(?:search|find|look\s+for|খুঁজো|খোঁজো|সার্চ)\s*(?:for|on\s+youtube)?\s*(.+)$",
        cmd,
    )
    if search:
        query = _clean_query(search.group(1))
        if query:
            return _plan("media", "media_youtube", "youtube search (context)",
                         {"query": query, "_command": cmd})

    search_after = _m(
        r"^(.+?)\s+(?:search|খুঁজো|খোঁজো|সার্চ)\s*(?:koro|kor|koren|করো|করুন)?$",
        cmd,
    )
    if search_after:
        query = _clean_query(search_after.group(1))
        if query:
            return _plan("media", "media_youtube", "youtube search (context)",
                         {"query": query, "_command": cmd})
    return None


def _rx(pattern: str, text: str) -> Optional[re.Match]:
    return _s(pattern, text, re.IGNORECASE)


def _word(alias: str) -> str:
    return r"(?<![a-z0-9\u0980-\u09ff])" + re.escape(alias) + r"(?![a-z0-9\u0980-\u09ff])"


def _resolve_app(raw: str) -> Optional[str]:
    token = _norm(raw)
    token = re.sub(r"\b(?:app|application|website|site|page)\b", " ", token)
    token = " ".join(word for word in token.split() if word not in _APP_FILLER)
    token = token.strip(" .,!?।:;-\"'")

    # Direct alias / canonical name.
    for canonical, aliases in APP_ALIASES.items():
        for alias in (canonical,) + tuple(aliases):
            if token == _norm(alias):
                return canonical
    # "google chrome browser" / "youtube app" style leftovers.
    for canonical, aliases in APP_ALIASES.items():
        for alias in (canonical,) + tuple(aliases):
            alias_norm = _norm(alias)
            if not alias_norm:
                continue
            if len(alias_norm) >= 4 and _s(_word(alias_norm), token):
                return canonical
    return None


def _resolve_app_exact(raw: str) -> Optional[str]:
    token = _norm(raw)
    token = re.sub(r"\b(?:app|application|website|site|page)\b", " ", token)
    token = " ".join(word for word in token.split() if word not in _APP_FILLER)
    token = token.strip(" .,!?।:;-\"'")
    for canonical, aliases in APP_ALIASES.items():
        for alias in (canonical,) + tuple(aliases):
            if token == _norm(alias):
                return canonical
    return None


def _extract_url(text: str) -> str:
    match = _URL_RE.search(_strip_polite(text))
    if not match:
        return ""
    value = match.group(0).strip().rstrip(".,;!?।")
    if value and not value.lower().startswith(("http://", "https://")):
        value = "https://" + value
    return value


def _extract_path(text: str) -> str:
    quoted = _s(r"[\"“”']([^\"“”']{3,})[\"“”']", str(text or ""))
    if quoted:
        return quoted.group(1).strip()
    match = _PATH_RE.search(str(text or ""))
    if not match:
        return ""
    value = (match.group(1) or match.group(2) or "").strip()
    # A path regex can swallow leading words ("review backend/file.py").
    # Pick the first token that looks like a path, keeping the rest intact.
    tokens = value.split()
    for index, token in enumerate(tokens):
        if _s(r"[\\/]|\.[A-Za-z0-9]{1,8}$", token):
            value = " ".join(tokens[index:])
            break
    return value


def _amount(text: str) -> Optional[float]:
    value = str(text or "").translate(_BN_DIGITS).replace(",", "")
    match = _AMOUNT_RE.search(value)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _minutes(text: str) -> int:
    value = str(text or "").translate(_BN_DIGITS)
    match = _s(r"(\d+)\s*(?:min|mins|minute|minutes|মিনিট)?", value, re.I)
    if not match:
        return 25
    try:
        return max(1, min(int(match.group(1)), 240))
    except ValueError:
        return 25


def _plan(agent: str, intent: str, reason: str, entities: Optional[Dict[str, Any]] = None, confidence: float = 0.9) -> Plan:
    return Plan(agent=agent, intent=intent, entities=entities or {}, confidence=confidence, reason=reason)


# ---------------------------------------------------------------------------
# Rule groups. Each returns a Plan or None.
# ---------------------------------------------------------------------------

def _call_rules(cmd: str) -> Optional[Plan]:
    if _s(r"\bwhats\s*app\b|হোয়াটসঅ্যাপ", cmd) and _s(r"\b(?:call|dial|kol)\b|কল|ফোন", cmd):
        return _plan("whatsapp_call", "whatsapp_call", "whatsapp call", {"_command": cmd})
    if _s(
        r"\b(?:receptionist|busy mode|call inbox|simulate call|test call|call summary|"
        r"call list|callback|call back)\b|রিসেপশনিস্ট|বিজি মোড|কল ধর|কল সামারি|কল লিস্ট",
        cmd,
    ):
        return _plan("call_receptionist", "call_receptionist", "call receptionist", {"_command": cmd})
    return None


def _app_rules(cmd: str) -> Optional[Plan]:
    url = _extract_url(cmd)
    if _m(r"^(?:open|launch|visit|go to|খোল|ওপেন)\b", cmd) and url:
        return _plan("web", "open_url", "open url", {"url": url, "_command": cmd})

    folder_match = _m(
        r"^(?:open|show|খোলো|খোল|দেখাও)\s+(?:my\s+|the\s+)?"
        r"(downloads?|desktop|documents?|pictures?|photos?|music|videos?)\s*(?:folder|directory|ফোল্ডার)$",
        cmd,
        re.I,
    )
    if folder_match:
        folder = folder_match.group(1).lower()
        folder = {
            "download": "downloads", "document": "documents", "picture": "pictures",
            "photo": "pictures", "video": "videos",
        }.get(folder, folder)
        return _plan("app", "open_folder", f"open {folder} folder", {"folder": folder, "_command": cmd})

    open_en = _m(
        r"^(?:(?:open|launch|start|run|load))\s+(?:the\s+|my\s+)?(.+)$",
        cmd,
        re.I,
    )
    open_bn = _m(
        r"^(.+?)\s+(?:খোলো|খোল|চালু\s*করো|চালু\s*কর|চালু|ওপেন\s*করো|ওপেন\s*কর|ওপেন)$",
        cmd,
        re.I,
    )
    match = open_en or open_bn
    if not match:
        # "youtube kholo" style Banglish
        match = _m(r"^(.+?)\s+(?:kholo|khol|chalu\s*koro|chalu\s*kor|open\s*koro)$", cmd, re.I)

    if match:
        raw = match.group(1).strip()
        # "open youtube and play music" is not a single app launch.
        if _s(r"\b(?:and|then|ar|আর)\b", raw):
            return None
        app = _resolve_app(raw)
        if app:
            return _plan("app", "open_app", f"known app: {app}", {"app_name": app, "_command": cmd})

    # App name alone ("youtube", "chrome") — exact aliases only, so
    # "youtube summary <url>" cannot be mistaken for opening the app.
    app = _resolve_app_exact(cmd)
    if app:
        return _plan("app", "open_app", f"known app: {app}", {"app_name": app, "_command": cmd})
    return None


def _pc_rules(cmd: str) -> Optional[Plan]:
    if _s(r"\b(?:shutdown|shut down|power off|turn off)\b.*\b(?:pc|computer|laptop|system)\b", cmd) or \
       _s(r"\b(?:pc|computer|laptop|system)\b.*\b(?:shutdown|shut down|power off)\b", cmd) or \
       _s(r"(?:পিসি|কম্পিউটার|ল্যাপটপ|সিস্টেম).*(?:শাটডাউন|বন্ধ)", cmd) or cmd in ("shutdown", "shut down", "শাটডাউন"):
        return _plan("pc", "pc_shutdown", "shutdown", {"_command": cmd})
    if _s(r"\b(?:restart|reboot)\b|রিস্টার্ট", cmd):
        return _plan("pc", "pc_restart", "restart", {"_command": cmd})
    if _s(r"\block\s+(?:the\s+)?(?:pc|screen|computer|system)\b|\block\s*screen\b|সিস্টেম\s*লক|স্ক্রিন\s*লক", cmd) or \
       _m(r"^(?:lock|লক)(?:\s+(?:pc|computer|system|পিসি|কম্পিউটার|সিস্টেম))?$", cmd):
        return _plan("pc", "pc_lock", "lock", {"_command": cmd})
    if _s(r"\b(?:sleep|hibernate)\b|ঘুম", cmd):
        return _plan("pc", "pc_sleep", "sleep", {"_command": cmd})
    if _s(r"\bbattery\b|ব্যাটারি|চার্জ|\bcharge\s+(?:status|level)\b", cmd):
        return _plan("pc", "pc_battery", "battery", {"_command": cmd})
    if _s(
        r"\b(?:system|pc)\s+status\b|\bdiagnostics?\b|\bhealth\s+check\b|"
        r"\b(?:cpu|ram|memory)\s+(?:usage|status|load)\b|\bhow\s+is\s+my\s+(?:pc|computer|laptop)\b|"
        r"সিস্টেম\s*স্ট্যাটাস|পিসি\s*স্ট্যাটাস",
        cmd,
    ):
        return _plan("pc", "pc_status", "system status", {"_command": cmd})
    if _s(r"\b(?:wi-?fi|internet|network)\s+(?:status|connection|info)\b|\bwi-?fi\b|ওয়াইফাই|ইন্টারনেট", cmd):
        if _s(r"\b(?:off|disable|বন্ধ)\b", cmd):
            return _plan("pc", "pc_wifi", "wifi off", {"enable": False, "_command": cmd})
        if _s(r"\b(?:on|enable|চালু)\b", cmd):
            return _plan("pc", "pc_wifi", "wifi on", {"enable": True, "_command": cmd})
        return _plan("pc", "pc_wifi", "wifi status", {"_command": cmd})
    if _s(r"\bbluetooth\b|ব্লুটুথ", cmd):
        if _s(r"\b(?:off|disable|বন্ধ)\b", cmd):
            return _plan("pc", "pc_bluetooth", "bluetooth off", {"enable": False, "_command": cmd})
        if _s(r"\b(?:on|enable|চালু)\b", cmd):
            return _plan("pc", "pc_bluetooth", "bluetooth on", {"enable": True, "_command": cmd})
        return _plan("pc", "pc_bluetooth", "bluetooth status", {"_command": cmd})
    if _s(
        r"\b(?:optimize|boost|tune\s*up|speed\s*up|clean\s*(?:pc|temp|junk|ram)|"
        r"free\s+(?:up\s+)?space|disk\s*cleanup|clear\s*temp)\b|অপটিমাইজ|জাঙ্ক|পরিষ্কার\s*কর",
        cmd,
    ):
        return _plan("pc", "pc_optimize", "optimize", {"_command": cmd})
    if _s(r"\b(?:top\s+)?process(?:es)?\b|\btask\s*manager\b|\bkill\s+process\b|প্রসেস", cmd):
        return _plan("pc", "process_manager", "processes", {"_command": cmd})
    if _s(r"\bstartup\s+(?:apps|programs|items)\b|স্টার্টআপ", cmd):
        return _plan("pc", "startup_apps", "startup apps", {"_command": cmd})
    return None


def _file_rules(cmd: str) -> Optional[Plan]:
    location = ""
    for key, aliases in {
        "downloads": ("downloads", "download", "ডাউনলোড", "ডাউনলোডস"),
        "desktop": ("desktop", "ডেস্কটপ"),
        "documents": ("documents", "docs", "ডকুমেন্ট", "ডকুমেন্টস"),
        "pictures": ("pictures", "photos", "images", "ছবি", "ফটো"),
    }.items():
        if any(_s(_word(alias), cmd) for alias in aliases):
            location = key
            break

    if _s(r"\b(?:organize|sort|tidy|arrange)\b|গোছাও|সাজাও|অর্গানাইজ", cmd):
        return _plan("file", "file_organize", "organize folder", {"location": location or "downloads", "_command": cmd})

    if _s(r"\bdisk\s*(?:usage|space)\b|\bstorage\s*(?:usage|space|status)\b|ডিস্ক\s*স্পেস", cmd):
        return _plan("file", "disk_usage", "disk usage", {"_command": cmd})

    list_match = _s(
        r"\blist\s+(?:the\s+)?(?:files|contents|folders)\b(?:\s+(?:in|of|at)\s+(.+))?|"
        r"\b(?:list|show)\s+(?:my\s+)?(?:downloads|desktop)\b|"
        r"\bshow\s+(?:me\s+)?(?:my\s+)?files\b",
        cmd,
    )
    if list_match:
        path = (list_match.group(1) or "").strip() or location
        return _plan("file", "file_list", "list folder", {"path": path, "location": location, "_command": cmd})
    if _s(
        r"(?:ফাইল|ফোল্ডার|ডাউনলোড)\s*(?:লিস্ট|তালিকা|দেখাও|দেখান|কি\s*আছে)|"
        r"(?:লিস্ট|তালিকা)\s*(?:দেখাও|করো)?\s*(?:ফাইল|ফোল্ডার)",
        cmd,
    ):
        return _plan("file", "file_list", "list folder", {"path": "", "location": location, "_command": cmd})

    find_match = _s(
        r"\b(?:find|search|locate)\s+(?:for\s+)?(?:a\s+|the\s+)?(?:file|folder)\s+(.+)$|"
        r"\b(?:find|locate)\s+(?:a\s+|the\s+)?(.+?)\s+(?:file|folder)\b|"
        r"\bwhere\s+is\s+(?:the\s+)?(?:file\s+)?(.+)$",
        cmd,
    )
    if find_match:
        query = next((group for group in find_match.groups() if group), "").strip()
        query = re.sub(r"\s+(?:file|folder|ফাইল)$", "", query).strip()
        # "where is dhaka" is a question, not a file search.
        if query and not (cmd.startswith("where is") and not _s(r"[.\\/]|file|folder|pdf|doc|xlsx|jpg|png", query)):
            return _plan("file", "file_search", "find file", {"query": query, "location": location, "_command": cmd})

    bn_find = _s(
        r"(?:ফাইল|ফোল্ডার)\s*(?:খুঁজো|খোঁজো|খুঁজে\s*(?:দাও|বের\s*করো)|সার্চ\s*করো)\s*(.*)$|"
        r"(.+?)\s*(?:ফাইল|ফোল্ডার)\s*(?:খুঁজো|খোঁজো|খুঁজে\s*(?:দাও|বের\s*করো))$",
        cmd,
    )
    if bn_find:
        query = next((group for group in bn_find.groups() if group), "").strip(" ?।.,")
        if query:
            return _plan("file", "file_search", "find file", {"query": query, "location": location, "_command": cmd})

    if _s(r"\bcreate\s+(?:a\s+)?(?:new\s+)?file\b|\bmake\s+(?:a\s+)?file\b|ফাইল\s*(?:বানাও|তৈরি)", cmd):
        path = _extract_path(cmd)
        return _plan("file", "file_create", "create file", {"path": path, "_command": cmd})

    if _s(r"\bdelete\s+(?:the\s+)?file\b|\bremove\s+(?:the\s+)?file\b|ফাইল\s*ডিলিট", cmd):
        return _plan("file", "file_delete", "delete file", {"path": _extract_path(cmd), "_command": cmd})

    copy_match = _s(r"\bcopy\s+(?:the\s+)?file\s+(.+?)\s+(?:to|into)\s+(.+)$", cmd)
    if copy_match:
        return _plan("file", "file_copy", "copy file", {"source": copy_match.group(1).strip(), "destination": copy_match.group(2).strip(), "_command": cmd})

    move_match = _s(r"\bmove\s+(?:the\s+)?file\s+(.+?)\s+(?:to|into)\s+(.+)$", cmd)
    if move_match:
        return _plan("file", "file_move", "move file", {"source": move_match.group(1).strip(), "destination": move_match.group(2).strip(), "_command": cmd})

    rename_match = _s(r"\brename\s+(?:the\s+)?file\s+(.+?)\s+(?:to|as)\s+(.+)$", cmd)
    if rename_match:
        return _plan("file", "file_rename", "rename file", {"path": rename_match.group(1).strip(), "new_name": rename_match.group(2).strip(), "_command": cmd})

    if _s(r"\bfile\s+(?:info|details)\b|\bdetails\s+of\s+(?:the\s+)?file\b", cmd):
        return _plan("file", "file_info", "file info", {"path": _extract_path(cmd), "_command": cmd})
    return None


_YT_WORD_RE = re.compile(r"\b(?:youtube|you\s*tube|yt|ইউটিউবে?|ইউটিউব)\b", re.I)
_YT_PLAY_VERB_RE = re.compile(
    r"\b(?:play|chalao|chala|bajao|sunao|chaliye\s*chalao|"
    r"চালাও|চালিয়ে\s*চালাও|চালিয়ে|বাজাও|শোনাও)\b",
    re.I,
)


def _youtube_play_query(text: str) -> str:
    """Extract the real search query from “youtube ... search ... play ...”."""
    value = _strip_polite(text)
    if not _YT_WORD_RE.search(value) or not _YT_PLAY_VERB_RE.search(value):
        return ""

    query = _YT_WORD_RE.sub(" ", value)
    query = re.sub(
        r"\b(?:open|launch|start|kholo|khol|khule|খুলে|খোলো|খোল|চালু)\b",
        " ", query, flags=re.I,
    )
    query = re.sub(
        r"\b(?:search|find|look\s+for|khujo|khunjo|সার্চ|খুঁজে|খোঁজো|খুঁজো)\b",
        " ", query, flags=re.I,
    )
    query = re.sub(r"\b(?:kore|kor|koro|koren|করে|করো|করুন)\b", " ", query, flags=re.I)
    query = _YT_PLAY_VERB_RE.sub(" ", query)
    query = re.sub(r"\b(?:on|in|e|এ)\b", " ", query, flags=re.I)
    query = re.sub(r"\b(?:and|then|ar|আর|এবং|please|pls|প্লিজ)\b", " ", query, flags=re.I)
    return _clean_query(query)


def _media_rules(cmd: str) -> Optional[Plan]:
    if _s(r"\b(?:pause|resume|stop)\s+(?:the\s+)?music\b|\bmusic\s+(?:status|stop|pause)\b", cmd):
        return _plan("media", "media_music", "music control", {"_command": cmd})
    if _s(r"\bplay\s+(?:some\s+)?(?:music|songs?|audio|playlist)\b|\b(?:gan|gaan|gaano)\s+(?:chalao|chala|bajao|sunao)\b|গান\s*(?:চালাও|শোনাও|বাজাও)|মিউজিক\s*চালাও", cmd, re.I):
        return _plan("media", "media_music", "play music", {"_command": cmd})
    if _s(r"\bplay\s+(?:the\s+)?song\s+(.+)$", cmd):
        return _plan("media", "media_music", "play song", {"query": _clean_query(_s(r"\bplay\s+(?:the\s+)?song\s+(.+)$", cmd).group(1)), "_command": cmd})

    # "youtube open kore <query> search kore play koro" and all of its
    # English/Bangla/Banglish variants: search + play is one real action.
    yt_play_query = _youtube_play_query(cmd)
    if yt_play_query:
        return _plan("media", "media_youtube_play", "youtube search and play",
                     {"query": yt_play_query, "_command": cmd})

    yt_match = _s(r"\b(?:youtube|ইউটিউব)\s+(?:search|খুঁজ)\s+(.+)$|\bsearch\s+(?:on\s+)?youtube\s+(?:for\s+)?(.+)$", cmd)
    if yt_match:
        query = next((group for group in yt_match.groups() if group), "").strip()
        return _plan("media", "media_youtube", "youtube search", {"query": query, "_command": cmd})

    play_yt = _s(r"\bplay\s+(.+?)\s+on\s+youtube\b", cmd)
    if play_yt:
        return _plan("media", "media_youtube_play", "play on youtube", {"query": play_yt.group(1).strip(), "_command": cmd})

    if _s(r"\b(?:generate|create|make|draw)\s+(?:an?\s+)?(?:image|picture|photo)\b|\bdraw\s+(.+)$|ছবি\s*(?:বানাও|তৈরি|জেনারেট)|ইমেজ\s*(?:বানাও|জেনারেট)", cmd):
        prompt = cmd
        for trigger in (
            "generate an image of", "generate image of", "generate an image", "generate image",
            "create an image of", "create image of", "create an image", "create image",
            "make an image of", "make image of", "make an image", "make image",
            "draw me", "draw", "ছবি বানাও", "ছবি তৈরি কর", "ইমেজ বানাও", "ছবি জেনারেট কর",
        ):
            match = _s(re.escape(trigger) + r"\s*(.*)$", cmd, re.I)
            if match:
                prompt = match.group(1).strip() or prompt
                break
        prompt = _clean_query(prompt)
        if prompt:
            return _plan("media", "media_image", "generate image", {"prompt": prompt, "query": prompt, "_command": cmd})

    if _s(r"\bmeme\b|মিম", cmd):
        top = bottom = ""
        top_match = _s(r"\btop\s*[:=]\s*[\"']?([^|\"']+)", cmd, re.I)
        bottom_match = _s(r"\bbottom\s*[:=]\s*[\"']?([^|\"']+)", cmd, re.I)
        if top_match:
            top = top_match.group(1).strip()
        if bottom_match:
            bottom = bottom_match.group(1).strip()
        if not top and not bottom and "|" in cmd:
            parts = [part.strip() for part in cmd.split("|") if part.strip()]
            if len(parts) >= 2:
                top, bottom = parts[-2], parts[-1]
        return _plan("media", "media_meme", "meme", {"top_text": top, "bottom_text": bottom, "prompt": _clean_query(cmd), "_command": cmd})

    if _s(r"\bdownload\s+(?:this\s+|the\s+)?(?:video|song|audio|music|clip|reel)\b|ভিডিও\s*ডাউনলোড|গান\s*ডাউনলোড", cmd) or (
        _m(r"^(?:download|ডাউনলোড)\b", cmd, re.I) and _extract_url(cmd)
    ):
        url = _extract_url(cmd)
        audio_only = bool(_s(r"\b(?:song|audio|music|গান)\b", cmd))
        return _plan("media", "media_download", "download media", {"url": url, "audio_only": audio_only, "_command": cmd})

    if _s(r"\b(?:subtitle|subtitles|caption|transcribe)\b|সাবটাইটেল|ট্রান্সক্রাইব", cmd):
        url = _extract_url(cmd)
        return _plan("media", "media_subtitle", "subtitle", {"url": url, "_command": cmd})

    if _s(r"\bplay\s+(?:the\s+)?video\s+(.+)$", cmd):
        return _plan("media", "media_youtube_play", "play video", {"query": _clean_query(_s(r"\bplay\s+(?:the\s+)?video\s+(.+)$", cmd).group(1)), "_command": cmd})

    # Generic "play <query>" without an explicit media noun behaves like a
    # YouTube search + play ("play lofi beats"), while "play music" is local.
    play_match = _m(r"^play\s+(.+)$", cmd)
    if play_match and not _s(r"\b(?:music|song|audio|playlist|video)\b", cmd):
        query = _clean_query(play_match.group(1))
        if query and query not in ("music", "song"):
            return _plan("media", "media_youtube_play", "play query", {"query": query, "_command": cmd})
    return None


def _productivity_rules(cmd: str) -> Optional[Plan]:
    add_task = _s(
        r"\b(?:add|new|create)\s+(?:a\s+)?(?:task|todo|to-do)\b\s*[:\-]?\s*(.*)$|"
        r"^todo\s*[:\-]?\s*(.*)$|"
        r"(?:নতুন\s+)?(?:কাজ|টাস্ক)\s*(?:যোগ\s*করো|যোগ\s*কর|যোগ|অ্যাড\s*করো|অ্যাড)\s*[:\-]?\s*(.*)$",
        cmd,
    )
    if add_task:
        title = next((group for group in add_task.groups() if group), "").strip()
        title = _clean_query(title)
        return _plan("productivity", "productivity_task", "add task", {"task": title, "title": title, "_command": cmd})

    if _s(r"\b(?:show|list|my|what are my)\s+(?:the\s+)?tasks?\b|\btask\s*list\b|\btodo\s*list\b|আমার\s*কাজ|কাজ\s*দেখাও|টাস্ক\s*দেখাও", cmd):
        return _plan("productivity", "productivity_show_tasks", "show tasks", {"_command": cmd})

    complete = _s(r"\b(?:complete|finish|done|close)\s+(?:the\s+)?task\b\s*[:\-]?\s*(.*)$|\bmark\s+task\b\s*(.*?)\s+(?:as\s+)?(?:done|complete)\b", cmd)
    if complete:
        target = next((group for group in complete.groups() if group), "").strip()
        return _plan("productivity", "productivity_complete_task", "complete task", {"task": _clean_query(target), "query": _clean_query(target), "_command": cmd})

    delete = _s(r"\b(?:delete|remove)\s+(?:the\s+)?task\b\s*[:\-]?\s*(.*)$", cmd)
    if delete:
        target = delete.group(1).strip()
        return _plan("productivity", "productivity_delete_task", "delete task", {"task": _clean_query(target), "query": _clean_query(target), "_command": cmd})

    remind = _s(r"\bremind\s+me\s+(?:to\s+)?(.+)$|\bset\s+(?:a\s+)?reminder\s+(?:to\s+|for\s+)?(.+)$|মনে\s*করিয়ে\s*দাও\s+(.+)$", cmd)
    if remind:
        text = next((group for group in remind.groups() if group), "").strip()
        return _plan("productivity", "productivity_reminder", "reminder", {"reminder": _clean_query(text), "text": _clean_query(text), "_command": cmd})

    note = _s(r"\b(?:save|add|make|quick)\s+(?:a\s+)?note\s*[:\-]?\s*(.*)$|\bnote\s+(?:that\s+)?(.+)$|নোট\s*(?:করো|লিখো|লিখে রাখো)?\s*[:\-]?\s*(.*)$", cmd)
    if note:
        text = next((group for group in note.groups() if group and group.strip()), "").strip()
        if text:
            return _plan("productivity", "productivity_note", "note", {"note": _clean_query(text), "text": _clean_query(text), "_command": cmd})

    if _s(r"\bpomodoro\b|\bfocus\s+(?:for|mode)\b|\bstudy\s+timer\b|পোমোডোরো", cmd):
        return _plan("productivity", "productivity_pomodoro", "pomodoro", {"minutes": _minutes(cmd), "_command": cmd})

    if _s(r"\bset\s+(?:an?\s+)?alarm\b|\balarm\s+(?:for|at)\b|অ্যালার্ম", cmd):
        return _plan("productivity", "productivity_alarm", "alarm", {"text": _clean_query(re.sub(r"^.*?\balarm\b\s*(?:for|at)?\s*", "", cmd, flags=re.I)), "_command": cmd})

    if _s(r"\b(?:my|show|list|upcoming)\s+calendar\b|\bcalendar\s+(?:list|events?)\b|ক্যালেন্ডার", cmd):
        return _plan("productivity", "productivity_calendar", "calendar", {"_command": cmd})
    return None


def _finance_rules(cmd: str) -> Optional[Plan]:
    if _s(
        r"\b(?:how\s+much\s+did\s+i\s+spend|spending\s+(?:summary|report)|expense\s+(?:summary|report)|"
        r"where\s+did\s+my\s+money\s+go|budget\s+(?:status|report))\b|কত\s*খরচ|খরচের\s*হিসাব|হিসাব\s*দেখাও",
        cmd,
    ):
        return _plan("finance", "finance_summary", "spending summary", {"_command": cmd})

    if _s(r"\bset\s+(?:a\s+)?budget\b|\bbudget\s+set\b|বাজেট\s*সেট", cmd):
        amount = _amount(cmd)
        return _plan("finance", "finance_budget", "set budget", {"amount": amount, "_command": cmd})
    if _s(r"\bbudget\b|বাজেট", cmd):
        return _plan("finance", "finance_budget", "budget", {"_command": cmd})

    add = _s(
        r"\b(?:add|log|record)\s+(?:an?\s+)?expense\s*(?:of)?\s*(.*)$|"
        r"\bspent\s+(.*)$|"
        r"\bexpense\s+(.*)$|"
        r"খরচ\s*(?:যোগ\s*করো|যোগ\s*কর|লিখো|লিখ)?\s*[:\-]?\s*(.*)$",
        cmd,
    )
    if add:
        detail = next((group for group in add.groups() if group), "").strip()
        amount = _amount(detail or cmd)
        note = detail
        if amount is not None:
            note = re.sub(r"(?:৳|tk|taka|৳)?\s*\d+(?:[.,]\d+)?\s*(?:tk|taka|৳)?", " ", note, flags=re.I)
        note = re.sub(r"\b(?:on|for|in|at)\b", " ", note, flags=re.I)
        note = _clean_query(note)
        return _plan("finance", "finance_add", "add expense", {"amount": amount, "note": note, "_command": cmd})
    return None


def _meeting_rules(cmd: str) -> Optional[Plan]:
    if _s(r"\b(?:list|show|my|upcoming)\s+meetings?\b|\bmeeting\s*list\b|মিটিং\s*(?:লিস্ট|দেখাও)", cmd):
        return _plan("meeting_autopilot", "meeting_list", "list meetings", {"_command": cmd})
    cancel = _s(r"\bcancel\s+(?:the\s+)?meeting\b\s*[:\-]?\s*(.*)$", cmd)
    if cancel:
        return _plan("meeting_autopilot", "meeting_cancel", "cancel meeting", {"id": cancel.group(1).strip(), "_command": cmd})
    if _s(r"\b(?:schedule|book|set\s*up|create|arrange)\s+(?:a\s+)?meeting\b|\bmeeting\s+(?:schedule|book)\b|মিটিং\s*(?:সিডিউল|বুক|কর)", cmd):
        title = ""
        title_match = _s(r"\b(?:about|on|titled|for)\s+(.+?)(?:\s+(?:at|on|tomorrow|today|আজ|কাল)\b|$)", cmd)
        if title_match:
            title = title_match.group(1).strip()
        return _plan("meeting_autopilot", "meeting_schedule", "schedule meeting", {"title": title, "when": cmd, "_command": cmd})
    return None


def _email_rules(cmd: str) -> Optional[Plan]:
    if _s(
        r"\b(?:check|read|open|show)\s+(?:my\s+)?(?:email|emails|inbox|mail)\b|"
        r"\b(?:email|inbox)\s+(?:status|triage|check)\b|\bunread\s+(?:email|mail)s?\b|"
        r"\bdraft\s+(?:a\s+)?(?:reply|email)\b|ইমেইল\s*(?:চেক|দেখাও)|ইনবক্স",
        cmd,
    ):
        intent = "email_draft" if "draft" in cmd.lower() else "email_triage"
        return _plan("email_triage", intent, "email triage", {"_command": cmd})
    if _s(
        r"\b(?:email|mail)\s+(?:draft|reply|compose)\b|"
        r"\bdraft\s+(?:an?\s+)?(?:email|mail)\b|"
        r"\b(?:write|compose)\s+(?:an?\s+)?(?:email|mail)\b|"
        r"\bsend\s+(?:an?\s+)?(?:email|mail)\b|"
        r"\breply\s+to\s+(?:the\s+)?(?:email|mail)\b|"
        r"ইমেইল\s*(?:ড্রাফট|ড্রাফ্ট|লিখো|লিখুন|রিপ্লাই|পাঠাও)",
        cmd,
    ):
        return _plan("email_triage", "email_draft", "email draft", {"_command": cmd})
    return None


def _security_rules(cmd: str) -> Optional[Plan]:
    if _s(
        r"\b(?:scan|check|run)\s+(?:for\s+)?(?:malware|virus(?:es)?)\b|"
        r"\b(?:malware|virus|security)\s+scan\b|"
        r"\bscan\s+(?:my\s+|the\s+)?(?:pc|computer|laptop|system)\b|"
        r"\b(?:scan|check)\s+(?:my\s+|the\s+)?(?:pc|computer|laptop)\s+for\s+(?:malware|virus(?:es)?)\b|"
        r"\bfull\s+(?:security\s+)?scan\b|ম্যালওয়্যার|ভাইরাস\s*স্ক্যান|সিকিউরিটি\s*স্ক্যান",
        cmd,
    ):
        return _plan("security_sentinel", "security_scan", "malware scan", {"_command": cmd})
    if _s(r"\b(?:network|port)\s+scan\b|নেটওয়ার্ক\s*স্ক্যান", cmd):
        return _plan("security_sentinel", "network_scan", "network scan", {"_command": cmd})

    email = _EMAIL_RE.search(cmd)
    if email and _s(r"\b(?:breach|breached|leak|leaked|hacked|compromised)\b|ব্রিচ|লিক|হ্যাক", cmd):
        return _plan("security_sentinel", "breach_check", "breach check", {"email": email.group(0), "_command": cmd})
    if _s(r"\b(?:check|test|verify)\s+(?:an?\s+)?(?:email|address)\s+(?:for\s+)?(?:breach|leak)\b|breach\s+check|check\s+breach|ব্রিচ\s*চেক", cmd):
        return _plan("security_sentinel", "breach_check", "breach check", {"email": email.group(0) if email else "", "_command": cmd})

    quoted = _s(r"[\"“”']([^\"“”']{4,})[\"“”']", cmd)
    if _s(r"\b(?:check|test|rate)\s+(?:my\s+)?password\b|\bpassword\s+(?:strength|check|test)\b|পাসওয়ার্ড\s*(?:চেক|শক্তি|টেস্ট)", cmd):
        password = quoted.group(1) if quoted else ""
        if not password:
            match = _s(r"(?:password|পাসওয়ার্ড)\s*(?:strength|check|test|চেক|শক্তি)?\s*[:=\-]?\s*(.+)$", cmd)
            if match and "password" not in match.group(1):
                password = match.group(1).strip()
        return _plan("security_sentinel", "password_check", "password check", {"password": password, "_command": cmd})

    if _s(r"\bgenerate\s+(?:a\s+)?(?:strong\s+)?password\b|পাসওয়ার্ড\s*(?:বানাও|জেনারেট)", cmd):
        return _plan("security", "security_password", "generate password", {"generate": True, "_command": cmd})

    if _s(
        r"\bprivacy\s+(?:audit|scan|status|report)\b|\bprivacy\s+mode\s+(?:on|off|enable|disable)\b|"
        r"\bclipboard\s+(?:check|scan)\b|\bblur\s+(?:faces|face)\b|প্রাইভেসি\s*(?:অডিট|স্ট্যাটাস|স্ক্যান)|ক্লিপবোর্ড",
        cmd,
    ):
        return _plan("privacy_guardian", "privacy_audit", "privacy", {"_command": cmd})

    if _s(r"\bfirewall\b|ফায়ারওয়াল", cmd):
        return _plan("security", "security_firewall", "firewall status", {"_command": cmd})

    if _s(r"\block\s+(?:the\s+)?(?:system|computer|pc)\b|সিস্টেম\s*লক", cmd):
        return _plan("pc", "pc_lock", "lock", {"_command": cmd})
    return None


def _terminal_rules(cmd: str) -> Optional[Plan]:
    git_match = _s(r"\bgit\s+(status|pull|push|branch|log|clone|checkout|merge)\b", cmd)
    if git_match:
        action = git_match.group(1)
        return _plan("terminal", f"git_{action}" if action in ("status", "pull", "push", "branch") else "terminal_git", "git", {"git_command": action, "command": f"git {action}", "_command": cmd})
    commit_match = _s(r"\bgit\s+commit\b(?:\s+-m)?\s*[\"“”']?(.+?)[\"“”']?$", cmd)
    if commit_match:
        return _plan("terminal", "git_commit", "git commit", {"message": commit_match.group(1).strip(), "_command": cmd})

    pip_match = _s(r"\bpip\s+(install|uninstall|update)\s+(\S+)", cmd)
    if pip_match:
        return _plan("terminal", "pip_install", "pip", {"package": pip_match.group(2), "_command": cmd})
    npm_match = _s(r"\bnpm\s+(install|uninstall|update)\s+(\S+)", cmd)
    if npm_match:
        return _plan("terminal", "npm_install", "npm", {"package": npm_match.group(2), "_command": cmd})

    if _s(r"\bipconfig\b|\bifconfig\b", cmd):
        return _plan("terminal", "ipconfig", "ipconfig", {"_command": cmd})
    ping_match = _s(r"\bping\s+(\S+)", cmd)
    if ping_match:
        return _plan("terminal", "ping", "ping", {"host": ping_match.group(1), "_command": cmd})
    if _s(r"\btasklist\b|\blist\s+processes\b", cmd):
        return _plan("terminal", "tasklist", "tasklist", {"_command": cmd})

    run_match = _s(
        r"^(?:run|execute|terminal|shell|cmd)\s*(?:command|cmd)?\s*[:\-]?\s*(.+)$",
        cmd,
    )
    if run_match:
        command = run_match.group(1).strip()
        if command and command not in ("git", "pip", "npm"):
            return _plan("terminal", "terminal_run", "run command", {"command": command, "_command": cmd})
    return None


def _coding_rules(cmd: str) -> Optional[Plan]:
    if _s(r"\bcode\s+review\b|\breview\s+(?:the\s+)?code\b|\bscan\s+(?:the\s+)?repo\b|\brepo\s+scan\b|কোড\s*রিভিউ", cmd):
        return _plan("coding", "coding_review", "code review", {"path": _extract_path(cmd), "_command": cmd})
    explain = _s(r"\bexplain\s+(?:the\s+)?file\b|\bexplain\s+code\b", cmd)
    if explain:
        question = re.sub(r"^.*?\b(?:file|code)\b\s*", "", cmd).strip()
        return _plan("coding", "coding_explain", "explain code", {"path": _extract_path(cmd), "question": question, "_command": cmd})
    fix = _s(r"\bfix\s+(?:the\s+)?bug\b|\bbug\s+fix\b|\bdebug\b", cmd)
    if fix:
        return _plan("coding", "coding_fix", "fix bug", {"path": _extract_path(cmd), "issue": _clean_query(re.sub(r"^.*?\b(?:bug|debug)\b\s*", "", cmd)), "_command": cmd})
    if _s(r"\brun\s+(?:the\s+)?tests?\b|\brun\s+tests?\b", cmd):
        return _plan("coding", "coding_test", "run tests", {"path": _extract_path(cmd), "_command": cmd})
    return None


def _screen_rules(cmd: str) -> Optional[Plan]:
    if _s(r"\bscreenshot\b|\bscreen\s*capture\b|\bcapture\s+(?:the\s+)?screen\b|স্ক্রিনশট", cmd):
        return _plan("screen_rpa", "screen_capture", "screenshot", {"_command": cmd})
    if _s(r"\bscreen\s*(?:size|resolution)\b|স্ক্রিন\s*সাইজ", cmd):
        return _plan("screen_rpa", "screen_size", "screen size", {"_command": cmd})
    if _s(r"\bscreen\s+(?:analyze|analysis|read)\b|\banalyze\s+(?:the\s+)?screen\b", cmd):
        return _plan("screen_rpa", "screen_analyze", "screen analyze", {"_command": cmd})
    return None


def _doc_rules(cmd: str) -> Optional[Plan]:
    if _s(r"\blist\s+(?:the\s+)?documents?\b|\bdoc(?:ument)?\s*list\b|\blist\s+docs\b", cmd):
        return _plan("doc_intel", "doc_list", "list documents", {"_command": cmd})
    if _s(r"\.pdf\b|\.docx?\b|\bdocument\b|ডকুমেন্ট", cmd) and _s(
        r"\b(?:ask|question|summarize|summary|analyze|analyse|explain|index|ingest)\b|প্রশ্ন|সারাংশ",
        cmd,
    ):
        return _plan("doc_intel", "doc_ask", "document question", {"path": _extract_path(cmd), "_command": cmd})
    return None


def _exam_rules(cmd: str) -> Optional[Plan]:
    if _s(r"\bdue\s+cards?\b|\breview\s+cards?\b|\bflash\s*cards?\b|ফ্ল্যাশকার্ড", cmd):
        return _plan("exam_coach", "exam_due_cards", "due cards", {"_command": cmd})
    if _s(r"\bweak\s+topics?\b|\bmy\s+weak\b|দুর্বল\s*বিষয়", cmd):
        return _plan("exam_coach", "exam_weak_topics", "weak topics", {"_command": cmd})
    if _s(r"\bmock\s+test\b|\bexam\s+plan\b|\bstudy\s+plan\b|মক\s*টেস্ট|সিলেবাস", cmd):
        intent = "exam_plan" if "plan" in cmd.lower() or "সিলেবাস" in cmd else "exam_mock_test"
        return _plan("exam_coach", intent, "exam coach", {"_command": cmd})
    quiz = _s(r"\bquiz\s+me\s+(?:on|about)\s+(.+)$|\bquiz\s+(?:on|about)\s+(.+)$", cmd)
    if quiz:
        topic = next((group for group in quiz.groups() if group), "").strip()
        return _plan("exam_coach", "exam_quiz", "quiz", {"topic": topic, "_command": cmd})
    return None


def _yt_rules(cmd: str) -> Optional[Plan]:
    url = _extract_url(cmd) if "youtu" in cmd.lower() else ""
    if url and _s(r"\b(?:summary|summarize|transcript|notes?|learn|quiz|study)\b|সারাংশ|নোট", cmd):
        if _s(r"\btranscript\b|ট্রান্সক্রিপ্ট", cmd):
            intent = "yt_transcript"
        elif _s(r"\bquiz\b", cmd):
            intent = "yt_quiz"
        elif _s(r"\bnotes?\b|নোট", cmd):
            intent = "yt_notes"
        else:
            intent = "yt_learn"
        return _plan("yt_learn", intent, "youtube learning", {"url": url, "_command": cmd})
    if _s(r"\byoutube\b|youtu\.be", cmd) and _s(r"\b(?:summary|summarize|transcript|notes?|quiz|learn)\b|সারাংশ|নোট", cmd):
        return _plan("yt_learn", "yt_learn", "youtube learning", {"query": cmd, "_command": cmd})
    return None


def _report_rules(cmd: str) -> Optional[Plan]:
    if _s(r"\b(?:list|show)\s+(?:my\s+)?(?:reports?|presentations?)\b", cmd):
        return _plan("report_builder", "report_list", "list reports", {"_command": cmd})
    if _s(r"\b(?:presentation|slide\s*deck|slides?|ppt|powerpoint)\b|প্রেজেন্টেশন|স্লাইড", cmd):
        topic = re.sub(r"^.*?\b(?:presentation|slides?|ppt|powerpoint|slide\s*deck)\b\s*(?:on|about|for)?\s*", "", cmd).strip()
        return _plan("report_builder", "presentation_build", "presentation", {"topic": _clean_query(topic), "_command": cmd})
    if _s(r"\b(?:make|create|build|write)\s+(?:a\s+)?report\b|\breport\s+on\b|রিপোর্ট\s*(?:বানাও|তৈরি)", cmd):
        topic = re.sub(r"^.*?\breport\b\s*(?:on|about|for)?\s*", "", cmd).strip()
        return _plan("report_builder", "report_build", "report", {"topic": _clean_query(topic), "_command": cmd})
    return None


def _research_rules(cmd: str) -> Optional[Plan]:
    if _s(r"\bdeep\s+research\b|\bresearch\s+report\b|\bcite\s+sources?\b|গভীর\s*গবেষণা", cmd):
        topic = re.sub(r"^.*?\b(?:deep\s+research|research\s+report)\b\s*(?:on|about|for)?\s*", "", cmd).strip()
        return _plan("research_pro", "deep_research", "deep research", {"topic": _clean_query(topic), "_command": cmd})
    research = _s(r"^(?:research|study|investigate)\s+(?:on\s+|about\s+)?(.+)$|গবেষণা\s*কর\s+(.+)$", cmd)
    if research:
        topic = next((group for group in research.groups() if group), "").strip()
        return _plan("web", "web_research", "web research", {"topic": _clean_query(topic), "query": _clean_query(topic), "_command": cmd})
    return None


def _web_rules(cmd: str) -> Optional[Plan]:
    url = _extract_url(cmd)
    if url and _s(r"\bsummarize\b|\bsummary\b|\btl;?dr\b|সারাংশ", cmd):
        return _plan("web", "web_summarize", "summarize url", {"url": url, "_command": cmd})
    if _s(r"\btranslate\b|\btranslation\b|অনুবাদ|ট্রান্সলেট", cmd):
        target = "Bengali" if _s(r"\b(?:bengali|bangla)\b|বাংলা", cmd, re.I) else \
                 "English" if _s(r"\benglish\b|ইংরেজি", cmd, re.I) else ""
        text = re.sub(r"^.*?\b(?:translate|translation)\b\s*", "", cmd)
        text = re.sub(r"\b(?:to|into|in)\s+(?:bengali|bangla|english|spanish|french|hindi|arabic)\b", "", text, flags=re.I)
        return _plan("web", "web_translate", "translate", {"text": _clean_query(text), "target_language": target, "_command": cmd})
    if _s(r"\bbookmarks?\b|\bsave\s+(?:this\s+)?page\b|বুকমার্ক", cmd):
        return _plan("web", "web_bookmark", "bookmarks", {"url": url, "_command": cmd})
    if _s(r"\bbrowsing\s+history\b|\bweb\s+history\b|\brecent\s+sites\b|ব্রাউজিং\s*হিস্টরি", cmd):
        return _plan("web", "web_history", "history", {"_command": cmd})
    if _s(r"\bnews\b|\bheadlines?\b|খবর|সংবাদ", cmd):
        topic = re.sub(r"^.*?\b(?:news|headlines?)\b\s*(?:about|on|for)?\s*", "", cmd).strip()
        return _plan("web", "web_news", "news", {"query": _clean_query(topic), "_command": cmd})
    if _s(r"\bwikipedia\b|উইকিপিডিয়া", cmd):
        query = re.sub(r"^.*?\bwikipedia\b\s*", "", cmd).strip()
        return _plan("web", "wikipedia_search", "wikipedia", {"query": _clean_query(query), "_command": cmd})

    search = _s(
        r"^(?:search\s+(?:the\s+)?web\s+(?:for\s+)?|google\s+|search\s+(?:for\s+)?|look\s+up\s+|find\s+online\s+)(.+)$|"
        r"গুগলে\s*সার্চ\s*কর\s+(.+)$",
        cmd,
    )
    if search:
        query = next((group for group in search.groups() if group), "").strip()
        return _plan("web", "web_search", "web search", {"query": _clean_query(query), "_command": cmd})
    if _s(r"\bsearch\s+(?:the\s+)?web\b|\bweb\s+search\b", cmd):
        query = re.sub(r"^.*?\b(?:search\s+(?:the\s+)?web|web\s+search)\b\s*(?:for)?\s*", "", cmd).strip()
        return _plan("web", "web_search", "web search", {"query": _clean_query(query), "_command": cmd})
    return None


_QUESTION_RE = re.compile(
    r"^(?:what|why|how|who|whom|whose|when|where|which|is|are|am|do|does|did|"
    r"can|could|should|would|will|tell\s+me\s+(?:about|more)|explain|describe|define|"
    r"difference\s+between|compare|meaning\s+of)\b|"
    r"^(?:কি|কী|কেন|কিভাবে|কীভাবে|কোথায়|কখন|কে|কার|কত|কোন|বলো|বলুন|ব্যাখ্যা|পরিচয়|জানতে)\b",
    re.IGNORECASE,
)


def plan_command(command: str, context: Optional[Dict[str, Any]] = None) -> Optional[Plan]:
    """Return a Plan for an actionable command, or None for AI chat.

    ``context`` is only supplied while planning a multi-step sentence; it
    resolves elliptical follow-up steps such as “search lofi” + “play”.
    """
    original = str(command or "").strip()
    if not original:
        return None
    cmd = _strip_polite(original)
    if not cmd:
        return None

    if context:
        contextual = _context_rules(cmd, context)
        if contextual:
            contextual.entities.setdefault("_command", original)
            contextual.entities.setdefault("_language", "bn" if is_bengali(original) else "en")
            return contextual

    # Explicit rules, ordered from most specific/risky to most general.
    for rule in (
        _call_rules,
        _app_rules,
        _pc_rules,
        _file_rules,
        _media_rules,
        _productivity_rules,
        _finance_rules,
        _meeting_rules,
        _email_rules,
        _security_rules,
        _terminal_rules,
        _coding_rules,
        _screen_rules,
        _doc_rules,
        _exam_rules,
        _yt_rules,
        _report_rules,
        _research_rules,
        _web_rules,
    ):
        plan = rule(cmd)
        if plan:
            plan.entities.setdefault("_command", original)
            plan.entities.setdefault("_language", "bn" if is_bengali(original) else "en")
            return plan

    # Professional question guard: ordinary questions stay with the AI unless a
    # rule above already claimed them as a concrete action.
    if _QUESTION_RE.search(cmd) or original.rstrip().endswith(("?", "؟")):
        return None
    return None


def plan_sequence(command: str) -> list:
    """Plan a compound command as an ordered list of steps.

    A single-action sentence returns one plan (or an empty list for chat).
    Multi-step is intentionally conservative: if any piece cannot be planned,
    the whole sentence is treated as one command so nothing is half-executed.
    """
    original = str(command or "").strip()
    if not original:
        return []

    segments = split_steps(original)
    if len(segments) <= 1:
        plan = plan_command(original)
        return [plan] if plan else []

    context: Dict[str, Any] = {}
    plans = []
    for segment in segments:
        plan = plan_command(segment, context=context)
        if plan is None:
            single = plan_command(original)
            return [single] if single else []
        plan.entities.setdefault("_step_command", segment)
        plans.append(plan)
        _advance_context(context, plan)

    return _collapse_plans(plans)


def is_action_command(command: str) -> bool:
    return plan_command(command) is not None


# Case-insensitive matching helpers: commands keep their original case for
# paths/URLs, but every rule pattern matches regardless of capitalization.
def _s(pattern, text, flags=0):
    return re.search(pattern, text, flags | re.IGNORECASE)


def _m(pattern, text, flags=0):
    return re.match(pattern, text, flags | re.IGNORECASE)
