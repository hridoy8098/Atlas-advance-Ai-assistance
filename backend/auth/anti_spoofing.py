# backend/auth/anti_spoofing.py — Atlas 6.0 Anti-Spoofing / Liveness Detection
# Blink detection, depth analysis, texture analysis — fake photo/video detect করে

import time
import base64
from io import BytesIO
from typing import Optional, Dict, Any, Tuple, List

import numpy as np
from PIL import Image

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    print("⚠️ pip install opencv-python")
    CV2_AVAILABLE = False

try:
    import face_recognition
    FACE_REC_AVAILABLE = True
except ImportError:
    FACE_REC_AVAILABLE = False

import config


class AntiSpoofing:
    """
    Atlas 6.0 Anti-Spoofing System
    - Blink detection (চোখের পলক)
    - Depth analysis (3D liveness)
    - Texture analysis (screen/photo detect)
    - Motion detection
    - Challenge-response
    """
    
    def __init__(self):
        self.blink_threshold = 0.2     # Eye aspect ratio threshold
        self.blink_frames = 3           # Consecutive frames for blink
        self.min_blinks = 2             # Minimum blinks for liveness
        self.depth_threshold = 0.3      # Depth variation threshold
        self.texture_threshold = 0.5    # Texture uniformity threshold
        
        # State tracking
        self.blink_counter = 0
        self.total_blinks = 0
        self.frame_count = 0
        self.previous_ear = None
        
        # Challenge mode
        self.challenge_actions = ["blink", "smile", "turn_left", "turn_right", "nod"]
        self.current_challenge = None
        
        status = "✅" if CV2_AVAILABLE else "❌"
        print(f"🎭 Anti-Spoofing initialized {status}")
    
    # ===== LIVENESS CHECK (MAIN) =====
    
    def check_liveness(self, image_data, previous_frame=None) -> Tuple[bool, str, Dict]:
        """
        Main liveness check
        
        Args:
            image_data: Current frame
            previous_frame: Previous frame (for motion analysis)
        
        Returns:
            (is_alive, message, details)
        """
        checks = {}
        
        # Check 1: Blink detection
        blink_result, blink_msg = self._check_blink(image_data)
        checks["blink"] = {"passed": blink_result, "message": blink_msg}
        
        # Check 2: Texture analysis (screen/photo detect)
        texture_result, texture_msg = self._check_texture(image_data)
        checks["texture"] = {"passed": texture_result, "message": texture_msg}
        
        # Check 3: Motion detection (if previous frame available)
        if previous_frame is not None:
            motion_result, motion_msg = self._check_motion(image_data, previous_frame)
            checks["motion"] = {"passed": motion_result, "message": motion_msg}
        
        # Check 4: Depth analysis
        depth_result, depth_msg = self._check_depth(image_data)
        checks["depth"] = {"passed": depth_result, "message": depth_msg}
        
        # Overall decision
        passed_checks = sum(1 for c in checks.values() if c["passed"])
        total_checks = len(checks)
        
        # Need at least 2 out of available checks to pass
        is_alive = passed_checks >= min(2, total_checks)
        
        if is_alive:
            message = f"✅ Liveness confirmed ({passed_checks}/{total_checks} checks)"
        else:
            message = f"🚫 Spoofing detected! ({passed_checks}/{total_checks} checks)"
        
        return is_alive, message, checks
    
    def is_alive(self, image_data, previous_frame=None) -> bool:
        """Quick liveness check"""
        is_alive, _, _ = self.check_liveness(image_data, previous_frame)
        return is_alive
    
    # ===== BLINK DETECTION =====
    
    def _check_blink(self, image_data) -> Tuple[bool, str]:
        """
        Eye blink detect করো
        Eye Aspect Ratio (EAR) ব্যবহার করে
        """
        if not CV2_AVAILABLE or not FACE_REC_AVAILABLE:
            return True, "Blink check skipped (library not available)"
        
        try:
            img = self._load_image(image_data)
            if img is None:
                return False, "Cannot load image"
            
            # Detect face landmarks
            face_landmarks_list = face_recognition.face_landmarks(img)
            
            if not face_landmarks_list:
                return False, "No face detected for blink check"
            
            landmarks = face_landmarks_list[0]
            
            # Get eye landmarks
            left_eye = landmarks.get("left_eye")
            right_eye = landmarks.get("right_eye")
            
            if not left_eye or not right_eye:
                return False, "Cannot detect eyes"
            
            # Calculate Eye Aspect Ratio
            left_ear = self._eye_aspect_ratio(left_eye)
            right_ear = self._eye_aspect_ratio(right_eye)
            ear = (left_ear + right_ear) / 2.0
            
            self.frame_count += 1
            
            # Blink detection logic
            if ear < self.blink_threshold:
                self.blink_counter += 1
            else:
                if self.blink_counter >= self.blink_frames:
                    self.total_blinks += 1
                    print(f"   👁️ Blink detected! (total: {self.total_blinks})")
                self.blink_counter = 0
            
            # Store for next frame
            self.previous_ear = ear
            
            # Check if enough blinks detected
            if self.total_blinks >= self.min_blinks:
                return True, f"Blink check passed ({self.total_blinks} blinks)"
            elif self.frame_count > 100 and self.total_blinks == 0:
                return False, "No blinks detected (possible photo)"
            
            return True, f"Blink check ongoing (blinks: {self.total_blinks})"
            
        except Exception as e:
            print(f"⚠️ Blink check error: {e}")
            return True, "Blink check error (passing)"
    
    def _eye_aspect_ratio(self, eye_points) -> float:
        """Calculate Eye Aspect Ratio"""
        if len(eye_points) < 6:
            return 1.0
        
        # Convert to numpy array
        points = np.array(eye_points)
        
        # Vertical distances
        v1 = np.linalg.norm(points[1] - points[5])
        v2 = np.linalg.norm(points[2] - points[4])
        
        # Horizontal distance
        h = np.linalg.norm(points[0] - points[3])
        
        if h == 0:
            return 1.0
        
        ear = (v1 + v2) / (2.0 * h)
        return ear
    
    # ===== TEXTURE ANALYSIS =====
    
    def _check_texture(self, image_data) -> Tuple[bool, str]:
        """
        Texture analysis — screen/printed photo detect করে
        Real face ≠ flat surface
        """
        if not CV2_AVAILABLE:
            return True, "Texture check skipped"
        
        try:
            img = self._load_image_cv2(image_data)
            if img is None:
                return False, "Cannot load image"
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
            
            # Detect face region
            face_locations = face_recognition.face_locations(img) if FACE_REC_AVAILABLE else []
            
            if face_locations:
                top, right, bottom, left = face_locations[0]
                face_region = gray[top:bottom, left:right]
            else:
                face_region = gray
            
            # Calculate Local Binary Pattern (LBP) variance
            # High variance = real face texture
            # Low variance = flat screen/photo
            
            # Simple variance check
            variance = np.var(face_region)
            
            # Edge detection (real faces have more edges)
            edges = cv2.Canny(face_region, 50, 150)
            edge_density = np.sum(edges > 0) / edges.size
            
            # Laplacian variance (blur detection)
            laplacian = cv2.Laplacian(face_region, cv2.CV_64F)
            laplacian_var = np.var(laplacian)
            
            # Normalize and combine
            texture_score = (variance / 10000 + edge_density + laplacian_var / 1000) / 3
            
            print(f"   Texture score: {texture_score:.3f} (var={variance:.0f}, edge={edge_density:.3f}, lap={laplacian_var:.1f})")
            
            if texture_score > self.texture_threshold:
                return True, f"Texture check passed ({texture_score:.2f})"
            else:
                return False, f"Possible screen/photo detected ({texture_score:.2f})"
                
        except Exception as e:
            print(f"⚠️ Texture check error: {e}")
            return True, "Texture check error (passing)"
    
    # ===== MOTION DETECTION =====
    
    def _check_motion(self, current_frame, previous_frame) -> Tuple[bool, str]:
        """
        Frame-to-frame motion detect করো
        Real person naturally moves
        """
        if not CV2_AVAILABLE:
            return True, "Motion check skipped"
        
        try:
            curr = self._load_image_cv2(current_frame)
            prev = self._load_image_cv2(previous_frame)
            
            if curr is None or prev is None:
                return False, "Cannot load frames"
            
            # Resize to same dimensions
            h, w = min(curr.shape[0], prev.shape[0]), min(curr.shape[1], prev.shape[1])
            curr = cv2.resize(curr, (w, h))
            prev = cv2.resize(prev, (w, h))
            
            # Convert to grayscale
            curr_gray = cv2.cvtColor(curr, cv2.COLOR_BGR2GRAY) if len(curr.shape) == 3 else curr
            prev_gray = cv2.cvtColor(prev, cv2.COLOR_BGR2GRAY) if len(prev.shape) == 3 else prev
            
            # Frame difference
            diff = cv2.absdiff(curr_gray, prev_gray)
            
            # Threshold
            _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
            
            # Motion percentage
            motion_percent = np.sum(thresh > 0) / thresh.size
            
            print(f"   Motion: {motion_percent:.3%}")
            
            if motion_percent > 0.001:  # Even tiny motion is OK
                return True, f"Motion detected ({motion_percent:.3%})"
            else:
                return False, "No motion (possible static image)"
                
        except Exception as e:
            print(f"⚠️ Motion check error: {e}")
            return True, "Motion check error (passing)"
    
    # ===== DEPTH ANALYSIS =====
    
    def _check_depth(self, image_data) -> Tuple[bool, str]:
        """
        Depth variation check করো
        Real face has depth (nose closer than ears)
        """
        if not CV2_AVAILABLE:
            return True, "Depth check skipped"
        
        try:
            img = self._load_image_cv2(image_data)
            if img is None:
                return False, "Cannot load image"
            
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
            
            # Center vs edge brightness variation
            h, w = gray.shape[:2]
            
            # Center region (nose area)
            center = gray[h//3:2*h//3, w//3:2*w//3]
            
            # Edge regions
            top = gray[0:h//3, :]
            bottom = gray[2*h//3:, :]
            left = gray[:, 0:w//3]
            right = gray[:, 2*w//3:]
            
            center_mean = np.mean(center)
            edges_mean = np.mean([np.mean(top), np.mean(bottom), np.mean(left), np.mean(right)])
            
            depth_ratio = abs(center_mean - edges_mean) / max(center_mean, 1)
            
            print(f"   Depth ratio: {depth_ratio:.3f}")
            
            if depth_ratio > self.depth_threshold:
                return True, f"Depth check passed ({depth_ratio:.3f})"
            else:
                return False, f"Flat surface detected ({depth_ratio:.3f})"
                
        except Exception as e:
            print(f"⚠️ Depth check error: {e}")
            return True, "Depth check error (passing)"
    
    # ===== CHALLENGE-RESPONSE =====
    
    def generate_challenge(self) -> str:
        """Random challenge generate করো"""
        import random
        self.current_challenge = random.choice(self.challenge_actions)
        return self.current_challenge
    
    def verify_challenge(self, image_data, challenge: str, 
                         previous_frame=None) -> Tuple[bool, str]:
        """
        Challenge response verify করো
        e.g., "blink" বললে blink করেছে কিনা check
        """
        if challenge == "blink":
            return self._check_blink(image_data)
        
        elif challenge in ["turn_left", "turn_right"]:
            if previous_frame is not None:
                return self._check_motion(image_data, previous_frame)
            return True, "Motion assumed"
        
        elif challenge == "smile":
            return self._check_smile(image_data)
        
        elif challenge == "nod":
            if previous_frame is not None:
                return self._check_motion(image_data, previous_frame)
            return True, "Motion assumed"
        
        return True, "Challenge passed (default)"
    
    def _check_smile(self, image_data) -> Tuple[bool, str]:
        """Smile detect করো (basic)"""
        if not FACE_REC_AVAILABLE:
            return True, "Smile check skipped"
        
        try:
            img = self._load_image(image_data)
            if img is None:
                return False, "Cannot load image"
            
            landmarks_list = face_recognition.face_landmarks(img)
            
            if not landmarks_list:
                return False, "No face detected"
            
            # Check mouth width vs height
            mouth = landmarks_list[0].get("top_lip", []) + landmarks_list[0].get("bottom_lip", [])
            
            if len(mouth) < 4:
                return True, "Cannot analyze mouth"
            
            # Simple heuristic
            mouth_width = abs(mouth[-1][0] - mouth[0][0])
            mouth_height = abs(max(m, key=lambda x: x[1])[1] - min(m, key=lambda x: x[1])[1])
            
            ratio = mouth_width / max(mouth_height, 1)
            
            if ratio > 2.5:
                return True, "Smile detected 😊"
            else:
                return False, "No smile detected"
                
        except Exception as e:
            return True, "Smile check error (passing)"
    
    # ===== RESET =====
    
    def reset(self):
        """Blink counter reset (নতুন session)"""
        self.blink_counter = 0
        self.total_blinks = 0
        self.frame_count = 0
        self.previous_ear = None
        self.current_challenge = None
        print("🔄 Anti-spoofing state reset")
    
    # ===== HELPERS =====
    
    def _load_image(self, image_data):
        """PIL Image load"""
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
    
    def _load_image_cv2(self, image_data):
        """OpenCV format image load"""
        if image_data is None:
            return None
        
        try:
            if isinstance(image_data, np.ndarray):
                if len(image_data.shape) == 2:
                    return cv2.cvtColor(image_data, cv2.COLOR_GRAY2BGR)
                return image_data
            
            pil_img = self._load_image(image_data)
            if pil_img is None:
                return None
            
            return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            
        except Exception as e:
            print(f"❌ CV2 image load error: {e}")
            return None
    
    def get_status(self) -> Dict:
        """Current anti-spoofing status"""
        return {
            "total_blinks": self.total_blinks,
            "frame_count": self.frame_count,
            "current_challenge": self.current_challenge,
            "liveness_confidence": min(100, self.total_blinks * 30)
        }
    
    def cleanup(self):
        self.reset()


# ===== Singleton =====
anti_spoofing = AntiSpoofing()


# ===== EEL EXPOSED FUNCTIONS =====
def setup_anti_spoofing_eel():
    """Frontend থেকে call করার জন্য"""
    try:
        import eel
        
        @eel.expose
        def check_liveness(image_data, previous_frame=None):
            """Liveness check"""
            is_alive, message, details = anti_spoofing.check_liveness(image_data, previous_frame)
            return {
                "is_alive": is_alive,
                "message": message,
                "details": {k: v["passed"] for k, v in details.items()}
            }
        
        @eel.expose
        def generate_challenge():
            """New challenge"""
            return anti_spoofing.generate_challenge()
        
        @eel.expose
        def verify_challenge(image_data, challenge, previous_frame=None):
            """Challenge verify"""
            success, message = anti_spoofing.verify_challenge(image_data, challenge, previous_frame)
            return {"success": success, "message": message}
        
        @eel.expose
        def reset_spoofing():
            """Reset state"""
            anti_spoofing.reset()
            return True
        
        print("✅ Anti-spoofing eel functions registered")
        
    except ImportError:
        print("⚠️ Eel not available")
    except Exception as e:
        print(f"⚠️ Anti-spoofing eel setup error: {e}")