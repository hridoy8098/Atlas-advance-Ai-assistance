# backend/agent/privacy_guardian_agent.py — Privacy Guardian Agent
# Sensitive-data audit, privacy mode, clipboard checks and image redaction.
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import config
from backend.security.privacy_mode import privacy_mode
from backend.security.screen_watermark import screen_watermark
from .agent_i18n import tr
from .advanced_common import (
    clean_text,
    data_file,
    fail,
    find_existing_path,
    ok,
    read_json,
    truncate,
    write_json,
)

AUDIT_FILE = data_file("privacy_audit.json")
TEXT_EXT = {".txt", ".md", ".csv", ".json", ".log", ".ini", ".yml", ".yaml", ".py", ".js", ".html"}
PATTERNS = [
    ("email", re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")),
    ("phone_bd", re.compile(r"(?:\+?880|0)1[3-9]\d{8}\b")),
    ("nid", re.compile(r"\b(?:\d{10}|\d{13}|\d{17})\b")),
    ("passport", re.compile(r"\b[A-Z]{1,2}\d{7,8}\b")),
    ("api_key", re.compile(r"\b(?:sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_-]{30,})\b")),
    ("password", re.compile(r"(?i)password\s*[:=]\s*['\"]?[^\s'\"]{6,}")),
]


class PrivacyGuardianAgent:
    name = "Privacy Guardian Agent"

    def get_capabilities(self) -> List[str]:
        return [
            "privacy_mode", "privacy_audit", "sensitive_scan", "clipboard_check",
            "clipboard_clear", "blur_faces", "watermark_image",
        ]

    def handle(self, intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        entities = entities or {}
        command = str(entities.get("_command", ""))
        intent_lower = str(intent or "").lower()
        lower = command.lower()

        try:
            if "clipboard" in intent_lower or "clipboard" in lower:
                if "clear" in lower or "clear" in intent_lower:
                    return self.clipboard_clear(command)
                return self.clipboard_check(command)
            if "blur" in intent_lower or "blur" in lower or "redact" in lower:
                image = entities.get("image") or entities.get("path") or find_existing_path(command)
                return self.blur_image(image)
            if "watermark" in intent_lower or "watermark" in lower:
                image = entities.get("image") or entities.get("path") or find_existing_path(command)
                return self.watermark_image(image, str(entities.get("text") or "ATLAS"))
            if any(word in lower for word in ("off", "disable", "বন্ধ")):
                return self.set_mode(False, command)
            if any(word in lower for word in ("on", "enable", "চালু")) and "audit" not in lower:
                return self.set_mode(True, command)
            if "mode" in intent_lower or "privacy status" in lower or "স্ট্যাটাস" in lower:
                return self.status(command)
            target = entities.get("path") or find_existing_path(command)
            return self.audit(target, command)
        except Exception as exc:
            return fail("privacy_guardian", f"Privacy Guardian error: {exc}")

    @staticmethod
    def _is_cloud() -> bool:
        return bool(getattr(config, "ATLAS_CLOUD", False))

    def _cloud_hint(self, command: str) -> Dict[str, Any]:
        return fail(
            "privacy_guardian",
            tr(command,
               "🔐 Privacy audit and clipboard checks run on your laptop. Start the laptop connector, then ask again.",
               "🔐 প্রাইভেসি অডিট ও ক্লিপবোর্ড চেক আপনার ল্যাপটপে চলে। ল্যাপটপ connector চালু করে আবার বলুন।"),
            needs_connector=True,
        )

    # ---------------- actions ----------------
    def set_mode(self, enabled: bool, command: str = "") -> Dict[str, Any]:
        result = privacy_mode.enable() if enabled else privacy_mode.disable()
        return ok(
            "privacy_guardian",
            tr(command, "🔒 Privacy mode ON." if enabled else "🔓 Privacy mode OFF.",
               "🔒 প্রাইভেসি মোড চালু।" if enabled else "🔓 প্রাইভেসি মোড বন্ধ।"),
            action="privacy_mode",
            **result,
        )

    def status(self, command: str = "") -> Dict[str, Any]:
        status = privacy_mode.status()
        enabled = status.get("enabled")
        return ok(
            "privacy_guardian",
            tr(command,
               "🔒 Privacy mode is ON." if enabled else "🔓 Privacy mode is OFF.",
               "🔒 প্রাইভেসি মোড চালু আছে।" if enabled else "🔓 প্রাইভেসি মোড বন্ধ আছে।"),
            action="privacy_status",
            **status,
        )

    def audit(self, target: Optional[Path] = None, command: str = "") -> Dict[str, Any]:
        if self._is_cloud():
            return self._cloud_hint(command)
        roots = []
        if target and target.exists():
            roots = [target]
        else:
            home = Path.home()
            roots = [home / "Desktop", home / "Documents", home / "Downloads"]

        files = []
        for root in roots:
            if not root.exists():
                continue
            if root.is_file():
                files.append(root)
                continue
            for path in root.rglob("*"):
                if path.is_file() and path.suffix.lower() in TEXT_EXT:
                    try:
                        if path.stat().st_size <= 2_000_000:
                            files.append(path)
                    except Exception:
                        continue
                if len(files) >= 300:
                    break
            if len(files) >= 300:
                break

        findings: List[Dict[str, Any]] = []
        counts: Dict[str, int] = {}
        for path in files:
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")[:500_000]
            except Exception:
                continue
            for kind, pattern in PATTERNS:
                matches = pattern.findall(text)
                if not matches:
                    continue
                unique = list(dict.fromkeys(matches))[:20]
                counts[kind] = counts.get(kind, 0) + len(unique)
                findings.append({
                    "file": str(path),
                    "kind": kind,
                    "count": len(unique),
                    "sample_masked": [self._mask(item) for item in unique[:3]],
                })

        risk = min(100, sum(counts.values()) * 4)
        result = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "files_scanned": len(files),
            "counts": counts,
            "findings": findings[:80],
            "risk_score": risk,
            "recommendation": (
                "Sensitive data পাওয়া গেছে — file encrypt/redact করুন, public folder-এ রাখবেন না।"
                if findings else "কোনো sensitive pattern পাওয়া যায়নি।"
            ),
        }
        state = read_json(AUDIT_FILE, {"history": []})
        state.setdefault("history", []).append(result)
        state["history"] = state["history"][-20:]
        write_json(AUDIT_FILE, state)

        return ok(
            "privacy_guardian",
            tr(command,
               f"🕵️ Privacy audit: {len(files)} file scanned, {sum(counts.values())} sensitive item(s).",
               f"🕵️ প্রাইভেসি অডিট: {len(files)}টি ফাইল স্ক্যান, {sum(counts.values())}টি সংবেদনশীল আইটেম পাওয়া গেছে।"),
            action="privacy_audit",
            **result,
        )

    def clipboard_check(self, command: str = "") -> Dict[str, Any]:
        if self._is_cloud():
            return self._cloud_hint(command)
        try:
            import pyperclip
            text = pyperclip.paste() or ""
        except Exception as exc:
            return fail("privacy_guardian", f"Clipboard পড়া যায়নি: {exc}")

        found = []
        for kind, pattern in PATTERNS:
            if pattern.search(text):
                found.append(kind)
        return ok(
            "privacy_guardian",
            tr(command,
               ("⚠️ Clipboard has sensitive data: " + ", ".join(found)) if found
               else "✅ No sensitive pattern in the clipboard.",
               ("⚠️ Clipboard-এ sensitive data আছে: " + ", ".join(found)) if found
               else "✅ Clipboard-এ sensitive pattern নেই।"),
            action="clipboard_check",
            length=len(text),
            findings=found,
            preview=truncate(text, 120) if not found else "",
        )

    def clipboard_clear(self, command: str = "") -> Dict[str, Any]:
        if self._is_cloud():
            return self._cloud_hint(command)
        try:
            import pyperclip
            pyperclip.copy("")
            return ok("privacy_guardian",
                      tr(command, "🧹 Clipboard cleared.", "🧹 Clipboard পরিষ্কার করা হয়েছে।"),
                      action="clipboard_clear")
        except Exception as exc:
            return fail("privacy_guardian", f"Clipboard clear failed: {exc}")

    def blur_image(self, image: Optional[Path]) -> Dict[str, Any]:
        if image is None or not image.exists() or not image.is_file():
            return fail("privacy_guardian", "Blur করার image path দিন।")
        try:
            from PIL import Image, ImageFilter
        except Exception as exc:
            return fail("privacy_guardian", f"Pillow missing: {exc}")

        output_dir = data_file("privacy_redacted")
        output_dir.mkdir(parents=True, exist_ok=True)
        output = output_dir / f"{image.stem}-redacted.png"
        image_obj = Image.open(image).convert("RGB")
        detected = 0

        try:
            import cv2
            import numpy as np
            frame = np.array(image_obj)
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
            cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
            faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))
            for (x, y, w, h) in faces:
                region = image_obj.crop((x, y, x + w, y + h)).filter(ImageFilter.GaussianBlur(radius=18))
                image_obj.paste(region, (x, y, x + w, y + h))
            detected = len(faces)
        except Exception:
            detected = 0

        if detected == 0:
            image_obj = image_obj.filter(ImageFilter.GaussianBlur(radius=16))
            note = "No face detected; whole image blurred."
        else:
            note = f"{detected} face(s) blurred."

        image_obj.save(output)
        return ok(
            "privacy_guardian",
            f"🖼️ Redacted image saved: {output.name}",
            output=str(output),
            faces=detected,
            note=note,
        )

    def watermark_image(self, image: Optional[Path], text: str = "ATLAS") -> Dict[str, Any]:
        if image is None or not image.exists():
            return fail("privacy_guardian", "Watermark করার image path দিন।")
        output = data_file("privacy_redacted") / f"{image.stem}-watermark.png"
        output.parent.mkdir(parents=True, exist_ok=True)
        try:
            result = screen_watermark.apply(str(image), text=text, out_path=str(output))
            return ok("privacy_guardian", f"💧 Watermark applied: {output.name}", **(result if isinstance(result, dict) else {"output": str(output)}))
        except Exception as exc:
            return fail("privacy_guardian", f"Watermark failed: {exc}")

    @staticmethod
    def _mask(value: str) -> str:
        text = str(value)
        if len(text) <= 4:
            return "•" * len(text)
        return text[:2] + "•" * min(10, len(text) - 4) + text[-2:]

    def test(self) -> Dict[str, Any]:
        state = read_json(AUDIT_FILE, {"history": []})
        return {
            "success": True,
            "agent": "privacy_guardian",
            "privacy_mode": privacy_mode.status().get("enabled"),
            "audits": len(state.get("history") or []),
            "message": "Privacy Guardian ready.",
        }


privacy_guardian_agent = PrivacyGuardianAgent()
