# backend/core/voice_output.py — Atlas 6.0 Voice Output (TTS) - FULLY FIXED
# Edge TTS (free) — বাংলা + English text-to-speech

import os
import subprocess
import time
import tempfile
import threading
import asyncio
from typing import Optional
from pathlib import Path

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    print("⚠️ pip install edge-tts")
    EDGE_TTS_AVAILABLE = False

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    print("⚠️ pip install pygame (optional, audio playback এর জন্য)")
    PYGAME_AVAILABLE = False

import config


class VoiceOutput:
    """
    Atlas 6.0 Voice Output System - FULLY FIXED
    - Edge TTS (Microsoft - completely free, no API key)
    - বাংলা voice: Nabanita (bn-BD)
    - English voice: Jenny (en-US)
    - Auto language detection
    """
    
    def __init__(self):
        self.voice_bn = config.EDGE_VOICE_BN
        self.voice_en = config.EDGE_VOICE_EN

        # Extra voices so Atlas replies in the same language the user spoke.
        self.voices = {
            "bn": self.voice_bn,
            "en": self.voice_en,
            "hi": "hi-IN-SwaraNeural",
            "ur": "ur-PK-UzmaNeural",
            "ar": "ar-SA-ZariyahNeural",
            "ru": "ru-RU-SvetlanaNeural",
            "es": "es-ES-ElviraNeural",
            "fr": "fr-FR-DeniseNeural",
            "de": "de-DE-KatjaNeural",
            "zh": "zh-CN-XiaoxiaoNeural",
            "ja": "ja-JP-NanamiNeural",
            "ko": "ko-KR-SunHiNeural",
        }
        self.speed = config.TTS_SPEED
        self.pitch = config.TTS_PITCH
        
        self.is_speaking = False
        self.current_thread = None
        self._shutting_down = False
        
        # Cache
        self.audio_cache = {}
        self.cache_enabled = True
        
        self._init_audio()
        
        print(f"🔊 Voice Output initialized")
        print(f"   Engine: Edge TTS (Free)")
        print(f"   বাংলা: {self.voice_bn}")
        print(f"   English: {self.voice_en}")
        print(f"   Pygame audio: {'✅' if PYGAME_AVAILABLE else '❌'}")
    
    def _init_audio(self):
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.init()
                print("   Audio mixer ready")
            except Exception as e:
                print(f"   ⚠️ Pygame mixer init failed: {e}")
    
    def detect_language(self, text: str) -> str:
        """Response text-এর script দেখে TTS voice বেছে নেয়।"""
        if not text:
            return "en"

        counts = {key: 0 for key in self.voices}
        urdu_chars = set("ٹڈڑںھہےۓ")

        for char in text:
            cp = ord(char)
            if 0x0980 <= cp <= 0x09FF:
                counts["bn"] += 1
            elif 0x0900 <= cp <= 0x097F:
                counts["hi"] += 1
            elif 0x0600 <= cp <= 0x06FF:
                counts["ur" if char in urdu_chars else "ar"] += 1
            elif 0x0400 <= cp <= 0x04FF:
                counts["ru"] += 1
            elif 0x4E00 <= cp <= 0x9FFF:
                counts["zh"] += 1
            elif 0x3040 <= cp <= 0x30FF:
                counts["ja"] += 1
            elif 0xAC00 <= cp <= 0xD7AF:
                counts["ko"] += 1
            elif char.isalpha() and char.isascii():
                counts["en"] += 1

        total_letters = sum(counts.values())
        if total_letters == 0:
            return "en"

        # Bengali/English mixed text is common — keep Bengali voice when Bengali is significant.
        if counts["bn"] and counts["bn"] / total_letters > 0.3:
            return "bn"

        # Urdu and Arabic share the Arabic script; Urdu-specific letters are the giveaway.
        if counts["ur"]:
            return "ur"
        if counts["ar"]:
            return "ar"

        best = max(counts, key=counts.get)
        return best if counts[best] else "en"
    
    def get_voice(self, language: str) -> str:
        return self.voices.get(language, self.voice_en)
    
    def speak(self, text: str, language: str = "auto", block: bool = False) -> bool:
        if not text or not text.strip() or self._shutting_down:
            return False

        detected = self.detect_language(text)
        if not language or language == "auto" or language not in self.voices:
            language = detected
        elif detected == "bn" and language != "bn":
            # Caller hint ভুল হলে text content-ই ঠিক — Bengali text এ en voice দিলে
            # edge-tts "No audio was received" error দেয়
            language = "bn"
        
        cache_key = f"{text}_{language}"
        if self.cache_enabled and cache_key in self.audio_cache:
            print(f"📦 Using cached audio: {text[:50]}...")
            return self._play_audio(self.audio_cache[cache_key], block)
        
        if block:
            return self._speak_sync(text, language)
        else:
            self.current_thread = threading.Thread(
                target=self._speak_sync,
                args=(text, language),
                daemon=True
            )
            self.current_thread.start()
            return True
    
    def _speak_sync(self, text: str, language: str) -> bool:
        self.is_speaking = True
        
        try:
            voice = self.get_voice(language)
            print(f"🔊 Speaking [{language}]: {text[:80]}...")
            
            audio_file = self._generate_audio(text, voice)
            
            if audio_file:
                cache_key = f"{text}_{language}"
                if self.cache_enabled and len(self.audio_cache) < 100:
                    self.audio_cache[cache_key] = audio_file
                
                success = self._play_audio(audio_file, block=True)
                
                if cache_key not in self.audio_cache:
                    self._cleanup_file(audio_file)
                
                self.is_speaking = False
                return success
            else:
                print("❌ Audio generation failed")
                self.is_speaking = False
                return False
                
        except Exception as e:
            print(f"❌ Speech error: {e}")
            self.is_speaking = False
            return False
    
    # ===== FIXED: CORRECT ASYNC HANDLING =====
    def _generate_audio(self, text: str, voice: str) -> Optional[str]:
        """Edge TTS দিয়ে audio file generate করো - FULLY FIXED"""
        if self._shutting_down:
            return None
        if not EDGE_TTS_AVAILABLE:
            return self._generate_audio_fallback(text, voice)
        
        try:
            temp_path = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False).name
            
            async def _save():
                communicate = edge_tts.Communicate(
                    text=text,
                    voice=voice,
                    rate=self.speed,
                    pitch=self.pitch
                )
                await communicate.save(temp_path)
            
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(_save())
                return temp_path
            finally:
                loop.close()
            
        except Exception as e:
            print(f"❌ Edge TTS error: {e}")
            return self._generate_audio_fallback(text, voice)
    
    def _generate_audio_fallback(self, text: str, voice: str) -> Optional[str]:
        """Fallback: System TTS engine ব্যবহার করো"""
        try:
            import platform
            
            temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            temp_path = temp_file.name
            temp_file.close()
            
            system = platform.system()
            
            if system == "Windows":
                try:
                    import win32com.client
                    speaker = win32com.client.Dispatch("SAPI.SpVoice")
                    speaker.Speak(text)
                    return None
                except:
                    return None
                
            elif system == "Darwin":
                subprocess.run(["say", "-o", temp_path, text])
                return temp_path
                
            else:
                subprocess.run(["espeak", "-w", temp_path, text])
                return temp_path
                
        except Exception as e:
            print(f"❌ Fallback TTS error: {e}")
            return None
    
    def _play_audio(self, audio_file: str, block: bool = True) -> bool:
        if not audio_file or not os.path.exists(audio_file):
            return False
        
        if PYGAME_AVAILABLE:
            return self._play_with_pygame(audio_file, block)
        
        return self._play_with_system(audio_file, block)
    
    def _play_with_pygame(self, audio_file: str, block: bool = True) -> bool:
        try:
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()
            
            if block:
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
            
            return True
            
        except Exception as e:
            print(f"⚠️ Pygame playback error: {e}")
            return self._play_with_system(audio_file, block)
    
    def _play_with_system(self, audio_file: str, block: bool = True) -> bool:
        try:
            import platform
            system = platform.system()
            
            if system == "Windows":
                os.startfile(audio_file)
            elif system == "Darwin":
                subprocess.run(["afplay", audio_file])
            else:
                subprocess.run(["xdg-open", audio_file])
            
            if block:
                file_size = os.path.getsize(audio_file)
                duration = min(file_size / 16000, 10)
                time.sleep(duration)
            
            return True
            
        except Exception as e:
            print(f"❌ System playback error: {e}")
            return False
    
    def speak_greeting(self) -> bool:
        import random
        
        greetings_bn = [
            
            "হ্যালো! অ্যাটলাস রেডি। কীভাবে সাহায্য করতে পারি?",
            "আসসালামু আলাইকুম! অ্যাটলাস প্রস্তুত। বলুন কী দরকার?",
        ]
        
        greetings_en = [
            "Hello! Atlas is online. How can I help you today?",
            "Hi there! Atlas at your service. What can I do for you?",
            "Greetings! Atlas ready. What would you like me to do?",
        ]
        
        hour = time.localtime().tm_hour
        if 5 <= hour < 12:
            time_greeting = "Good morning!"
        elif 12 <= hour < 17:
            time_greeting = "Good afternoon!"
        elif 17 <= hour < 22:
            time_greeting = "Good evening!"
        else:
            time_greeting = "Hello!"
        
        if config.ATLAS_LANGUAGE == "bn":
            greeting = random.choice(greetings_bn)
        else:
            greeting = f"{time_greeting} " + random.choice(greetings_en)
        
        return self.speak(greeting)
    
    def stop_speaking(self):
        self.is_speaking = False
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.music.stop()
            except:
                pass
        print("🔇 Speech stopped")
    
    def set_speed(self, speed: str):
        self.speed = speed
        print(f"⚡ Speech speed: {speed}")
    
    def clear_cache(self):
        for file_path in self.audio_cache.values():
            self._cleanup_file(file_path)
        self.audio_cache.clear()
        print("🗑️ Audio cache cleared")
    
    def _cleanup_file(self, file_path: str):
        try:
            if file_path and os.path.exists(file_path):
                os.unlink(file_path)
        except:
            pass
    
    def cleanup(self):
        self._shutting_down = True
        self.stop_speaking()
        self.clear_cache()
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.quit()
            except:
                pass
        print("🔊 Voice output cleaned up")


voice_output = VoiceOutput()


def setup_voice_output_eel():
    try:
        import eel
        
        @eel.expose
        def speak_text(text, language="auto"):
            return voice_output.speak(text, language)
        
        @eel.expose
        def stop_speaking():
            voice_output.stop_speaking()
        
        @eel.expose
        def set_voice_speed(speed):
            voice_output.set_speed(speed)
        
        print("✅ Voice output eel functions registered")
        
    except ImportError:
        print("⚠️ Eel not available")
    except Exception as e:
        print(f"⚠️ Voice output eel setup error: {e}")