# backend/auth/authenticator.py — Atlas 6.0 Main Auth Controller
# All auth methods orchestrate করে

from typing import Optional, Dict, Any, Tuple
from datetime import datetime

import config
from backend.auth.auth_logger import auth_logger
from backend.auth.pin_auth import pin_auth
from backend.auth.session_manager import session_manager
try:
    from backend.auth.face_auth import face_auth_engine
    FACE_AUTH_AVAILABLE = True
except Exception:
    face_auth_engine = None
    FACE_AUTH_AVAILABLE = False

try:
    from backend.auth.voice_auth import voice_auth
    VOICE_AUTH_AVAILABLE = True
except:
    VOICE_AUTH_AVAILABLE = False

try:
    from backend.auth.anti_spoofing import anti_spoofing
    ANTI_SPOOF_AVAILABLE = True
except:
    ANTI_SPOOF_AVAILABLE = False


class Authenticator:
    """Main authentication orchestrator"""
    
    def __init__(self):
        self.max_attempts = config.AUTH_MAX_ATTEMPTS
        self.lockout_duration = config.AUTH_LOCKOUT_TIME
        self.attempts = {}
        
        print("🔐 Authenticator initialized")
        print(f"   Methods: PIN, Face, Voice, Guest")
    
    # ===== MAIN AUTH =====
    
    def authenticate(self, method: str, data: Any) -> Tuple[bool, str, Optional[str]]:
        """
        Main authenticate function
        Returns: (success, message, session_token)
        """
        method = method.lower()
        
        if method == 'pin':
            return self._auth_pin(data)
        elif method == 'face':
            return self._auth_face(data)
        elif method == 'voice':
            return self._auth_voice(data)
        elif method == 'guest':
            return self._auth_guest()
        else:
            return False, "Unknown auth method", None
    
    # ===== PIN AUTH =====
    
    def _auth_pin(self, pin: str) -> Tuple[bool, str, Optional[str]]:
        success, msg = pin_auth.verify(pin)
        
        if success:
            token = session_manager.create_session("main_user", "pin")
            auth_logger.log_event("login", method="pin", user_id="main_user", success=True)
            return True, "✅ PIN verified", token
        
        auth_logger.log_event("login_failed", method="pin", success=False, details=msg)
        return False, msg, None
    
    # ===== FACE AUTH =====
    
    def _auth_face(self, image_data) -> Tuple[bool, str, Optional[str]]:
        if not FACE_AUTH_AVAILABLE or face_auth_engine is None:
            return False, "Face auth not available", None

        # Anti-spoofing check
        if ANTI_SPOOF_AVAILABLE:
            is_alive, spoof_msg, _ = anti_spoofing.check_liveness(image_data)
            if not is_alive:
                auth_logger.log_event("spoof_detected", method="face", success=False, details=spoof_msg)
                return False, f"🚫 {spoof_msg}", None
        
        # Recognize face
        user_id, confidence, info = face_auth_engine.recognize(image_data)
        
        if user_id and confidence > 50:
            token = session_manager.create_session(user_id, "face")
            auth_logger.log_event("login", method="face", user_id=user_id, success=True,
                                 details=f"confidence:{confidence:.1f}%")
            return True, f"✅ Welcome {info.get('name', user_id)}! ({confidence:.1f}%)", token
        
        auth_logger.log_event("login_failed", method="face", success=False,
                             details=f"confidence:{confidence:.1f}")
        return False, f"❌ Face not recognized ({confidence:.1f}%)", None
    
    # ===== VOICE AUTH =====
    
    def _auth_voice(self, audio_data) -> Tuple[bool, str, Optional[str]]:
        if not VOICE_AUTH_AVAILABLE:
            return False, "Voice auth not configured", None
        
        success, msg, user_id = voice_auth.verify(audio_data)
        
        if success:
            token = session_manager.create_session(user_id, "voice")
            auth_logger.log_event("login", method="voice", user_id=user_id, success=True)
            return True, msg, token
        
        auth_logger.log_event("login_failed", method="voice", success=False, details=msg)
        return False, msg, None
    
    # ===== GUEST MODE =====
    
    def _auth_guest(self) -> Tuple[bool, str, Optional[str]]:
        token = session_manager.create_session("guest", "guest")
        auth_logger.log_event("login", method="guest", user_id="guest", success=True)
        return True, "👤 Guest mode - limited access", token
    
    # ===== ATTEMPT TRACKING =====
    
    def check_attempts(self, method: str) -> bool:
        """Check if method is locked"""
        if method not in self.attempts:
            return True
        
        data = self.attempts[method]
        if data['count'] >= self.max_attempts:
            if (datetime.now() - data['last_attempt']).seconds < self.lockout_duration:
                return False
            # Reset after lockout
            data['count'] = 0
        
        return True
    
    def record_attempt(self, method: str):
        """Record failed attempt"""
        if method not in self.attempts:
            self.attempts[method] = {'count': 0, 'last_attempt': datetime.now()}
        
        self.attempts[method]['count'] += 1
        self.attempts[method]['last_attempt'] = datetime.now()
    
    def reset_attempts(self, method: str = None):
        """Reset attempts"""
        if method:
            self.attempts.pop(method, None)
        else:
            self.attempts.clear()
    
    # ===== UTILITY =====
    
    def logout(self, token: str):
        """User logout"""
        session_manager.end_session(token)
        auth_logger.log_event("logout", success=True)
    
    def get_active_user(self) -> Optional[str]:
        return session_manager.active_user
    
    def get_status(self) -> Dict:
        face_count = 0
        if FACE_AUTH_AVAILABLE and face_auth_engine is not None:
            try:
                face_count = face_auth_engine.get_face_count()
            except Exception:
                pass
        return {
            "active_sessions": session_manager.get_session_count(),
            "pin_configured": pin_auth.is_configured(),
            "face_configured": face_count > 0,
            "voice_configured": VOICE_AUTH_AVAILABLE,
            "locked_methods": [m for m, d in self.attempts.items() 
                             if d['count'] >= self.max_attempts]
        }


# Singleton
authenticator = Authenticator()