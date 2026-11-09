# config.py — Atlas 6.0 Configuration
# .env file থেকে সব keys load করে

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# ===== Load .env file =====
load_dotenv()

# ===== PROJECT PATHS =====
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
FRONTEND_DIR = BASE_DIR / "frontend"

# ============================================================
# 🔑 API KEYS (.env থেকে load)
# ============================================================

# Groq Keys (10টা)
GROQ_API_KEYS = []
for i in range(1, 11):
    key = os.getenv(f"GROQ_KEY_{i}")
    if key and "your_groq_key" not in key.lower() and "xxxxxxx" not in key.lower():
        GROQ_API_KEYS.append(key)

# Gemini Key — single string (backward compat)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ✅ FIX 1: GEMINI_API_KEYS list — ai_engine.py এটা expect করে
# Multiple keys চাইলে .env এ GEMINI_API_KEY_2, _3 add করো
GEMINI_API_KEYS = []
for i in range(1, 6):
    if i == 1:
        key = os.getenv("GEMINI_API_KEY", "")
    else:
        key = os.getenv(f"GEMINI_API_KEY_{i}", "")
    if key and "your" not in key.lower() and "xxxxxxx" not in key.lower():
        GEMINI_API_KEYS.append(key)

# Weather API
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")

# VirusTotal API
VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY", "")

# HaveIBeenPwned API
HIBP_API_KEY = os.getenv("HIBP_API_KEY", "")

# News API
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")

# ============================================================
# 🔐 AUTH SETTINGS
# ============================================================

AUTH_PIN = os.getenv("AUTH_PIN", "")
AUTH_MAX_ATTEMPTS = 3
AUTH_LOCKOUT_TIME = 600
SESSION_TIMEOUT = 1800
FACE_SCAN_TIMEOUT = 10

# ============================================================
# 🤖 AI MODEL SETTINGS
# ============================================================

# Primary AI provider: "gemini" (default) or "groq"
# Gemini slow/blocked hole: AI_PRIMARY=groq diye start koro
AI_PRIMARY = os.getenv("AI_PRIMARY", "gemini").strip().lower()

# Gemini (Primary AI) — Gemini আগে, Groq পরে
GEMINI_CHAT_MODEL = "gemini-3.8-flash"
GEMINI_FALLBACK_MODELS = ["gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-flash-latest"]
VISION_MODEL = "gemini-3.8-flash"

# Groq (Backup AI)
GROQ_MODEL = "openai/gpt-oss-120b"
GROQ_MODEL_FAST = "openai/gpt-oss-20b"
GROQ_MODEL_LONG = "openai/gpt-oss-120b"
GROQ_WHISPER_MODEL = "whisper-large-v3"

# ✅ FIX 2: DEFAULT_MODEL alias — ai_engine.py এর Groq fallback এটা use করে
DEFAULT_MODEL = GROQ_MODEL

# Rate limits
GROQ_RPM_LIMIT = 30
GROQ_RPD_LIMIT = 1000
GEMINI_RPM_LIMIT = 15
GEMINI_RPD_LIMIT = 1500
GROQ_KEY_STRATEGY = "round_robin"
GEMINI_KEY_STRATEGY = "round_robin"
AUTO_SWITCH_ON_LIMIT = True
KEY_COOLDOWN_TIME = 65

# ============================================================
# 🎤 VOICE SETTINGS
# ============================================================

TTS_ENGINE = "edge"
EDGE_VOICE_BN = "bn-BD-NabanitaNeural"
EDGE_VOICE_EN = "en-US-JennyNeural"
TTS_SPEED = "+0%"
TTS_PITCH = "+0Hz"
WAKE_WORD = "atlas"
LISTENING_TIMEOUT = 5
VOICE_LANGUAGE = "auto"

# ============================================================
# 🗄️ DATABASE PATHS
# ============================================================

