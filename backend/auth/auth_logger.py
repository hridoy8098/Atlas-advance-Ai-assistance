# backend/auth/auth_logger.py — Atlas 6.0 Auth Logger
# সব auth attempts log করে রাখে

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

import config


class AuthLogger:
    """Authentication event logger"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(config.DB_AUTH)
        self.conn = None
        self._init_db()
    
    def _init_db(self):
        """Database initialize"""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = self.conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS auth_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    method TEXT,
                    user_id TEXT,
                    success INTEGER DEFAULT 0,
                    details TEXT,
                    ip_address TEXT,
                    device_info TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS intruder_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    image_path TEXT,
                    confidence REAL,
                    action_taken TEXT,
                    details TEXT
                )
            ''')
            
            self.conn.commit()
            
        except Exception as e:
            print(f"❌ Auth logger init error: {e}")
            self.conn = None
    
    # ===== LOGGING =====
    
    def log_event(self, event_type: str, method: str = None, user_id: str = None,
                  success: bool = False, details: str = None):
        """Auth event log করো"""
        if self.conn is None:
            return
        
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO auth_logs (timestamp, event_type, method, user_id, success, details)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                event_type,
                method,
                user_id,
                1 if success else 0,
                details
            ))
            self.conn.commit()
            
        except Exception as e:
            print(f"❌ Log error: {e}")
    
    def log_intruder(self, image_path: str = None, confidence: float = 0,
                     action_taken: str = "alert", details: str = None):
        """Intruder detection log"""
        if self.conn is None:
            return
        
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO intruder_logs (timestamp, image_path, confidence, action_taken, details)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                image_path,
                confidence,
                action_taken,
                details
            ))
            self.conn.commit()
            
        except Exception as e:
            print(f"❌ Intruder log error: {e}")
    
    # ===== RETRIEVAL =====
    
    def get_recent_logs(self, limit: int = 20) -> List[Dict]:
        """Recent auth logs"""
        if self.conn is None:
            return []
        
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM auth_logs ORDER BY timestamp DESC LIMIT ?', (limit,))
            return [dict(row) for row in cursor.fetchall()]
        except:
            return []
    
    def get_failed_attempts(self, minutes: int = 10) -> int:
        """Recent failed attempts count"""
        if self.conn is None:
            return 0
        
        try:
            from datetime import timedelta
            cutoff = (datetime.now() - timedelta(minutes=minutes)).isoformat()
            
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM auth_logs 
                WHERE success = 0 AND timestamp > ?
            ''', (cutoff,))
            return cursor.fetchone()[0]
        except:
            return 0
    
    def get_intruder_logs(self, limit: int = 10) -> List[Dict]:
        """Intruder logs"""
        if self.conn is None:
            return []
        
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM intruder_logs ORDER BY timestamp DESC LIMIT ?', (limit,))
            return [dict(row) for row in cursor.fetchall()]
        except:
            return []
    
    def get_auth_stats(self) -> Dict:
        """Auth statistics"""
        if self.conn is None:
            return {}
        
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM auth_logs")
            total = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM auth_logs WHERE success = 1")
            success = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM intruder_logs")
            intruders = cursor.fetchone()[0]
            
            today = datetime.now().strftime("%Y-%m-%d")
            cursor.execute("SELECT COUNT(*) FROM auth_logs WHERE timestamp LIKE ?", (f"{today}%",))
            today_total = cursor.fetchone()[0]
            
            return {
                "total_attempts": total,
                "successful": success,
                "failed": total - success,
                "intruders_detected": intruders,
                "today_attempts": today_total,
                "success_rate": f"{(success/max(total,1)*100):.1f}%"
            }
            
        except:
            return {}
    
    def clear_logs(self, older_than_days: int = 30):
        """পুরনো logs clear করো"""
        if self.conn is None:
            return
        
        try:
            from datetime import timedelta
            cutoff = (datetime.now() - timedelta(days=older_than_days)).isoformat()
            
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM auth_logs WHERE timestamp < ?', (cutoff,))
            deleted = cursor.rowcount
            self.conn.commit()
            
            print(f"🗑️ Cleared {deleted} old auth logs")
            
        except Exception as e:
            print(f"❌ Log cleanup error: {e}")
    
    def cleanup(self):
        if self.conn:
            self.conn.close()


# Singleton
auth_logger = AuthLogger()