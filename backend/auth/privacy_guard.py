# backend/auth/privacy_guard.py — Atlas 6.0 Privacy Guard

import time
import threading
from datetime import datetime
from typing import Optional, Dict

import config
from backend.auth.auth_logger import auth_logger


class PrivacyGuard:
    """Privacy protection system"""
    
    def __init__(self):
        self.privacy_mode = False
        self.fake_screen = False
        self.watermark_enabled = False
        self.auto_privacy = False
        self.privacy_triggers = []
        self.last_check = time.time()
        
        print(f"🛡️ Privacy Guard initialized")
    
    # ===== PRIVACY MODE =====
    
    def enable_privacy(self, reason: str = "manual") -> bool:
        """Enable privacy mode (blur screen)"""
        if self.privacy_mode:
            return False
        
        self.privacy_mode = True
        auth_logger.log_event("privacy_on", success=True, details=reason)
        
        # Trigger UI blur
        try:
            import eel
            eel.showNotification("Privacy", "Screen content hidden 🔒", "warning")()
        except:
            pass
        
        print(f"🛡️ Privacy mode ON: {reason}")
        return True
    
    def disable_privacy(self) -> bool:
        """Disable privacy mode"""
        if not self.privacy_mode:
            return False
        
        self.privacy_mode = False
        auth_logger.log_event("privacy_off", success=True)
        
        try:
            import eel
            eel.showNotification("Privacy", "Screen content visible", "info")()
        except:
            pass
        
        print("🛡️ Privacy mode OFF")
        return True
    
    def toggle_privacy(self) -> bool:
        """Toggle privacy mode"""
        if self.privacy_mode:
            return self.disable_privacy()
        return self.enable_privacy()
    
    # ===== FAKE SCREEN =====
    
    def show_fake_screen(self, screen_type: str = "desktop") -> bool:
        """Show fake screen (boss mode)"""
        if self.fake_screen:
            return False
        
        self.fake_screen = True
        auth_logger.log_event("fake_screen_on", details=screen_type)
        print(f"🎭 Fake screen ON: {screen_type}")
        return True
    
    def hide_fake_screen(self) -> bool:
        """Hide fake screen"""
        if not self.fake_screen:
            return False
        
        self.fake_screen = False
        print("🎭 Fake screen OFF")
        return True
    
    # ===== AUTO PRIVACY =====
    
    def enable_auto_privacy(self):
        """Enable auto privacy on window blur"""
        self.auto_privacy = True
        print("🛡️ Auto-privacy enabled")
    
    def disable_auto_privacy(self):
        self.auto_privacy = False
        print("🛡️ Auto-privacy disabled")
    
    def on_window_blur(self):
        """Called when window loses focus"""
        if self.auto_privacy:
            self.enable_privacy("window_blur")
    
    def on_window_focus(self):
        """Called when window gains focus"""
        if self.auto_privacy and self.privacy_mode:
            self.disable_privacy()
    
    # ===== STATUS =====
    
    def get_status(self) -> Dict:
        return {
            "privacy_mode": self.privacy_mode,
            "fake_screen": self.fake_screen,
            "auto_privacy": self.auto_privacy,
            "watermark": self.watermark_enabled
        }
    
    def cleanup(self):
        if self.privacy_mode:
            self.disable_privacy()
        if self.fake_screen:
            self.hide_fake_screen()


privacy_guard = PrivacyGuard()