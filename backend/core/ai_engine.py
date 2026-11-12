# backend/core/ai_engine.py — Atlas 6.0 AI Engine
# Gemini (Primary AI) + Groq multi-key (Backup AI) + Whisper STT
# Priority: আগে Gemini, rate-limit/error হলে Groq

import time
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple

try:
    from groq import Groq, RateLimitError, APIError
except ImportError:
    print("⚠️ pip install groq")
    Groq = None
    RateLimitError = Exception
    APIError = Exception

# Gemini — নতুন google-genai SDK (পুরনো google-generativeai এখন deprecated)
try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    genai = None
    GENAI_AVAILABLE = False
    print("⚠️ pip install google-genai (Gemini features এর জন্য)")

try:
    from google.genai import types as genai_types
except ImportError:
    genai_types = None

import config


class MultiKeyManager:
    """Multiple API keys manage করে - rotate, rate limit track, auto-switch"""
    
    def __init__(self, keys: List[str], rpm_limit: int, rpd_limit: int, strategy: str = "round_robin"):
        self.keys = keys
        self.rpm_limit = rpm_limit
        self.rpd_limit = rpd_limit
        self.strategy = strategy
        self.current_index = 0
        self.key_stats = {}
        
        for i, key in enumerate(keys):
            if key and "তোমার" not in key and "your" not in key.lower():
                self.key_stats[i] = {
                    "key": key,
                    "rpm_used": 0,
                    "rpd_used": 0,
                    "total_requests": 0,
                    "rate_limited": False,
                    "limited_until": None,
                    "last_used": None,
                    "last_reset_rpm": time.time(),
                    "last_reset_rpd": datetime.now().date()
                }
    
    @property
    def active_keys_count(self):
        return len([k for k in self.key_stats.values() if not k["rate_limited"]])
    
    def get_next_key(self) -> Tuple[int, str]:
        """পরবর্তী available key return করে"""
        if not self.key_stats:
            return None, None
        
        self._reset_counters_if_needed()
        
        if self.strategy == "round_robin":
            return self._round_robin()
        elif self.strategy == "least_used":
            return self._least_used()
        elif self.strategy == "random":
            return self._random()
        else:
            return self._round_robin()
    
    def _round_robin(self) -> Tuple[int, str]:
        attempts = 0
        while attempts < len(self.key_stats):
            idx = self.current_index % len(self.key_stats)
            self.current_index += 1
            
            if idx in self.key_stats:
                stat = self.key_stats[idx]
                if not stat["rate_limited"] and stat["rpm_used"] < self.rpm_limit:
                    return idx, stat["key"]
            
            attempts += 1
        
        return self._wait_for_available_key()
    
    def _least_used(self) -> Tuple[int, str]:
        available = [(i, s) for i, s in self.key_stats.items() 
                     if not s["rate_limited"] and s["rpm_used"] < self.rpm_limit]
        if not available:
            return self._wait_for_available_key()
        
        available.sort(key=lambda x: x[1]["total_requests"])
        idx, stat = available[0]
        return idx, stat["key"]
    
    def _random(self) -> Tuple[int, str]:
        import random
        available = [(i, s) for i, s in self.key_stats.items() 
                     if not s["rate_limited"] and s["rpm_used"] < self.rpm_limit]
        if not available:
            return self._wait_for_available_key()
        
        idx, stat = random.choice(available)
        return idx, stat["key"]
    
    def _wait_for_available_key(self) -> Tuple[int, str]:
        now = time.time()
        for i, stat in self.key_stats.items():
            if stat["rate_limited"] and stat["limited_until"]:
                if now >= stat["limited_until"]:
                    stat["rate_limited"] = False
                    stat["limited_until"] = None
                    stat["rpm_used"] = 0
                    return i, stat["key"]
        
        return None, None
    
    def mark_used(self, key_index: int):
        if key_index in self.key_stats:
            stat = self.key_stats[key_index]
            stat["rpm_used"] += 1
            stat["rpd_used"] += 1
            stat["total_requests"] += 1
            stat["last_used"] = time.time()
    
    def mark_rate_limited(self, key_index: int, cooldown_seconds: int = 65):
        if key_index in self.key_stats:
            stat = self.key_stats[key_index]
            stat["rate_limited"] = True
            stat["limited_until"] = time.time() + cooldown_seconds
            print(f"⏳ Key {key_index} rate limited for {cooldown_seconds}s")
    
    def _reset_counters_if_needed(self):
        now = time.time()
        today = datetime.now().date()
        
        for stat in self.key_stats.values():
            if now - stat["last_reset_rpm"] >= 60:
                stat["rpm_used"] = 0
                stat["last_reset_rpm"] = now
            
            if today != stat["last_reset_rpd"]:
                stat["rpd_used"] = 0
                stat["last_reset_rpd"] = today
            
            if stat["rate_limited"] and stat["limited_until"]:
                if now >= stat["limited_until"]:
                    stat["rate_limited"] = False
                    stat["limited_until"] = None
                    stat["rpm_used"] = 0
    
    def get_status(self) -> List[Dict]:
        self._reset_counters_if_needed()
        status_list = []
        for i, stat in self.key_stats.items():
            status_list.append({
                "index": i,
                "rpm_used": stat["rpm_used"],
                "rpm_left": self.rpm_limit - stat["rpm_used"],
                "day_used": stat["rpd_used"],
                "limited": stat["rate_limited"],
                "total": stat["total_requests"]
            })
        return status_list


