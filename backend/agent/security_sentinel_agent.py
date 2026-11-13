# backend/agent/security_sentinel_agent.py — Security Sentinel Agent
# Malware heuristics + live network exposure + breach/password checks + quarantine.
from __future__ import annotations

import hashlib
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import config
from backend.security.breach_detector import breach_detector
from backend.security.malware_scanner import malware_scanner
from backend.security.network_monitor import network_monitor
from backend.security.password_manager import password_manager
from .agent_i18n import tr
from .advanced_common import (
    clean_text,
    data_file,
    fail,
    find_existing_path,
    human_bytes,
    ok,
    read_json,
    resolve_path,
    truncate,
    write_json,
)

STATE_FILE = data_file("security_sentinel.json")
QUARANTINE_DIR = data_file("quarantine")


class SecuritySentinelAgent:
    name = "Security Sentinel Agent"

    def get_capabilities(self) -> List[str]:
        return [
            "malware_scan", "network_scan", "breach_check", "password_check",
            "security_scan", "quarantine_file",
        ]

    def handle(self, intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        entities = entities or {}
        command = str(entities.get("_command", ""))
        intent_lower = str(intent or "").lower()
        lower = command.lower()

        try:
            if "password" in intent_lower or "password" in lower:
                password = str(entities.get("password") or self._quoted(command) or "")
                return self.password_check(password)
            if "breach" in intent_lower or "breach" in lower:
                email = str(entities.get("email") or self._email(command) or "")
                return self.breach_check(email)
            if "network" in intent_lower or "network" in lower:
                return self.network_scan(command)
            if "quarantine" in intent_lower or "quarantine" in lower:
                target = entities.get("path") or find_existing_path(command)
                return self.quarantine(target, bool(entities.get("confirm")), command)
            target = entities.get("path") or find_existing_path(command)
            if target:
                return self.scan_files([str(target)], command)
            return self.full_scan(command=command)
        except Exception as exc:
            return fail("security_sentinel", f"Security Sentinel error: {exc}")

    @staticmethod
    def _is_cloud() -> bool:
        return bool(getattr(config, "ATLAS_CLOUD", False))

    def _cloud_hint(self, command: str = "") -> Dict[str, Any]:
        return fail(
            "security_sentinel",
            tr(command,
               "🛡️ File and network scanning runs on your laptop, not the cloud server. Start the laptop connector, then ask again.",
               "🛡️ ফাইল ও নেটওয়ার্ক স্ক্যান আপনার ল্যাপটপে চলে, ক্লাউড সার্ভারে নয়। ল্যাপটপ connector চালু করে আবার বলুন।"),
            needs_connector=True,
        )

    # ---------------- actions ----------------
    def full_scan(self, paths: Optional[List[str]] = None, max_files: int = 1500,
                  command: str = "") -> Dict[str, Any]:
        if self._is_cloud():
            return self._cloud_hint(command)
        scan = malware_scanner.scan(paths=paths, max_files=max_files)
        network = network_monitor.summary()
        listening = int(network.get("listening", 0))
        suspicious = int(scan.get("suspicious_count", 0))

        risk = min(100, suspicious * 12 + max(0, listening - 8) * 2)
        if risk >= 70:
            level = "high"
        elif risk >= 35:
            level = "medium"
        else:
            level = "low"

        recommendations = []
        if suspicious:
            recommendations.append("Suspicious file-গুলো quarantine করুন বা VirusTotal-এ যাচাই করুন।")
        if listening > 12:
            recommendations.append(f"{listening}টি listening port আছে — অপ্রয়োজনীয় service বন্ধ করুন।")
        if not recommendations:
            recommendations.append("বড় কোনো ঝুঁকি পাওয়া যায়নি; নিয়মিত scan চালিয়ে যান।")

        result = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "files_scanned": scan.get("files_scanned", 0),
            "suspicious_count": suspicious,
            "suspicious": scan.get("suspicious", []),
            "network": network,
            "risk_score": risk,
            "risk_level": level,
            "recommendations": recommendations,
            "duration_ms": scan.get("duration_ms", 0),
        }
        self._remember(result)
        return ok(
            "security_sentinel",
            f"🛡️ Scan complete — risk {risk}/100 ({level}), {suspicious} suspicious file(s).",
            **result,
        )

    def scan_files(self, paths: List[str], command: str = "") -> Dict[str, Any]:
        if self._is_cloud():
            return self._cloud_hint(command)
        scan = malware_scanner.scan(paths=paths, max_files=3000)
        suspicious = scan.get("suspicious", [])
        return ok(
            "security_sentinel",
            tr(command,
               f"🔍 {scan.get('files_scanned', 0)} file scanned; {len(suspicious)} suspicious.",
               f"🔍 {scan.get('files_scanned', 0)}টি ফাইল স্ক্যান; {len(suspicious)}টি সন্দেহজনক।"),
            **scan,
        )

    def network_scan(self, command: str = "") -> Dict[str, Any]:
        if self._is_cloud():
            return self._cloud_hint(command)
        summary = network_monitor.summary()
        connections = network_monitor.active_connections(limit=30)
        return ok(
            "security_sentinel",
            tr(command,
               f"🌐 {summary.get('established', 0)} established, {summary.get('listening', 0)} listening.",
               f"🌐 {summary.get('established', 0)}টি established, {summary.get('listening', 0)}টি listening।"),
            network=summary,
            connections=connections,
            note="শুধু নিজের process-গুলো monitor করুন; unknown remote connection দেখলে যাচাই করুন।",
        )

    def breach_check(self, email: str) -> Dict[str, Any]:
        email = clean_text(email)
        if "@" not in email:
            return fail("security_sentinel", "Breach check-এর জন্য email দিন।")
        result = breach_detector.check(email)
        if not result.get("available"):
            return fail("security_sentinel", f"Breach lookup unavailable: {result.get('message')}", email=email)
        message = (
            f"⚠️ {email} found in {result.get('count', 0)} breach(es). Password বদলান।"
            if result.get("breached") else f"✅ No known breach for {email}."
        )
        payload = {key: value for key, value in result.items() if key not in ("message", "success", "agent")}
        return ok("security_sentinel", message, **payload, email=email)

    def password_check(self, password: str) -> Dict[str, Any]:
        if not password:
            return fail("security_sentinel", "Password দিন (quote করে), যেমন: “password check ‘abc123’”।")
        result = password_manager.strength(password)
        score = result.get("score", 0)
        entropy = result.get("entropy_bits", result.get("entropy", 0))
        message = f"🔐 Password strength: {score}/100 (entropy {entropy})."
        suggestions = result.get("suggestions") or []
        if suggestions:
            message += " " + " ".join(str(item) for item in suggestions[:2])
        return ok("security_sentinel", message, **result, password_masked="•" * min(len(password), 12))

    def quarantine(self, target: Optional[Path], confirm: bool = False, command: str = "") -> Dict[str, Any]:
        if self._is_cloud():
            return self._cloud_hint(command)
        if target is None or not target.exists() or not target.is_file():
            return fail("security_sentinel", "Quarantine করার file path দিন।")
        if not confirm:
            return fail(
                "security_sentinel",
                "⚠️ Quarantine করতে confirm=true দরকার। File সরানো হবে, delete হবে না।",
                path=str(target),
                pending=True,
            )
        try:
            QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha256(target.read_bytes()).hexdigest()[:12]
            destination = QUARANTINE_DIR / f"{digest}-{target.name}"
            manifest = read_json(QUARANTINE_DIR / "manifest.json", {"items": []})
            manifest.setdefault("items", []).append({
                "original": str(target),
                "quarantined": str(destination),
                "sha256": digest,
                "size": target.stat().st_size,
                "ts": datetime.now().isoformat(timespec="seconds"),
            })
            shutil.move(str(target), str(destination))
            write_json(QUARANTINE_DIR / "manifest.json", manifest)
            return ok(
                "security_sentinel",
                f"🔒 Quarantined: {destination.name}",
                original=str(target),
                quarantined=str(destination),
                sha256=digest,
            )
        except Exception as exc:
            return fail("security_sentinel", f"Quarantine failed: {exc}")

    # ---------------- helpers ----------------
    @staticmethod
    def _remember(result: Dict[str, Any]) -> None:
        state = read_json(STATE_FILE, {"history": []})
        state.setdefault("history", []).append(result)
        state["history"] = state["history"][-20:]
        write_json(STATE_FILE, state)

    @staticmethod
    def _email(command: str) -> str:
        match = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", command)
        return match.group(0) if match else ""

    @staticmethod
    def _quoted(command: str) -> str:
        match = re.search(r"[\"“”'‘’]([^\"“”'‘’]{1,200})[\"“”'‘’]", command)
        return match.group(1) if match else ""

    def test(self) -> Dict[str, Any]:
        state = read_json(STATE_FILE, {"history": []})
        return {
            "success": True,
            "agent": "security_sentinel",
            "last_scans": len(state.get("history") or []),
            "network_monitor": bool(network_monitor.summary().get("total") is not None),
            "message": "Security Sentinel ready.",
        }


security_sentinel_agent = SecuritySentinelAgent()
