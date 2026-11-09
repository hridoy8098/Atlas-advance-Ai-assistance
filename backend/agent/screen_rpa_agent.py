# backend/agent/screen_rpa_agent.py — Screen Vision RPA Agent
# Screenshot/vision analysis plus safe mouse-keyboard automation.
from __future__ import annotations

import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import config
from .advanced_common import fail, ok, truncate

try:
    import pyautogui  # type: ignore
except Exception:  # pragma: no cover - headless environments
    pyautogui = None

try:
    import pyperclip  # type: ignore
except Exception:  # pragma: no cover
    pyperclip = None


class ScreenRPAAgent:
    name = "Screen Vision RPA Agent"

    def get_capabilities(self) -> List[str]:
        return [
            "screen_capture", "screen_analyze", "screen_click", "screen_type",
            "screen_hotkey", "screen_scroll", "screen_locate", "screen_size",
        ]

    def handle(self, intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        entities = entities or {}
        command = str(entities.get("_command", ""))
        intent_lower = str(intent or "").lower()

        if pyautogui is None:
            return fail("screen_rpa", "pyautogui পাওয়া যায়নি। `pip install pyautogui` দরকার।")

        try:
            if "size" in intent_lower:
                return self.size()
            if "analyze" in intent_lower or "vision" in intent_lower or "dekho" in command.lower():
                return self.analyze(str(entities.get("prompt") or command))
            if "click" in intent_lower or "click" in command.lower():
                point = self._parse_point(command, entities)
                if not point:
                    return fail("screen_rpa", "Click-এর জন্য coordinate দিন, যেমন: “click 500 800”।")
                return self.click(point[0], point[1])
            if "type" in intent_lower or "likho" in command.lower() or "lekho" in command.lower():
                text = str(entities.get("text") or self._quoted(command))
                if not text:
                    return fail("screen_rpa", "Type করার text দিন (quote করে), যেমন: “type koro ‘Hello’”。")
                return self.type_text(text)
            if "hotkey" in intent_lower or "shortcut" in intent_lower:
                keys = self._parse_keys(str(entities.get("keys") or command))
                if not keys:
                    return fail("screen_rpa", "Keys দিন, যেমন: “hotkey ctrl+s”।")
                return self.hotkey(keys)
            if "scroll" in intent_lower:
                amount = int(entities.get("amount") or self._first_number(command) or -500)
                return self.scroll(amount)
            if "locate" in intent_lower or "find image" in command.lower():
                image = str(entities.get("image") or self._quoted(command))
                return self.locate(image)
            if "capture" in intent_lower or "screenshot" in intent_lower or "screenshot" in command.lower():
                return self.capture()
            return self.capture()
        except Exception as exc:
            return fail("screen_rpa", f"Screen RPA error: {exc}")

    # ---------------- actions ----------------
    def capture(self) -> Dict[str, Any]:
        folder = config.DATA_DIR / "screen_rpa"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"screen-{datetime.now().strftime('%Y%m%d-%H%M%S')}.png"
        image = pyautogui.screenshot()
        image.save(path)
        return ok(
            "screen_rpa",
            f"📸 Screenshot saved: {path}",
            path=str(path),
            size=f"{image.width}x{image.height}",
        )

    def analyze(self, prompt: str = "") -> Dict[str, Any]:
        image = pyautogui.screenshot()
        folder = config.DATA_DIR / "screen_rpa"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"vision-{datetime.now().strftime('%Y%m%d-%H%M%S')}.png"
        image.save(path)

        import io
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        try:
            from backend.core.ai_engine import ai_engine
            description = ai_engine.chat_vision(
                buffer.getvalue(),
                prompt=(prompt or "Describe this screen. What is the user doing and what is a safe next action?"),
            ) or ""
        except Exception as exc:
            description = ""
            error = str(exc)
        else:
            error = ""

        if not description:
            return ok(
                "screen_rpa",
                "Screenshot নেওয়া হয়েছে; vision AI এখন unavailable।",
                path=str(path),
                error=error or None,
                hint="Screenshot Review pane-এ খুলে দেখুন।",
            )
        return ok("screen_rpa", "🖼️ Screen analyzed.", path=str(path), description=truncate(description, 4000))

    def click(self, x: int, y: int) -> Dict[str, Any]:
        width, height = pyautogui.size()
        x, y = int(x), int(y)
        if not (0 <= x <= width and 0 <= y <= height):
            return fail("screen_rpa", f"Coordinate screen-এর বাইরে ({x},{y}); screen {width}x{height}।")
        pyautogui.moveTo(x, y, duration=0.2)
        pyautogui.click()
        return ok("screen_rpa", f"🖱️ Clicked ({x}, {y}).", x=x, y=y)

    def type_text(self, text: str) -> Dict[str, Any]:
        text = str(text or "")[:4000]
        if not text:
            return fail("screen_rpa", "Type করার text খালি।")

        # pyautogui cannot type Bangla/Unicode directly; clipboard paste handles it.
        if pyperclip is not None and any(ord(char) > 127 for char in text):
            old = None
            try:
                old = pyperclip.paste()
            except Exception:
                old = None
            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.2)
            if old is not None:
                try:
                    pyperclip.copy(old)
                except Exception:
                    pass
            return ok("screen_rpa", "⌨️ Typed text via clipboard paste.", length=len(text), method="clipboard")

        pyautogui.write(text, interval=0.02)
        return ok("screen_rpa", "⌨️ Typed text.", length=len(text), method="keyboard")

    def hotkey(self, keys: List[str]) -> Dict[str, Any]:
        pyautogui.hotkey(*keys)
        return ok("screen_rpa", f"⌨️ Hotkey: {'+'.join(keys)}", keys=keys)

    def scroll(self, amount: int) -> Dict[str, Any]:
        pyautogui.scroll(int(amount))
        return ok("screen_rpa", f"🖱️ Scrolled {amount}.", amount=int(amount))

    def locate(self, image_path: str) -> Dict[str, Any]:
        path = Path(str(image_path or "")).expanduser()
        if not path.exists():
            return fail("screen_rpa", "Template image পাওয়া যায়নি। image path দিন।")
        try:
            box = pyautogui.locateOnScreen(str(path), confidence=0.8)
        except Exception as exc:
            return fail("screen_rpa", f"Image locate failed: {exc}")
        if not box:
            return fail("screen_rpa", "Screen-এ template image পাওয়া যায়নি।")
        center = pyautogui.center(box)
        return ok("screen_rpa", f"🎯 Found at {center.x},{center.y}.", x=center.x, y=center.y, box=list(box))

    def size(self) -> Dict[str, Any]:
        width, height = pyautogui.size()
        return ok("screen_rpa", f"🖥️ Screen size: {width}x{height}.", width=width, height=height)

    def test(self) -> Dict[str, Any]:
        if pyautogui is None:
            return {"success": False, "agent": "screen_rpa", "message": "pyautogui not installed"}
        width, height = pyautogui.size()
        return {
            "success": True,
            "agent": "screen_rpa",
            "screen": f"{width}x{height}",
            "clipboard": pyperclip is not None,
            "message": "Screen RPA ready.",
        }

    # ---------------- helpers ----------------
    @staticmethod
    def _parse_point(command: str, entities: Dict[str, Any]) -> Optional[Tuple[int, int]]:
        x = entities.get("x")
        y = entities.get("y")
        if x is not None and y is not None:
            return int(x), int(y)
        match = re.search(r"(-?\d{1,5})\s*[, ]\s*(-?\d{1,5})", command)
        if match:
            return int(match.group(1)), int(match.group(2))
        return None

    @staticmethod
    def _first_number(command: str) -> Optional[int]:
        match = re.search(r"-?\d{1,5}", str(command or ""))
        return int(match.group(0)) if match else None

    @staticmethod
    def _quoted(command: str) -> str:
        match = re.search(r"[\"“”'‘’]([^\"“”'‘’]{1,4000})[\"“”'‘’]", str(command or ""))
        return match.group(1).strip() if match else ""

    @staticmethod
    def _parse_keys(command: str) -> List[str]:
        match = re.search(r"(?:hotkey|shortcut)\s+([a-z0-9+\-\s]+)$", command, flags=re.I)
        raw = match.group(1) if match else command
        keys = [part.strip().lower() for part in re.split(r"[+\s]+", raw) if part.strip()]
        return keys[:5]


screen_rpa_agent = ScreenRPAAgent()
