# backend/auth/face_auth.py — Atlas 6.0 Face Recognition (OpenCV Fallback)

import os
import json
import base64
import hashlib
from io import BytesIO
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

import numpy as np
from PIL import Image

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    print("⚠️ pip install opencv-python")
    CV2_AVAILABLE = False

# Try face_recognition (optional)
try:
    import face_recognition
    FACE_REC_AVAILABLE = True
    print("✅ face_recognition loaded")
except ImportError:
    FACE_REC_AVAILABLE = False
    print("⚠️ face_recognition not installed - using OpenCV fallback")

import config
from backend.auth.auth_logger import auth_logger


class FaceAuthEngine:
    
    def __init__(self):
        self.faces_dir = config.FACE_DATA_DIR
        self.known_faces = {}
        self.face_encodings = []
        self.face_labels = []
        self.threshold = config.FACE_SIMILARITY_THRESHOLD
        
        # OpenCV face detector
        self.face_cascade = None
        if CV2_AVAILABLE:
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
        
        os.makedirs(self.faces_dir, exist_ok=True)
        self._load_known_faces()
        
        print(f"👤 Face Auth initialized (CV2:{CV2_AVAILABLE}, FR:{FACE_REC_AVAILABLE})")
    
    def encode_face(self, image_data) -> Optional[np.ndarray]:
        """Face encoding (dlib or OpenCV histogram)"""
        img = self._load_image(image_data)
        if img is None:
            return None
        
        if FACE_REC_AVAILABLE:
            try:
                import face_recognition
                img_np = np.array(img) if isinstance(img, Image.Image) else img
                locations = face_recognition.face_locations(img_np)
                if locations:
                    return face_recognition.face_encodings(img_np, [locations[0]])[0]
            except:
                pass
        
        # OpenCV fallback: use face histogram as "encoding"
        img_cv = self._to_cv2(img)
        if img_cv is None:
            return None
        
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 5)
        
        if len(faces) > 0:
            (x, y, w, h) = faces[0]
            face_roi = gray[y:y+h, x:x+w]
            face_roi = cv2.resize(face_roi, (128, 128))
            hist = cv2.calcHist([face_roi], [0], None, [256], [0, 256])
            cv2.normalize(hist, hist)
            return hist.flatten()
        
        return None
    
    def recognize(self, image_data) -> Tuple[Optional[str], float, Optional[Dict]]:
        """Face recognize"""
        if not self.known_faces:
            return None, 0.0, None
        
        encoding = self.encode_face(image_data)
        if encoding is None:
            return None, 0.0, None
        
        if not self.face_encodings:
            return None, 0.0, None
        
        if FACE_REC_AVAILABLE:
            import face_recognition
            distances = face_recognition.face_distance(self.face_encodings, encoding)
            best_idx = np.argmin(distances)
            best_dist = distances[best_idx]
            confidence = (1 - best_dist) * 100
            
            if best_dist <= self.threshold:
                user_id = self.face_labels[best_idx]
                return user_id, confidence, {
                    "user_id": user_id,
                    "name": self.known_faces[user_id]["name"],
                    "confidence": round(confidence, 1),
                    "distance": round(float(best_dist), 4)
                }
        else:
            # OpenCV: compare histograms
            best_score = 0
            best_idx = 0
            for i, known_enc in enumerate(self.face_encodings):
                score = cv2.compareHist(encoding.astype(np.float32), 
                                       known_enc.astype(np.float32), 
                                       cv2.HISTCMP_CORREL)
                if score > best_score:
                    best_score = score
                    best_idx = i
            
            if best_score > 0.5:
                user_id = self.face_labels[best_idx]
                confidence = best_score * 100
                return user_id, confidence, {
                    "user_id": user_id,
                    "name": self.known_faces[user_id]["name"],
                    "confidence": round(confidence, 1)
                }
        
        return None, 0.0, None
    
    def recognize_from_base64(self, base64_str: str):
        if ',' in base64_str:
            base64_str = base64_str.split(',')[1]
        image_bytes = base64.b64decode(base64_str)
        return self.recognize(Image.open(BytesIO(image_bytes)))
    
    def detect_faces(self, image_data) -> List[Dict]:
        """Detect faces"""
        img_cv = self._to_cv2(self._load_image(image_data))
        if img_cv is None:
            return []
        
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 5)
        
        result = []
        for i, (x, y, w, h) in enumerate(faces):
            result.append({
                "index": i,
                "location": {"top": y, "right": x+w, "bottom": y+h, "left": x},
                "width": w, "height": h,
                "center": {"x": x + w//2, "y": y + h//2}
            })
        return result
    
    def register_face(self, user_id: str, name: str, 
                      image_data=None, encodings: List = None) -> bool:
        """Register face"""
        if encodings is None and image_data is not None:
            encoding = self.encode_face(image_data)
            if encoding is None:
                return False
            encodings = [encoding]
        
        if not encodings:
            return False
        
        face_data = {
            "user_id": user_id, "name": name,
            "encodings": [enc.tolist() for enc in encodings],
            "encoding_count": len(encodings),
            "registered_at": datetime.now().isoformat()
        }
        
        with open(self.faces_dir / f"{user_id}.json", 'w') as f:
            json.dump(face_data, f, indent=2)
        
        self.known_faces[user_id] = {"name": name, "encodings": encodings, "metadata": face_data}
        self._rebuild_index()
        print(f"✅ Face registered: {name} ({len(encodings)} encodings)")
        return True
    
    def _rebuild_index(self):
        self.face_encodings = []
        self.face_labels = []
        for uid, data in self.known_faces.items():
            for enc in data["encodings"]:
                self.face_encodings.append(enc)
                self.face_labels.append(uid)
    
    def _load_known_faces(self):
        if not os.path.exists(self.faces_dir):
            return
        for fp in Path(self.faces_dir).glob("*.json"):
            try:
                with open(fp) as f:
                    data = json.load(f)
                uid = data["user_id"]
                encs = [np.array(e) for e in data["encodings"]]
                self.known_faces[uid] = {"name": data["name"], "encodings": encs, "metadata": data}
                print(f"   Loaded: {data['name']} ({len(encs)} encodings)")
            except:
                pass
        self._rebuild_index()
    
    def _load_image(self, image_data):
        if image_data is None: return None
        try:
            if isinstance(image_data, Image.Image): return image_data
            if isinstance(image_data, np.ndarray): return Image.fromarray(image_data)
            if isinstance(image_data, str):
                if ',' in image_data: image_data = image_data.split(',')[1]
                return Image.open(BytesIO(base64.b64decode(image_data)))
            if isinstance(image_data, bytes): return Image.open(BytesIO(image_data))
            return None
        except: return None
    
    def _to_cv2(self, img):
        if img is None: return None
        if isinstance(img, np.ndarray):
            if len(img.shape)==2: return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            return cv2.cvtColor(img, cv2.COLOR_RGB2BGR) if img.shape[2]==3 else img
        if isinstance(img, Image.Image):
            return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        return None
    
    def get_known_users(self) -> List[Dict]:
        return [{"user_id": uid, "name": d["name"], "encoding_count": len(d["encodings"])} 
                for uid, d in self.known_faces.items()]
    
    def get_face_count(self) -> int:
        return len(self.known_faces)


face_auth_engine = FaceAuthEngine()


def setup_face_auth_eel():
    try:
        import eel
        from backend.auth.session_manager import session_manager
        
        @eel.expose
        def verify_face(image_data):
            user_id, confidence, info = face_auth_engine.recognize_from_base64(image_data)
            if user_id and confidence > 50:
                token = session_manager.create_session(user_id, "face")
                return {
                    "success": True,
                    "user_id": user_id,
                    "session_token": token,
                    "confidence": round(confidence, 1),
                }
            return {
                "success": False,
                "confidence": round(confidence, 1) if confidence else 0,
                "reason": "Face not recognized",
            }
        
        @eel.expose
        def detect_faces(image_data):
            faces = face_auth_engine.detect_faces(image_data)
            return {"face_count": len(faces), "faces": faces, "emotions": []}
        
        @eel.expose
        def get_known_users():
            return face_auth_engine.get_known_users()
        
        print("✅ Face auth eel registered (OpenCV mode)")
    except: pass
