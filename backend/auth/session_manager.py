# backend/auth/session_manager.py — Atlas 6.0 Session Manager (FIXED)

import time
import uuid
import threading
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple  # ✅ FIXED

import config
from backend.auth.auth_logger import auth_logger


class SessionManager:
    """Session management system"""
    
    def __init__(self):
        self.sessions = {}
        self.active_user = None
        self.session_timeout = config.SESSION_TIMEOUT
        self.cleanup_thread = None
        self.running = False
        
        self.start_cleanup()
        print(f"📋 Session Manager initialized (timeout: {self.session_timeout}s)")
    
    def create_session(self, user_id: str, method: str = "face") -> Optional[str]:
        token = f"atlas_{uuid.uuid4().hex}_{int(time.time())}"
        
        session = {
            "token": token,
            "user_id": user_id,
            "method": method,
            "created_at": datetime.now().isoformat(),
            "last_activity": time.time(),
            "expires_at": time.time() + self.session_timeout,
            "is_active": True,
            "ip": None,
            "device": None
        }
        
        self.sessions[token] = session
        self.active_user = user_id
        
        auth_logger.log_event("session_created", method=method, 
                             user_id=user_id, success=True)
        
        print(f"✅ Session created: {token[:16]}... for {user_id}")
        return token
    
    def validate(self, token: str) -> Tuple[bool, Optional[str]]:  # ✅ Tuple works now
        if not token or token not in self.sessions:
            return False, None
        
        session = self.sessions[token]
        
        if time.time() > session["expires_at"]:
            self._expire_session(token)
            return False, None
        
        if not session["is_active"]:
            return False, None
        
        session["last_activity"] = time.time()
        session["expires_at"] = time.time() + self.session_timeout
        
        return True, session["user_id"]
    
    def is_valid(self, token: str) -> bool:
        valid, _ = self.validate(token)
        return valid
    
    def get_user(self, token: str) -> Optional[str]:
        _, user_id = self.validate(token)
        return user_id
    
    def extend(self, token: str, minutes: int = 30) -> bool:
        if token in self.sessions:
            self.sessions[token]["expires_at"] = time.time() + (minutes * 60)
            self.sessions[token]["last_activity"] = time.time()
            return True
        return False
    
    def expire(self, token: str):
        self._expire_session(token)
    
    def _expire_session(self, token: str):
        if token in self.sessions:
            self.sessions[token]["is_active"] = False
            user_id = self.sessions[token]["user_id"]
            auth_logger.log_event("session_expired", user_id=user_id, 
                                 success=True, details="timeout")
            print(f"⏰ Session expired: {token[:16]}...")
    
    def end_session(self, token: str):
        if token in self.sessions:
            user_id = self.sessions[token]["user_id"]
            self.sessions[token]["is_active"] = False
            if self.active_user == user_id:
                self.active_user = None
            auth_logger.log_event("session_ended", user_id=user_id, 
                                 success=True, details="manual_logout")
            print(f"👋 Session ended: {user_id}")
    
    def end_all_sessions(self):
        for token in list(self.sessions.keys()):
            self.end_session(token)
    
    def get_session_info(self, token: str) -> Optional[Dict]:
        if token in self.sessions:
            session = self.sessions[token].copy()
            session["remaining"] = max(0, int(session["expires_at"] - time.time()))
            return session
        return None
    
    def get_active_sessions(self) -> List[Dict]:
        active = []
        for token, session in self.sessions.items():
            if session["is_active"] and time.time() < session["expires_at"]:
                active.append({
                    "token_preview": token[:16] + "...",
                    "user_id": session["user_id"],
                    "method": session["method"],
                    "created": session["created_at"],
                    "remaining": int(session["expires_at"] - time.time())
                })
        return active
    
    def get_session_count(self) -> int:
        return len(self.get_active_sessions())
    
    def start_cleanup(self):
        self.running = True
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
    
    def _cleanup_loop(self):
        while self.running:
            try:
                now = time.time()
                expired_tokens = []
                for token, session in self.sessions.items():
                    if now > session["expires_at"]:
                        expired_tokens.append(token)
                for token in expired_tokens:
                    self._expire_session(token)
                if expired_tokens:
                    print(f"🧹 Cleaned {len(expired_tokens)} expired sessions")
            except Exception as e:
                print(f"⚠️ Session cleanup error: {e}")
            time.sleep(60)
    
    def stop_cleanup(self):
        self.running = False
    
    def cleanup(self):
        self.stop_cleanup()
        self.end_all_sessions()


session_manager = SessionManager()