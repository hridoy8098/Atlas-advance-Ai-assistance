# backend/agent/terminal_agent.py — guarded terminal command runner.
#
# Commands run in the Atlas project directory with a timeout. A deny-list blocks
# destructive system-wide commands, and the cloud server refuses local execution
# (the laptop connector must handle it).

from __future__ import annotations

import os
import platform
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import config
from .agent_i18n import tr
from .base_agent import BaseAgent

_DENY_PATTERNS = [
    r"\brm\s+-rf\s+/(?:\s|$)",
    r"\brm\s+-rf\s+~",
    r"\bdel\s+/[fsq]\b.*\b[a-z]:\\?(?:\s|$)",
    r"\brd\s+/s\s+/q\s+[a-z]:\\?(?:\s|$)",
    r"\bformat\s+[a-z]:",
    r"\bmkfs(?:\.\w+)?\b",
    r"\bfdisk\b",
    r"\bdiskpart\b",
    r"\bdd\s+if=.*\bof=/dev/",
    r"\bRemove-Item\b.*-Recurse.*-Force.*[a-z]:\\?(?:\s|$)",
    r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bhalt\b",
]
_WRITE_PATTERNS = ("git push", "git reset --hard", "pip install", "npm install", "npm update", "del ", "rm ")


class TerminalAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Terminal Agent", description="Guarded terminal, git, pip and npm commands")
        self.system = platform.system()
        self.cwd = str(Path(config.BASE_DIR))

    def get_capabilities(self) -> List[str]:
        return [
            "terminal_run", "terminal_git", "git_status", "git_pull", "git_push",
            "git_commit", "git_branch", "ipconfig", "ping", "tasklist", "dir_list",
            "python_run", "pip_install", "npm_install",
        ]

    @staticmethod
    def _is_cloud() -> bool:
        return bool(getattr(config, "ATLAS_CLOUD", False))

    # ---------------- safety ----------------
    @staticmethod
    def is_dangerous(command: str) -> bool:
        lowered = str(command or "").lower()
        return any(re.search(pattern, lowered) for pattern in _DENY_PATTERNS)

    @staticmethod
    def needs_confirmation(command: str) -> bool:
        lowered = str(command or "").lower().strip()
        return any(lowered.startswith(pattern) for pattern in _WRITE_PATTERNS)

    # ---------------- execution ----------------
    def execute(self, command: str, timeout: int = 40, cwd: str = "") -> Dict[str, Any]:
        command = str(command or "").strip()
        if not command:
            return {"success": False, "stdout": "", "stderr": "empty command", "code": -1}
        if self.is_dangerous(command):
            return {"success": False, "stdout": "", "stderr": "🚫 Dangerous command blocked", "code": -1}
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                cwd=cwd or self.cwd,
            )
            return {
                "success": result.returncode == 0,
                "stdout": (result.stdout or "").strip(),
                "stderr": (result.stderr or "").strip(),
                "code": result.returncode,
                "command": command,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "stdout": "", "stderr": f"Timeout after {timeout}s",
                    "code": -1, "command": command}
        except Exception as exc:
            return {"success": False, "stdout": "", "stderr": str(exc), "code": -1, "command": command}

    def execute_safe(self, command: str) -> Dict[str, Any]:
        return self.execute(command)

    # ---------------- named commands ----------------
    def git_status(self) -> Dict:
        return self.execute("git status")

    def git_pull(self) -> Dict:
        return self.execute("git pull")

    def git_push(self) -> Dict:
        return self.execute("git push")

    def git_commit(self, message: str) -> Dict:
        safe_message = str(message or "Atlas commit").replace('"', "'")
        return self.execute(f'git commit -m "{safe_message}"')

    def git_branch(self) -> Dict:
        return self.execute("git branch")

    def ipconfig(self) -> Dict:
        return self.execute("ipconfig" if self.system == "Windows" else "ifconfig")

    def ping(self, host: str = "google.com", count: int = 4) -> Dict:
        host = re.sub(r"[^\w.\-:]", "", str(host or "google.com"))
        cmd = f"ping -n {int(count)} {host}" if self.system == "Windows" else f"ping -c {int(count)} {host}"
        return self.execute(cmd)

    def tasklist(self) -> Dict:
        return self.execute("tasklist" if self.system == "Windows" else "ps aux")

    def dir_list(self, path: str = ".") -> Dict:
        return self.execute(f"dir {path}" if self.system == "Windows" else f"ls -la {path}")

    def pip_install(self, package: str) -> Dict:
        package = re.sub(r"[^\w.\-=\[\]<>]", "", str(package or ""))
        return self.execute(f"{sys.executable} -m pip install {package}")

    def npm_install(self, package: str, action: str = "install") -> Dict:
        package = re.sub(r"[^\w@/.\-]", "", str(package or ""))
        return self.execute(f"npm {action} {package}")

    def python_run(self, script: str) -> Dict:
        script = str(script or "")
        if self.is_dangerous(script):
            return {"success": False, "stdout": "", "stderr": "🚫 Dangerous command blocked", "code": -1}
        return self.execute(f"{sys.executable} {script}")

    def python_version(self) -> Dict:
        return self.execute(f"{sys.executable} --version")

    # ---------------- dispatch ----------------
    def handle(self, intent: str, entities: Dict = None) -> Dict:
        entities = dict(entities or {})
        intent_lower = str(intent or "").lower()
        command = str(entities.get("command") or entities.get("git_command") or "")
        original = str(entities.get("_command", ""))

        if not command:
            command = self._extract_command(original)
        # "git status" intent with no explicit command.
        if not command:
            if intent_lower.startswith("git_"):
                command = "git " + intent_lower.split("_", 1)[1]
            elif intent_lower == "ipconfig":
                command = "ipconfig" if self.system == "Windows" else "ifconfig"
            elif intent_lower == "tasklist":
                command = "tasklist" if self.system == "Windows" else "ps aux"
            elif intent_lower == "ping":
                command = f"ping -n 4 {entities.get('host') or 'google.com'}" if self.system == "Windows" \
                    else f"ping -c 4 {entities.get('host') or 'google.com'}"

        if self._is_cloud():
            return {"success": False, "action": "terminal_needs_connector", "agent": "terminal",
                    "needs_connector": True,
                    "message": tr(original,
                                  "⌨️ Terminal commands run on your laptop, not the cloud server. "
                                  "Start the laptop connector, then ask again.",
                                  "⌨️ টার্মিনাল কমান্ড আপনার ল্যাপটপে চলে, ক্লাউড সার্ভারে নয়। "
                                  "ল্যাপটপ connector চালু করে আবার বলুন।")}

        if not command:
            return {"success": False, "action": "terminal_unknown", "agent": "terminal",
                    "message": tr(original,
                                  "Which command should I run? Example: “run command git status”.",
                                  "কোন কমান্ড চালাব? উদাহরণ: “run command git status”।")}

        if self.is_dangerous(command):
            return {"success": False, "action": "terminal_blocked", "agent": "terminal",
                    "message": tr(original,
                                  "🚫 That command is blocked because it can damage the system.",
                                  "🚫 কমান্ডটি ব্লক করা হয়েছে কারণ এটি সিস্টেমের ক্ষতি করতে পারে।"),
                    "command": command}

        try:
            # Named shortcuts keep clean structured output.
            if command.strip() == "git status":
                result = self.git_status()
                action = "git_status"
            elif command.strip() == "git pull":
                result = self.git_pull()
                action = "git_pull"
            elif command.strip() == "git push":
                result = self.git_push()
                action = "git_push"
            elif command.strip() == "git branch":
                result = self.git_branch()
                action = "git_branch"
            elif command.strip().startswith("git commit"):
                message = entities.get("message") or re.sub(r"^git\s+commit(?:\s+-m)?\s*", "", command).strip("\"' ")
                result = self.git_commit(message or "Atlas commit")
                action = "git_commit"
            elif intent_lower == "ipconfig" or command.strip() in ("ipconfig", "ifconfig"):
                result = self.ipconfig()
                action = "ipconfig"
            elif intent_lower == "tasklist" or command.strip() in ("tasklist", "ps aux"):
                result = self.tasklist()
                action = "tasklist"
            elif intent_lower == "ping" or command.strip().startswith("ping "):
                match = re.search(r"ping\s+(?:-\w+\s+\d+\s+)?(\S+)", command)
                result = self.ping(match.group(1) if match else "google.com")
                action = "ping"
            else:
                result = self.execute(command)
                action = "terminal_run"
            return self._wrap(action, result, original)
        except Exception as exc:
            return {"success": False, "action": "terminal_error", "agent": "terminal",
                    "message": tr(original, f"Terminal Agent error: {exc}", f"টার্মিনাল এজেন্টে সমস্যা: {exc}")}

    @staticmethod
    def _extract_command(text: str) -> str:
        value = str(text or "").strip()
        if not value:
            return ""
        match = re.match(
            r"^(?:please\s+|atlas\s+)?(?:run|execute|terminal|shell|cmd)\s*(?:command|cmd)?\s*[:\-]?\s*(.+)$",
            value, re.I,
        )
        if match:
            candidate = match.group(1).strip()
            if candidate.lower() not in ("git", "pip", "npm"):
                return candidate
        # Bare commands the planner may pass through.
        if re.match(r"^(?:git|pip|npm|python|node|dir|ls|ipconfig|ping|tasklist)\b", value, re.I):
            return value
        return ""

    def _wrap(self, action: str, result: Dict, original: str = "") -> Dict:
        success = bool(result.get("success"))
        output = result.get("stdout") if success else (result.get("stderr") or result.get("stdout"))
        output = str(output or "done")
        if len(output) > 2500:
            output = output[:2500] + "..."
        if success:
            message = tr(original, f"⌨️ {action} done:\n{output}", f"⌨️ {action} সম্পন্ন:\n{output}")
        else:
            message = tr(original, f"⚠️ {action} failed (code {result.get('code')}):\n{output}",
                         f"⚠️ {action} ব্যর্থ (code {result.get('code')}):\n{output}")
        return {
            "success": success,
            "action": action,
            "agent": "terminal",
            "message": message,
            "stdout": result.get("stdout", ""),
            "stderr": result.get("stderr", ""),
            "code": result.get("code", -1),
        }

    # ---------------- self test ----------------
    def test(self) -> Dict[str, Any]:
        marker = "atlas-terminal-selftest"
        result = self.execute(f"echo {marker}")
        checks = {
            "execute": result.get("success") and marker in str(result.get("stdout", "")),
            "git_repo": Path(self.cwd, ".git").exists(),
            "deny_list": self.is_dangerous("rm -rf /"),
            "cwd": Path(self.cwd).exists(),
        }
        return {"success": checks["execute"] and checks["deny_list"] and checks["cwd"],
                "agent": "terminal",
                "message": "Terminal execution and safety guard verified." if checks["execute"]
                           else "Terminal execution failed.",
                "checks": checks}


terminal_agent = TerminalAgent()
