# backend/connector/connector_manager.py — outbound laptop connection for cloud relay.
#
# Architecture:
#   phone  ->  cloud Atlas server  ->  WebSocket  ->  laptop connector
#
# The laptop opens one outbound WebSocket, so it works behind NAT and on mobile
# networks without port forwarding. The cloud server forwards any non-phone
# command to the laptop and returns the laptop's JSON result to the phone.

from __future__ import annotations

import asyncio
import json
import os
import secrets
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import config

PAIRING_FILE: Path = config.DATA_DIR / "pairing.json"
DEFAULT_TIMEOUT = 120.0


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _load_pairing() -> Dict[str, Any]:
    try:
        with open(PAIRING_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and data.get("token"):
            return data
    except Exception:
        pass
    token = secrets.token_urlsafe(18)
    data = {"token": token, "created_at": _now()}
    try:
        PAIRING_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(PAIRING_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return data


class ConnectorManager:
    def __init__(self) -> None:
        self._socket = None
        self._lock = asyncio.Lock()
        self._pending: Dict[str, asyncio.Future] = {}
        self.name = ""
        self.connected_at: Optional[str] = None
        self.last_seen: Optional[str] = None
        self.last_error = ""
        self._pairing = _load_pairing()
        self.token = os.getenv("ATLAS_PAIR_TOKEN", "") or self._pairing.get("token", "")

    # ---------------- pairing ----------------

    @property
    def token_from_env(self) -> bool:
        return bool(os.getenv("ATLAS_PAIR_TOKEN", ""))

    def check_token(self, token: str) -> bool:
        return bool(self.token) and secrets.compare_digest(str(token), str(self.token))

    # ---------------- connection ----------------

    @property
    def connected(self) -> bool:
        return self._socket is not None

    async def attach(self, socket, name: str = "laptop") -> None:
        async with self._lock:
            self._socket = socket
            self.name = (name or "laptop").strip()[:64]
            self.connected_at = _now()
            self.last_seen = self.connected_at
            self.last_error = ""
        print(f"🔗 Laptop connector attached: {self.name}")

    async def detach(self, socket=None) -> None:
        async with self._lock:
            if socket is not None and self._socket is not socket:
                return
            self._socket = None
            self.name = ""
            self.connected_at = None
            for fut in self._pending.values():
                if not fut.done():
                    fut.cancel()
            self._pending.clear()
        print("🔌 Laptop connector detached")

    def handle_message(self, raw: str) -> None:
        try:
            data = json.loads(raw)
        except Exception:
            return
        if not isinstance(data, dict):
            return
        req_id = str(data.get("id", ""))
        future = self._pending.get(req_id)
        if future and not future.done():
            future.set_result(data)
        self.last_seen = _now()

    async def execute(
        self,
        command: str,
        platform: str = "desktop",
        timeout: float = DEFAULT_TIMEOUT,
    ) -> Optional[Dict[str, Any]]:
        socket = self._socket
        if socket is None:
            return None

        req_id = uuid.uuid4().hex
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        self._pending[req_id] = future
        try:
            await socket.send_text(json.dumps({
                "type": "command",
                "id": req_id,
                "command": command,
                "platform": platform,
                "sent_at": _now(),
            }, ensure_ascii=False))
            data = await asyncio.wait_for(future, timeout=timeout)
            if data.get("success"):
                result = data.get("result")
                if isinstance(result, dict):
                    return result
            self.last_error = str(data.get("error") or "Laptop could not run the command")
            return {
                "response": f"⚠️ Laptop: {self.last_error}",
                "success": False,
                "action": "laptop_error",
                "agent": "laptop_connector",
            }
        except asyncio.TimeoutError:
            self.last_error = "Laptop did not answer in time"
            return {
                "response": "⚠️ Laptop সময়মতো উত্তর দেয়নি। Laptop চালু এবং connector চলছে কি?",
                "success": False,
                "action": "laptop_timeout",
                "agent": "laptop_connector",
            }
        except Exception as exc:
            self.last_error = str(exc)
            import traceback
            traceback.print_exc()
            return {
                "response": f"⚠️ Laptop connector error: {exc}",
                "success": False,
                "action": "laptop_error",
                "agent": "laptop_connector",
            }
        finally:
            self._pending.pop(req_id, None)

    def status(self) -> Dict[str, Any]:
        return {
            "success": True,
            "connected": self.connected,
            "name": self.name,
            "connected_at": self.connected_at,
            "last_seen": self.last_seen,
            "last_error": self.last_error,
            "pairing_configured": bool(self.token),
            "pairing_from_env": self.token_from_env,
            "relay_enabled": os.getenv("ATLAS_CLOUD", "0") == "1",
        }


PHONE_ONLY_KEYWORDS = (
    "whatsapp", "হোয়াটসঅ্যাপ", "receptionist", "রিসেপশনিস্ট",
    "busy mode", "বিজি মোড", "call inbox", "simulate call",
    "test call", "call summary", "call list", "কল সামারি",
    "কল লিস্ট", "callback", "কলব্যাক",
)


def is_phone_only(command: str) -> bool:
    text = str(command or "").lower()
    return any(word in text for word in PHONE_ONLY_KEYWORDS)


connector_manager = ConnectorManager()
