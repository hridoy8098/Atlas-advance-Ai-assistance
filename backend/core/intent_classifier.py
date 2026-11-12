"""
backend/core/intent_classifier.py
Atlas 7.0 - Intent Classification Engine
Supports: Bangla + English + Mixed commands
Features: AI classification + Robust fallback + Context awareness
"""

import json
import re
from typing import Dict, List, Optional, Tuple
from backend.core.ai_engine import ai_engine


# Obvious conversational phrases do not need an LLM round-trip just to be
# classified as "chat". Matching them locally removes one full AI request from
# every greeting, which is the most visible latency in the phone voice flow.
_FAST_CHAT_RE = re.compile(
    r"^(?:"
    r"(?:hi|hello|hey|yo|hola|সালাম|হ্যালো|হাই|ওহে)(?:\s+(?:there|atlas|boss|friend))?"
    r"|(?:how\s+are\s+you|how\s+is\s+it\s+going|what'?s\s+up|কেমন\s+আছো|কেমন\s+আছেন|কি\s+খবর|কী\s+খবর)"
    r"|(?:good\s+(?:morning|afternoon|evening|night)|শুভ\s+(?:সকাল|সন্ধ্যা|রাত))"
    r"|(?:thanks|thank\s+you|thx|ধন্যবাদ)"
    r"|(?:ok|okay|alright|bye|goodbye|see\s+you|বিদায়|আল্লাহ\s+হাফেজ)"
    r"|(?:who\s+are\s+you|what\s+can\s+you\s+do|help|তুমি\s+কে|আপনি\s+কে)"
    r"|(?:tell\s+me\s+(?:a\s+)?joke|tell\s+me\s+something)"
    r"|(?:i\s+(?:am|feel)\s+(?:sad|happy|tired|bored|good|fine))"
    r"|(?:nice|good\s+job|well\s+done)"
    r")[\s!.,।?]*$",
    re.IGNORECASE,
)


