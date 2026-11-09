# backend/core/voice_input.py — Atlas 6.0 Voice Input (STT)
# Groq Whisper ব্যবহার করে বাংলা + English speech-to-text

import os
import time
import wave
import tempfile
import threading
from typing import Optional, Callable
from datetime import datetime

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    print("⚠️ pip install pyaudio")
    print("   Windows: pip install pipwin && pipwin install pyaudio")
    pyaudio = None
    PYAUDIO_AVAILABLE = False

try:
    import speech_recognition as sr
except ImportError:
    print("⚠️ pip install SpeechRecognition")
    sr = None

import config
from backend.core.ai_engine import ai_engine


class VoiceInput:
    """
    Atlas 6.0 Voice Input System
    - Groq Whisper STT (বাংলা + English)
    - Wake word detection
    - Real-time recording
    - Auto language detection
    """
    
    def __init__(self):
        self.audio = None
        self.stream = None
        self.is_listening = False
        self.is_recording = False
        self.recognizer = None
        
        # ✅ FIX: pyaudio None হলে এখানেই crash হতো (pyaudio.paInt16)
        # এখন PYAUDIO_AVAILABLE দিয়ে safely set করা হচ্ছে
        if PYAUDIO_AVAILABLE:
            self.format = pyaudio.paInt16
        else:
            self.format = None

        self.channels = 1
        self.rate = 16000  # 16kHz for Whisper
        self.chunk = 1024
        self.record_seconds = 5
        
        # Wake word
        self.wake_word = config.WAKE_WORD.lower()
        self.wake_word_detected = False
        
        # Callbacks
        self.on_speech_detected = None
        self.on_transcription = None
        self.on_wake_word = None
        
        # Initialize
        self._init_audio()
        self._init_recognizer()
        
        print(f"🎤 Voice Input initialized")
        print(f"   PyAudio: {'✅' if PYAUDIO_AVAILABLE else '❌ (recording disabled)'}")
        print(f"   Wake word: '{self.wake_word}'")
        print(f"   Rate: {self.rate}Hz, Channels: {self.channels}")
    
    def _init_audio(self):
        """PyAudio initialize করো"""
        if not PYAUDIO_AVAILABLE:
            print("❌ PyAudio not installed — microphone recording disabled")
            self.audio = None
            return
        
        try:
            self.audio = pyaudio.PyAudio()
            print("✅ Audio device ready")
            
            # List available input devices
            info = self.audio.get_host_api_info_by_index(0)
            num_devices = info.get('deviceCount')
            for i in range(num_devices):
                device_info = self.audio.get_device_info_by_host_api_device_index(0, i)
                if device_info.get('maxInputChannels') > 0:
                    print(f"   🎙️ Input device {i}: {device_info.get('name')}")
                    
        except Exception as e:
            print(f"❌ Audio init failed: {e}")
            self.audio = None
    
    def _init_recognizer(self):
        """SpeechRecognition initialize করো (backup STT)"""
        if sr:
            self.recognizer = sr.Recognizer()
            self.recognizer.energy_threshold = 4000
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.pause_threshold = 0.8
    
    # ===== RECORDING =====
    
    def record_audio(self, duration: int = None, silent: bool = False, cancel_event=None) -> Optional[bytes]:
        """
        Audio record করে bytes return করে
        duration: seconds (None = default record_seconds)
        cancel_event: threading.Event set করলে recording sathe sathe bondho hoy
        """
        # ✅ FIX: audio বা format None হলে gracefully return করে
        if self.audio is None:
            if not silent:
                print("❌ Audio not available — PyAudio install করো")
            return None
        
        if self.format is None:
            if not silent:
                print("❌ Audio format not set — PyAudio properly installed নেই")
            return None

        if cancel_event is not None and cancel_event.is_set():
            return None
        
        duration = duration or self.record_seconds
        
        if not silent:
            print(f"🎙️ Recording for {duration}s...")
        
        try:
            self.stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk
            )
            
            frames = []
            self.is_recording = True
            
            for _ in range(0, int(self.rate / self.chunk * duration)):
                if not self.is_recording:
                    break
                if cancel_event is not None and cancel_event.is_set():
                    break
                try:
                    data = self.stream.read(self.chunk, exception_on_overflow=False)
                    frames.append(data)
                except Exception:
                    break
            
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
            self.is_recording = False
            
            # Convert to WAV bytes
            audio_bytes = self._frames_to_wav(frames)
            
            if not silent:
                print(f"✅ Recorded: {len(audio_bytes)} bytes")
            
            return audio_bytes
            
        except Exception as e:
            print(f"❌ Recording error: {e}")
            self.is_recording = False
            # Stream cleanup
            if self.stream:
                try:
                    self.stream.stop_stream()
                    self.stream.close()
                    self.stream = None
                except Exception:
                    pass
            return None
    
    def _frames_to_wav(self, frames: list) -> bytes:
        """Audio frames কে WAV bytes এ convert করো"""
        if not frames:
            return b""
        
        # ✅ FIX: audio বা format None হলে raw bytes return করে crash এড়ায়
        if self.audio is None or self.format is None:
            return b''.join(frames)
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
        
        try:
            wf = wave.open(temp_path, 'wb')
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.audio.get_sample_size(self.format))
            wf.setframerate(self.rate)
            wf.writeframes(b''.join(frames))
            wf.close()
            
            with open(temp_path, 'rb') as f:
                audio_bytes = f.read()
            
            os.unlink(temp_path)
            return audio_bytes
            
        except Exception as e:
            print(f"❌ WAV conversion error: {e}")
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            return b''.join(frames)
    
    # ===== TRANSCRIPTION =====
    
    def transcribe(self, audio_bytes: bytes, language: str = None) -> Optional[str]:
        """
        Audio bytes কে text এ convert করো
        language: "bn", "en", None (auto)
        """
        if audio_bytes is None or len(audio_bytes) < 100:
            return None

        print(f"📝 Transcribing {len(audio_bytes)} bytes...")
        
        # Try Groq Whisper first
        text = ai_engine.transcribe_audio(audio_bytes)

        if text:
            print(f"   Result: {text[:100]}...")
            return text.strip()

        # Fallback: Google STT (free, no API key needed)
        text = self._google_stt_fallback(audio_bytes, language)

        if text:
            print(f"   Fallback result: {text[:100]}...")
            return text.strip()

        print("❌ Transcription failed")
        return None

    def _google_stt_fallback(self, audio_bytes: bytes, language: str = None) -> Optional[str]:
        """Google Speech Recognition fallback (free tier)"""
        if sr is None or self.recognizer is None:
            return None
        
        temp_path = None
        audio = None
        
        try:
            # Save as temp WAV
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_bytes)
                temp_path = f.name
            
            with sr.AudioFile(temp_path) as source:
                audio = self.recognizer.record(source)
            
            os.unlink(temp_path)
            temp_path = None
            
            # Recognize — default Bengali
            lang = language or "bn-BD"
            text = self.recognizer.recognize_google(audio, language=lang)
            return text
            
        except sr.UnknownValueError:
            # Try English if Bengali fails
            if audio and lang != "en-US":
                try:
                    text = self.recognizer.recognize_google(audio, language="en-US")
                    return text
                except Exception:
                    pass
            return None
            
        except sr.RequestError as e:
            print(f"⚠️ Google STT error: {e}")
            return None
            
        except Exception as e:
            print(f"❌ Fallback STT error: {e}")
            return None
        
        finally:
            # ✅ FIX: temp file cleanup নিশ্চিত করা
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
    
    # ===== LISTENING MODES =====
    
    def listen_once(self, duration: int = None, language: str = None) -> Optional[str]:
        """একবার listen করে text return করো"""
        audio_bytes = self.record_audio(duration=duration)
        if audio_bytes:
            return self.transcribe(audio_bytes, language)
        return None
    
    def listen_with_wake_word(self, timeout: int = 30) -> Optional[str]:
        """
        Wake word এর জন্য wait করে, তারপর command listen করে
        "atlas" বললেই activate হবে
        """
        if self.audio is None:
            print("❌ Audio not available — wake word detection disabled")
            return None

        print(f"🎤 Waiting for wake word: '{self.wake_word}'...")
        print("   (Press Ctrl+C to cancel)")
        
        start_time = time.time()
        self.wake_word_detected = False
        
        while time.time() - start_time < timeout:
            # Record short chunk
            audio_bytes = self.record_audio(duration=2, silent=True)
            if audio_bytes is None:
                continue
            
            # Check for wake word
            text = self.transcribe(audio_bytes, "en")
            
            if text and self.wake_word in text.lower():
                self.wake_word_detected = True
                print(f"⚡ Wake word detected!")
                
                if self.on_wake_word:
                    self.on_wake_word()
                
                # Listen for actual command
                print("🎙️ Listening for command...")
                command = self.listen_once(duration=5)
                
                if command:
                    # Remove wake word if included
                    command = command.lower().replace(self.wake_word, "").strip()
                
                return command
        
        print("⏰ Wake word timeout")
        return None
    
    def start_continuous_listening(self, callback: Callable = None):
        """
        Continuous listening mode (background thread)
        প্রতিবার wake word detect করলে callback call করে
        """
        if self.audio is None:
            print("❌ Audio not available — continuous listening disabled")
            return

        if self.is_listening:
            print("⚠️ Already listening")
            return
        
        self.is_listening = True
        
        def listen_loop():
            print("🎤 Continuous listening started...")
            print(f"   Wake word: '{self.wake_word}'")
            
            while self.is_listening:
                try:
                    command = self.listen_with_wake_word(timeout=60)
                    
                    if command and callback:
                        callback(command)
                    elif command:
                        print(f"📝 Heard: {command}")
                    else:
                        # Mic error/None return hole tight loop e log spam hoy — backoff
                        time.sleep(0.5)
                        
                except Exception as e:
                    print(f"⚠️ Listen error: {e}")
                    time.sleep(1)
            
            print("🎤 Listening stopped")
        
        thread = threading.Thread(target=listen_loop, daemon=True)
        thread.start()
    
    def stop_listening(self):
        """Continuous listening বন্ধ করো"""
        self.is_listening = False
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception:
                pass
            self.stream = None
        print("🎤 Stopped listening")
    
    def listen_from_microphone_with_ui_feedback(self) -> Optional[str]:
        """
        UI feedback সহ listen করে (frontend এ mic visualizer দেখাবে)
        """
        print("🎙️ Listening (mic animation দেখবে)...")
        
        self._set_mic_state("listening")
        audio_bytes = self.record_audio(duration=5)
        self._set_mic_state("processing")
        
        if audio_bytes:
            text = self.transcribe(audio_bytes)
            self._set_mic_state("idle")
            return text
        
        self._set_mic_state("idle")
        return None
    
    def _set_mic_state(self, state: str):
        """Eel mic state set করো — eel না থাকলে silently skip"""
        try:
            import eel
            eel.setMicState(state)()
        except Exception:
            pass
    
    # ===== LANGUAGE DETECTION =====
    
    def detect_language(self, text: str) -> str:
        """Text বাংলা নাকি English detect করো"""
        if not text:
            return "en"
        
        bengali_chars = sum(1 for c in text if '\u0980' <= c <= '\u09FF')
        total_chars = len(text.replace(" ", ""))
        
        if total_chars == 0:
            return "en"
        
        bengali_ratio = bengali_chars / total_chars
        
        if bengali_ratio > 0.3:
            return "bn"
        return "en"
    
    # ===== CLEANUP =====
    
    def cleanup(self):
        """Audio resources clean করো"""
        self.stop_listening()
        if self.audio:
            try:
                self.audio.terminate()
            except Exception:
                pass
        print("🎤 Voice input cleaned up")
    
    def __del__(self):
        try:
            self.cleanup()
        except Exception:
            pass


# ===== Singleton =====
voice_input = VoiceInput()


# ===== EEL EXPOSED FUNCTIONS =====
def setup_voice_eel():
    """Frontend থেকে call করার জন্য eel functions"""
    try:
        import eel
        
        @eel.expose
        def start_listening():
            """UI button থেকে voice listening start"""
            text = voice_input.listen_from_microphone_with_ui_feedback()
            if text:
                return text
            return None
        
        @eel.expose
        def start_wake_word_listening():
            """Wake word listening start"""
            voice_input.start_continuous_listening(
                callback=lambda cmd: eel.receiverText(cmd) if cmd else None
            )
        
        @eel.expose
        def stop_listening():
            """Listening বন্ধ করো"""
            voice_input.stop_listening()
        
        print("✅ Voice eel functions registered")
        
    except ImportError:
        print("⚠️ Eel not available - voice UI features disabled")
    except Exception as e:
        print(f"⚠️ Voice eel setup error: {e}")
