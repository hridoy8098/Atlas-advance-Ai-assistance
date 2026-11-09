# backend/auth/guest_mode.py — Atlas 6.0 Guest Mode

from typing import Dict, List, Optional
from datetime import datetime

import config
from backend.auth.session_manager import session_manager
from backend.auth.auth_logger import auth_logger


class GuestMode:
    """Limited access guest mode"""
    
    def __init__(self):
        # Features allowed for guests
        self.allowed_features = [
            "chat",           # Basic chat
            "get_time",       # Time
            "get_date",       # Date
            "get_weather",    # Weather
            "tell_joke",      # Jokes
            "greeting",       # Greetings
            "open_website",   # Browse web
        ]
        
        # Blocked features for guests
        self.blocked_features = [
            "system_status",  # System info
            "open_app",       # App control
            "file_operations",# File access
            "screenshot",     # Screen capture
            "lock_system",    # System control
            "settings",       # Settings access
            "face_register",  # Auth changes
            "terminal",       # Terminal access
        ]
        
        self.active_guests = []
        self.max_guests = 3
        
        print(f"👤 Guest Mode initialized")
        print(f"   Allowed: {len(self.allowed_features)} features")
        print(f"   Blocked: {len(self.blocked_features)} features")
    
    # ===== GUEST SESSION =====
    
    def create_guest_session(self, guest_name: str = None) -> Optional[str]:
        """Create limited guest session"""
        if len(self.active_guests) >= self.max_guests:
            print(f"❌ Max guests reached ({self.max_guests})")
            return None
        
        guest_id = f"guest_{datetime.now().strftime('%H%M%S')}"
        guest_name = guest_name or f"Guest_{len(self.active_guests) + 1}"
        
        token = session_manager.create_session(guest_id, "guest")
        
        guest_info = {
            "guest_id": guest_id,
            "name": guest_name,
            "token": token,
            "joined_at": datetime.now(),
            "active": True
        }
        
        self.active_guests.append(guest_info)
        auth_logger.log_event("guest_joined", method="guest", user_id=guest_id, success=True)
        
        print(f"👤 Guest joined: {guest_name} ({guest_id})")
        return token
    
    def end_guest_session(self, guest_id: str):
        """End guest session"""
        for guest in self.active_guests:
            if guest["guest_id"] == guest_id:
                guest["active"] = False
                session_manager.end_session(guest["token"])
                auth_logger.log_event("guest_left", user_id=guest_id, success=True)
                print(f"👋 Guest left: {guest['name']}")
                break
        
        # Clean inactive
        self.active_guests = [g for g in self.active_guests if g["active"]]
    
    def end_all_guests(self):
        """End all guest sessions"""
        for guest in self.active_guests:
            session_manager.end_session(guest["token"])
        
        self.active_guests = []
        print("👋 All guests removed")
    
    # ===== PERMISSION CHECK =====
    
    def is_allowed(self, feature: str) -> bool:
        """Check if feature is allowed for guests"""
        return feature in self.allowed_features
    
    def is_blocked(self, feature: str) -> bool:
        """Check if feature is blocked"""
        return feature in self.blocked_features
    
    def can_access(self, feature: str) -> bool:
        """Check access permission"""
        if feature in self.blocked_features:
            return False
        return True
    
    def filter_response(self, response: str) -> str:
        """Filter sensitive info from response"""
        # Remove system info from guest responses
        sensitive_patterns = [
            "CPU:", "RAM:", "Disk:", "Battery:", "IP:", "MAC:",
            "password", "token", "session"
        ]
        
        for pattern in sensitive_patterns:
            if pattern.lower() in response.lower():
                return "This information is not available in guest mode."
        
        return response
    
    # ===== STATUS =====
    
    def get_active_guests(self) -> List[Dict]:
        return [{"name": g["name"], "joined": g["joined_at"].isoformat()} 
                for g in self.active_guests if g["active"]]
    
    def get_guest_count(self) -> int:
        return len([g for g in self.active_guests if g["active"]])
    
    def is_guest(self, user_id: str) -> bool:
        return user_id and user_id.startswith("guest_")
    
    def cleanup(self):
        self.end_all_guests()


guest_mode = GuestMode()