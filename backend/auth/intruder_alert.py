# backend/auth/intruder_alert.py — Atlas 6.0 Intruder Detection

import os
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

import config
from backend.auth.auth_logger import auth_logger

try:
    import cv2
    CV2_AVAILABLE = True
except:
    CV2_AVAILABLE = False


class IntruderAlert:
    """Unknown face detection + alert system"""
    
    def __init__(self):
        self.alerts_enabled = True
        self.alert_sound = True
        self.auto_lock = True
        self.capture_photo = True
        self.intruder_count = 0
        self.last_alert = None
        self.alert_cooldown = 30  # seconds between alerts
        self.monitoring = False
        self.monitor_thread = None
        
        # Intruder photos
        self.photos_dir = config.DATA_DIR / "intruder_photos"
        os.makedirs(self.photos_dir, exist_ok=True)
        
        print(f"🚨 Intruder Alert initialized")
        print(f"   Auto-lock: {self.auto_lock}")
        print(f"   Capture photo: {self.capture_photo}")
    
    # ===== ALERT =====
    
    def trigger_alert(self, image_data=None, reason: str = "Unknown face detected") -> Dict:
        """Trigger intruder alert"""
        import time
        
        # Check cooldown
        if self.last_alert:
            if time.time() - self.last_alert < self.alert_cooldown:
                return {"alerted": False, "reason": "Cooldown active"}
        
        self.last_alert = time.time()
        self.intruder_count += 1
        
        print(f"🚨 INTRUDER ALERT! {reason}")
        
        # Capture photo
        photo_path = None
        if self.capture_photo and image_data is not None:
            photo_path = self._save_intruder_photo(image_data)
        
        # Log
        auth_logger.log_intruder(
            image_path=photo_path,
            confidence=0,
            action_taken="alert",
            details=reason
        )
        
        # Auto lock
        if self.auto_lock:
            try:
                from backend.auth.lock_screen import lock_screen
                lock_screen.emergency_lock()
            except:
                pass
        
        # Notify UI
        try:
            import eel
            eel.intruderAlert(photo_path)()
        except:
            pass
        
        return {
            "alerted": True,
            "reason": reason,
            "photo": photo_path,
            "count": self.intruder_count,
            "timestamp": datetime.now().isoformat()
        }
    
    def _save_intruder_photo(self, image_data) -> Optional[str]:
        """Save intruder photo"""
        try:
            import cv2
            import numpy as np
            from PIL import Image
            
            if isinstance(image_data, str):
                import base64
                from io import BytesIO
                if ',' in image_data:
                    image_data = image_data.split(',')[1]
                img_bytes = base64.b64decode(image_data)
                img = Image.open(BytesIO(img_bytes))
                img_np = np.array(img)
            elif isinstance(image_data, np.ndarray):
                img_np = image_data
            else:
                return None
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"intruder_{timestamp}_{self.intruder_count}.jpg"
            filepath = str(self.photos_dir / filename)
            
            if len(img_np.shape) == 3:
                img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
            
            cv2.imwrite(filepath, img_np)
            return filepath
            
        except Exception as e:
            print(f"⚠️ Photo save error: {e}")
            return None
    
    # ===== MONITORING =====
    
    def start_monitoring(self, camera_index: int = 0, interval: int = 5):
        """Start camera monitoring for intruders"""
        if not CV2_AVAILABLE:
            print("❌ OpenCV not installed")
            return
        
        if self.monitoring:
            return
        
        self.monitoring = True
        
        def monitor_loop():
            from backend.auth.face_auth import face_auth_engine
            import cv2
            
            cap = cv2.VideoCapture(camera_index)
            print("📷 Intruder monitoring started")
            
            while self.monitoring:
                ret, frame = cap.read()
                if not ret:
                    time.sleep(1)
                    continue
                
                # Detect faces
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                faces = face_auth_engine.detect_faces(rgb)
                
                if faces:
                    # Try to recognize
                    for face in faces:
                        user_id, confidence, info = face_auth_engine.recognize(rgb)
                        
                        if user_id is None or confidence < 40:
                            # Unknown face!
                            self.trigger_alert(rgb, f"Unknown face (conf:{confidence:.1f})")
                            break
                
                time.sleep(interval)
            
            cap.release()
            print("📷 Intruder monitoring stopped")
        
        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring = False
    
    # ===== STATUS =====
    
    def get_status(self) -> Dict:
        return {
            "alerts_enabled": self.alerts_enabled,
            "auto_lock": self.auto_lock,
            "capture_photo": self.capture_photo,
            "intruder_count": self.intruder_count,
            "last_alert": datetime.fromtimestamp(self.last_alert).isoformat() if self.last_alert else None,
            "monitoring": self.monitoring
        }
    
    def get_intruder_photos(self, limit: int = 20) -> List[str]:
        """Get recent intruder photos"""
        photos = sorted(self.photos_dir.glob("*.jpg"), reverse=True)
        return [str(p) for p in photos[:limit]]
    
    def clear_photos(self):
        """Delete all intruder photos"""
        for p in self.photos_dir.glob("*.jpg"):
            p.unlink()
        print("🗑️ Intruder photos cleared")
    
    def cleanup(self):
        self.stop_monitoring()


intruder_alert = IntruderAlert()