class IntentClassifier:
    """Smart intent classification with multi-layer fallback"""

    def __init__(self):
        self.confidence_threshold = 0.6
        self.context_history = []  # Last 3 commands for context

        # ========== COMPREHENSIVE INTENT DATABASE ==========
        self.intent_patterns = {
            # ===== APP / OPEN COMMANDS =====
            "open_app": {
                "keywords_en": ["open", "launch", "start", "run", "load"],
                "keywords_bn": ["খোল", "চালু", "ওপেন", "লঞ্চ", "শুরু"],
                "apps": {
                    "youtube": ["youtube", "yt", "ইউটিউব", "ইউটিউবে"],
                    "chrome": ["chrome", "google chrome", "ক্রোম", "ব্রাউজার"],
                    "vscode": ["vscode", "vs code", "code", "ভিএসকোড", "এডিটর"],
                    "gmail": ["gmail", "email", "mail", "জিমেইল", "ইমেইল"],
                    "github": ["github", "git", "গিটহাব", "গিট"],
                    "facebook": ["facebook", "fb", "ফেসবুক", "ফব"],
                    "whatsapp": ["whatsapp", "wa", "হোয়াটসঅ্যাপ", "হোয়াটস্"],
                    "chatgpt": ["chatgpt", "gpt", "chat gpt", "চ্যাটজিপিটি"],
                    "spotify": ["spotify", "music app", "স্পটিফাই"],
                    "discord": ["discord", "ডিসকোর্ড"],
                    "notion": ["notion", "নোশন"],
                    "slack": ["slack", "স্ল্যাক"],
                    "zoom": ["zoom", "জুম"],
                    "teams": ["teams", "microsoft teams", "টিমস্"],
                    "excel": ["excel", "spreadsheet", "এক্সেল"],
                    "word": ["word", "ms word", "ওয়ার্ড"],
                    "powerpoint": ["powerpoint", "ppt", "পাওয়ারপয়েন্ট"],
                    "calculator": ["calculator", "calc", "ক্যালকুলেটর"],
                    "terminal": ["terminal", "cmd", "command prompt", "টার্মিনাল"],
                    "settings": ["settings", "control panel", "সেটিংস্"],
                    "explorer": ["explorer", "file explorer", "ফাইল এক্সপ্লোরার"],
                }
            },

            # ===== PC / SYSTEM COMMANDS =====
            "pc_optimize": {
                "keywords_en": ["optimize", "boost", "speed up", "tune up", "performance"],
                "keywords_bn": ["অপটিমাইজ", "ফাস্ট", "গতি", "পারফরম্যান্স", "টিউন"],
                "sub_actions": ["clean ram", "close background", "disk cleanup", "registry clean"]
            },
            "pc_clean": {
                "keywords_en": ["clean", "clear", "delete temp", "remove junk", "free space"],
                "keywords_bn": ["পরিষ্কার", "পরিষ্কার কর", "জাঙ্ক", "ফাঁকা", "খালি"],
                "sub_actions": ["temp files", "recycle bin", "cache", "logs"]
            },
            "pc_shutdown": {
                "keywords_en": ["shutdown", "turn off", "power off", "sleep"],
                "keywords_bn": ["শাটডাউন", "বন্ধ", "অফ", "ঘুম"],
            },
            "pc_restart": {
                "keywords_en": ["restart", "reboot", "reload"],
                "keywords_bn": ["রিস্টার্ট", "রিবুট", "আবার চালু"],
            },
            "pc_lock": {
                "keywords_en": ["lock", "screen lock", "lock pc"],
                "keywords_bn": ["লক", "লক কর", "স্ক্রিন লক"],
            },
            "pc_battery": {
                "keywords_en": ["battery", "power", "charge", "battery saver"],
                "keywords_bn": ["ব্যাটারি", "চার্জ", "পাওয়ার", "ব্যাটারি সেভার"],
            },
            "pc_status": {
                "keywords_en": ["system status", "pc status", "check system", "diagnostics", "health"],
                "keywords_bn": ["সিস্টেম স্ট্যাটাস", "পিসি অবস্থা", "চেক", "হেলথ"],
            },
            "pc_wifi": {
                "keywords_en": ["wifi", "internet", "network", "connection"],
                "keywords_bn": ["ওয়াইফাই", "ইন্টারনেট", "নেটওয়ার্ক", "কানেকশন"],
            },
            "pc_bluetooth": {
                "keywords_en": ["bluetooth", "pair", "connect bluetooth"],
                "keywords_bn": ["ব্লুটুথ", "পেয়ার", "কানেক্ট"],
            },

            # ===== FILE COMMANDS =====
            "file_organize": {
                "keywords_en": ["organize", "sort", "arrange", "tidy", "manage files"],
                "keywords_bn": ["গোছাও", "সাজাও", "অর্গানাইজ", "ব্যবস্থা"],
                "locations": ["downloads", "desktop", "documents", "pictures", "ডাউনলোডস", "ডেস্কটপ"]
            },
            "file_search": {
                "keywords_en": ["find file", "search file", "locate", "where is"],
                "keywords_bn": ["ফাইল খুঁজ", "সার্চ", "কোথায়", "খুঁজে বের কর"],
            },
            "file_create": {
                "keywords_en": ["create file", "new file", "make file", "create folder", "new folder"],
                "keywords_bn": ["ফাইল বানাও", "নতুন ফাইল", "ফোল্ডার", "তৈরি"],
            },
            "file_delete": {
                "keywords_en": ["delete file", "remove file", "trash", "recycle"],
                "keywords_bn": ["ডিলিট", "মুছে ফেল", "ট্র্যাশ", "রিমুভ"],
            },
            "file_copy": {
                "keywords_en": ["copy file", "duplicate", "clone"],
                "keywords_bn": ["কপি", "ডুপ্লিকেট", "ক্লোন"],
            },
            "file_move": {
                "keywords_en": ["move file", "transfer", "relocate"],
                "keywords_bn": ["মুভ", "সরাও", "ট্রান্সফার"],
            },
            "file_rename": {
                "keywords_en": ["rename", "change name", "new name"],
                "keywords_bn": ["রিনেম", "নাম বদলাও", "নতুন নাম"],
            },
            "file_backup": {
                "keywords_en": ["backup", "save copy", "export"],
                "keywords_bn": ["ব্যাকআপ", "কপি রাখ", "এক্সপোর্ট"],
            },

            # ===== WEB / RESEARCH COMMANDS =====
            "web_search": {
                "keywords_en": ["search", "google", "look up", "find online"],
                "keywords_bn": ["সার্চ", "গুগল", "খুঁজ", "অনলাইনে"],
            },
            "web_research": {
                "keywords_en": ["research", "learn about", "tell me about", "explain", "what is", "how to"],
                "keywords_bn": ["রিসার্চ", "জানতে চাই", "বলো", "ব্যাখ্যা", "কী", "কিভাবে"],
            },
            "web_summarize": {
                "keywords_en": ["summarize", "summary", "tl;dr", "short version"],
                "keywords_bn": ["সারাংশ", "সংক্ষেপ", "সংক্ষিপ্ত"],
            },
            "web_translate": {
                "keywords_en": ["translate", "translation", "convert language"],
                "keywords_bn": ["ট্রান্সলেট", "অনুবাদ", "ভাষা বদলাও"],
            },
            "web_bookmark": {
                "keywords_en": ["bookmark", "save page", "favorite"],
                "keywords_bn": ["বুকমার্ক", "সেভ", "ফেভারিট"],
            },
            "web_history": {
                "keywords_en": ["history", "browsing history", "recent sites"],
                "keywords_bn": ["হিস্টরি", "ব্রাউজিং", "সাম্প্রতিক"],
            },

            # ===== MEDIA COMMANDS =====
            "media_youtube": {
                "keywords_en": ["youtube", "play video", "watch", "stream"],
                "keywords_bn": ["ইউটিউব", "ভিডিও", "দেখ", "প্লে"],
            },
            "media_music": {
                "keywords_en": ["play music", "song", "audio", "playlist", "spotify"],
                "keywords_bn": ["গান", "মিউজিক", "শোন", "প্লেলিস্ট"],
            },
            "media_video": {
                "keywords_en": ["video", "movie", "film", "clip"],
                "keywords_bn": ["ভিডিও", "সিনেমা", "মুভি", "ক্লিপ"],
            },
            "media_image": {
                "keywords_en": ["image", "picture", "photo", "generate image", "create image"],
                "keywords_bn": ["ছবি", "ইমেজ", "ফটো", "জেনারেট", "বানাও"],
            },
            "media_meme": {
                "keywords_en": ["meme", "funny image", "joke image"],
                "keywords_bn": ["মিম", "মজার ছবি", "জোক"],
            },
            "media_download": {
                "keywords_en": ["download", "save video", "download song"],
                "keywords_bn": ["ডাউনলোড", "সেভ", "ভিডিও ডাউনলোড"],
            },
            "media_subtitle": {
                "keywords_en": ["subtitle", "caption", "transcribe"],
                "keywords_bn": ["সাবটাইটেল", "ক্যাপশন", "ট্রান্সক্রাইব"],
            },
            "media_convert": {
                "keywords_en": ["convert", "mp3", "mp4", "format change"],
                "keywords_bn": ["কনভার্ট", "ফরম্যাট", "বদলাও"],
            },

            # ===== PRODUCTIVITY COMMANDS =====
            "productivity_task": {
                "keywords_en": ["task", "todo", "to-do", "add task", "new task", "work"],
                "keywords_bn": ["টাস্ক", "কাজ", "টু-ডু", "নতুন কাজ", "যোগ কর"],
            },
            "productivity_show_tasks": {
                "keywords_en": ["show tasks", "my tasks", "task list", "what to do"],
                "keywords_bn": ["টাস্ক দেখাও", "আমার কাজ", "কী করব", "লিস্ট"],
            },
            "productivity_pomodoro": {
                "keywords_en": ["pomodoro", "focus", "concentrate", "timer", "study mode"],
                "keywords_bn": ["পোমোডোরো", "ফোকাস", "মনোযোগ", "টাইমার", "পড়াশোনা"],
            },
            "productivity_reminder": {
                "keywords_en": ["remind", "reminder", "alert", "notify", "don't forget"],
                "keywords_bn": ["রিমাইন্ডার", "মনে করিয়ে", "আলার্ট", "ভুলো না"],
            },
            "productivity_calendar": {
                "keywords_en": ["calendar", "schedule", "event", "appointment", "meeting"],
                "keywords_bn": ["ক্যালেন্ডার", "সিডিউল", "ইভেন্ট", "মিটিং", "অ্যাপয়েন্টমেন্ট"],
            },
            "productivity_note": {
                "keywords_en": ["note", "write down", "save note", "quick note"],
                "keywords_bn": ["নোট", "লিখে রাখ", "সেভ", "কুইক নোট"],
            },
            "productivity_alarm": {
                "keywords_en": ["alarm", "wake me", "set alarm"],
                "keywords_bn": ["অ্যালার্ম", "জাগাও", "ঘড়ি"],
            },

            # ===== SECURITY COMMANDS =====
            "security_lock": {
                "keywords_en": ["lock system", "lock screen", "lock computer"],
                "keywords_bn": ["সিস্টেম লক", "লক", "কম্পিউটার লক"],
            },
            "security_privacy": {
                "keywords_en": ["privacy mode", "incognito", "private", "hide"],
                "keywords_bn": ["প্রাইভেসি", "গোপন", "লুকাও", "ইনকগনিটো"],
            },
            "security_breach": {
                "keywords_en": ["breach", "hack check", "compromised", "leak"],
                "keywords_bn": ["ব্রিচ", "হ্যাক", "লিক", "কম্প্রোমাইজড"],
            },
            "security_password": {
                "keywords_en": ["password", "pass check", "strong password", "generate password"],
                "keywords_bn": ["পাসওয়ার্ড", "পাস", "জেনারেট", "শক্তিশালী"],
            },
            "security_scan": {
                "keywords_en": ["scan", "virus scan", "malware", "security check"],
                "keywords_bn": ["স্ক্যান", "ভাইরাস", "ম্যালওয়্যার", "নিরাপত্তা চেক"],
            },
            "security_firewall": {
                "keywords_en": ["firewall", "block", "allow", "network security"],
                "keywords_bn": ["ফায়ারওয়াল", "ব্লক", "অনুমতি", "নেটওয়ার্ক নিরাপত্তা"],
            },

            # ===== TERMINAL / DEV COMMANDS =====
            "terminal_run": {
                "keywords_en": ["run command", "execute", "terminal", "cmd", "shell"],
                "keywords_bn": ["রান", "এক্সিকিউট", "কমান্ড", "টার্মিনাল"],
            },
            "terminal_git": {
                "keywords_en": ["git", "commit", "push", "pull", "branch", "repository"],
                "keywords_bn": ["গিট", "কমিট", "পুশ", "পুল", "ব্রাঞ্চ"],
            },
            "terminal_pip": {
                "keywords_en": ["pip", "install package", "python package"],
                "keywords_bn": ["পিপ", "প্যাকেজ", "ইন্সটল", "পাইথন"],
            },
            "terminal_npm": {
                "keywords_en": ["npm", "node", "install module", "yarn"],
                "keywords_bn": ["এনপিএম", "নোড", "মডিউল", "ইয়ার্ন"],
            },

            # ===== WEATHER / TIME / INFO =====
            "info_weather": {
                "keywords_en": ["weather", "temperature", "rain", "sunny", "forecast"],
                "keywords_bn": ["আবহাওয়া", "তাপমাত্রা", "বৃষ্টি", "রোদ", "পূর্বাভাস"],
            },
            "info_time": {
                "keywords_en": ["time", "what time", "clock", "current time"],
                "keywords_bn": ["সময়", "কটা বাজে", "ঘড়ি", "বর্তমান"],
            },
            "info_date": {
                "keywords_en": ["date", "today", "day", "what day"],
                "keywords_bn": ["তারিখ", "আজ", "কী দিন", "বার"],
            },
            "info_news": {
                "keywords_en": ["news", "headlines", "latest", "update"],
                "keywords_bn": ["খবর", "নিউজ", "সর্বশেষ", "আপডেট"],
            },

            # ===== CHAT / GENERAL =====
            "chat": {
                "keywords_en": ["hello", "hi", "hey", "how are you", "thanks", "thank you"],
                "keywords_bn": ["হ্যালো", "হাই", "কেমন", "ধন্যবাদ", "থ্যাংকস"],
            },
            "chat_help": {
                "keywords_en": ["help", "what can you do", "capabilities", "features", "commands"],
                "keywords_bn": ["হেল্প", "কী করতে পারো", "ক্যাপাবিলিটি", "ফিচার", "কমান্ড"],
            },
        }

    # ========== MAIN CLASSIFY METHOD ==========

    def classify(self, command: str) -> Dict:
        """
        Multi-layer classification:
        1. AI Classification (most accurate)
        2. Regex Pattern Matching
        3. Keyword Scoring
        4. Context Awareness
        5. Default fallback
        """
        if not command or not command.strip():
            return self._default_response("empty")

        command = command.strip()
        cmd_lower = command.lower()

        # Layer 1: Regex Pattern Matching (precise, no network)
        regex_result = self._regex_classify(command)
        if regex_result:
            regex_result["method"] = "regex"
            self._update_context(command, regex_result["intent"])
            return regex_result

        # Layer 2: Keyword Scoring (fast, no network)
        keyword_result = self._keyword_classify(command)
        if keyword_result and keyword_result.get("confidence", 0) >= 0.4:
            keyword_result["method"] = "keyword"
            self._update_context(command, keyword_result["intent"])
            return keyword_result

        # Layer 3: Obvious conversation (no AI classification needed)
        if self._fast_chat(command):
            result = {
                "intent": "chat",
                "entities": {"query": command},
                "confidence": 0.95,
                "method": "fast",
            }
            self._update_context(command, "chat")
            return result

        # Layer 4: AI Classification (only for ambiguous / agent commands)
        ai_result = self._ai_classify(command)
        if ai_result and ai_result.get("confidence", 0) >= self.confidence_threshold:
            ai_result["method"] = "ai"
            self._update_context(command, ai_result["intent"])
            return ai_result

        # Layer 5: Context Awareness
        context_result = self._context_classify(command)
        if context_result:
            context_result["method"] = "context"
            self._update_context(command, context_result["intent"])
            return context_result

        # Layer 6: Default fallback
        fallback = self._default_response("unknown", command)
        self._update_context(command, "chat")
        return fallback

    def _fast_chat(self, command: str) -> bool:
        """True for greetings/thanks/small talk that should go straight to chat."""
        text = re.sub(r"[^\w\s\u0980-\u09FF']", " ", command.lower())
        text = re.sub(r"\s+", " ", text).strip()
        return bool(text and _FAST_CHAT_RE.match(text))

    # ========== LAYER 1: AI CLASSIFICATION ==========

    def _ai_classify(self, command: str) -> Optional[Dict]:
        """Use AI engine for intent classification"""
        try:
            prompt = f"""You are an intent classifier for Atlas 7.0 AI Assistant.
Analyze the user command and classify it into one intent.

Available intents and examples:
- open_app: "open youtube", "chrome চালু কর", "gmail খোল"
- pc_optimize: "optimize my pc", "pc fast কর", "performance boost"
- pc_clean: "clean pc", "junk clear কর", "disk cleanup"
- pc_shutdown: "shutdown", "pc off কর", "sleep mode"
- pc_restart: "restart", "reboot কর"
- pc_lock: "lock pc", "screen lock কর"
- pc_battery: "battery status", "চার্জ কত"
- pc_status: "system status", "pc health check"
- file_organize: "organize downloads", "ফাইল গোছাও", "desktop সাজাও"
- file_search: "find my resume", "file খুঁজ", "document কোথায়"
- file_create: "create new file", "folder বানাও", "new document"
- file_delete: "delete file", "মুছে ফেল", "remove"
- file_copy: "copy file", "duplicate কর"
- file_move: "move file", "transfer কর"
- file_rename: "rename file", "নাম বদলাও"
- file_backup: "backup files", "copy রাখ"
- web_search: "search google", "google এ খুঁজ", "look up"
- web_research: "research AI", "AI সম্পর্কে জানতে চাই", "explain quantum"
- web_summarize: "summarize this", "সংক্ষেপে বলো"
- web_translate: "translate to bangla", "বাংলায় অনুবাদ"
- web_bookmark: "bookmark this", "save page"
- web_history: "show history", "browsing history"
- media_youtube: "youtube এ খুঁজ", "play video", "ভিডিও দেখ"
- media_music: "play music", "গান শোন", "spotify চালু"
- media_video: "play movie", "সিনেমা দেখ", "video player"
- media_image: "generate image", "ছবি বানাও", "AI image"
- media_meme: "make meme", "মিম বানাও", "funny image"
- media_download: "download video", "ভিডিও ডাউনলোড", "save song"
- media_subtitle: "add subtitle", "সাবটাইটেল যোগ"
- media_convert: "convert to mp3", "mp4 এ কনভার্ট"
- productivity_task: "add task", "new task", "কাজ যোগ কর"
- productivity_show_tasks: "show tasks", "আমার কাজ দেখাও"
- productivity_pomodoro: "pomodoro start", "focus mode", "পড়াশোনা টাইমার"
- productivity_reminder: "remind me", "মনে করিয়ে দিও", "alert দাও"
- productivity_calendar: "show calendar", "schedule দেখাও", "meeting কখন"
- productivity_note: "take note", "নোট নাও", "write down"
- productivity_alarm: "set alarm", "ঘড়ি বাজাও", "wake me up"
- security_lock: "lock system", "system lock কর"
- security_privacy: "privacy mode", "incognito", "গোপন মোড"
- security_breach: "check breach", "email hacked?", "leak check"
- security_password: "check password", "strong password", "password generate"
- security_scan: "virus scan", "malware check", "security scan"
- security_firewall: "firewall status", "block site", "allow connection"
- terminal_run: "run command", "terminal এ রান", "execute script"
- terminal_git: "git status", "git commit", "push কর"
- terminal_pip: "pip install", "package install"
- terminal_npm: "npm install", "node module"
- info_weather: "weather কেমন", "temperature কত", "rain forecast"
- info_time: "time কত", "কটা বাজে", "current time"
- info_date: "date কত", "আজ কত তারিখ", "what day"
- info_news: "news দেখাও", "headlines", "latest update"
- chat: "hello", "hi", "কেমন আছো", "thanks"
- chat_help: "help", "কী করতে পারো", "features দেখাও"

Command: "{command}"

Return ONLY valid JSON in this exact format:
{{"intent": "intent_name", "entities": {{"key": "value"}}, "confidence": 0.95}}

If unsure, use "chat" intent with low confidence."""

            response = ai_engine.chat(
                prompt,
                use_history=False,
                system_prompt="You are an intent classifier. Return ONLY valid JSON in the requested format."
            )

            # Clean JSON response
            response = self._clean_json_response(response)
            result = json.loads(response)

            # Validate intent exists
            if result.get("intent") not in self.intent_patterns:
                result["intent"] = "chat"
                result["confidence"] = 0.3

            # Ensure entities exist
            if "entities" not in result:
                result["entities"] = {}

            # Extract additional entities from command
            result["entities"] = self._extract_entities(command, result["intent"], result["entities"])

            return result

        except Exception as e:
            print(f"AI classification error: {e}")
            return None

    def _clean_json_response(self, response: str) -> str:
        """Clean AI JSON response"""
        response = response.strip()
        # Remove markdown code blocks
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        # Remove extra text, keep only JSON
        response = response.strip()
        # Find first { and last }
        start = response.find("{")
        end = response.rfind("}")
        if start != -1 and end != -1:
            response = response[start:end+1]
        return response

    # ========== LAYER 2: REGEX CLASSIFICATION ==========

    def _regex_classify(self, command: str) -> Optional[Dict]:
        """Pattern matching for precise commands"""
        patterns = [
            # Bengali info queries. The older Bengali patterns below were
            # saved with broken encoding, so proper Unicode is added explicitly.
            (r"(?:আজ\s+)?(?:কী|কি)\s+তারিখ|আজ\s+(?:তারিখ|কত\s+তারিখ)|আজ\s+(?:কী|কি)\s+বার", "info_date", None),
            (r"(?:এখন\s+)?(?:কয়টা|কত)\s+বাজে|এখন\s+সময়\s+কত|সময়\s+কত\s+বাজে", "info_time", None),
            (r"(?:আজ\s+)?(?:আবহা\w*|তাপমাত্রা|বৃষ্টি)\s*(?:কেমন|কী|কি)?", "info_weather", None),
            # Open app with explicit app name
            (r"(?:open|launch|start|run|খোল|চালু|ওপেন)\s+(\w+)", "open_app", "app_name"),
            # URL open
            (r"(?:go to|visit|open|খোল)\s+(https?://\S+|\w+\.\w+)", "open_app", "url"),
            # YouTube search
            (r"(?:youtube|ইউটিউব)(?:\s+(?:এ|on|in))?\s+(?:খুঁজ|search|দেখ|play)?\s*(.+)", "media_youtube", "query"),
            # Search with query
            (r"(?:search|google|খুঁজ|look up)\s+(?:for|এর|জন্য)?\s*(.+)", "web_search", "query"),
            # Research topic
            (r"(?:research|learn about|tell me about|explain|জানতে চাই|ব্যাখ্যা|কী)\s+(.+)", "web_research", "topic"),
            # Task with description
            (r"(?:add|new|create|যোগ|নতুন)\s+(?:task|todo|কাজ|টাস্ক)\s*(?::|-)?\s*(.+)", "productivity_task", "task"),
            # Reminder with time
            (r"(?:remind|মনে করিয়ে|alert)\s+(?:me|আমাকে)?\s*(?:to|যেন)?\s*(.+?)(?:\s+(?:at|on|in|পরে|এ|কখন))?\s*(.+)?", "productivity_reminder", "reminder"),
            # Pomodoro with optional time
            (r"(?:pomodoro|focus|timer|টাইমার|পড়াশোনা)(?:\s+(?:for|of|duration))?\s*(\d+)?", "productivity_pomodoro", "minutes"),
            # File operations with path
            (r"(?:organize|sort|গোছাও|সাজাও)\s+(?:the|my)?\s*(downloads|desktop|documents|ডাউনলোড|ডেস্কটপ)?", "file_organize", "location"),
            # Weather with location
            (r"(?:weather|temperature|আবহাওয়া|তাপমাত্রা)(?:\s+(?:in|at|of|এ|এর))?\s*(.+)?", "info_weather", "location"),
            # Time query
            (r"(?:time|কটা বাজে|সময়|clock)(?:\s+(?:is it|now|এখন))?", "info_time", None),
            # Date query  
            (r"(?:date|তারিখ|day|দিন)(?:\s+(?:is it|today|আজ))?", "info_date", None),
            # Breach check with email
            (r"(?:breach|leak|hack|ব্রিচ|লিক)(?:\s+(?:check|test|চেক))?\s*(?:for|of)?\s*(\S+@\S+)", "security_breach", "email"),
            # Password check
            (r"(?:password|pass|পাসওয়ার্ড)(?:\s+(?:check|strength|test|চেক))?\s*(.+)?", "security_password", "password"),
            # System commands
            (r"(?:shutdown|turn off|power off|শাটডাউন|বন্ধ)(?:\s+(?:pc|computer|system|পিসি))?", "pc_shutdown", None),
            (r"(?:restart|reboot|রিস্টার্ট|আবার চালু)(?:\s+(?:pc|computer|system|পিসি))?", "pc_restart", None),
            (r"(?:lock|লক)(?:\s+(?:pc|screen|computer|system|পিসি|স্ক্রিন))?", "pc_lock", None),
            # Git commands
            (r"(?:git|গিট)\s+(status|pull|push|commit|branch|log|clone|checkout|merge)", "terminal_git", "git_command"),
            # Install packages
            (r"(?:pip|npm|yarn)\s+(install|uninstall|update|list)\s*(\S+)?", "terminal_pip", "package"),
        ]

        for pattern, intent, entity_key in patterns:
            match = re.search(pattern, command, re.IGNORECASE)
            if match:
                entities = {}
                if entity_key and match.groups():
                    value = match.group(1).strip() if match.group(1) else ""
                    if value:
                        entities[entity_key] = value

                # Extract additional entities
                entities = self._extract_entities(command, intent, entities)

                return {
                    "intent": intent,
                    "entities": entities,
                    "confidence": 0.85,
                    "matched_pattern": pattern
                }

        return None

    # ========== LAYER 3: KEYWORD SCORING ==========

    def _keyword_classify(self, command: str) -> Optional[Dict]:
        """Score-based keyword matching"""
        cmd_lower = command.lower()
        scores = {}

        for intent, data in self.intent_patterns.items():
            score = 0
            matched_keywords = []

            # Check English keywords
            for kw in data.get("keywords_en", []):
                if kw in cmd_lower:
                    score += len(kw.split()) * 2  # Longer matches = higher score
                    matched_keywords.append(kw)

            # Check Bangla keywords
            for kw in data.get("keywords_bn", []):
                if kw in cmd_lower:
                    score += len(kw) * 1.5  # Bangla characters weighted
                    matched_keywords.append(kw)

            # Check app names for open_app
            if intent == "open_app":
                for app_name, aliases in data.get("apps", {}).items():
                    for alias in aliases:
                        if alias in cmd_lower:
                            score += 10
                            matched_keywords.append(f"app:{app_name}")
                            break

            # Check sub-actions
            for sub in data.get("sub_actions", []):
                if sub in cmd_lower:
                    score += 3
                    matched_keywords.append(sub)

            # Check locations for file operations
            for loc in data.get("locations", []):
                if loc in cmd_lower:
                    score += 5
                    matched_keywords.append(f"loc:{loc}")

            scores[intent] = {
                "score": score,
                "keywords": matched_keywords
            }

        # Find best match
        best_intent = None
        best_score = 0

        for intent, data in scores.items():
            if data["score"] > best_score:
                best_score = data["score"]
                best_intent = intent

        if best_intent and best_score >= 3:
            confidence = min(0.4 + (best_score * 0.05), 0.75)
            entities = self._extract_entities(command, best_intent, {})

            return {
                "intent": best_intent,
                "entities": entities,
                "confidence": confidence,
                "matched_keywords": scores[best_intent]["keywords"]
            }

        return None

    # ========== LAYER 4: CONTEXT AWARENESS ==========

    def _context_classify(self, command: str) -> Optional[Dict]:
        """Use conversation context for ambiguous commands"""
        if not self.context_history:
            return None

        # Check if command is a follow-up
        follow_up_patterns = [
            r"^(yes|yeah|sure|ok|ঠিক|হ্যাঁ|জি|করো|ok)$",
            r"^(no|nah|not|না|নেই)$",
            r"^(again|repeat|আবার|আরেকবার)$",
            r"^(cancel|stop|abort|বাতিল|থামো)$",
            r"^(more|another|আরও|আরেকটা)$",
            r"^(done|finished|complete|হয়ে গেছে|শেষ)$",
        ]

        for pattern in follow_up_patterns:
            if re.match(pattern, command.strip(), re.IGNORECASE):
                last_intent = self.context_history[-1]["intent"] if self.context_history else "chat"
                return {
                    "intent": last_intent,
                    "entities": {"follow_up": command.strip()},
                    "confidence": 0.5,
                    "context_used": True
                }

        # Check for pronoun references
            pronoun_patterns = [
                r"\b(it|that|this|the file|the folder|সেটা|এটা|ওটা|ফাইলটা|ফোল্ডারটা)\b",
        ]
        for pattern in pronoun_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                if self.context_history:
                    last_intent = self.context_history[-1]["intent"]
                    last_entities = self.context_history[-1]["entities"]
                    return {
                        "intent": last_intent,
                        "entities": {**last_entities, "pronoun_reference": True},
                        "confidence": 0.45,
                        "context_used": True
                    }

        return None

    # ========== ENTITY EXTRACTION ==========

    def _extract_entities(self, command: str, intent: str, existing: Dict) -> Dict:
        """Extract relevant entities based on intent"""
        entities = existing.copy()
        cmd_lower = command.lower()

        # Extract app name
        if intent == "open_app":
            for app_name, aliases in self.intent_patterns["open_app"]["apps"].items():
                for alias in aliases:
                    if alias in cmd_lower:
                        entities["app_name"] = app_name
                        break
                if "app_name" in entities:
                    break
            if "app_name" not in entities:
                # Try to extract any word after open/launch/start
                match = re.search(r"(?:open|launch|start|run|খোল|চালু|ওপেন)\s+(\w+)", command, re.IGNORECASE)
                if match:
                    entities["app_name"] = match.group(1).lower()

        # Extract query/topic
        elif intent in ["web_search", "web_research", "media_youtube"]:
            if "query" not in entities and "topic" not in entities:
                # Remove intent keywords to get query
                query = command
                remove_words = ["search", "google", "research", "youtube", "খুঁজ", "জানতে", "দেখ", "play", "about", "for"]
                for word in remove_words:
                    query = re.sub(r'\b' + re.escape(word) + r'\b', '', query, flags=re.IGNORECASE)
                    query = query.strip().strip("',.!?\"")
                if query:
                    entities["query"] = query
                    entities["topic"] = query

        # Extract task
        elif intent == "productivity_task":
            if "task" not in entities:
                match = re.search(r"(?:task|todo|কাজ|টাস্ক)\s*(?::|-)?\s*(.+)", command, re.IGNORECASE)
                if match:
                    entities["task"] = match.group(1).strip()
                else:
                    # Remove keywords and use rest as task
                    task = re.sub(r'\b(add|new|create|task|todo|কাজ|টাস্ক|যোগ|নতুন)\b', '', command, flags=re.IGNORECASE).strip()
                    if task:
                        entities["task"] = task

        # Extract reminder with time
        elif intent == "productivity_reminder":
            if "reminder" not in entities:
                # Try to extract time
                time_match = re.search(r"(?:at|on|in|পরে|এ|কখন)\s+(.+?)(?:\s|$)", command, re.IGNORECASE)
                if time_match:
                    entities["time"] = time_match.group(1).strip()

                # Extract reminder text
                reminder = re.sub(r'\b(remind|me|to|alert|মনে|করিয়ে|আমাকে|যেন)\b', '', command, flags=re.IGNORECASE).strip()
                if reminder:
                    entities["reminder"] = reminder

        # Extract minutes for pomodoro
        elif intent == "productivity_pomodoro":
            if "minutes" not in entities:
                match = re.search(r'(\d+)\s*(?:min|minute|মিনিট)?', command, re.IGNORECASE)
                if match:
                    entities["minutes"] = int(match.group(1))
                else:
                    entities["minutes"] = 25  # Default

        # Extract location for file operations
        elif intent == "file_organize":
            if "location" not in entities:
                locations = {
                    "downloads": ["downloads", "download", "ডাউনলোড", "ডাউনলোডস"],
                    "desktop": ["desktop", "ডেস্কটপ"],
                    "documents": ["documents", "docs", "ডকুমেন্টস", "ডকুমেন্ট"],
                    "pictures": ["pictures", "photos", "images", "ছবি", "ফটো"],
                }
                for loc, aliases in locations.items():
                    for alias in aliases:
                        if alias in cmd_lower:
                            entities["location"] = loc
                            break
                    if "location" in entities:
                        break
                if "location" not in entities:
                    entities["location"] = "downloads"  # Default

        # Extract file path
        elif intent in ["file_search", "file_delete", "file_copy", "file_move", "file_rename"]:
            path_match = re.search(r'["\'](.+?)["\']|(\b\w+\.\w+\b)', command)
            if path_match:
                entities["file_name"] = path_match.group(1) or path_match.group(2)

        # Extract URL
        elif intent in ["open_app", "web_search"]:
            url_match = re.search(r'(https?://\S+|\w+\.\w+\.\w+)', command)
            if url_match:
                entities["url"] = url_match.group(1)
                if not entities["url"].startswith("http"):
                    entities["url"] = "https://" + entities["url"]

        # Extract email for breach check
        elif intent == "security_breach":
            email_match = re.search(r'(\S+@\S+\.\S+)', command)
            if email_match:
                entities["email"] = email_match.group(1)

        # Extract language for translation
        elif intent == "web_translate":
            lang_match = re.search(r'(?:to|in|এ|তে)\s+(bangla|english|bengali|spanish|french|hindi|বাংলা|ইংরেজি)', command, re.IGNORECASE)
            if lang_match:
                entities["target_language"] = lang_match.group(1)

        return entities

    # ========== DEFAULT RESPONSE ==========

    def _default_response(self, reason: str, command: str = "") -> Dict:
        """Default fallback response"""
        return {
            "intent": "chat",
            "entities": {"query": command, "fallback_reason": reason},
            "confidence": 0.2,
            "method": "fallback",
            "message": "General conversation or unclear command"
        }

    # ========== CONTEXT MANAGEMENT ==========

    def _update_context(self, command: str, intent: str):
        """Update conversation context"""
        self.context_history.append({
            "command": command,
            "intent": intent,
            "timestamp": self._get_timestamp()
        })
        # Keep only last 5
        if len(self.context_history) > 5:
            self.context_history = self.context_history[-5:]

    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()

    def get_context(self) -> List[Dict]:
        """Get current context history"""
        return self.context_history.copy()

    def clear_context(self):
        """Clear conversation context"""
        self.context_history = []

    # ========== UTILITY METHODS ==========

    def get_all_intents(self) -> List[str]:
        """Get list of all available intents"""
        return list(self.intent_patterns.keys())

    def get_intent_info(self, intent: str) -> Dict:
        """Get information about a specific intent"""
        return self.intent_patterns.get(intent, {})

    def add_custom_intent(self, intent_name: str, keywords_en: List[str], keywords_bn: List[str] = None):
        """Add a custom intent dynamically"""
        self.intent_patterns[intent_name] = {
            "keywords_en": keywords_en,
            "keywords_bn": keywords_bn or [],
            "custom": True
        }

    def batch_classify(self, commands: List[str]) -> List[Dict]:
        """Classify multiple commands at once"""
        return [self.classify(cmd) for cmd in commands]


