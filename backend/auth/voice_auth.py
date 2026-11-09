# backend/auth/voice_auth.py — Atlas 6.0 Voice Authentication

import os
import json
import hashlib
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

import config
from backend.auth.auth_logger import auth_logger


class VoiceAuth:
    """Voice passphrase authentication"""
    
    def __init__(self):
        self.voice_dir = config.VOICE_DATA_DIR
        self.passphrase_hash = None
        self.max_attempts = config.AUTH_MAX_ATTEMPTS
        self.lockout_duration = config.AUTH_LOCKOUT_TIME
        self.failed_attempts = 0
        self.locked_until = 0
        
        # Default passphrases
        self.passphrases = [
            "atlas unlock my system",
            "atlas open sesame",
            "hello atlas",
        ]
        
        os.makedirs(self.voice_dir, exist_ok=True)
        self._load_passphrase()
        
        print(f"🎤 Voice Auth initialized")
    
    def _load_passphrase(self):
        """Load saved passphrase"""
        filepath = self.voice_dir / "passphrase.json"
        if filepath.exists():
            try:
                with open(filepath) as f:
                    data = json.load(f)
                    self.passphrase_hash = data.get('hash')
            except:
                pass
    
    def _save_passphrase(self, passphrase: str):
        """Save passphrase hash"""
        self.passphrase_hash = hashlib.sha256(passphrase.encode()).hexdigest()
        
        filepath = self.voice_dir / "passphrase.json"
        with open(filepath, 'w') as f:
            json.dump({'hash': self.passphrase_hash, 'updated': datetime.now().isoformat()}, f)
    
    # ===== SETUP =====
    
    def set_passphrase(self, passphrase: str) -> bool:
        """Set voice passphrase"""
        if len(passphrase) < 5:
            return False
        
        self._save_passphrase(passphrase.lower())
        print("✅ Voice passphrase set")
        return True
    
    # ===== VERIFICATION =====
    
    def verify(self, audio_data) -> Tuple[bool, str, str]:
        """
        Verify voice input
        Returns: (success, message, user_id)
        """
        import time
        
        if self._is_locked():
            remaining = int(self.locked_until - time.time())
            return False, f"🔒 Locked for {remaining}s", ""
        
        # For now, simple passphrase match
        # Future: actual voice fingerprint matching
        text = self._transcribe(audio_data)
        
        if not text:
            return False, "Could not understand audio", ""
        
        # Check passphrases
        text_lower = text.lower().strip()
        
        for phrase in self.passphrases:
            if phrase in text_lower:
                self._reset_attempts()
                auth_logger.log_event("login", method="voice", user_id="main_user", success=True)
                return True, "✅ Voice recognized", "main_user"
        
        # Check custom passphrase
        if self.passphrase_hash:
            text_hash = hashlib.sha256(text_lower.encode()).hexdigest()
            if text_hash == self.passphrase_hash:
                self._reset_attempts()
                return True, "✅ Voice verified", "main_user"
        
        self._record_failure()
        return False, "❌ Voice not recognized", ""
    
    def _transcribe(self, audio_data) -> Optional[str]:
        """Transcribe audio to text"""
        try:
            from backend.core.voice_input import voice_input
            return voice_input.transcribe(audio_data)
        except:
            pass
        
        # Basic: save audio and recognize
        try:
            import speech_recognition as sr
            
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_data)
                temp_path = f.name
            
            recognizer = sr.Recognizer()
            with sr.AudioFile(temp_path) as source:
                audio = recognizer.record(source)
            
            os.unlink(temp_path)
            
            try:
                return recognizer.recognize_google(audio)
            except:
                return None
        except:
            return None
    
    # ===== HELPERS =====
    
    def _is_locked(self) -> bool:
        import time
        if self.locked_until > 0 and time.time() < self.locked_until:
            return True
        if self.locked_until > 0 and time.time() >= self.locked_until:
            self._reset_attempts()
        return False
    
    def _record_failure(self):
        self.failed_attempts += 1
        if self.failed_attempts >= self.max_attempts:
            import time
            self.locked_until = time.time() + self.lockout_duration
    
    def _reset_attempts(self):
        self.failed_attempts = 0
        self.locked_until = 0
    
    def is_configured(self) -> bool:
        return self.passphrase_hash is not None


voice_auth = VoiceAuth()