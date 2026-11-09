# backend/auth/lock_screen.py — Atlas 6.0 Lock Screen Controller

import time
import threading
from datetime import datetime
from typing import Optional

import config
from backend.auth.session_manager import session_manager
from backend.auth.auth_logger import auth_logger


class LockScreen:
    """System lock screen manager"""
    
    def __init__(self):
        self.is_locked = False
        self.locked_at = None
        self.idle_timeout = 300  # 5 minutes idle → auto lock
        self.last_activity = time.time()
        self.idle_thread = None
        self.idle_running = False
        
        print(f"🔒 Lock Screen initialized (idle timeout: {self.idle_timeout}s)")
    
    # ===== LOCK / UNLOCK =====
    
    def lock(self, reason: str = "manual") -> bool:
        """Lock the system"""
        if self.is_locked:
            return False
        
        self.is_locked = True
        self.locked_at = datetime.now()
        
        auth_logger.log_event("system_locked", success=True, details=reason)
        
        print(f"🔒 System locked: {reason}")
        return True
    
    def unlock(self, method: str = "pin") -> bool:
        """Unlock the system"""
        if not self.is_locked:
            return False
        
        self.is_locked = False
        self.locked_at = None
        self.last_activity = time.time()
        
        auth_logger.log_event("system_unlocked", method=method, success=True)
        
        print(f"🔓 System unlocked via {method}")
        return True
    
    def toggle(self) -> bool:
        """Toggle lock state"""
        if self.is_locked:
            return self.unlock()
        return self.lock()
    
    # ===== IDLE DETECTION =====
    
    def update_activity(self):
        """Update last activity time"""
        self.last_activity = time.time()
    
    def start_idle_monitor(self):
        """Start idle monitoring thread"""
        if self.idle_running:
            return
        
        self.idle_running = True
        
        def monitor():
            while self.idle_running:
                if not self.is_locked:
                    idle_time = time.time() - self.last_activity
                    if idle_time > self.idle_timeout:
                        self.lock("idle_timeout")
                time.sleep(10)
        
        self.idle_thread = threading.Thread(target=monitor, daemon=True)
        self.idle_thread.start()
        print("👁️ Idle monitor started")
    
    def stop_idle_monitor(self):
        """Stop idle monitoring"""
        self.idle_running = False
    
    # ===== EMERGENCY =====
    
    def emergency_lock(self) -> bool:
        """Emergency immediate lock"""
        session_manager.end_all_sessions()
        self.lock("emergency")
        auth_logger.log_event("emergency_lock", success=True)
        print("🚨 EMERGENCY LOCK ENGAGED!")
        return True
    
    # ===== STATUS =====
    
    def get_status(self) -> dict:
        """Current lock status"""
        idle_time = int(time.time() - self.last_activity) if not self.is_locked else 0
        
        return {
            "is_locked": self.is_locked,
            "locked_at": self.locked_at.isoformat() if self.locked_at else None,
            "locked_for": int((datetime.now() - self.locked_at).total_seconds()) if self.locked_at else 0,
            "idle_time": idle_time,
            "idle_timeout": self.idle_timeout,
            "auto_lock_in": max(0, self.idle_timeout - idle_time)
        }
    
    def set_idle_timeout(self, seconds: int):
        """Set idle timeout"""
        self.idle_timeout = max(30, seconds)
    
    def cleanup(self):
        self.stop_idle_monitor()


lock_screen = LockScreen()