# ========== CONVENIENCE FUNCTIONS ==========

_classifier = None

def get_classifier() -> IntentClassifier:
    """Get or create singleton classifier"""
    global _classifier
    if _classifier is None:
        _classifier = IntentClassifier()
    return _classifier

def classify_intent(command: str) -> Dict:
    """Main function to classify a single command"""
    classifier = get_classifier()
    return classifier.classify(command)

def classify_batch(commands: List[str]) -> List[Dict]:
    """Classify multiple commands"""
    classifier = get_classifier()
    return classifier.batch_classify(commands)

def get_available_intents() -> List[str]:
    """Get all available intent names"""
    classifier = get_classifier()
    return classifier.get_all_intents()


# ========== TESTING ==========
if __name__ == "__main__":
    test_commands = [
        "open youtube",
        "youtube খোল",
        "optimize my pc",
        "pc পরিষ্কার কর",
        "organize downloads",
        "downloads গোছাও",
        "research artificial intelligence",
        "AI সম্পর্কে জানতে চাই",
        "add task: complete project",
        "নতুন কাজ যোগ কর: প্রজেক্ট শেষ কর",
        "pomodoro start 30 minutes",
        "30 মিনিট পোমোডোরো",
        "lock pc",
        "screen lock কর",
        "check breach for test@email.com",
        "weather in Dhaka",
        "ঢাকার আবহাওয়া",
        "what time is it",
        "কটা বাজে",
        "hello",
        "হ্যালো",
    ]

    classifier = IntentClassifier()
    for cmd in test_commands:
        result = classifier.classify(cmd)
        print(f"\nCommand: {cmd}")
        print(f"  Intent: {result['intent']}")
        print(f"  Entities: {result['entities']}")
        print(f"  Confidence: {result['confidence']}")
        print(f"  Method: {result.get('method', 'unknown')}")