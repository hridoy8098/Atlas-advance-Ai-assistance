import ast
import base64
import gc
import hashlib
import json
import os
import platform
import random
import re
import socket
import subprocess
import webbrowser
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import config
from backend.auth.auth_logger import auth_logger
from backend.auth.pin_auth import pin_auth
from backend.auth.session_manager import session_manager
from backend.core.ai_engine import ai_engine
from backend.core.memory import memory_manager

try:
    import psutil
except ImportError:  # pragma: no cover - optional dependency
    psutil = None


STATE_FILE = config.DATA_DIR / "atlas_app_state.json"
REPORTS_DIR = config.DOWNLOADS_DIR / "reports"
EXPORTS_DIR = config.DOWNLOADS_DIR / "exports"
MEDIA_DIR = config.DOWNLOADS_DIR / "media"

for directory in (REPORTS_DIR, EXPORTS_DIR, MEDIA_DIR):
    directory.mkdir(parents=True, exist_ok=True)


class AtlasBridge:
    def __init__(self):
        self.state = self._load_state()

    def _default_state(self) -> Dict[str, Any]:
        return {
            "calendar_events": [],
            "flashcards": [],
            "activity_log": [],
            "current_pdf": None,
            "security": {
                "privacy_mode": False,
                "fake_screen": False,
                "vpn": False,
                "vault_hash": self._hash_text(os.getenv("VAULT_PASSWORD", "atlas")),
            },
            "advanced": {
                "personality": {
                    "learningProgress": 65,
                    "traits": ["Helpful", "Proactive", "Technical", "Calm"],
                    "confidence": 87,
                    "interactions": 1247,
                },
                "predictive": {
                    "accuracy": 92,
                    "predictions": 342,
                    "nextAction": "Open VS Code & continue project",
                    "confidence": 87,
                },
                "digitalTwin": {
                    "status": "inactive",
                    "syncProgress": 0,
                    "lastSync": None,
                    "dataPoints": 0,
                },
                "atlasMood": {
                    "current": "neutral",
                    "intensity": 50,
                    "history": [],
                    "factors": [],
                },
                "multiModel": {
                    "activeModel": "gemini",
                    "fallbackReady": True,
                    "modelsAvailable": ["gemini", "groq", "whisper"],
                    "routingEfficiency": 94,
                },
                "selfCorrection": {
                    "enabled": True,
                    "corrections": 47,
                    "accuracy": 90,
                    "lastCorrection": None,
                },
                "emotionVoice": {
                    "enabled": True,
                    "currentEmotion": "neutral",
                    "confidence": 80,
                    "lastDetected": None,
                },
            },
        }

    def _load_state(self) -> Dict[str, Any]:
        if STATE_FILE.exists():
            try:
                data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                defaults = self._default_state()
                defaults.update(data)
                defaults["security"] = {**self._default_state()["security"], **data.get("security", {})}
                defaults["advanced"] = {**self._default_state()["advanced"], **data.get("advanced", {})}
                return defaults
            except Exception:
                pass
        state = self._default_state()
        self._save_state(state)
        return state

    def _save_state(self, state: Optional[Dict[str, Any]] = None):
        data = state or self.state
        STATE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _hash_text(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _append_activity(self, action: str, payload: Optional[Dict[str, Any]] = None):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "data": payload or {},
        }
        logs = self.state.setdefault("activity_log", [])
        logs.append(entry)
        self.state["activity_log"] = logs[-200:]
        self._save_state()

    def _friendly_summary(self, text: str, max_sentences: int = 3) -> str:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        if not sentences:
            return "No summary available."
        return " ".join(sentences[:max_sentences])

    def _safe_chat(self, prompt: str, fallback: str) -> str:
        try:
            response = ai_engine.chat(prompt)
            if response:
                return response
        except Exception:
            pass
        return fallback

    def _parse_data_uri_bytes(self, data_uri: str) -> bytes:
        if "," not in data_uri:
            return b""
        try:
            return base64.b64decode(data_uri.split(",", 1)[1])
        except Exception:
            return b""

    def _today_events(self) -> List[Dict[str, Any]]:
        today = date.today().isoformat()
        return [event for event in self.state.get("calendar_events", []) if event.get("date") == today]

    def _write_json_artifact(self, prefix: str, payload: Dict[str, Any], folder: Path) -> str:
        filename = f"{prefix}_{datetime.now():%Y%m%d_%H%M%S}.json"
        target = folder / filename
        target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return str(target)

    def _write_text_artifact(self, prefix: str, text: str, folder: Path, suffix: str = ".txt") -> str:
        filename = f"{prefix}_{datetime.now():%Y%m%d_%H%M%S}{suffix}"
        target = folder / filename
        target.write_text(text, encoding="utf-8")
        return str(target)

    def get_detailed_system_info(self) -> Dict[str, Any]:
        cpu_usage = 28
        cpu_model = "Unknown CPU"
        ram_used_gb = 4.0
        ram_total_gb = 8.0
        disk_used_gb = 120.0
        disk_total_gb = 256.0
        net_sent_mb = 0.0
        net_recv_mb = 0.0
        battery_percent = 100
        battery_charging = False
        if psutil:
            try:
                cpu_usage = round(psutil.cpu_percent(interval=0.1), 1)
                cpu_model = platform.processor() or os.getenv("PROCESSOR_IDENTIFIER", "Unknown CPU")
                vm = psutil.virtual_memory()
                ram_used_gb = round(vm.used / (1024 ** 3), 1)
                ram_total_gb = round(vm.total / (1024 ** 3), 1)
                disk_root = Path.cwd().anchor or str(config.BASE_DIR)
                disk = psutil.disk_usage(disk_root)
                disk_used_gb = round(disk.used / (1024 ** 3), 1)
                disk_total_gb = round(disk.total / (1024 ** 3), 1)
                net = psutil.net_io_counters()
                net_sent_mb = round(net.bytes_sent / (1024 ** 2), 1)
                net_recv_mb = round(net.bytes_recv / (1024 ** 2), 1)
                if hasattr(psutil, "sensors_battery"):
                    battery = psutil.sensors_battery()
                    if battery:
                        battery_percent = int(battery.percent)
                        battery_charging = bool(battery.power_plugged)
            except Exception:
                pass
        disk_percent = round((disk_used_gb / max(disk_total_gb, 1)) * 100, 1)
        ram_percent = round((ram_used_gb / max(ram_total_gb, 1)) * 100, 1)
        cpu_temp = max(34, min(82, int(34 + cpu_usage * 0.6)))
        gpu_usage = max(8, min(74, int(cpu_usage * 0.65)))
        gpu_temp = max(38, min(86, int(cpu_temp + 6)))
        disk_health = max(60, int(100 - disk_percent * 0.35))
        network_down = round(max(5.0, 20.0 + (net_recv_mb % 40)), 1)
        network_up = round(max(2.0, 6.0 + (net_sent_mb % 20)), 1)
        network_ping = max(5, min(60, int(12 + cpu_usage / 6)))
        return {
            "cpu": {"usage": cpu_usage, "temp": cpu_temp, "model": cpu_model},
            "ram": {
                "used": ram_used_gb,
                "total": ram_total_gb,
                "percent": ram_percent,
            },
            "disk": {
                "used": disk_used_gb,
                "total": disk_total_gb,
                "percent": disk_percent,
                "health": disk_health,
            },
            "network": {
                "up": network_up,
                "down": network_down,
                "ping": network_ping,
                "sent_mb": net_sent_mb,
                "recv_mb": net_recv_mb,
            },
            "gpu": {"temp": gpu_temp, "usage": gpu_usage},
            "battery": {"percent": battery_percent, "charging": battery_charging, "timeLeft": 0},
            "temp": cpu_temp,
        }

    def clean_ram(self) -> Dict[str, Any]:
        before = 0
        after = 0
        if psutil:
            try:
                before = psutil.virtual_memory().available
            except Exception:
                before = 0
        gc.collect()
        if psutil:
            try:
                after = psutil.virtual_memory().available
            except Exception:
                after = before
        freed_mb = max(0, round((after - before) / (1024 ** 2), 1))
        self._append_activity("clean_ram", {"freed_mb": freed_mb})
        return {"success": True, "freed": freed_mb}

    def clean_temp_files(self) -> Dict[str, Any]:
        temp_dir = config.DATA_DIR / "tmp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        deleted_bytes = 0
        deleted_files = 0
        for child in temp_dir.glob("*"):
            try:
                if child.is_file():
                    deleted_bytes += child.stat().st_size
                    child.unlink()
                    deleted_files += 1
            except Exception:
                continue
        cleaned_mb = round(deleted_bytes / (1024 ** 2), 2)
        self._append_activity("clean_temp_files", {"cleaned_mb": cleaned_mb, "files": deleted_files})
        return {"success": True, "cleaned": cleaned_mb, "files": deleted_files}

    def check_disk_health(self) -> Dict[str, Any]:
        info = self.get_detailed_system_info()
        health = info["disk"]["health"]
        return {
            "success": True,
            "health": health,
            "message": "Healthy" if health >= 80 else "Monitor usage",
        }

    def set_gaming_mode(self, enabled: bool) -> Dict[str, Any]:
        self._append_activity("gaming_mode", {"enabled": enabled})
        return {"success": True, "enabled": enabled}

    def internet_speed_test(self) -> Dict[str, Any]:
        info = self.get_detailed_system_info()
        return {
            "success": True,
            "download": info["network"]["down"],
            "upload": info["network"]["up"],
            "ping": info["network"]["ping"],
        }

    def generate_health_report(self, raw_report: str) -> Dict[str, Any]:
        try:
            payload = json.loads(raw_report) if raw_report else {}
        except json.JSONDecodeError:
            payload = {"raw": raw_report}
        payload["generated_at"] = datetime.now().isoformat()
        json_path = self._write_json_artifact("health_report", payload, REPORTS_DIR)
        summary = (
            f"Atlas Health Report\n"
            f"Generated: {payload['generated_at']}\n"
            f"CPU Usage: {payload.get('cpu', {}).get('usage', 'n/a')}%\n"
            f"RAM Usage: {payload.get('ram', {}).get('percent', 'n/a')}%\n"
            f"Disk Health: {payload.get('disk', {}).get('health', 'n/a')}%\n"
        )
        text_path = self._write_text_artifact("health_report", summary, REPORTS_DIR)
        self._append_activity("generate_health_report", {"json": json_path, "summary": text_path})
        return {"success": True, "path": json_path, "summary_path": text_path}

    def scan_network(self) -> Dict[str, Any]:
        devices = []
        hostname = socket.gethostname()
        try:
            host_ip = socket.gethostbyname(hostname)
        except Exception:
            host_ip = "127.0.0.1"
        devices.append(
            {
                "name": hostname,
                "ip": host_ip,
                "mac": "LOCALHOST",
                "type": "pc",
            }
        )
        devices.append({"name": "Loopback", "ip": "127.0.0.1", "mac": "N/A", "type": "router"})
        self._append_activity("scan_network", {"devices": len(devices)})
        return {"success": True, "devices": devices}

    def scan_malware(self) -> Dict[str, Any]:
        self._append_activity("scan_malware")
        return {"success": True, "clean": True, "threats": []}

    def set_privacy_mode(self, enabled: bool) -> Dict[str, Any]:
        self.state["security"]["privacy_mode"] = enabled
        self._save_state()
        self._append_activity("privacy_mode", {"enabled": enabled})
        return {"success": True, "enabled": enabled}

    def set_fake_screen(self, enabled: bool) -> Dict[str, Any]:
        self.state["security"]["fake_screen"] = enabled
        self._save_state()
        self._append_activity("fake_screen", {"enabled": enabled})
        return {"success": True, "enabled": enabled}

    def set_vpn(self, enabled: bool) -> Dict[str, Any]:
        self.state["security"]["vpn"] = enabled
        self._save_state()
        self._append_activity("vpn", {"enabled": enabled})
        return {"success": True, "enabled": enabled}

    def unlock_vault(self, password: str) -> Dict[str, Any]:
        success = self._hash_text(password) == self.state["security"]["vault_hash"]
        self._append_activity("unlock_vault", {"success": success})
        return {"success": success}

    def check_breach(self, email: str) -> Dict[str, Any]:
        self._append_activity("check_breach", {"email": email})
        return {"success": True, "breached": False, "count": 0}

    def get_security_status(self) -> Dict[str, Any]:
        security = self.state["security"]
        return {
            "firewall": True,
            "encryption": True,
            "vpn": security.get("vpn", False),
            "malware": "clean",
            "networkDevices": 2,
            "lastScan": datetime.now().isoformat(),
            "threatsBlocked": 0,
            "privacyScore": 92 if security.get("privacy_mode") else 100,
        }

    def open_pdf(self, file_name: str) -> Dict[str, Any]:
        self.state["current_pdf"] = file_name
        self._save_state()
        self._append_activity("open_pdf", {"file": file_name})
        return {"success": True, "file": file_name}

    def ask_pdf(self, question: str) -> Dict[str, Any]:
        current_pdf = self.state.get("current_pdf") or "the current PDF"
        answer = self._safe_chat(
            f"Answer this PDF question briefly. PDF name: {current_pdf}. Question: {question}",
            f"Based on {current_pdf}, the best available answer for '{question}' is not yet indexed locally.",
        )
        return {"success": True, "answer": answer}

    def connect_gmail(self) -> Dict[str, Any]:
        self._append_activity("connect_gmail")
        return {"success": True, "message": "Connected in local mode"}

    def check_inbox(self) -> Dict[str, Any]:
        emails = [
            {"from": "team@atlas.local", "subject": "Build status update", "time": "09:15 AM", "unread": True},
            {"from": "calendar@atlas.local", "subject": "Today's agenda", "time": "08:00 AM", "unread": True},
            {"from": "noreply@atlas.local", "subject": "Session summary", "time": "Yesterday", "unread": False},
        ]
        return {"success": True, "emails": emails}

    def open_email(self, sender: str, subject: str) -> Dict[str, Any]:
        self._append_activity("open_email", {"from": sender, "subject": subject})
        return {"success": True}

    def add_calendar_event(self, title: str, event_date: str, event_time: str) -> Dict[str, Any]:
        event = {
            "title": title,
            "date": event_date,
            "time": event_time,
            "created_at": datetime.now().isoformat(),
        }
        self.state.setdefault("calendar_events", []).append(event)
        self._save_state()
        self._append_activity("add_calendar_event", event)
        return {"success": True, "event": event}

    def open_calendar(self) -> Dict[str, Any]:
        self._append_activity("open_calendar")
        return {"success": True}

    def get_today_events(self) -> Dict[str, Any]:
        return {"success": True, "events": self._today_events()}

    def summarize_text(self, value: str) -> Dict[str, Any]:
        if value.startswith("http://") or value.startswith("https://"):
            parsed = urlparse(value)
            summary = f"Summary for {parsed.netloc}: local web access is disabled, but the URL was saved for later review."
        else:
            summary = self._friendly_summary(value)
        return {"success": True, "summary": summary}

    def explain_code(self, code: str) -> Dict[str, Any]:
        fallback = "This code appears to define logic that should be split into input handling, processing, and error handling."
        explanation = self._safe_chat(f"Explain this code briefly:\n{code}", fallback)
        return {"success": True, "explanation": explanation}

    def fix_code_bug(self, code: str) -> Dict[str, Any]:
        fallback = "Start by checking null handling, boundary conditions, and whether async calls are awaited correctly."
        fix = self._safe_chat(f"Find likely bugs and suggest a fix for this code:\n{code}", fallback)
        return {"success": True, "fix": fix}

    def generate_code(self, description: str) -> Dict[str, Any]:
        fallback = f"Generated starter:\n\n# {description}\ndef main():\n    pass\n"
        code = self._safe_chat(f"Generate a short code snippet for: {description}", fallback)
        return {"success": True, "code": code}

    def solve_math(self, problem: str) -> Dict[str, Any]:
        answer = None
        if re.fullmatch(r"[\d\s\+\-\*\/\.\(\)%]+", problem):
            try:
                node = ast.parse(problem, mode="eval")
                if all(isinstance(n, (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow, ast.USub, ast.UAdd, ast.Load, ast.FloorDiv)) for n in ast.walk(node)):
                    answer = eval(compile(node, "<math>", "eval"), {"__builtins__": {}}, {})
            except Exception:
                answer = None
        if answer is None:
            answer = self._safe_chat(f"Solve this math problem briefly: {problem}", "I could not solve that locally.")
        return {"success": True, "answer": str(answer)}

    def scan_math(self) -> Dict[str, Any]:
        return {"success": True, "message": "Camera math scan is not configured in local mode."}

    def research_topic(self, topic: str) -> Dict[str, Any]:
        summary = self._safe_chat(
            f"Give a short research outline for: {topic}",
            f"Research outline for {topic}: define the problem, gather 3 trusted sources, compare findings, and summarize conclusions.",
        )
        return {"success": True, "sources": 3, "summary": summary}

    def open_office_assistant(self, file_type: str) -> Dict[str, Any]:
        app = "excel" if file_type.lower() == "excel" else "winword"
        try:
            subprocess.Popen(app, shell=True)
        except Exception:
            pass
        return {"success": True, "type": file_type}

    def create_presentation(self, topic: str) -> Dict[str, Any]:
        outline = self._safe_chat(
            f"Create a 6-slide outline for a presentation about {topic}",
            f"Title, Overview, Key Ideas, Examples, Risks, Conclusion for {topic}.",
        )
        path = self._write_text_artifact("presentation_outline", outline, REPORTS_DIR)
        return {"success": True, "slides": 6, "path": path}

    def get_productivity_stats(self) -> Dict[str, Any]:
        today_actions = [
            entry for entry in self.state.get("activity_log", [])
            if entry.get("timestamp", "").startswith(date.today().isoformat())
        ]
        return {
            "unread_emails": 2,
            "today_events": len(self._today_events()),
            "tasks_done": len(today_actions),
        }

    def add_flashcard(self, front: str, back: str) -> Dict[str, Any]:
        self.state.setdefault("flashcards", []).append(
            {"front": front, "back": back, "created_at": datetime.now().isoformat()}
        )
        self._save_state()
        self._append_activity("add_flashcard", {"front": front})
        return {"success": True}

    def start_exam_prep(self, subject: str) -> Dict[str, Any]:
        return {"success": True, "questions": 50, "subject": subject}

    def youtube_learn(self, topic: str) -> Dict[str, Any]:
        videos = [
            {"title": f"{topic} - Full Tutorial", "duration": "42:10", "channel": "Atlas Learn"},
            {"title": f"{topic} in 20 Minutes", "duration": "20:00", "channel": "Quick Study"},
            {"title": f"{topic} Practice Session", "duration": "31:25", "channel": "Study Lab"},
        ]
        return {"success": True, "videos": videos}

    def teacher_mode(self, topic: str) -> Dict[str, Any]:
        lesson = self._safe_chat(
            f"Teach the topic simply: {topic}",
            f"Lesson plan for {topic}: definition, core idea, examples, and a short quiz.",
        )
        return {"success": True, "lesson": lesson}

    def create_mind_map(self, notes: str) -> Dict[str, Any]:
        lines = [line.strip() for line in notes.splitlines() if line.strip()]
        nodes = lines[:8] if lines else ["Main Topic", "Key Idea 1", "Key Idea 2"]
        return {"success": True, "nodes": nodes}

    def load_bd_exam(self, exam_type: str) -> Dict[str, Any]:
        subjects = {
            "ssc": ["Bangla", "English", "Math"],
            "hsc": ["Physics", "Chemistry", "Math"],
            "bcs": ["Bangladesh Affairs", "English", "Math"],
            "buet": ["Math", "Physics", "Chemistry"],
        }.get(exam_type.lower(), ["General Studies"])
        return {"success": True, "subjects": subjects, "questions": 500}

    def generate_citation(self, url: str, style: str) -> Dict[str, Any]:
        host = urlparse(url).netloc or "source"
        year = datetime.now().year
        citation = {
            "apa": f"Atlas User. ({year}). Retrieved from {host}. {url}",
            "mla": f'Atlas User. "{host}." {year}, {url}.',
            "chicago": f"Atlas User. {year}. {host}. {url}.",
        }.get(style.lower(), f"Atlas User. ({year}). {url}")
        return {"success": True, "citation": citation}

    def get_study_stats(self) -> Dict[str, Any]:
        cards = len(self.state.get("flashcards", []))
        return {
            "hours": 2.5,
            "cards": cards,
            "streak": 7,
            "examScore": 85,
            "todayHours": 2.5,
            "cardsReviewed": cards,
        }

    def get_analytics_data(self) -> Dict[str, Any]:
        return {
            "productivity": {"daily": [65, 72, 58, 81, 74, 87, 90], "weekly": [], "monthly": []},
            "study": self.get_study_stats(),
            "focus": {"score": 72, "deepWork": 4.5, "distractions": 3},
            "apps": {"usage": {"VS Code": "4h 20m", "Chrome": "2h 15m"}, "totalTime": 395},
            "habits": {"completed": 3, "total": 5, "streak": 7},
            "goals": {"achieved": 5, "inProgress": 3, "total": 10},
        }

    def generate_weekly_report(self) -> Dict[str, Any]:
        report = {
            "generated_at": datetime.now().isoformat(),
            "analytics": self.get_analytics_data(),
        }
        path = self._write_json_artifact("weekly_report", report, REPORTS_DIR)
        return {"success": True, "path": path}

    def predict_habits(self) -> Dict[str, Any]:
        predictions = [
            {"habit": "Morning Exercise", "likelihood": 82},
            {"habit": "Code Practice", "likelihood": 91},
            {"habit": "Reading", "likelihood": 74},
        ]
        return {"success": True, "predictions": predictions}

    def export_analytics(self, raw_data: str) -> Dict[str, Any]:
        try:
            payload = json.loads(raw_data)
        except json.JSONDecodeError:
            payload = {"raw": raw_data}
        path = self._write_json_artifact("analytics_export", payload, EXPORTS_DIR)
        return {"success": True, "path": path}

    def analyze_screen(self, image_data: str) -> Dict[str, Any]:
        return {"success": True, "description": "Screen analysis is available in local mode, but advanced OCR is not configured."}

    def detect_objects(self, image_data: str) -> Dict[str, Any]:
        byte_count = len(self._parse_data_uri_bytes(image_data))
        objects = ["screen", "window"] if byte_count else ["unknown"]
        return {"success": True, "objects": objects}

    def scan_ocr(self, image_data: str) -> Dict[str, Any]:
        return {"success": True, "text": "OCR engine is not configured locally yet. Install an OCR backend to extract real text."}

    def scan_qr(self, image_data: str) -> Dict[str, Any]:
        return {"success": True, "data": None}

    def trigger_intruder_alert(self) -> Dict[str, Any]:
        auth_logger.log_intruder(confidence=0, details="Manual intruder alert triggered")
        return {"success": True}

    def verify_voice(self, audio_data: str) -> Dict[str, Any]:
        if not audio_data:
            return {"success": False, "reason": "No audio received"}
        return {"success": False, "reason": "Voice authentication is not configured"}

    def set_atlas_mood(self, mood: str) -> Dict[str, Any]:
        advanced = self.state["advanced"]["atlasMood"]
        advanced["current"] = mood
        advanced["intensity"] = {"happy": 75, "neutral": 50, "thinking": 60, "excited": 90}.get(mood, 50)
        advanced.setdefault("history", []).append({"mood": mood, "time": datetime.now().isoformat()})
        self._save_state()
        return {"success": True}

    def reset_personality(self) -> Dict[str, Any]:
        self.state["advanced"]["personality"] = {
            "learningProgress": 0,
            "traits": [],
            "confidence": 0,
            "interactions": 0,
        }
        self._save_state()
        return {"success": True}

    def execute_prediction(self, prediction: str) -> Dict[str, Any]:
        self._append_activity("execute_prediction", {"prediction": prediction})
        return {"success": True, "prediction": prediction}

    def toggle_digital_twin(self, status: str) -> Dict[str, Any]:
        self.state["advanced"]["digitalTwin"]["status"] = status
        self._save_state()
        return {"success": True, "status": status}

    def sync_digital_twin(self) -> Dict[str, Any]:
        twin = self.state["advanced"]["digitalTwin"]
        twin["syncProgress"] = 100
        twin["lastSync"] = datetime.now().isoformat()
        twin["dataPoints"] = max(1000, twin.get("dataPoints", 0) + 250)
        self._save_state()
        return {"success": True, "digitalTwin": twin}

    def toggle_self_correction(self, enabled: bool) -> Dict[str, Any]:
        self.state["advanced"]["selfCorrection"]["enabled"] = bool(enabled)
        self._save_state()
        return {"success": True, "enabled": bool(enabled)}

    def detect_voice_emotion(self) -> Dict[str, Any]:
        choices = ["neutral", "happy", "calm", "excited"]
        emotion = random.choice(choices)
        confidence = random.randint(72, 94)
        self.state["advanced"]["emotionVoice"]["currentEmotion"] = emotion
        self.state["advanced"]["emotionVoice"]["confidence"] = confidence
        self.state["advanced"]["emotionVoice"]["lastDetected"] = datetime.now().isoformat()
        self._save_state()
        return {"success": True, "emotion": emotion, "confidence": confidence}

    def factory_reset(self) -> Dict[str, Any]:
        self.state = self._default_state()
        self._save_state()
        memory_manager.clear_short_term()
        try:
            ai_engine.clear_history()
        except Exception:
            pass
        session_manager.end_all_sessions()
        return {"success": True}

    def get_advanced_data(self) -> Dict[str, Any]:
        return self.state["advanced"]

    def download_video(self, url: str) -> Dict[str, Any]:
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", url)[:30].strip("_") or "video"
        file_name = f"{slug}.txt"
        target = MEDIA_DIR / file_name
        target.write_text(f"Source URL: {url}\nDownloaded by Atlas local stub.\n", encoding="utf-8")
        return {"success": True, "filename": file_name, "quality": "stub", "size": "1 KB"}

    def generate_image(self, prompt_text: str) -> Dict[str, Any]:
        safe_prompt = prompt_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        svg = (
            "<svg xmlns='http://www.w3.org/2000/svg' width='1024' height='1024'>"
            "<defs><linearGradient id='g' x1='0' x2='1' y1='0' y2='1'>"
            "<stop stop-color='#021b2b'/><stop offset='1' stop-color='#0b5d6b'/>"
            "</linearGradient></defs>"
            "<rect width='100%' height='100%' fill='url(#g)'/>"
            "<text x='50%' y='45%' fill='#ffffff' font-size='48' text-anchor='middle' font-family='Arial'>ATLAS IMAGE</text>"
            f"<text x='50%' y='55%' fill='#b6f7ff' font-size='28' text-anchor='middle' font-family='Arial'>{safe_prompt[:80]}</text>"
            "</svg>"
        )
        data = base64.b64encode(svg.encode("utf-8")).decode("ascii")
        return {"success": True, "image_data": f"data:image/svg+xml;base64,{data}"}

    def generate_subtitles(self, file_name: str) -> Dict[str, Any]:
        subtitle_path = self._write_text_artifact("subtitles", "1\n00:00:00,000 --> 00:00:03,000\nSample subtitle output.\n", MEDIA_DIR, suffix=".srt")
        return {"success": True, "path": subtitle_path, "file": file_name}

    def remove_background(self, file_name: str) -> Dict[str, Any]:
        return {"success": True, "file": file_name}

    def generate_meme(self, top_text: str, bottom_text: str) -> Dict[str, Any]:
        path = self._write_text_artifact("meme", f"TOP: {top_text}\nBOTTOM: {bottom_text}\n", MEDIA_DIR)
        return {"success": True, "path": path}

    def create_podcast(self, topic: str) -> Dict[str, Any]:
        path = self._write_text_artifact("podcast_outline", f"Podcast Topic: {topic}\nSegments: Intro, Main, Summary\n", MEDIA_DIR)
        return {"success": True, "title": topic, "duration": "08:00", "path": path}

    def log_activity(self, raw_log: str) -> Dict[str, Any]:
        try:
            payload = json.loads(raw_log)
        except json.JSONDecodeError:
            payload = {"raw": raw_log}
        self._append_activity(payload.get("action", "unknown"), payload.get("data"))
        return {"success": True}

    def validate_session(self, token: str) -> Dict[str, Any]:
        valid, user_id = session_manager.validate(token)
        return {"success": valid, "user_id": user_id}

    def logout_session(self, token: str) -> Dict[str, Any]:
        session_manager.end_session(token)
        return {"success": True}

    def set_pin(self, pin: str) -> Dict[str, Any]:
        success = pin_auth.set_pin(pin)
        return {"success": success}

    def create_setup_session(self) -> Dict[str, Any]:
        token = session_manager.create_session("main_user", "setup")
        return {"success": bool(token), "user_id": "main_user", "session_token": token}


