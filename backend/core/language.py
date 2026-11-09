# backend/core/language.py — Atlas 6.0 Auto Language Detection
# বাংলা + English auto detect এবং switch

import re
import string
from typing import Optional, Dict, List, Tuple


class LanguageDetector:
    """
    Atlas 6.0 Language Detection System
    - Auto detect বাংলা vs English
    - Mixed language handling (Banglish)
    - Script detection
    - Language confidence scoring
    """
    
    def __init__(self):
        # Bengali Unicode ranges
        self.bengali_range = (0x0980, 0x09FF)
        self.bengali_numerals = range(0x09E6, 0x09EF + 1)  # ০-৯
        
        # Common Bengali words (detection এর জন্য)
        self.common_bengali_words = {
            'আমি', 'তুমি', 'সে', 'এই', 'ওই', 'কী', 'কেন', 'কখন', 'কোথায়', 'কে',
            'হ্যাঁ', 'না', 'আছে', 'নেই', 'হবে', 'করো', 'করবে', 'বলো', 'দাও', 'নাও',
            'ভালো', 'খারাপ', 'বড়', 'ছোট', 'নতুন', 'পুরনো', 'এক', 'দুই', 'তিন',
            'এবং', 'অথবা', 'কিন্তু', 'তাই', 'যদি', 'তবে', 'কারণ', 'জন্য', 'থেকে',
            'আমার', 'তোমার', 'তার', 'দের', 'দেরকে', 'গুলো', 'টি', 'খানা',
            'হয়', 'ছিল', 'থাকে', 'থাকবে', 'দেয়', 'নেয়', 'করে', 'বলে', 'যায়',
        }
        
        # Common English words (detection এর জন্য)
        self.common_english_words = {
            'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'can', 'could', 'shall', 'should', 'may', 'might', 'must',
            'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her',
            'this', 'that', 'these', 'those', 'here', 'there',
            'what', 'which', 'who', 'whom', 'whose', 'where', 'when', 'why', 'how',
            'a', 'an', 'the', 'and', 'or', 'but', 'if', 'then', 'else',
            'good', 'bad', 'big', 'small', 'new', 'old', 'one', 'two', 'three',
        }
        
        # Romanized Bengali patterns (Banglish)
        self.banglish_patterns = [
            r'\b(ami|tumi|se|kemon|bhalo|kharap|kichu|kotha|bolo|dao|nao)\b',
            r'\b(ki|keno|kokhon|kothay|ke|kar|kake|kader)\b',
            r'\b(hae|ha|na|ase|nai|hobe|korbo|korbe|bolbo|bolbe)\b',
            r'\b(eto|oto|koto|ekhon|tokhon|jokhon|ekhane|okhane|jekhane)\b',
        ]
        
        # Transliteration map (English → Bengali)
        self.transliteration_map = {
            'ami': 'আমি', 'tumi': 'তুমি', 'se': 'সে',
            'bhalo': 'ভালো', 'kharap': 'খারাপ', 'kemon': 'কেমন',
            'ki': 'কী', 'keno': 'কেনো', 'kothay': 'কোথায়',
            'hae': 'হ্যাঁ', 'na': 'না', 'ase': 'আছে', 'nai': 'নেই',
            'hobe': 'হবে', 'koro': 'করো', 'bolo': 'বলো', 'dao': 'দাও',
        }
        
        print("🌐 Language Detector initialized")
    
    # ===== MAIN DETECTION =====
    
    def detect(self, text: str) -> str:
        """
        Main detection function
        Returns: "bn", "en", "mixed", "banglish"
        """
        if not text or not text.strip():
            return "en"  # Default English
        
        text = text.strip()
        
        # Method 1: Unicode script detection
        script_result = self._detect_by_script(text)
        if script_result in ["bn", "en"]:
            return script_result
        
        # Method 2: Word frequency analysis
        word_result = self._detect_by_words(text)
        if word_result in ["bn", "en"]:
            return word_result
        
        # Method 3: Banglish detection
        if self._is_banglish(text):
            return "banglish"
        
        # Mixed
        return "mixed"
    
    def detect_with_confidence(self, text: str) -> Tuple[str, float]:
        """
        Language detect with confidence score
        Returns: (language, confidence 0-100)
        """
        if not text or not text.strip():
            return ("en", 100.0)
        
        text = text.strip()
        
        # Count characters by script
        bengali_chars = sum(1 for c in text if '\u0980' <= c <= '\u09FF')
        english_chars = sum(1 for c in text if c.isascii() and c.isalpha())
        total_chars = max(bengali_chars + english_chars, 1)
        
        # Calculate ratios
        bengali_ratio = (bengali_chars / total_chars) * 100
        english_ratio = (english_chars / total_chars) * 100
        
        # Determine language
        if bengali_ratio > 70:
            return ("bn", bengali_ratio)
        elif english_ratio > 70:
            return ("en", english_ratio)
        elif bengali_ratio > 30:
            return ("mixed", max(bengali_ratio, english_ratio))
        else:
            # Check Banglish
            if self._is_banglish(text):
                return ("banglish", 60.0)
            return ("en", english_ratio)
    
    # ===== SCRIPT DETECTION =====
    
    def _detect_by_script(self, text: str) -> Optional[str]:
        """Unicode script analysis"""
        bengali_count = 0
        english_count = 0
        total_letters = 0
        
        for char in text:
            if '\u0980' <= char <= '\u09FF':
                bengali_count += 1
                total_letters += 1
            elif char.isalpha() and char.isascii():
                english_count += 1
                total_letters += 1
        
        if total_letters == 0:
            return None
        
        bengali_ratio = bengali_count / total_letters
        
        if bengali_ratio > 0.7:
            return "bn"
        elif bengali_ratio < 0.1:
            return "en"
        
        return None  # Mixed, need more analysis
    
    # ===== WORD FREQUENCY =====
    
    def _detect_by_words(self, text: str) -> Optional[str]:
        """Common word frequency analysis"""
        # Tokenize
        words = self._tokenize(text.lower())
        
        if not words:
            return None
        
        bengali_hits = 0
        english_hits = 0
        
        for word in words:
            if word in self.common_bengali_words:
                bengali_hits += 1
            if word in self.common_english_words:
                english_hits += 1
        
        total_hits = bengali_hits + english_hits
        
        if total_hits == 0:
            return None
        
        if bengali_hits > english_hits * 2:
            return "bn"
        elif english_hits > bengali_hits * 2:
            return "en"
        
        return None
    
    # ===== BANGLISH DETECTION =====
    
    def _is_banglish(self, text: str) -> bool:
        """Check if text is Romanized Bengali (Banglish)"""
        text_lower = text.lower()
        
        for pattern in self.banglish_patterns:
            if re.search(pattern, text_lower):
                return True
        
        return False
    
    def banglish_to_bengali(self, text: str) -> str:
        """Convert Banglish → Bengali (basic)"""
        words = text.lower().split()
        converted = []
        
        for word in words:
            if word in self.transliteration_map:
                converted.append(self.transliteration_map[word])
            else:
                converted.append(word)
        
        return ' '.join(converted)
    
    # ===== UTILITY FUNCTIONS =====
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple word tokenizer"""
        # Remove punctuation
        text = text.translate(str.maketrans('', '', string.punctuation))
        # Split by whitespace
        return text.split()
    
    def is_bengali_char(self, char: str) -> bool:
        """Check if single character is Bengali"""
        if len(char) != 1:
            return False
        return '\u0980' <= char <= '\u09FF'
    
    def is_bengali_numeral(self, char: str) -> bool:
        """Check if character is Bengali numeral (০-৯)"""
        if len(char) != 1:
            return False
        return 0x09E6 <= ord(char) <= 0x09EF
    
    def bengali_to_english_numeral(self, bengali_num: str) -> str:
        """Convert Bengali numerals to English (১২৩ → 123)"""
        result = ""
        for char in bengali_num:
            if self.is_bengali_numeral(char):
                english_digit = ord(char) - 0x09E6
                result += str(english_digit)
            else:
                result += char
        return result
    
    def english_to_bengali_numeral(self, english_num: str) -> str:
        """Convert English numerals to Bengali (123 → ১২৩)"""
        result = ""
        for char in english_num:
            if char.isdigit():
                bengali_digit = chr(0x09E6 + int(char))
                result += bengali_digit
            else:
                result += char
        return result
    
    # ===== TEXT STATISTICS =====
    
    def get_text_stats(self, text: str) -> Dict:
        """Text analysis statistics"""
        if not text:
            return {}
        
        bengali_chars = sum(1 for c in text if '\u0980' <= c <= '\u09FF')
        english_chars = sum(1 for c in text if c.isascii() and c.isalpha())
        digits = sum(1 for c in text if c.isdigit())
        spaces = sum(1 for c in text if c.isspace())
        punctuation = sum(1 for c in text if c in string.punctuation)
        
        total_chars = len(text)
        words = len(self._tokenize(text))
        sentences = len(re.split(r'[।.!?]+', text))
        
        return {
            "total_chars": total_chars,
            "total_words": words,
            "total_sentences": sentences,
            "bengali_chars": bengali_chars,
            "english_chars": english_chars,
            "digits": digits,
            "spaces": spaces,
            "punctuation": punctuation,
            "bengali_percentage": round((bengali_chars / max(total_chars, 1)) * 100, 1),
            "english_percentage": round((english_chars / max(total_chars, 1)) * 100, 1),
        }
    
    # ===== LANGUAGE SWITCHING =====
    
    def get_response_language(self, user_text: str, preferred_language: str = "auto") -> str:
        """
        User এর text দেখে response এর language decide করো
        """
        if preferred_language != "auto":
            return preferred_language
        
        detected = self.detect(user_text)
        
        # Banglish → Bengali response
        if detected == "banglish":
            return "bn"
        
        # Mixed → check majority
        if detected == "mixed":
            _, confidence = self.detect_with_confidence(user_text)
            return "bn" if confidence > 50 else "en"
        
        return detected  # "bn" or "en"
    
    def get_greeting(self, language: str = "auto", formal: bool = False) -> str:
        """Language অনুযায়ী greeting return করো"""
        import random
        from datetime import datetime
        
        hour = datetime.now().hour
        
        greetings = {
            "bn": {
                "morning": ["সুপ্রভাত!", "শুভ সকাল!", "গুড মর্নিং!"],
                "afternoon": ["শুভ অপরাহ্ণ!", "গুড আফটারনুন!"],
                "evening": ["শুভ সন্ধ্যা!", "গুড ইভনিং!"],
                "night": ["শুভ রাত্রি!", "গুড নাইট!"],
                "general": ["নমস্কার!", "হ্যালো!", "আসসালামু আলাইকুম!"],
            },
            "en": {
                "morning": ["Good morning!", "Rise and shine!", "Morning!"],
                "afternoon": ["Good afternoon!", "Afternoon!"],
                "evening": ["Good evening!", "Evening!"],
                "night": ["Good night!", "Sweet dreams!"],
                "general": ["Hello!", "Hi there!", "Greetings!"],
            }
        }
        
        if language not in greetings:
            language = "en"
        
        # Time-based
        if 5 <= hour < 12:
            time_key = "morning"
        elif 12 <= hour < 17:
            time_key = "afternoon"
        elif 17 <= hour < 22:
            time_key = "evening"
        else:
            time_key = "night"
        
        greeting_list = greetings[language].get(time_key, greetings[language]["general"])
        return random.choice(greeting_list)


# ===== Singleton =====
language_detector = LanguageDetector()


# ===== HELPER FUNCTIONS (Quick use) =====

def detect_language(text: str) -> str:
    """Quick language detection"""
    return language_detector.detect(text)


def is_bengali(text: str) -> bool:
    """Check if text is primarily Bengali"""
    return language_detector.detect(text) in ["bn", "banglish"]


def is_english(text: str) -> bool:
    """Check if text is primarily English"""
    return language_detector.detect(text) == "en"


def get_lang(text: str) -> str:
    """Short form: returns 'bn' or 'en'"""
    result = language_detector.detect(text)
    if result == "banglish":
        return "bn"
    if result == "mixed":
        _, _ = language_detector.detect_with_confidence(text)
        return "bn" if _ > 50 else "en"
    return result


# ===== EEL EXPOSED FUNCTIONS =====
def setup_language_eel():
    """Frontend থেকে call করার জন্য eel functions"""
    try:
        import eel
        
        @eel.expose
        def detect_user_language(text):
            """User text এর language detect করো"""
            lang, confidence = language_detector.detect_with_confidence(text)
            return {"language": lang, "confidence": confidence}
        
        @eel.expose
        def get_text_info(text):
            """Text statistics"""
            return language_detector.get_text_stats(text)
        
        @eel.expose
        def convert_banglish(text):
            """Banglish → Bengali convert"""
            return language_detector.banglish_to_bengali(text)
        
        print("✅ Language eel functions registered")
        
    except ImportError:
        print("⚠️ Eel not available")
    except Exception as e:
        print(f"⚠️ Language eel setup error: {e}")