DB_MEMORY = DATA_DIR / "atlas_memory.db"
DB_HABITS = DATA_DIR / "atlas_habits.db"
DB_NOTES = DATA_DIR / "atlas_notes.db"
DB_AUTH = DATA_DIR / "atlas_auth.db"
DB_ANALYTICS = DATA_DIR / "atlas_analytics.db"
DB_JOURNAL = DATA_DIR / "atlas_journal.db"

# ============================================================
# 📁 OTHER PATHS
# ============================================================

FACE_DATA_DIR = DATA_DIR / "user_profile" / "faces"
VOICE_DATA_DIR = DATA_DIR / "user_profile" / "voice"
DOWNLOADS_DIR = DATA_DIR / "downloads"
BACKUPS_DIR = DATA_DIR / "backups"
LOGS_DIR = BASE_DIR / "logs"

# Create directories
for dir_path in [FACE_DATA_DIR, VOICE_DATA_DIR, DOWNLOADS_DIR, BACKUPS_DIR, LOGS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# ============================================================
# 🎨 UI SETTINGS
# ============================================================

EEL_PORT = 8888
EEL_HOST = "localhost"
APP_NAME = "ATLAS 6.0"
WINDOW_SIZE = (1600, 900)
WINDOW_TITLE = "ATLAS 6.0 - AI Assistant"
THEME_COLOR = "#00ffff"

# ============================================================
# 👤 PERSONALITY
# ============================================================

ATLAS_NAME = "Atlas"
USER_NAME = os.getenv("USER_NAME", "Boss")
ATLAS_LANGUAGE = "auto"
DEFAULT_CITY = "Dhaka"
PRAYER_CITY = "Dhaka"
PRAYER_COUNTRY = "Bangladesh"

ATLAS_SYSTEM_PROMPT = f"""তুমি {ATLAS_NAME}, একটি advanced personal AI assistant।
তুমি {USER_NAME} এর personal assistant।
তুমি বাংলা এবং English দুটোতেই কথা বলতে পারো।
User যে language এ কথা বলবে, তুমি সেই language এ reply করবে।
তুমি helpful, friendly এবং intelligent।
তোমার responses concise এবং practical হবে।
"""

# ============================================================
# 🌐 EXTERNAL APIs
# ============================================================

PRAYER_API_URL = "https://api.aladhan.com/v1/timingsByCity"
DSE_API_URL = "https://www.dsebd.org/latest_share_price_scroll_l.php"
GMAIL_CREDENTIALS_FILE = DATA_DIR / "gmail_credentials.json"
GMAIL_TOKEN_FILE = DATA_DIR / "gmail_token.json"

# ============================================================
# ⚙️ SYSTEM
# ============================================================

DEBUG = os.getenv("DEBUG", "False").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
APP_VERSION = "6.0.0"
SHORT_TERM_MEMORY_SIZE = 20
LONG_TERM_MEMORY_ENABLED = True
FACE_SIMILARITY_THRESHOLD = 0.6

# ============================================================
# ✅ CHECK
# ============================================================

def check_config():
    """Configuration check করে report দিবে"""
    print("=" * 60)
    print(f"🔍 {APP_NAME} v{APP_VERSION} Configuration Check")
    print("=" * 60)
    print(f"   Groq keys loaded:   {len(GROQ_API_KEYS)}")
    print(f"   Gemini keys loaded: {len(GEMINI_API_KEYS)}")
    print(f"   Gemini model:       {GEMINI_CHAT_MODEL}")
    print(f"   Groq default:       {DEFAULT_MODEL}")
    print(f"   Weather API: {'✅' if WEATHER_API_KEY else '❌'}")
    print(f"   VirusTotal:  {'✅' if VIRUSTOTAL_API_KEY else '❌'}")
    print(f"   News API:    {'✅' if NEWS_API_KEY else '❌'}")
    print(f"   User: {USER_NAME}")
    print(f"   Debug: {DEBUG}")
    print("=" * 60)

# Auto-check on import
if __name__ != "__main__":
    check_config()
