# backend/agent/terminal_agent.py — Atlas 6.0 Terminal Controller

import subprocess
import os
import platform
from typing import Optional, Dict


class TerminalAgent:
    """Terminal command execution"""
    
    def __init__(self):
        self.system = platform.system()
        self.shell = True if self.system == "Windows" else False
        print(f"💻 Terminal Agent initialized")
    
    # ===== EXECUTION =====
    
    def execute(self, command: str, timeout: int = 30) -> Dict:
        """Execute terminal command"""
        try:
            result = subprocess.run(
                command,
                shell=self.shell,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=os.getcwd()
            )
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout.strip() or "(no output)",
                "stderr": result.stderr.strip() or "",
                "code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "stdout": "", "stderr": f"Timeout after {timeout}s", "code": -1}
        except Exception as e:
            return {"success": False, "stdout": "", "stderr": str(e), "code": -1}
    
    def execute_safe(self, command: str) -> Dict:
        """Execute safe commands only"""
        # Block dangerous commands
        dangerous = ["rm -rf", "del /F", "format", "fdisk", "mkfs", "dd if="]
        for d in dangerous:
            if d in command.lower():
                return {"success": False, "stdout": "", "stderr": "🚫 Dangerous command blocked", "code": -1}
        
        return self.execute(command)
    
    # ===== GIT COMMANDS =====
    
    def git_status(self) -> Dict:
        return self.execute("git status")
    
    def git_pull(self) -> Dict:
        return self.execute("git pull")
    
    def git_push(self) -> Dict:
        return self.execute("git push")
    
    def git_commit(self, message: str) -> Dict:
        return self.execute(f'git commit -m "{message}"')
    
    def git_branch(self) -> Dict:
        return self.execute("git branch")
    
    # ===== SYSTEM COMMANDS =====
    
    def ipconfig(self) -> Dict:
        """Network config"""
        cmd = "ipconfig" if self.system == "Windows" else "ifconfig"
        return self.execute(cmd)
    
    def ping(self, host: str = "google.com", count: int = 4) -> Dict:
        """Ping host"""
        cmd = f"ping -n {count} {host}" if self.system == "Windows" else f"ping -c {count} {host}"
        return self.execute(cmd)
    
    def tasklist(self) -> Dict:
        """List processes"""
        cmd = "tasklist" if self.system == "Windows" else "ps aux"
        return self.execute(cmd)
    
    def dir_list(self, path: str = ".") -> Dict:
        """List directory"""
        cmd = f"dir {path}" if self.system == "Windows" else f"ls -la {path}"
        return self.execute(cmd)
    
    # ===== PYTHON =====
    
    def pip_install(self, package: str) -> Dict:
        return self.execute(f"pip install {package}")
    
    def python_run(self, script: str) -> Dict:
        return self.execute(f"python {script}")
    
    def python_version(self) -> Dict:
        return self.execute("python --version")

    # ===== AGENT INTERFACE =====

    def get_capabilities(self) -> list:
        return [
            "terminal_run", "terminal_git", "terminal_pip", "terminal_npm",
            "git_status", "git_pull", "git_push", "git_commit", "git_branch",
            "ipconfig", "ping", "tasklist", "dir_list", "python_run",
        ]

    def handle(self, intent: str, entities: Dict = None) -> Dict:
        entities = entities or {}
        intent_lower = str(intent or "").lower()
        command = str(entities.get("command") or entities.get("cmd") or "")
        cmd_lower = command.lower()
        try:
            if intent_lower == "git_status" or cmd_lower.strip() == "git status":
                return self._wrap("git_status", self.git_status())
            if intent_lower == "git_pull":
                return self._wrap("git_pull", self.git_pull())
            if intent_lower == "git_push":
                return self._wrap("git_push", self.git_push())
            if intent_lower == "git_commit":
                message = str(entities.get("message", "Atlas commit"))
                return self._wrap("git_commit", self.git_commit(message))
            if intent_lower == "git_branch":
                return self._wrap("git_branch", self.git_branch())
            if intent_lower == "ipconfig":
                return self._wrap("ipconfig", self.ipconfig())
            if intent_lower == "ping":
                return self._wrap("ping", self.ping(str(entities.get("host", "google.com"))))
            if intent_lower == "tasklist":
                return self._wrap("tasklist", self.tasklist())
            if intent_lower == "python_version":
                return self._wrap("python_version", self.python_version())
            if command:
                return self._wrap("terminal_run", self.execute_safe(command))
            return {
                "success": False,
                "action": "terminal_unknown",
                "message": "কোন command চালাব? উদাহরণ: 'run command git status'।",
            }
        except Exception as exc:
            return {"success": False, "action": "terminal_error", "message": f"Terminal Agent error: {exc}"}

    def _wrap(self, action: str, result: Dict) -> Dict:
        ok = bool(result.get("success"))
        output = result.get("stdout") if ok else (result.get("stderr") or result.get("stdout"))
        return {
            "success": ok,
            "action": action,
            "message": f"⌨️ {action}: {output or 'done'}",
            "stdout": result.get("stdout", ""),
            "stderr": result.get("stderr", ""),
            "code": result.get("code", -1),
        }


# Singleton
terminal_agent = TerminalAgent()