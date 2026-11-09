# backend/auth/face_register.py — Atlas 6.0 Face Registration System
# Multi-angle face registration with OpenCV fallback

import os
import time
import base64
from io import BytesIO
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

import numpy as np
from PIL import Image

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("⚠️ pip install opencv-python")

# face_recognition optional
try:
    import face_recognition
    FACE_REC_AVAILABLE = True
except ImportError:
    FACE_REC_AVAILABLE = False
    print("⚠️ face_recognition not installed - using OpenCV fallback")

import config
from backend.auth.face_auth import face_auth_engine
from backend.auth.anti_spoofing import anti_spoofing
from backend.auth.auth_logger import auth_logger


class FaceRegistration:
    """
    Atlas 6.0 Face Registration System
    - Guided multi-angle capture
    - Quality checking
    - Anti-spoofing during registration
    """
    
    def __init__(self):
        self.angles = [
            {"name": "front", "instruction": "Look straight at the camera 😐", "icon": "bi-camera"},
            {"name": "left", "instruction": "Turn your head slightly left 👈", "icon": "bi-arrow-left"},
            {"name": "right", "instruction": "Turn your head slightly right 👉", "icon": "bi-arrow-right"},
            {"name": "up", "instruction": "Tilt your head slightly up 👆", "icon": "bi-arrow-up"},
            {"name": "down", "instruction": "Tilt your head slightly down 👇", "icon": "bi-arrow-down"},
        ]
        
        self.current_angle_index = 0
        self.captured_images = []
        self.captured_encodings = []
        self.is_registration_active = False
        self.user_id = None
        self.user_name = None
        
        # Quality thresholds
        self.min_face_size = 80
        self.min_brightness = 50
        self.max_brightness = 240
        self.min_sharpness = 30
        
        print(f"📸 Face Registration initialized ({len(self.angles)} angles)")
    
    # ===== START REGISTRATION =====
    
    def start_registration(self, user_id: str, user_name: str) -> Dict:
        """Registration process start"""
        self.user_id = user_id
        self.user_name = user_name
        self.current_angle_index = 0
        self.captured_images = []
        self.captured_encodings = []
        self.is_registration_active = True
        
        auth_logger.log_event("registration_started", method="face",
                             user_id=user_id, success=True)
        
        print(f"📸 Registration started: {user_name}")
        
        return {
            "status": "started",
            "user_id": user_id,
            "user_name": user_name,
            "total_angles": len(self.angles),
            "current_angle": 0,
            "current_angle_name": self.angles[0]["name"],
            "instruction": self.angles[0]["instruction"],
            "icon": self.angles[0]["icon"],
            "progress": 0
        }
    
    # ===== CAPTURE ANGLE =====
    
    def capture_angle(self, image_data) -> Dict:
        """Current angle capture"""
        if not self.is_registration_active:
            return {"status": "error", "message": "Registration not active"}
        
        if self.current_angle_index >= len(self.angles):
            return {"status": "error", "message": "All angles captured"}
        
        current_angle = self.angles[self.current_angle_index]
        
        # Load image
        img = self._load_image(image_data)
        if img is None:
            return {"status": "retry", "message": "Cannot load image"}
        
        # Quality check
        quality = self._check_quality(img)
        if not quality["passed"]:
            return {"status": "retry", "message": quality["message"], "issues": quality.get("issues", [])}
        
        # Anti-spoofing check (optional)
        if FACE_REC_AVAILABLE:
            try:
                is_alive, spoof_msg, _ = anti_spoofing.check_liveness(img)
                if not is_alive:
                    return {"status": "retry", "message": f"Liveness failed: {spoof_msg}"}
            except:
                pass  # Skip if anti-spoofing fails
        
        # Encode face
        encoding = face_auth_engine.encode_face(img)
        if encoding is None:
            return {"status": "retry", "message": "No face detected. Make sure your face is clearly visible."}
        
        # Store
        self.captured_images.append(img)
        self.captured_encodings.append(encoding)
        self.current_angle_index += 1
        
        print(f"   ✅ Captured: {current_angle['name']}")
        
        progress = int((self.current_angle_index / len(self.angles)) * 100)
        
        # Check if done
        if self.current_angle_index >= len(self.angles):
            return self._complete_registration()
        
        next_angle = self.angles[self.current_angle_index]
        
        return {
            "status": "success",
            "message": f"✅ {current_angle['name']} captured!",
            "angle_captured": current_angle['name'],
            "current_angle": self.current_angle_index,
            "current_angle_name": next_angle["name"],
            "instruction": next_angle["instruction"],
            "icon": next_angle["icon"],
            "progress": progress,
            "total_angles": len(self.angles)
        }
    
    # ===== SKIP ANGLE =====
    
    def skip_angle(self) -> Dict:
        """Skip current angle"""
        if not self.is_registration_active:
            return {"status": "error", "message": "Registration not active"}
        
        skipped = self.angles[self.current_angle_index]["name"]
        self.current_angle_index += 1
        
        print(f"   ⏭️ Skipped: {skipped}")
        
        progress = int((self.current_angle_index / len(self.angles)) * 100)
        
        if self.current_angle_index >= len(self.angles):
            return self._complete_registration()
        
        next_angle = self.angles[self.current_angle_index]
        
        return {
            "status": "skipped",
            "message": f"Skipped {skipped}",
            "current_angle": self.current_angle_index,
            "current_angle_name": next_angle["name"],
            "instruction": next_angle["instruction"],
            "icon": next_angle["icon"],
            "progress": progress
        }
    
    # ===== RETRY ANGLE =====
    
    def retry_angle(self) -> Dict:
        """Retry same angle"""
        if not self.is_registration_active:
            return {"status": "error", "message": "Registration not active"}
        
        current = self.angles[self.current_angle_index]
        
        return {
            "status": "retry_ready",
            "message": "Ready for retry",
            "current_angle": self.current_angle_index,
            "current_angle_name": current["name"],
            "instruction": current["instruction"],
            "icon": current["icon"],
            "progress": int((self.current_angle_index / len(self.angles)) * 100)
        }
    
    # ===== COMPLETE =====
    
    def _complete_registration(self) -> Dict:
        """Complete registration"""
        self.is_registration_active = False
        
        if len(self.captured_encodings) < 2:
            return {
                "status": "failed",
                "message": "Need at least 2 angles with detected faces",
                "captured_count": len(self.captured_encodings)
            }
        
        success = face_auth_engine.register_face(
            user_id=self.user_id,
            name=self.user_name,
            encodings=self.captured_encodings
        )
        
        if success:
            auth_logger.log_event("registration_completed", method="face",
                                 user_id=self.user_id, success=True,
                                 details=f"{len(self.captured_encodings)} angles")
            
            print(f"🎉 Registration complete: {self.user_name}")
            
            return {
                "status": "completed",
                "message": f"🎉 Face registered! {len(self.captured_encodings)} angles captured.",
                "user_id": self.user_id,
                "user_name": self.user_name,
                "angles_captured": len(self.captured_encodings),
                "total_angles": len(self.angles),
                "progress": 100
            }
        
        return {"status": "failed", "message": "Failed to save face data"}
    
    # ===== CANCEL =====
    
    def cancel_registration(self) -> Dict:
        """Cancel registration"""
        self.is_registration_active = False
        self.captured_images = []
        self.captured_encodings = []
        self.current_angle_index = 0
        
        print("❌ Registration cancelled")
        return {"status": "cancelled", "message": "Registration cancelled"}
    
    # ===== QUALITY CHECK =====
    
    def _check_quality(self, img) -> Dict:
        """Image quality check"""
        issues = []
        
        if not CV2_AVAILABLE:
            return {"passed": True, "message": "OK (CV2 not available)", "issues": []}
        
        try:
            # Convert to numpy
            if isinstance(img, Image.Image):
                img_np = np.array(img)
            else:
                img_np = img
            
            # Convert to grayscale
            if len(img_np.shape) == 3:
                gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_np
            
            # 1. Brightness check
            brightness = np.mean(gray)
            if brightness < self.min_brightness:
                issues.append("Too dark - need more light 💡")
            elif brightness > self.max_brightness:
                issues.append("Too bright - reduce light ☀️")
            
            # 2. Sharpness check
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            sharpness = np.var(laplacian)
            if sharpness < self.min_sharpness:
                issues.append("Image blurry - hold still 📷")
            
            # 3. Face detection
            cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            faces = cascade.detectMultiScale(gray, 1.1, 5)
            
            if len(faces) == 0:
                issues.append("No face detected 👤")
            else:
                (x, y, w, h) = faces[0]
                
                if w < self.min_face_size or h < self.min_face_size:
                    issues.append("Face too small - move closer 🔍")
                
                # Check centering
                h_img, w_img = gray.shape[:2]
                face_cx = x + w//2
                face_cy = y + h//2
                offset_x = abs(face_cx - w_img/2) / w_img
                offset_y = abs(face_cy - h_img/2) / h_img
                
                if offset_x > 0.3 or offset_y > 0.3:
                    issues.append("Center your face 📍")
            
            passed = len(issues) == 0
            
            return {
                "passed": passed,
                "message": "✅ Quality OK" if passed else f"❌ {issues[0]}",
                "issues": issues,
                "metrics": {
                    "brightness": round(float(brightness), 1),
                    "sharpness": round(float(sharpness), 1),
                    "faces_found": len(faces)
                }
            }
            
        except Exception as e:
            print(f"⚠️ Quality check error: {e}")
            return {"passed": True, "message": "Quality check skipped", "issues": []}
    
    # ===== STATUS =====
    
    def get_registration_status(self) -> Dict:
        """Current registration status"""
        if not self.is_registration_active:
            return {"status": "inactive"}
        
        return {
            "status": "active",
            "user_id": self.user_id,
            "user_name": self.user_name,
            "current_angle": self.current_angle_index,
            "total_angles": len(self.angles),
            "angles_captured": len(self.captured_encodings),
            "progress": int((self.current_angle_index / len(self.angles)) * 100)
        }
    
    # ===== HELPERS =====
    
    def _load_image(self, image_data):
        """Load image from various formats"""
        if image_data is None:
            return None
        
        try:
            if isinstance(image_data, Image.Image):
                return image_data
            if isinstance(image_data, np.ndarray):
                return Image.fromarray(image_data)
            if isinstance(image_data, str):
                if ',' in image_data:
                    image_data = image_data.split(',')[1]
                img_bytes = base64.b64decode(image_data)
                return Image.open(BytesIO(img_bytes))
            if isinstance(image_data, bytes):
                return Image.open(BytesIO(image_data))
            return None
        except Exception as e:
            print(f"❌ Image load error: {e}")
            return None
    
    def cleanup(self):
        self.cancel_registration()


# ===== Singleton =====
face_registration = FaceRegistration()


# ===== EEL FUNCTIONS =====
def setup_face_register_eel():
    """Register eel functions for frontend"""
    try:
        import eel
        
        @eel.expose
        def start_face_registration(user_id, user_name):
            return face_registration.start_registration(user_id, user_name)
        
        @eel.expose
        def capture_registration_angle(image_data):
            return face_registration.capture_angle(image_data)
        
        @eel.expose
        def skip_registration_angle():
            return face_registration.skip_angle()
        
        @eel.expose
        def retry_registration_angle():
            return face_registration.retry_angle()
        
        @eel.expose
        def cancel_registration():
            return face_registration.cancel_registration()
        
        @eel.expose
        def get_registration_status():
            return face_registration.get_registration_status()
        
        print("✅ Face registration eel functions registered")
        
    except ImportError:
        print("⚠️ Eel not available")
    except Exception as e:
        print(f"⚠️ Face registration eel error: {e}")