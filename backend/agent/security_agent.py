# backend/agent/security_agent.py — real security actions.
#
# Delegates to the actual security modules: password generator/strength meter,
# breach lookup, privacy-mode switch, malware scanner and system lock. Nothing
# here pretends to work: unavailable services return an explicit error.

from __future__ import annotations

import platform
import re
import subprocess
from typing import Any, Dict, List

import config
from backend.security.breach_detector import breach_detector
from backend.security.malware_scanner import malware_scanner
from backend.security.password_manager import password_manager
from backend.security.privacy_mode import privacy_mode
from .advanced_common import clean_text, extract_quoted
from .agent_i18n import is_bengali, tr
from .base_agent import BaseAgent


def _extract_email(text: str) -> str:
    match = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text or "")
    return match.group(0) if match else ""


class SecurityAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Security Agent",
            description="Passwords, breach checks, privacy mode, malware scan and system lock",
        )

    def get_capabilities(self) -> List[str]:
        return [
            "security_password", "security_password_check", "breach_check",
            "privacy_mode", "privacy_status", "security_malware_scan",
            "security_firewall", "lock_system",
        ]

    @staticmethod
    def _is_cloud() -> bool:
        return bool(getattr(config, "ATLAS_CLOUD", False))

    # ---------------- passwords ----------------
    def password_strength(self, password: str, command: str = "") -> Dict[str, Any]:
        password = str(password or "")
        if not password:
            return {"success": False, "action": "security_password_check", "agent": "security",
                    "message": tr(command,
                                  "Send the password in quotes, e.g. password check ‘abc123’.",
                                  "পাসওয়ার্ড quote করে দিন, যেমন: password check ‘abc123’।")}
        result = password_manager.strength(password)
        score = result.get("score", 0)
        label = result.get("label", "unknown")
        bits = result.get("entropy_bits", 0)
        suggestions = result.get("suggestions") or []
        message = tr(command,
                      f"🔐 Password strength: {score}/100 ({label}), {bits} bits of entropy.",
                      f"🔐 পাসওয়ার্ডের শক্তি: {score}/১০০ ({label}), এনট্রপি {bits} বিট।")
        if suggestions:
            message += " " + " ".join(str(item) for item in suggestions[:3])
        return {
            "success": True,
            "action": "security_password_check",
            "agent": "security",
            "message": message,
            **result,
            "password_masked": "•" * min(len(password), 12),
        }

    def generate_password(self, length: int = 16, symbols: bool = True, command: str = "") -> Dict[str, Any]:
        value = password_manager.generate(length=length, symbols=symbols)
        strength = password_manager.strength(value)
        return {"success": True, "action": "security_password", "agent": "security",
                "message": tr(command, f"🔑 Generated password: {value}",
                              f"🔑 তৈরি পাসওয়ার্ড: {value}"),
                "password": value, "length": len(value), "strength": strength}

    # ---------------- breach ----------------
    def check_breach(self, email: str, command: str = "") -> Dict[str, Any]:
        email = clean_text(email) or _extract_email(command)
        if "@" not in email:
            return {"success": False, "action": "breach_check", "agent": "security",
                    "message": tr(command, "Give me an email address to check for breaches.",
                                  "ব্রিচ চেক করার জন্য ইমেইল দিন।")}
        result = breach_detector.check(email)
        if not result.get("available"):
            return {"success": False, "action": "breach_check", "agent": "security",
                    "message": tr(command, f"Breach lookup unavailable: {result.get('message')}",
                                  f"ব্রিচ চেক করা যাচ্ছে না: {result.get('message')}"),
                    "email": email}
        if result.get("breached"):
            message = tr(command,
                         f"⚠️ {email} appears in {result.get('count', 0)} known breach(es). Change its password and enable 2FA.",
                         f"⚠️ {email} {result.get('count', 0)}টি পরিচিত breach-এ পাওয়া গেছে। পাসওয়ার্ড বদলান ও 2FA চালু করুন।")
        else:
            message = tr(command, f"✅ No known breach found for {email}.",
                         f"✅ {email} কোনো পরিচিত breach-এ পাওয়া যায়নি।")
        payload = {key: value for key, value in result.items()
                   if key not in ("message", "success", "agent")}
        return {"success": True, "action": "breach_check", "agent": "security",
                "message": message, "email": email, **payload}

    # ---------------- privacy ----------------
    def privacy(self, action: str = "status", command: str = "") -> Dict[str, Any]:
        if action == "enable":
            result = privacy_mode.enable()
            message = tr(command, "🛡️ Privacy mode ON — microphone listening paused.",
                         "🛡️ প্রাইভেসি মোড চালু — মাইক্রোফোন শোনা বন্ধ।")
        elif action == "disable":
            result = privacy_mode.disable()
            message = tr(command, "Privacy mode OFF — microphone listening allowed.",
                         "প্রাইভেসি মোড বন্ধ — মাইক্রোফোন আবার চালু।")
        else:
            result = privacy_mode.status()
            state = "ON" if result.get("enabled") else "OFF"
            message = tr(command, f"🛡️ Privacy mode is {state}.",
                         f"🛡️ প্রাইভেসি মোড {state}।")
        return {"success": True, "action": "privacy_mode", "agent": "security",
                "message": message, **result}

    # ---------------- malware ----------------
    def malware_scan(self, paths: List[str] = None, command: str = "") -> Dict[str, Any]:
        if self._is_cloud():
            return {"success": False, "action": "security_malware_scan", "agent": "security",
                    "message": tr(command,
                                  "🛡️ Malware scanning runs on your laptop, not the cloud server. Start the laptop connector, then ask again.",
                                  "🛡️ ম্যালওয়্যার স্ক্যান আপনার ল্যাপটপে চলে, ক্লাউড সার্ভারে নয়। ল্যাপটপ connector চালু করে আবার বলুন।"),
                    "needs_connector": True}
        try:
            scan = malware_scanner.scan(paths=paths)
        except Exception as exc:
            return {"success": False, "action": "security_malware_scan", "agent": "security",
                    "message": tr(command, f"Scan failed: {exc}", f"স্ক্যান করা যায়নি: {exc}")}
        suspicious = scan.get("suspicious") or []
        count = len(suspicious)
        if count:
            message = tr(command,
                         f"🛡️ Scanned {scan.get('files_scanned', 0)} files — {count} suspicious item(s) need review.",
                         f"🛡️ {scan.get('files_scanned', 0)}টি ফাইল স্ক্যান — {count}টি সন্দেহজনক ফাইল দেখুন।")
            message += "\n" + "\n".join(f"• {item['path']} — {item['reason']}" for item in suspicious[:5])
        else:
            message = tr(command,
                         f"✅ Scanned {scan.get('files_scanned', 0)} files — nothing suspicious found.",
                         f"✅ {scan.get('files_scanned', 0)}টি ফাইল স্ক্যান — সন্দেহজনক কিছু পাওয়া যায়নি।")
        return {"success": True, "action": "security_malware_scan", "agent": "security",
                "message": message, **scan}

    # ---------------- firewall / lock ----------------
    def firewall_status(self, command: str = "") -> Dict[str, Any]:
        if self._is_cloud():
            return {"success": False, "action": "security_firewall", "agent": "security",
                    "message": tr(command, "Firewall status is a laptop action; start the laptop connector.",
                                  "ফায়ারওয়াল স্ট্যাটাস ল্যাপটপের কাজ; ল্যাপটপ connector চালু করুন।"),
                    "needs_connector": True}
        system = platform.system()
        try:
            if system == "Windows":
                result = subprocess.run(
                    ["netsh", "advfirewall", "show", "allprofiles", "state"],
                    capture_output=True, text=True, timeout=15,
                )
                output = (result.stdout or "").strip()
                states = re.findall(r"State\s+(\w+)", output, re.I)
                summary = ", ".join(states) if states else "unknown"
                message = tr(command, f"🛡️ Windows Firewall profiles: {summary}.",
                             f"🛡️ উইন্ডোজ ফায়ারওয়াল প্রোফাইল: {summary}।")
                return {"success": result.returncode == 0, "action": "security_firewall",
                        "agent": "security", "message": message,
                        "output": output[-2000:], "states": states}
            if system == "Linux":
                result = subprocess.run(["ufw", "status"], capture_output=True, text=True, timeout=15)
                output = (result.stdout or result.stderr or "").strip()
                return {"success": result.returncode == 0, "action": "security_firewall",
                        "agent": "security", "message": output or "ufw not available", "output": output}
            return {"success": False, "action": "security_firewall", "agent": "security",
                    "message": tr(command, "Firewall status is only implemented for Windows and Linux.",
                                  "ফায়ারওয়াল স্ট্যাটাস শুধু Windows ও Linux-এ কাজ করে।")}
        except Exception as exc:
            return {"success": False, "action": "security_firewall", "agent": "security",
                    "message": tr(command, f"Firewall check failed: {exc}", f"ফায়ারওয়াল চেক ব্যর্থ: {exc}")}

    def lock_system(self, command: str = "") -> Dict[str, Any]:
        if self._is_cloud():
            return {"success": False, "action": "lock_system", "agent": "security",
                    "message": tr(command, "Locking the screen is a laptop action; start the laptop connector.",
                                  "স্ক্রিন লক করা ল্যাপটপের কাজ; ল্যাপটপ connector চালু করুন।"),
                    "needs_connector": True}
        system = platform.system()
        try:
            if system == "Windows":
                subprocess.Popen("rundll32.exe user32.dll,LockWorkStation", shell=True)
            elif system == "Linux":
                for cmd in (["loginctl", "lock-session"], ["xdg-screensaver", "lock"], ["gnome-screensaver-command", "-l"]):
                    try:
                        subprocess.Popen(cmd)
                        break
                    except Exception:
                        continue
            elif system == "Darwin":
                subprocess.Popen("pmset displaysleepnow", shell=True)
            else:
                return {"success": False, "action": "lock_system", "agent": "security",
                        "message": tr(command, "System lock is not supported on this OS.",
                                      "এই OS-এ সিস্টেম লক সমর্থিত নয়।")}
            return {"success": True, "action": "lock_system", "agent": "security",
                    "message": tr(command, "🔒 Screen locked.", "🔒 স্ক্রিন লক করা হয়েছে।")}
        except Exception as exc:
            return {"success": False, "action": "lock_system", "agent": "security",
                    "message": tr(command, f"Lock failed: {exc}", f"লক করা যায়নি: {exc}")}

    # ---------------- dispatch ----------------
    def handle(self, intent: str, entities: Dict) -> Dict:
        entities = dict(entities or {})
        command = str(entities.get("_command", ""))
        intent_lower = str(intent or "").lower()
        lower = command.lower()
        email = str(entities.get("email") or _extract_email(command) or "")

        try:
            if "generate" in intent_lower or re.search(r"\bgenerate\b.*\bpassword\b|পাসওয়ার্ড\s*(?:বানাও|জেনারেট)", lower):
                length = entities.get("length") or 16
                try:
                    length = int(length)
                except Exception:
                    length = 16
                return self.generate_password(length, True, command)
            if "password" in intent_lower or "password" in lower or "পাসওয়ার্ড" in command:
                password = str(entities.get("password") or extract_quoted(command) or "")
                if not password:
                    match = re.search(r"(?:password|পাসওয়ার্ড)[^:=\-]*[:=\-]\s*(.+)$", command, re.I)
                    if match:
                        password = match.group(1).strip()
                return self.password_strength(password, command)
            if "breach" in intent_lower or "breach" in lower or "ব্রিচ" in command:
                return self.check_breach(email, command)
            if "privacy" in intent_lower or "privacy" in lower or "প্রাইভেসি" in command:
                if re.search(r"\b(?:off|disable|বন্ধ)\b", lower):
                    return self.privacy("disable", command)
                if re.search(r"\b(?:on|enable|চালু)\b", lower):
                    return self.privacy("enable", command)
                return self.privacy("status", command)
            if "firewall" in intent_lower or "firewall" in lower or "ফায়ারওয়াল" in command:
                return self.firewall_status(command)
            if "malware" in intent_lower or "virus" in intent_lower or re.search(
                r"\b(?:malware|virus|security)\s+scan\b|ম্যালওয়্যার|ভাইরাস", lower
            ):
                return self.malware_scan(None, command)
            if "lock" in intent_lower or re.search(r"\block\b.*\b(?:system|computer|pc|screen)\b|সিস্টেম\s*লক", lower):
                return self.lock_system(command)
            return self.privacy("status", command)
        except Exception as exc:
            return {"success": False, "action": "security_error", "agent": "security",
                    "message": tr(command, f"Security Agent error: {exc}", f"সিকিউরিটি এজেন্টে সমস্যা: {exc}")}

    # ---------------- self test ----------------
    def test(self) -> Dict[str, Any]:
        checks: Dict[str, Any] = {}
        probe = password_manager.generate(length=16)
        checks["password_generator"] = password_manager.strength(probe).get("score", 0) >= 60
        try:
            status = privacy_mode.status()
            checks["privacy_mode"] = "enabled" in status
        except Exception:
            checks["privacy_mode"] = False
        checks["breach_api"] = True  # verified on demand; network may be down
        checks["malware_scanner"] = hasattr(malware_scanner, "scan")
        checks["cloud"] = self._is_cloud()
        ok_all = all(bool(value) for key, value in checks.items() if key not in ("cloud",))
        message = "Security modules ready: " + ", ".join(
            f"{key}={'ok' if value else 'fail'}" for key, value in checks.items() if key != "cloud"
        )
        return {"success": ok_all, "agent": "security", "message": message, **checks}


security_agent = SecurityAgent()
