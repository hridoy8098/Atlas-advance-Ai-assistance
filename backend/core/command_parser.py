# backend/core/command_parser.py — Atlas 6.0 Command Parser
# NLP → Action Router — User command বুঝে action decide করে

import re
import json
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

import config
from backend.core.language import language_detector, get_lang


class CommandParser:
    """
    Atlas 6.0 Command Parser
    - Natural language understanding
    - Intent detection (বাংলা + English)
    - Entity extraction
    - Action routing
    """
    
    def __init__(self):
        # Intent patterns (বাংলা + English)
        self.intents = self._load_intents()
        
        # Action mapping
        self.action_map = {
            # System
            "system_status": "system_agent.get_status",
            "cpu_usage": "system_agent.get_cpu",
            "ram_usage": "system_agent.get_ram",
            "disk_usage": "system_agent.get_disk",
            "battery": "system_agent.get_battery",
            "optimize_system": "system_agent.optimize",
            "clean_ram": "system_agent.clean_ram",
            "clean_temp": "system_agent.clean_temp",
            
            # Apps
            "open_app": "app_agent.open",
            "close_app": "app_agent.close",
            "switch_app": "app_agent.switch",
            "list_apps": "app_agent.list_running",
            
            # Files
            "open_file": "file_agent.open",
            "create_file": "file_agent.create",
            "delete_file": "file_agent.delete",
            "search_file": "file_agent.search",
            "organize_files": "file_agent.organize",
            
            # Browser
            "open_website": "browser_agent.open",
            "search_web": "browser_agent.search",
            "close_tab": "browser_agent.close_tab",
            
            # Terminal
            "run_command": "terminal_agent.execute",
            "git_command": "terminal_agent.git",
            
            # Vision
            "take_screenshot": "vision.screenshot",
            "read_screen": "vision.read_screen",
            "scan_qr": "vision.scan_qr",
            "detect_objects": "vision.detect_objects",
            "scan_ocr": "vision.ocr",
            
            # Productivity
            "read_pdf": "productivity.read_pdf",
            "check_email": "productivity.check_email",
            "add_event": "productivity.add_calendar",
            "summarize": "productivity.summarize",
            "solve_math": "productivity.solve_math",
            
            # Study
            "flashcards": "study.flashcards",
            "exam_prep": "study.exam_prep",
            "youtube_learn": "study.youtube",
            "teacher_mode": "study.teach",
            
            # Media
            "play_music": "media.play_music",
            "download_video": "media.download_video",
            "generate_image": "media.generate_image",
            "create_meme": "media.create_meme",
            
            # Security
            "lock_system": "security.lock",
            "privacy_mode": "security.privacy",
            "scan_network": "security.scan_network",
            "scan_malware": "security.malware_scan",
            
            # Info
            "get_time": "info.time",
            "get_date": "info.date",
            "get_weather": "info.weather",
            "get_news": "info.news",
            "prayer_times": "info.prayer",
            "stock_price": "info.stock",
            "currency_convert": "info.currency",
            
            # General
            "tell_joke": "fun.joke",
            "tell_story": "fun.story",
            "quiz": "fun.quiz",
            "debate": "fun.debate",
            "greeting": "general.greet",
            "goodbye": "general.goodbye",
            "thanks": "general.thanks",
        }
        
        print(f"🎯 Command Parser initialized")
        print(f"   Intents loaded: {len(self.intents)}")
        print(f"   Actions mapped: {len(self.action_map)}")
    
    def _load_intents(self) -> Dict:
        """Intent patterns load করো (বাংলা + English)"""
        return {
            # ===== SYSTEM =====
            "system_status": {
                "patterns": [
                    # English
                    r"\b(system\s*status|how.*system|system\s*info|pc\s*status|computer\s*status)\b",
                    # বাংলা
                    r"\b(সিস্টেম\s*স্ট্যাটাস|সিস্টেম\s*কেমন|পিসি\s*স্ট্যাটাস|কম্পিউটার\s*কেমন)\b",
                ],
                "priority": 1
            },
            "cpu_usage": {
                "patterns": [
                    r"\b(cpu|processor|processing)(\s*usage|\s*কত|\s*status)?\b",
                    r"\b(সিপিইউ|প্রসেসর)(\s*কত|\s*ব্যবহার)?\b",
                ],
                "priority": 1
            },
            "ram_usage": {
                "patterns": [
                    r"\b(ram|memory|মেমরি|র‌্যাম)(\s*usage|\s*কত|\s*used)?\b",
                ],
                "priority": 1
            },
            "disk_usage": {
                "patterns": [
                    r"\b(disk|storage|ডিস্ক|স্টোরেজ)(\s*usage|\s*কত|\s*space)?\b",
                ],
                "priority": 1
            },
            "battery": {
                "patterns": [
                    r"\b(battery|bat|চার্জ|ব্যাটারি)(\s*level|\s*percentage|\s*কত)?\b",
                ],
                "priority": 1
            },
            "optimize_system": {
                "patterns": [
                    r"\b(optimize|speed\s*up|boost|clean)\s*(system|pc|computer|সিস্টেম|পিসি)\b",
                    r"\b(অপ্টিমাইজ|পরিষ্কার|দ্রুত)\s*(কর|করো|করুন)\b",
                ],
                "priority": 1
            },
            "clean_ram": {
                "patterns": [
                    r"\b(clean|clear|free)\s*(ram|memory)\b",
                    r"\b(র‌্যাম|মেমরি)\s*(পরিষ্কার|খালি|ক্লিন)\b",
                ],
                "priority": 1
            },
            "clean_temp": {
                "patterns": [
                    r"\b(clean|clear|delete)\s*(temp|temporary|cache|junk)\b",
                    r"\b(টেম্প|অস্থায়ী|ক্যাশে|জাংক)\s*(ফাইল\s*)?(পরিষ্কার|মুছ|ডিলিট)\b",
                ],
                "priority": 1
            },
            
            # ===== APPS =====
            "open_app": {
                "patterns": [
                    r"\b(open|start|launch|খোল|খুল|চালু|শুরু)\s+(.+?)\b",
                    r"\b(.+?)\s*(খোল|খুল|চালু|open|start)\b",
                ],
                "priority": 2,
                "entity": "app_name"
            },
            "close_app": {
                "patterns": [
                    r"\b(close|quit|exit|stop|বন্ধ|বন্ধ\s*কর)\s+(.+?)\b",
                    r"\b(.+?)\s*(বন্ধ|close|quit)\b",
                ],
                "priority": 2,
                "entity": "app_name"
            },
            
            # ===== FILES =====
            "open_file": {
                "patterns": [
                    r"\b(open|show|display|দেখা|দেখ|খোল)\s+(file|ফাইল|document|ডকুমেন্ট)?\s*(.+?)?\b",
                ],
                "priority": 2,
                "entity": "file_name"
            },
            "search_file": {
                "patterns": [
                    r"\b(search|find|look\s*for|খুঁজ|খোঁজ|সার্চ)\s+(file|ফাইল)?\s*(.+?)\b",
                ],
                "priority": 2,
                "entity": "search_query"
            },
            "organize_files": {
                "patterns": [
                    r"\b(organize|sort|arrange|গোছা|সাজা)\s*(files|ফাইল|downloads|ডাউনলোড)\b",
                ],
                "priority": 1
            },
            
            # ===== BROWSER =====
            "open_website": {
                "patterns": [
                    r"\b(open|go\s*to|visit|navigate|যা|চল|দেখ)\s+(website|site|ওয়েবসাইট|সাইট)?\s*(.+?)\b",
                    r"\b(.+?)\s*(\.com|\.org|\.net|\.io|\.dev)\b",
                ],
                "priority": 2,
                "entity": "url"
            },
            "search_web": {
                "patterns": [
                    r"\b(search|google|সার্চ|খুঁজ)\s+(for\s+)?(.+?)(\s+on\s+(web|internet|নেট))?\b",
                ],
                "priority": 3,
                "entity": "search_term"
            },
            
            # ===== TERMINAL =====
            "run_command": {
                "patterns": [
                    r"\b(run|execute|চালা)\s+(command|কমান্ড)?\s*(.+?)\b",
                ],
                "priority": 3,
                "entity": "command"
            },
            
            # ===== VISION =====
            "take_screenshot": {
                "patterns": [
                    r"\b(take\s*(a\s*)?screenshot|screenshot|capture\s*screen|স্ক্রিনশট|ছবি\s*তোল)\b",
                ],
                "priority": 1
            },
            "read_screen": {
                "patterns": [
                    r"\b(read|analyze|check|দেখ|পড়|বিশ্লেষণ)\s*(my\s*)?(screen|display|স্ক্রিন|ডিসপ্লে)\b",
                ],
                "priority": 1
            },
            "scan_qr": {
                "patterns": [
                    r"\b(scan|read)\s*(qr|barcode|কিউআর|বারকোড)\b",
                ],
                "priority": 1
            },
            "scan_ocr": {
                "patterns": [
                    r"\b(scan|read|extract)\s*(text|document|image|লেখা|টেক্সট)\b",
                    r"\b(ocr|ওসিআর)\b",
                ],
                "priority": 1
            },
            
            # ===== PRODUCTIVITY =====
            "read_pdf": {
                "patterns": [
                    r"\b(read|open|analyze|পড়|দেখ)\s*(pdf|পিডিএফ)\b",
                ],
                "priority": 1
            },
            "check_email": {
                "patterns": [
                    r"\b(check|show|read)\s*(email|mail|gmail|ইমেইল|মেইল|ইনবক্স)\b",
                ],
                "priority": 1
            },
            "summarize": {
                "patterns": [
                    r"\b(summarize|summary|sum\s*up|সংক্ষেপ|সারাংশ)\s*(this|text|document)?\b",
                ],
                "priority": 1
            },
            "solve_math": {
                "patterns": [
                    r"\b(solve|calculate|compute|সমাধান|গণনা)\s*(math|problem|equation|অংক)?\b",
                ],
                "priority": 2
            },
            
            # ===== STUDY =====
            "flashcards": {
                "patterns": [
                    r"\b(flashcard|flash\s*card|study\s*card|ফ্ল্যাশকার্ড|কার্ড)\b",
                ],
                "priority": 1
            },
            "exam_prep": {
                "patterns": [
                    r"\b(exam|test|পরীক্ষা)\s*(prep|preparation|প্রস্তুতি|practice|প্র্যাকটিস)\b",
                ],
                "priority": 1
            },
            "youtube_learn": {
                "patterns": [
                    r"\b(youtube|ইউটিউব)\s*(learn|teach|tutorial|শিখ|পড়)\b",
                ],
                "priority": 1
            },
            "teacher_mode": {
                "patterns": [
                    r"\b(teach|explain|শেখা|বুঝিয়ে\s*দাও|পড়া)\s*(me\s+)?(about\s+)?(.+?)\b",
                ],
                "priority": 3,
                "entity": "topic"
            },
            
            # ===== MEDIA =====
            "play_music": {
                "patterns": [
                    r"\b(play|start|চালা|বাজা)\s*(music|song|গান|মিউজিক)\b",
                ],
                "priority": 1
            },
            "download_video": {
                "patterns": [
                    r"\b(download|save|ডাউনলোড|সেভ)\s*(video|ভিডিও)\b",
                ],
                "priority": 1
            },
            "generate_image": {
                "patterns": [
                    r"\b(generate|create|make|বানা|তৈরি\s*কর)\s*(image|picture|photo|ছবি|ইমেজ)\b",
                ],
                "priority": 1
            },
            "create_meme": {
                "patterns": [
                    r"\b(create|make|generate|বানা)\s*(meme|মিম)\b",
                ],
                "priority": 1
            },
            
            # ===== SECURITY =====
            "lock_system": {
                "patterns": [
                    r"\b(lock|লক)\s*(system|pc|computer|screen|সিস্টেম|স্ক্রিন)\b",
                ],
                "priority": 1
            },
            "privacy_mode": {
                "patterns": [
                    r"\b(privacy|private|secret|গোপন|প্রাইভেসি)\s*(mode|মোড)\b",
                ],
                "priority": 1
            },
            
            # ===== INFO =====
            "get_time": {
                "patterns": [
                    r"\b(what\s*(is\s*)?(the\s*)?time|time\s*now|কয়টা\s*বাজে|সময়\s*কত|টাইম)\b",
                ],
                "priority": 1
            },
            "get_date": {
                "patterns": [
                    r"\b(what\s*(is\s*)?(the\s*)?date|today.*date|আজ\s*কত\s*তারিখ|আজ\s*কি\s*তারিখ)\b",
                ],
                "priority": 1
            },
            "get_weather": {
                "patterns": [
                    r"\b(weather|আবহাওয়া|তাপমাত্রা|temperature)\s*(of|in|at|এর|এ)?\s*(.+?)?\b",
                ],
                "priority": 2,
                "entity": "city"
            },
            "get_news": {
                "patterns": [
                    r"\b(news|খবর|নিউজ|সংবাদ)\s*(update|headline|today)?\b",
                ],
                "priority": 1
            },
            "prayer_times": {
                "patterns": [
                    r"\b(prayer|namaz|salat|নামাজ|সালাত|প্রার্থনা)\s*(time|সময়|ওয়াক্ত)?\b",
                ],
                "priority": 1
            },
            "stock_price": {
                "patterns": [
                    r"\b(stock|share|শেয়ার|স্টক)\s*(price|market|দাম|বাজার)\b",
                ],
                "priority": 1
            },
            
            # ===== FUN =====
            "tell_joke": {
                "patterns": [
                    r"\b(tell\s*(me\s*)?(a\s*)?joke|joke|কৌতুক|জোকস|মজা\s*কর)\b",
                ],
                "priority": 1
            },
            "tell_story": {
                "patterns": [
                    r"\b(tell\s*(me\s*)?(a\s*)?story|story|গল্প|কাহিনী)\b",
                ],
                "priority": 1
            },
            "quiz": {
                "patterns": [
                    r"\b(quiz|trivia|কুইজ|ধাঁধা|প্রশ্ন\s*কর)\b",
                ],
                "priority": 1
            },
            
            # ===== GENERAL =====
            "greeting": {
                "patterns": [
                    r"\b^(hi|hello|hey|হাই|হ্যালো|নমস্কার|আসসালামু\s*আলাইকুম)\b",
                ],
                "priority": 3
            },
            "goodbye": {
                "patterns": [
                    r"\b(bye|goodbye|see\s*you|বিদায়|আল্লাহ\s*হাফেজ|খোদা\s*হাফেজ)\b",
                ],
                "priority": 3
            },
            "thanks": {
                "patterns": [
                    r"\b(thanks|thank\s*you|thx|ধন্যবাদ|থ্যাংকস|থ্যাংক\s*ইউ)\b",
                ],
                "priority": 3
            },
        }
    
    # ===== MAIN PARSE FUNCTION =====
    
    def parse(self, text: str) -> Dict:
        """
        User command parse করে intent + entities return করো
        
        Returns:
            {
                "intent": str,
                "action": str,
                "entities": dict,
                "confidence": float,
                "language": str,
                "original_text": str
            }
        """
        if not text or not text.strip():
            return self._empty_result(text)
        
        text = text.strip()
        language = get_lang(text)
        
        # Find matching intent
        matches = []
        
        for intent_name, intent_data in self.intents.items():
            for pattern in intent_data["patterns"]:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    # Extract entity if present
                    entities = {}
                    if "entity" in intent_data:
                        entity_value = self._extract_entity(match, intent_data["entity"])
                        if entity_value:
                            entities[intent_data["entity"]] = entity_value
                    
                    confidence = self._calculate_confidence(match, intent_data["priority"])
                    
                    matches.append({
                        "intent": intent_name,
                        "action": self.action_map.get(intent_name, "general.chat"),
                        "entities": entities,
                        "confidence": confidence,
                        "priority": intent_data["priority"]
                    })
        
        # Select best match
        if matches:
            # Sort by priority (lower = more specific) and confidence
            matches.sort(key=lambda x: (x["priority"], -x["confidence"]))
            best = matches[0]
            
            return {
                "intent": best["intent"],
                "action": best["action"],
                "entities": best["entities"],
                "confidence": best["confidence"],
                "language": language,
                "original_text": text,
                "is_command": True
            }
        
        # No intent found → general chat
        return {
            "intent": "chat",
            "action": "general.chat",
            "entities": {"message": text},
            "confidence": 0.5,
            "language": language,
            "original_text": text,
            "is_command": False
        }
    
    def _extract_entity(self, match: re.Match, entity_name: str) -> Optional[str]:
        """Regex match থেকে entity value extract করো"""
        groups = match.groups()
        
        # Last non-None group is usually the entity
        for group in reversed(groups):
            if group and group.strip():
                # Clean up the entity
                entity = group.strip()
                # Remove common noise words
                noise = ["the", "a", "an", "টা", "টি", "খানা"]
                for word in noise:
                    entity = re.sub(rf'\b{word}\b', '', entity, flags=re.IGNORECASE)
                return entity.strip()
        
        return None
    
    def _calculate_confidence(self, match: re.Match, priority: int) -> float:
        """Match confidence calculate করো"""
        # Base confidence from priority
        base_confidence = {1: 0.95, 2: 0.85, 3: 0.75}.get(priority, 0.6)
        
        # Adjust by match length ratio
        matched_text = match.group(0)
        full_text = match.string
        if full_text:
            ratio = len(matched_text) / len(full_text)
            base_confidence += ratio * 0.1
        
        return min(1.0, base_confidence)
    
    def _empty_result(self, text: str) -> Dict:
        """Empty input result"""
        return {
            "intent": None,
            "action": None,
            "entities": {},
            "confidence": 0,
            "language": "en",
            "original_text": text or "",
            "is_command": False
        }
    
    # ===== QUICK PARSE =====
    
    def get_intent(self, text: str) -> str:
        """Quick intent only"""
        result = self.parse(text)
        return result["intent"]
    
    def get_action(self, text: str) -> str:
        """Quick action only"""
        result = self.parse(text)
        return result["action"]
    
    def is_command(self, text: str) -> bool:
        """Check if text is a command"""
        result = self.parse(text)
        return result["is_command"]
    
    # ===== SPECIAL COMMANDS =====
    
    def parse_special(self, text: str) -> Optional[Dict]:
        """Special commands (shortcuts)"""
        text_lower = text.lower().strip()
        
        specials = {
            # Shortcuts
            "ss": {"action": "vision.screenshot", "intent": "take_screenshot"},
            "lock": {"action": "security.lock", "intent": "lock_system"},
            "weather": {"action": "info.weather", "intent": "get_weather"},
            "time": {"action": "info.time", "intent": "get_time"},
            "news": {"action": "info.news", "intent": "get_news"},
            "joke": {"action": "fun.joke", "intent": "tell_joke"},
            
            # Bangla shortcuts
            "স্ক্রিনশট": {"action": "vision.screenshot", "intent": "take_screenshot"},
            "আবহাওয়া": {"action": "info.weather", "intent": "get_weather"},
            "নামাজ": {"action": "info.prayer", "intent": "prayer_times"},
        }
        
        if text_lower in specials:
            spec = specials[text_lower]
            return {
                "intent": spec["intent"],
                "action": spec["action"],
                "entities": {},
                "confidence": 1.0,
                "language": get_lang(text),
                "original_text": text,
                "is_command": True,
                "is_special": True
            }
        
        return None
    
    # ===== UTILITY =====
    
    def explain_intent(self, text: str) -> str:
        """Debug: Explain what was parsed"""
        result = self.parse(text)
        special = self.parse_special(text)
        
        if special:
            return f"⚡ Special: {special['intent']} → {special['action']}"
        
        if result["is_command"]:
            entities_str = ", ".join(f"{k}={v}" for k, v in result["entities"].items())
            return f"🎯 Intent: {result['intent']}\n📦 Action: {result['action']}\n🏷️ Entities: {entities_str or 'none'}\n📊 Confidence: {result['confidence']:.0%}"
        
        return f"💬 General chat (no command detected)"


# ===== Singleton =====
command_parser = CommandParser()


# ===== QUICK FUNCTIONS =====

def parse_command(text: str) -> Dict:
    """Quick parse"""
    return command_parser.parse(text)


def get_intent(text: str) -> str:
    """Quick intent"""
    return command_parser.get_intent(text)


def get_action(text: str) -> str:
    """Quick action"""
    return command_parser.get_action(text)


# ===== EEL EXPOSED FUNCTIONS =====
def setup_command_parser_eel():
    """Frontend থেকে call করার জন্য eel functions"""
    try:
        import eel
        
        @eel.expose
        def parse_user_command(text):
            """User command parse করো"""
            result = command_parser.parse(text)
            return {
                "intent": result["intent"],
                "action": result["action"],
                "entities": result["entities"],
                "confidence": result["confidence"],
                "language": result["language"],
                "is_command": result["is_command"]
            }
        
        @eel.expose
        def explain_command(text):
            """Debug: command explain করো"""
            return command_parser.explain_intent(text)
        
        print("✅ Command parser eel functions registered")
        
    except ImportError:
        print("⚠️ Eel not available")
    except Exception as e:
        print(f"⚠️ Command parser eel setup error: {e}")