class AtlasAI:
    """Atlas 6.0 AI Engine - Main class (Gemini primary, Groq backup)"""
    
    def __init__(self):
        # ===== Gemini setup (PRIMARY AI) =====
        # config.GEMINI_API_KEYS (list) — একাধিক key support
        self.gemini_key_manager = None
        self.gemini_clients = {}
        
        if GENAI_AVAILABLE:
            gemini_keys_list = getattr(config, "GEMINI_API_KEYS", [])
            
            # fallback: single key থাকলেও কাজ করবে
            if not gemini_keys_list:
                single_key = getattr(config, "GEMINI_API_KEY", "")
                if single_key and "your" not in single_key.lower() and "xxxxxxx" not in single_key.lower():
                    gemini_keys_list = [single_key]
            
            valid_keys = [k for k in gemini_keys_list if k and "তোমার" not in k and "your" not in k.lower()]
            
            if valid_keys:
                self.gemini_key_manager = MultiKeyManager(
                    keys=valid_keys,
                    rpm_limit=config.GEMINI_RPM_LIMIT,
                    rpd_limit=config.GEMINI_RPD_LIMIT,
                    strategy=config.GEMINI_KEY_STRATEGY
                )
                for i, key_info in self.gemini_key_manager.key_stats.items():
                    try:
                        # নতুন SDK: প্রতি key-র জন্য আলাদা client
                        self.gemini_clients[i] = genai.Client(
                            api_key=key_info["key"],
                            http_options={"timeout": 60000}  # 60s
                        )
                    except Exception as e:
                        print(f"❌ Gemini client {i} init failed: {e}")
            else:
                print("⚠️ No valid Gemini keys found - Gemini disabled")
        else:
            print("ℹ️ google-genai not installed - Gemini disabled")
            print("   Install: pip install google-genai")
        
        # ===== Groq setup (BACKUP AI) =====
        self.groq_key_manager = None
        self.groq_clients = {}
        
        if Groq:
            valid_keys = [k for k in config.GROQ_API_KEYS if k and "তোমার" not in k]
            if valid_keys:
                self.groq_key_manager = MultiKeyManager(
                    keys=valid_keys,
                    rpm_limit=config.GROQ_RPM_LIMIT,
                    rpd_limit=config.GROQ_RPD_LIMIT,
                    strategy=config.GROQ_KEY_STRATEGY
                )
                for i, key in self.groq_key_manager.key_stats.items():
                    try:
                        self.groq_clients[i] = Groq(api_key=key["key"])
                    except Exception as e:
                        print(f"❌ Groq client {i} init failed: {e}")
        
        # Conversation history
        self.conversation_history = []
        self.max_history = config.SHORT_TERM_MEMORY_SIZE
        
        # Stats
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        
        # Print status
        gemini_count = self.gemini_key_manager.active_keys_count if self.gemini_key_manager else 0
        groq_count = self.groq_key_manager.active_keys_count if self.groq_key_manager else 0
        print(f"✅ Atlas AI Engine initialized")
        print(f"   Gemini (primary): {gemini_count} keys")
        print(f"   Groq (backup):    {groq_count} keys")
    
    # ============================================================
    # 🤖 CHAT — Gemini আগে, fail করলে Groq
    # ============================================================
    
    def chat(self, message: str, model: str = None, system_prompt: str = None, use_history: bool = True) -> str:
        """Main chat function — Gemini (primary) → Groq (backup) → canned fallback"""
        gemini_model = None
        groq_only = False
        
        if model:
            m = str(model).lower()
            if m.startswith("gemini"):
                gemini_model = model          # নির্দিষ্ট Gemini model চাওয়া হয়েছে
            else:
                groq_only = True              # নির্দিষ্ট Groq model চাওয়া হয়েছে

        # config.AI_PRIMARY=groq: use the fast provider first, but keep Gemini
        # as a safety net. Skipping Gemini entirely turned a Groq outage into a
        # canned reply.
        prefer_groq = bool(
            not gemini_model
            and not groq_only
            and getattr(config, "AI_PRIMARY", "gemini") == "groq"
        )

        if prefer_groq:
            if self.groq_key_manager is not None:
                response = self._groq_chat(message, model, system_prompt, use_history)
                if response:
                    return response
            if self.gemini_key_manager is not None:
                response = self._gemini_chat(message, system_prompt, use_history, gemini_model)
                if response:
                    return response
            return self._fallback_response(message)

        # 1) Gemini first (user priority)
        if not groq_only and self.gemini_key_manager is not None:
            response = self._gemini_chat(message, system_prompt, use_history, gemini_model)
            if response:
                return response
        
        # 2) Groq backup
        if self.groq_key_manager is not None:
            response = self._groq_chat(message, model, system_prompt, use_history)
            if response:
                return response
        
        # 3) কিছুই কাজ না করলে
        return self._fallback_response(message)
    
    def _gemini_models(self, preferred: str = None) -> List[str]:
        """চেষ্টা করার মতো Gemini model গুলো ordered list আকারে"""
        candidates = []
        if preferred:
            candidates.append(preferred)
        candidates.append(getattr(config, "GEMINI_CHAT_MODEL", "gemini-3.8-flash"))
        for m in getattr(config, "GEMINI_FALLBACK_MODELS", []):
            candidates.append(m)
        
        seen, ordered = set(), []
        for m in candidates:
            if m and m not in seen:
                seen.add(m)
                ordered.append(m)
        return ordered
    
    def _remember(self, message: str, response: str):
        """Conversation history-তে successful exchange save করে"""
        self.conversation_history.append({"role": "user", "content": message})
        self.conversation_history.append({"role": "assistant", "content": response})
        
        if len(self.conversation_history) > self.max_history * 2:
            self.conversation_history = self.conversation_history[-self.max_history * 2:]
    
    def _gemini_chat(self, message: str, system_prompt: str = None,
                     use_history: bool = True, preferred_model: str = None) -> Optional[str]:
        """Gemini দিয়ে text generation — success হলে text, নাহলে None (Groq ধরবে)"""
        if self.gemini_key_manager is None:
            return None
        
        key_index, api_key = self.gemini_key_manager.get_next_key()
        
        if key_index is None:
            print("⚠️ No available Gemini keys")
            return None
        
        client = self.gemini_clients.get(key_index)
        if client is None:
            try:
                client = genai.Client(api_key=api_key, http_options={"timeout": 60000})
                self.gemini_clients[key_index] = client
            except Exception as e:
                print(f"❌ Gemini client init failed: {e}")
                return None
        
        # History → Gemini contents format
        contents = []
        if use_history:
            for entry in self.conversation_history[-self.max_history:]:
                role = "model" if entry["role"] == "assistant" else "user"
                contents.append({"role": role, "parts": [{"text": entry["content"]}]})
        contents.append({"role": "user", "parts": [{"text": message}]})
        
        gen_config = {"temperature": 0.7, "max_output_tokens": 1024}
        if system_prompt:
            gen_config["system_instruction"] = system_prompt
        
        for model_name in self._gemini_models(preferred_model):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=gen_config
                )
                
                try:
                    text = response.text
                except Exception:
                    text = None
                
                if text:
                    self.gemini_key_manager.mark_used(key_index)
                    self.total_requests += 1
                    self.successful_requests += 1
                    if use_history:
                        self._remember(message, text)
                    print(f"💎 Gemini ({model_name}) → reply")
                    return text
                
                print(f"⚠️ Gemini ({model_name}) empty response")
            
            except Exception as e:
                error_msg = str(e)
                low = error_msg.lower()
                print(f"❌ Gemini error ({model_name}): {error_msg[:200]}")
                
                # Rate limit / quota → key mark করে Groq backup-কে ছেড়ে দিই
                if "429" in error_msg or "resource_exhausted" in low or "quota" in low or "rate limit" in low:
                    self.gemini_key_manager.mark_rate_limited(key_index, config.KEY_COOLDOWN_TIME)
                    self.failed_requests += 1
                    return None
                
                # Model টা নেই/সাপোর্ট করে না → পরের model try করি
                if "404" in error_msg or "not found" in low or "not supported" in low or "invalid model" in low:
                    continue
                
                self.failed_requests += 1
                return None
        
        return None
    
    def _groq_chat(self, message: str, model: str = None,
                   system_prompt: str = None, use_history: bool = True) -> Optional[str]:
        """Groq দিয়ে text generation (backup) — success হলে text, নাহলে None"""
        if self.groq_key_manager is None:
            return None
        
        default_model = getattr(config, "DEFAULT_MODEL", None) or getattr(config, "GROQ_MODEL", "llama3-70b-8192")
        model = model or default_model
        
        for attempt in range(3):
            key_index, api_key = self.groq_key_manager.get_next_key()
            
            if key_index is None:
                print("❌ No available Groq keys")
                return None
            
            client = self.groq_clients.get(key_index)
            if not client:
                try:
                    client = Groq(api_key=api_key)
                    self.groq_clients[key_index] = client
                except Exception as e:
                    print(f"❌ Groq client init failed: {e}")
                    return None
            
            try:
                messages = []
                
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                
                if use_history:
                    for entry in self.conversation_history[-self.max_history:]:
                        messages.append(entry)
                
                messages.append({"role": "user", "content": message})
                
                completion = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1024,
                    top_p=1,
                    stream=False
                )
                
                response = completion.choices[0].message.content
                
                self.groq_key_manager.mark_used(key_index)
                self.total_requests += 1
                self.successful_requests += 1
                
                if use_history:
                    self._remember(message, response)
                
                print(f"⚡ Groq ({model}) → reply")
                return response
            
            except RateLimitError:
                print(f"⚠️ Groq key {key_index} rate limited")
                self.groq_key_manager.mark_rate_limited(key_index, config.KEY_COOLDOWN_TIME)
                continue  # পরের key দিয়ে আরেকবার try
            
            except APIError as e:
                print(f"❌ Groq API error: {e}")
                self.failed_requests += 1
                return None
            
            except Exception as e:
                print(f"❌ Groq unexpected error: {e}")
                self.failed_requests += 1
                return None
        
        self.failed_requests += 1
        return None
    
    def chat_vision(self, image_data, prompt: str = "What do you see in this image?") -> str:
        """Gemini দিয়ে image analysis"""
        if not GENAI_AVAILABLE or self.gemini_key_manager is None:
            return "Vision features not available. Install: pip install google-genai"
        
        key_index, api_key = self.gemini_key_manager.get_next_key()
        
        if key_index is None:
            return "All Gemini keys are rate limited. Try again later."
        
        try:
            client = self.gemini_clients.get(key_index)
            if client is None:
                client = genai.Client(api_key=api_key, http_options={"timeout": 60000})
                self.gemini_clients[key_index] = client
            
            # bytes দিলে সেটাকে SDK-র Part বানিয়ে দিই
            if isinstance(image_data, (bytes, bytearray)) and genai_types is not None:
                contents = [prompt, genai_types.Part.from_bytes(data=bytes(image_data), mime_type="image/jpeg")]
            else:
                contents = [prompt, image_data]
            
            response = None
            last_error = None
            for model_name in self._gemini_models(getattr(config, "VISION_MODEL", None)):
                try:
                    response = client.models.generate_content(model=model_name, contents=contents)
                    break
                except Exception as e:
                    last_error = e
                    low = str(e).lower()
                    print(f"❌ Gemini vision error ({model_name}): {str(e)[:200]}")
                    if "404" in str(e) or "not found" in low or "not supported" in low:
                        continue
                    break
            
            if response is None:
                raise last_error or Exception("vision request failed")
            
            self.gemini_key_manager.mark_used(key_index)
            self.total_requests += 1
            self.successful_requests += 1
            
            try:
                return response.text
            except Exception:
                return "No description available."
        
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Gemini vision failed: {error_msg[:200]}")
            
            if "429" in error_msg or "quota" in error_msg.lower() or "resource_exhausted" in error_msg.lower():
                self.gemini_key_manager.mark_rate_limited(key_index, config.KEY_COOLDOWN_TIME)
                # অন্য key available থাকলে আরেকবার try
                if self.gemini_key_manager.active_keys_count > 0:
                    return self.chat_vision(image_data, prompt)
                return "All Gemini keys exhausted. Try again later."
            
            self.failed_requests += 1
            return f"Vision analysis failed: {error_msg}"
    
    def transcribe_audio(self, audio_data: bytes) -> Optional[str]:
        """Groq Whisper দিয়ে STT"""
        if self.groq_key_manager is None:
            return None
        
        key_index, api_key = self.groq_key_manager.get_next_key()
        
        if key_index is None:
            return None
        
        try:
            client = self.groq_clients.get(key_index)
            if not client:
                return None
            
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_data)
                temp_path = f.name
            
            with open(temp_path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    model=config.GROQ_WHISPER_MODEL,
                    file=audio_file,
                    response_format="text"
                )
            
            import os
            os.unlink(temp_path)
            
            self.groq_key_manager.mark_used(key_index)
            return transcription
            
        except Exception as e:
            print(f"❌ Transcription error: {e}")
            return None
    
    def _fallback_response(self, message: str) -> str:
        """Fallback যখন API unavailable"""
        import random
        responses = [
            "I'm processing your request... 🤔",
            "Let me think about that...",
            "Interesting! Let me analyze...",
            "One moment please...",
        ]
        return random.choice(responses)
    
    def get_key_status(self) -> Dict:
        """Frontend এর জন্য key status"""
        return {
            "groq": self.groq_key_manager.get_status() if self.groq_key_manager else [],
            "gemini": self.gemini_key_manager.get_status() if self.gemini_key_manager else [],
            "total_requests": self.total_requests,
            "success_rate": f"{(self.successful_requests / max(1, self.total_requests) * 100):.1f}%"
        }
    
    def clear_history(self):
        self.conversation_history = []
        print("🗑️ Conversation history cleared")
    
    def get_history(self) -> List[Dict]:
        return self.conversation_history


# ===== Singleton =====
ai_engine = AtlasAI()
