# backend/agent/app_agent.py — strict app launcher with verified launches.
#
# Only known apps are launched. Unknown names return a clear error instead of
# blindly running the name as a shell command or opening "name.com".
#
# Web apps open in the default browser on the laptop. Desktop apps are spawned
# and verified with psutil. On the cloud server, desktop launches are refused
# with a connector hint; web links are returned so the phone can open them.

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import time
import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Optional

import config
from .agent_i18n import tr
from .base_agent import BaseAgent

try:
    import psutil
except Exception:  # pragma: no cover
    psutil = None

# canonical app -> target description
#   web: url
#   desktop: per-OS launch candidates and process names to verify
APP_TARGETS: Dict[str, Dict[str, Any]] = {
    # ---- web apps ----
    "youtube": {"kind": "web", "url": "https://www.youtube.com"},
    "gmail": {"kind": "web", "url": "https://mail.google.com"},
    "github": {"kind": "web", "url": "https://github.com"},
    "chatgpt": {"kind": "web", "url": "https://chatgpt.com"},
    "facebook": {"kind": "web", "url": "https://www.facebook.com"},
    "messenger": {"kind": "web", "url": "https://www.messenger.com"},
    "whatsapp": {"kind": "web", "url": "https://web.whatsapp.com"},
    "instagram": {"kind": "web", "url": "https://www.instagram.com"},
    "linkedin": {"kind": "web", "url": "https://www.linkedin.com"},
    "reddit": {"kind": "web", "url": "https://www.reddit.com"},
    "twitter": {"kind": "web", "url": "https://x.com"},
    "netflix": {"kind": "web", "url": "https://www.netflix.com"},
    "notion": {"kind": "web", "url": "https://www.notion.so"},
    "slack": {"kind": "web", "url": "https://app.slack.com"},
    "zoom": {"kind": "web", "url": "https://zoom.us/join"},
    "teams": {"kind": "web", "url": "https://teams.microsoft.com"},
    "drive": {"kind": "web", "url": "https://drive.google.com"},
    "maps": {"kind": "web", "url": "https://maps.google.com"},
    "amazon": {"kind": "web", "url": "https://www.amazon.com"},
    "canva": {"kind": "web", "url": "https://www.canva.com"},
    "stackoverflow": {"kind": "web", "url": "https://stackoverflow.com"},
    "wikipedia": {"kind": "web", "url": "https://www.wikipedia.org"},
    "google": {"kind": "web", "url": "https://www.google.com"},
    "spotify": {"kind": "web", "url": "https://open.spotify.com"},

    # ---- Windows-native / installed desktop apps ----
    "notepad": {
        "kind": "desktop",
        "windows": ["notepad.exe"],
        "processes": ["notepad.exe"],
        "darwin": ["open", "-a", "TextEdit"],
        "linux": ["gedit"],
    },
    "calculator": {
        "kind": "desktop",
        "windows": ["calc.exe"],
        "processes": ["CalculatorApp.exe", "Calculator.exe", "calc.exe"],
        "darwin": ["open", "-a", "Calculator"],
        "linux": ["gnome-calculator"],
    },
    "paint": {
        "kind": "desktop",
        "windows": ["mspaint.exe"],
        "processes": ["mspaint.exe"],
        "darwin": ["open", "-a", "Preview"],
        "linux": ["gimp"],
    },
    "explorer": {
        "kind": "desktop",
        "windows": ["explorer.exe"],
        "processes": ["explorer.exe"],
        "darwin": ["open", "."],
        "linux": ["xdg-open", "."],
    },
    "taskmanager": {
        "kind": "desktop",
        "windows": ["taskmgr.exe"],
        "processes": ["Taskmgr.exe"],
        "darwin": ["open", "-a", "Activity Monitor"],
        "linux": ["gnome-system-monitor"],
    },
    "settings": {
        "kind": "desktop",
        "windows": ["ms-settings:"],
        "processes": ["SystemSettings.exe", "ApplicationFrameHost.exe"],
        "darwin": ["open", "-a", "System Settings"],
        "linux": ["gnome-control-center"],
    },
    "terminal": {
        "kind": "desktop",
        "windows": ["wt.exe", "powershell.exe"],
        "processes": ["WindowsTerminal.exe", "powershell.exe"],
        "darwin": ["open", "-a", "Terminal"],
        "linux": ["x-terminal-emulator"],
    },
    "cmd": {
        "kind": "desktop",
        "windows": ["cmd.exe"],
        "processes": ["cmd.exe"],
        "darwin": ["open", "-a", "Terminal"],
        "linux": ["x-terminal-emulator"],
    },
    "vscode": {
        "kind": "desktop",
        "windows": [
            shutil.which("code") or "",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
            r"C:\Program Files\Microsoft VS Code\Code.exe",
        ],
        "processes": ["Code.exe"],
        "darwin": ["open", "-a", "Visual Studio Code"],
        "linux": ["code"],
    },
    "chrome": {
        "kind": "desktop",
        "windows": [
            shutil.which("chrome") or "",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ],
        "processes": ["chrome.exe"],
        "darwin": ["open", "-a", "Google Chrome"],
        "linux": ["google-chrome"],
        # If Chrome is missing, fall back to the default browser.
        "fallback_url": "https://www.google.com",
    },
    "edge": {
        "kind": "desktop",
        "windows": [
            shutil.which("msedge") or "",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ],
        "processes": ["msedge.exe"],
        "darwin": ["open", "-a", "Microsoft Edge"],
        "linux": ["microsoft-edge"],
        "fallback_url": "https://www.google.com",
    },
    "word": {
        "kind": "desktop",
        "windows": ["winword.exe"],
        "processes": ["WINWORD.EXE"],
        "darwin": ["open", "-a", "Microsoft Word"],
        "linux": ["libreoffice", "--writer"],
        "fallback_url": "https://www.office.com/launch/word",
    },
    "excel": {
        "kind": "desktop",
        "windows": ["excel.exe"],
        "processes": ["EXCEL.EXE"],
        "darwin": ["open", "-a", "Microsoft Excel"],
        "linux": ["libreoffice", "--calc"],
        "fallback_url": "https://www.office.com/launch/excel",
    },
    "powerpoint": {
        "kind": "desktop",
        "windows": ["powerpnt.exe"],
        "processes": ["POWERPNT.EXE"],
        "darwin": ["open", "-a", "Microsoft PowerPoint"],
        "linux": ["libreoffice", "--impress"],
        "fallback_url": "https://www.office.com/launch/powerpoint",
    },
    "telegram": {
        "kind": "desktop",
        "windows": ["Telegram.exe"],
        "processes": ["Telegram.exe"],
        "darwin": ["open", "-a", "Telegram"],
        "linux": ["telegram-desktop"],
        "fallback_url": "https://web.telegram.org",
    },
    "discord": {
        "kind": "desktop",
        "windows": [os.path.expandvars(r"%LOCALAPPDATA%\Discord\Update.exe --processStart Discord.exe")],
        "processes": ["Discord.exe"],
        "darwin": ["open", "-a", "Discord"],
        "linux": ["discord"],
        "fallback_url": "https://discord.com/app",
    },
    "vlc": {
        "kind": "desktop",
        "windows": [r"C:\Program Files\VideoLAN\VLC\vlc.exe", r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"],
        "processes": ["vlc.exe"],
        "darwin": ["open", "-a", "VLC"],
        "linux": ["vlc"],
    },
    "steam": {
        "kind": "desktop",
        "windows": ["steam.exe"],
        "processes": ["steam.exe"],
        "darwin": ["open", "-a", "Steam"],
        "linux": ["steam"],
    },
    "obs": {
        "kind": "desktop",
        "windows": [r"C:\Program Files\obs-studio\bin\64bit\obs64.exe"],
        "processes": ["obs64.exe"],
        "darwin": ["open", "-a", "OBS"],
        "linux": ["obs"],
        "fallback_url": "https://obsproject.com",
    },
}

# Extra aliases that the planner does not need but the launcher should accept.
EXTRA_ALIASES: Dict[str, str] = {
    "word pad": "notepad",
    "msedge": "edge",
    "microsoft edge": "edge",
    "google chrome": "chrome",
    "visual studio code": "vscode",
    "vs code": "vscode",
    "code": "vscode",
    "microsoft word": "word",
    "microsoft excel": "excel",
    "microsoft powerpoint": "powerpoint",
    "ppt": "powerpoint",
    "x": "twitter",
    "whats app": "whatsapp",
    "file explorer": "explorer",
    "files": "explorer",
    "command prompt": "cmd",
    "powershell": "cmd",
    "terminal": "terminal",
    "system settings": "settings",
    "control panel": "settings",
    "task manager": "taskmanager",
    "activity monitor": "taskmanager",
    "obs studio": "obs",
    "গুগল ক্রোম": "chrome",
    "ইউটিউব": "youtube",
    "ফেসবুক": "facebook",
    "হোয়াটসঅ্যাপ": "whatsapp",
    "জিমেইল": "gmail",
    "নোটপ্যাড": "notepad",
    "ক্যালকুলেটর": "calculator",
    "টার্মিনাল": "terminal",
    "সেটিংস": "settings",
    "ফাইল এক্সপ্লোরার": "explorer",
    "ভিএসকোড": "vscode",
    "এক্সেল": "excel",
    "ওয়ার্ড": "word",
    "পাওয়ারপয়েন্ট": "powerpoint",
}


def _norm(value: str) -> str:
    return " ".join(str(value or "").lower().replace("’", "'").split()).strip(" .,!?।:;-\"'")


class AppAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="App Agent",
            description="Opens known desktop and web applications, with verified launches",
        )

    def get_capabilities(self) -> List[str]:
        return ["open_app", "open_folder", "list_apps", "open_youtube", "open_chrome", "open_vscode"]

    @staticmethod
    def _is_cloud() -> bool:
        return bool(getattr(config, "ATLAS_CLOUD", False))

    # ---------------- resolution ----------------
    @staticmethod
    def _resolve(app_name: str) -> Optional[str]:
        token = _norm(app_name)
        if not token:
            return None
        token = token.replace(" app", "").strip()
        if token in APP_TARGETS:
            return token
        if token in EXTRA_ALIASES:
            return EXTRA_ALIASES[token]
        # Try the planner's alias table too, so "yt" / "fb" / Bangla names work.
        try:
            from .smart_planner import APP_ALIASES
            for canonical, aliases in APP_ALIASES.items():
                for alias in (canonical,) + tuple(aliases):
                    if token == _norm(alias) and canonical in APP_TARGETS:
                        return canonical
        except Exception:
            pass
        return None

    def known_apps(self) -> List[str]:
        return sorted(APP_TARGETS)

    # ---------------- launch helpers ----------------
    def _candidates(self, target: Dict[str, Any]) -> List[str]:
        system = platform.system()
        key = "windows" if system == "Windows" else "darwin" if system == "Darwin" else "linux"
        values = target.get(key) or []
        return [str(value) for value in values if value]

    @staticmethod
    def _process_running(names: List[str], timeout: float = 2.0) -> bool:
        if not names or psutil is None:
            return False
        lowered = {name.lower() for name in names if name}
        deadline = time.time() + timeout
        while True:
            try:
                for proc in psutil.process_iter(["name"]):
                    name = str(proc.info.get("name") or "").lower()
                    if name in lowered:
                        return True
            except Exception:
                pass
            if time.time() >= deadline:
                return False
            time.sleep(0.2)

    @staticmethod
    def _find_executable(candidate: str) -> str:
        if not candidate:
            return ""
        expanded = os.path.expandvars(candidate).strip()
        if os.path.isabs(expanded) and os.path.exists(expanded):
            return expanded
        # "Update.exe --processStart Discord.exe" style launcher strings.
        first = expanded.split(" --", 1)[0]
        if os.path.isabs(first) and os.path.exists(first):
            return expanded
        found = shutil.which(expanded)
        if found:
            return found
        return ""

    def _spawn(self, candidate: str) -> bool:
        try:
            if os.name == "nt":
                if candidate.startswith("ms-"):
                    try:
                        os.startfile(candidate)  # type: ignore[attr-defined]
                        return True
                    except Exception:
                        return False
                resolved = self._find_executable(candidate)
                if resolved:
                    # Pass through extra args from launcher strings.
                    if " " in resolved and resolved != candidate:
                        subprocess.Popen(resolved, shell=False)
                    else:
                        subprocess.Popen([resolved])
                    return True
                # Let Windows resolve App Paths (winword.exe, steam.exe, ...).
                subprocess.Popen(["cmd", "/c", "start", "", candidate], shell=False)
                return True
            resolved = self._find_executable(candidate)
            if resolved:
                args = candidate.split() if " " in candidate else [resolved]
                subprocess.Popen(args)
                return True
            args = candidate.split()
            if args:
                subprocess.Popen(args)
                return True
        except Exception:
            return False
        return False

    # ---------------- public actions ----------------
    def open_folder(self, folder: str, command: str = "") -> Dict[str, Any]:
        name = _norm(folder)
        mapping = {
            "download": "Downloads", "downloads": "Downloads",
            "desktop": "Desktop",
            "document": "Documents", "documents": "Documents",
            "picture": "Pictures", "pictures": "Pictures", "photo": "Pictures", "photos": "Pictures",
            "music": "Music",
            "video": "Videos", "videos": "Videos",
        }
        folder_name = mapping.get(name)
        if not folder_name:
            return {"success": False, "action": "open_folder", "agent": "app",
                    "message": tr(command, f"I don't know the folder “{folder}”.",
                                  f"“{folder}” ফোল্ডার চিনি না।")}
        target = Path.home() / folder_name
        if not target.exists():
            return {"success": False, "action": "open_folder", "agent": "app",
                    "message": tr(command, f"The folder {folder_name} does not exist.",
                                  f"{folder_name} ফোল্ডারটি নেই।")}
        if self._is_cloud():
            return {"success": False, "action": "open_folder", "agent": "app",
                    "needs_connector": True,
                    "message": tr(command,
                                  f"📂 Opening {folder_name} is a laptop action. Start the laptop connector, then ask again.",
                                  f"📂 {folder_name} খোলা ল্যাপটপের কাজ। ল্যাপটপ connector চালু করে আবার বলুন।")}
        try:
            if platform.system() == "Windows":
                os.startfile(str(target))  # type: ignore[attr-defined]
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", str(target)])
            else:
                subprocess.Popen(["xdg-open", str(target)])
        except Exception as exc:
            return {"success": False, "action": "open_folder", "agent": "app",
                    "message": tr(command, f"Could not open {folder_name}: {exc}",
                                  f"{folder_name} খোলা যায়নি: {exc}")}
        return {"success": True, "action": "open_folder", "agent": "app",
                "folder": folder_name, "path": str(target),
                "message": tr(command, f"📂 Opened {folder_name}.",
                              f"📂 {folder_name} খোলা হয়েছে।")}

    def open_app(self, app_name: str, command: str = "") -> Dict[str, Any]:
        canonical = self._resolve(app_name)
        if not canonical:
            return {
                "success": False,
                "action": "open_app",
                "agent": "app",
                "message": tr(command,
                              f"I don't have “{app_name}” in my app list. Known apps include: "
                              + ", ".join(self.known_apps()[:18]) + ".",
                              f"“{app_name}” আমার অ্যাপ লিস্টে নেই। পরিচিত অ্যাপ: "
                              + ", ".join(self.known_apps()[:18]) + "।"),
                "known_apps": self.known_apps(),
            }

        target = APP_TARGETS[canonical]

        if target.get("kind") == "web":
            url = target["url"]
            opened = False
            if not self._is_cloud():
                try:
                    opened = bool(webbrowser.open(url))
                except Exception:
                    opened = False
            if opened:
                message = tr(command, f"✅ Opened {canonical.title()}.", f"✅ {canonical} খোলা হয়েছে।")
            else:
                message = tr(command, f"🌐 {canonical.title()} link: {url}",
                             f"🌐 {canonical} লিংক: {url}")
            return {"success": True, "action": "open_app", "agent": "app", "app": canonical,
                    "kind": "web", "url": url, "opened": opened, "verified": opened,
                    "message": message}

        # Desktop app.
        if self._is_cloud():
            return {
                "success": False,
                "action": "open_app",
                "agent": "app",
                "app": canonical,
                "kind": "desktop",
                "needs_connector": True,
                "message": tr(command,
                              f"🖥️ {canonical.title()} is a desktop app. Start the laptop connector on your PC, then ask again.",
                              f"🖥️ {canonical} ডেস্কটপ অ্যাপ। আপনার PC-তে laptop connector চালু করে আবার বলুন।"),
            }

        candidates = self._candidates(target)
        if not candidates:
            return {
                "success": False, "action": "open_app", "agent": "app", "app": canonical,
                "message": tr(command, f"No launcher is configured for {canonical} on this OS.",
                              f"এই OS-এ {canonical} চালু করার কমান্ড নেই।"),
            }

        spawned = False
        used = ""
        for candidate in candidates:
            if self._spawn(candidate):
                spawned = True
                used = candidate
                break
        if not spawned:
            fallback = target.get("fallback_url")
            if fallback:
                opened = False
                try:
                    opened = bool(webbrowser.open(fallback))
                except Exception:
                    opened = False
                return {
                    "success": True, "action": "open_app", "agent": "app", "app": canonical,
                    "kind": "web", "url": fallback, "opened": opened, "verified": opened,
                    "message": tr(command,
                                  f"⚠️ {canonical.title()} is not installed; opened it in the browser instead: {fallback}",
                                  f"⚠️ {canonical} ইনস্টল নেই; ব্রাউজারে খোলা হয়েছে: {fallback}"),
                }
            return {
                "success": False, "action": "open_app", "agent": "app", "app": canonical,
                "message": tr(command, f"Could not launch {canonical}. It may not be installed.",
                              f"{canonical} চালু করা যায়নি। এটি ইনস্টল না-ও থাকতে পারে।"),
                "tried": candidates,
            }

        process_names = target.get("processes") or []
        verified = self._process_running(process_names, timeout=2.0) if process_names else False
        if verified:
            message = tr(command, f"✅ Opened {canonical.title()} (process verified).",
                         f"✅ {canonical} খোলা হয়েছে (প্রসেস যাচাই করা হয়েছে)।")
        else:
            message = tr(command,
                         f"➡️ Launch command sent for {canonical.title()}; it is still starting or uses an existing window.",
                         f"➡️ {canonical} চালু করার কমান্ড পাঠানো হয়েছে; হয়তো এখনো শুরু হচ্ছে বা আগের উইন্ডো ব্যবহার করছে।")
        return {
            "success": True,
            "action": "open_app",
            "agent": "app",
            "app": canonical,
            "kind": "desktop",
            "command": used,
            "verified": verified,
            "message": message,
        }

    def handle(self, intent: str, entities: Dict) -> Dict:
        entities = dict(entities or {})
        command = str(entities.get("_command", ""))
        intent_lower = str(intent or "").lower()
        if intent_lower == "open_folder" or entities.get("folder"):
            return self.open_folder(
                str(entities.get("folder") or entities.get("path") or ""), command
            )
        app_name = str(
            entities.get("app_name") or entities.get("app") or entities.get("query") or ""
        ).strip()
        if not app_name:
            # Extract "open <app>" or "<app> kholo" from the raw command.
            import re
            match = re.match(r"^(?:open|launch|start|run|load)\s+(?:the\s+|my\s+)?(.+)$", command, re.I)
            if not match:
                match = re.match(r"^(.+?)\s+(?:kholo|khol|chalu\s*koro|chalu\s*kor)$", command, re.I)
            if match:
                app_name = match.group(1).strip()
        if not app_name:
            return {"success": False, "action": "open_app", "agent": "app",
                    "message": tr(command, "Which app should I open?",
                                  "কোন অ্যাপ খুলব?")}
        return self.open_app(app_name, command)

    # ---------------- self test ----------------
    def test(self) -> Dict[str, Any]:
        checks = {
            "youtube": self._resolve("youtube") == "youtube",
            "vscode": self._resolve("vs code") == "vscode",
            "bangla_notepad": self._resolve("নোটপ্যাড") == "notepad",
            "unknown_rejected": self._resolve("some random unknown app") is None,
        }
        platform_key = "windows" if platform.system() == "Windows" else "darwin" if platform.system() == "Darwin" else "linux"
        launchable = sum(1 for target in APP_TARGETS.values()
                         if target.get("kind") == "desktop" and target.get(platform_key))
        ok_all = all(checks.values())
        return {
            "success": ok_all,
            "agent": "app",
            "message": f"{len(APP_TARGETS)} apps registered, {launchable} desktop launchers for {platform_key}."
                       + ("" if ok_all else " Resolver check failed."),
            "checks": checks,
            "apps": len(APP_TARGETS),
        }


app_agent = AppAgent()