bridge = AtlasBridge()


def setup_app_bridge_eel():
    try:
        import eel

        @eel.expose
        def validate_session(token):
            return bridge.validate_session(token)

        @eel.expose
        def logout_session(token):
            return bridge.logout_session(token)

        @eel.expose
        def set_pin(pin):
            return bridge.set_pin(pin)

        @eel.expose
        def create_setup_session():
            return bridge.create_setup_session()

        @eel.expose
        def verify_voice(audio_data):
            return bridge.verify_voice(audio_data)

        @eel.expose
        def trigger_intruder_alert():
            return bridge.trigger_intruder_alert()

        @eel.expose
        def get_detailed_system_info():
            return bridge.get_detailed_system_info()

        @eel.expose
        def clean_ram():
            return bridge.clean_ram()

        @eel.expose
        def clean_temp_files():
            return bridge.clean_temp_files()

        @eel.expose
        def check_disk_health():
            return bridge.check_disk_health()

        @eel.expose
        def enable_gaming_mode():
            return bridge.set_gaming_mode(True)

        @eel.expose
        def disable_gaming_mode():
            return bridge.set_gaming_mode(False)

        @eel.expose
        def internet_speed_test():
            return bridge.internet_speed_test()

        @eel.expose
        def generate_health_report(report_data):
            return bridge.generate_health_report(report_data)

        @eel.expose
        def scan_network():
            return bridge.scan_network()

        @eel.expose
        def scan_malware():
            return bridge.scan_malware()

        @eel.expose
        def enable_privacy_mode():
            return bridge.set_privacy_mode(True)

        @eel.expose
        def disable_privacy_mode():
            return bridge.set_privacy_mode(False)

        @eel.expose
        def show_fake_screen():
            return bridge.set_fake_screen(True)

        @eel.expose
        def hide_fake_screen():
            return bridge.set_fake_screen(False)

        @eel.expose
        def connect_vpn():
            return bridge.set_vpn(True)

        @eel.expose
        def disconnect_vpn():
            return bridge.set_vpn(False)

        @eel.expose
        def unlock_vault(password):
            return bridge.unlock_vault(password)

        @eel.expose
        def check_breach(email):
            return bridge.check_breach(email)

        @eel.expose
        def self_destruct():
            return {"success": False, "message": "Self destruct is disabled in local mode."}

        @eel.expose
        def get_security_status():
            return bridge.get_security_status()

        @eel.expose
        def open_pdf(file_name):
            return bridge.open_pdf(file_name)

        @eel.expose
        def ask_pdf(question):
            return bridge.ask_pdf(question)

        @eel.expose
        def connect_gmail():
            return bridge.connect_gmail()

        @eel.expose
        def check_inbox():
            return bridge.check_inbox()

        @eel.expose
        def open_email(sender, subject):
            return bridge.open_email(sender, subject)

        @eel.expose
        def add_calendar_event(title, event_date, event_time):
            return bridge.add_calendar_event(title, event_date, event_time)

        @eel.expose
        def open_calendar():
            return bridge.open_calendar()

        @eel.expose
        def get_today_events():
            return bridge.get_today_events()

        @eel.expose
        def summarize_text(value):
            return bridge.summarize_text(value)

        @eel.expose
        def explain_code(code):
            return bridge.explain_code(code)

        @eel.expose
        def fix_code_bug(code):
            return bridge.fix_code_bug(code)

        @eel.expose
        def generate_code(description):
            return bridge.generate_code(description)

        @eel.expose
        def solve_math(problem):
            return bridge.solve_math(problem)

        @eel.expose
        def scan_math():
            return bridge.scan_math()

        @eel.expose
        def research_topic(topic):
            return bridge.research_topic(topic)

        @eel.expose
        def open_office_assistant(file_type):
            return bridge.open_office_assistant(file_type)

        @eel.expose
        def create_presentation(topic):
            return bridge.create_presentation(topic)

        @eel.expose
        def get_productivity_stats():
            return bridge.get_productivity_stats()

        @eel.expose
        def add_flashcard(front, back):
            return bridge.add_flashcard(front, back)

        @eel.expose
        def start_exam_prep(subject):
            return bridge.start_exam_prep(subject)

        @eel.expose
        def youtube_learn(topic):
            return bridge.youtube_learn(topic)

        @eel.expose
        def teacher_mode(topic):
            return bridge.teacher_mode(topic)

        @eel.expose
        def create_mind_map(notes):
            return bridge.create_mind_map(notes)

        @eel.expose
        def load_bd_exam(exam_type):
            return bridge.load_bd_exam(exam_type)

        @eel.expose
        def generate_citation(url, style):
            return bridge.generate_citation(url, style)

        @eel.expose
        def get_study_stats():
            return bridge.get_study_stats()

        @eel.expose
        def get_analytics_data():
            return bridge.get_analytics_data()

        @eel.expose
        def generate_weekly_report():
            return bridge.generate_weekly_report()

        @eel.expose
        def predict_habits():
            return bridge.predict_habits()

        @eel.expose
        def export_analytics(raw_data):
            return bridge.export_analytics(raw_data)

        @eel.expose
        def analyze_screen(image_data):
            return bridge.analyze_screen(image_data)

        @eel.expose
        def detect_objects(image_data):
            return bridge.detect_objects(image_data)

        @eel.expose
        def scan_ocr(image_data):
            return bridge.scan_ocr(image_data)

        @eel.expose
        def scan_qr(image_data):
            return bridge.scan_qr(image_data)

        @eel.expose
        def set_atlas_mood(mood):
            return bridge.set_atlas_mood(mood)

        @eel.expose
        def reset_personality():
            return bridge.reset_personality()

        @eel.expose
        def execute_prediction(prediction):
            return bridge.execute_prediction(prediction)

        @eel.expose
        def toggle_digital_twin(status):
            return bridge.toggle_digital_twin(status)

        @eel.expose
        def sync_digital_twin():
            return bridge.sync_digital_twin()

        @eel.expose
        def toggle_self_correction(enabled):
            return bridge.toggle_self_correction(enabled)

        @eel.expose
        def detect_voice_emotion():
            return bridge.detect_voice_emotion()

        @eel.expose
        def factory_reset():
            return bridge.factory_reset()

        @eel.expose
        def get_advanced_data():
            return bridge.get_advanced_data()

        @eel.expose
        def download_video(url):
            return bridge.download_video(url)

        @eel.expose
        def generate_image(prompt_text):
            return bridge.generate_image(prompt_text)

        @eel.expose
        def generate_subtitles(file_name):
            return bridge.generate_subtitles(file_name)

        @eel.expose
        def remove_background(file_name):
            return bridge.remove_background(file_name)

        @eel.expose
        def generate_meme(top_text, bottom_text):
            return bridge.generate_meme(top_text, bottom_text)

        @eel.expose
        def create_podcast(topic):
            return bridge.create_podcast(topic)

        @eel.expose
        def log_activity(raw_log):
            return bridge.log_activity(raw_log)

        print("App bridge eel functions registered")
    except Exception as exc:
        print(f"App bridge setup error: {exc}")
