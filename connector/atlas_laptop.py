#!/usr/bin/env python
# connector/atlas_laptop.py — run on the laptop so a phone can use PC agents remotely.
#
# Usage:
#   python connector/atlas_laptop.py --server https://your-atlas.hf.space --token <pair-code>
#
# The connector opens one outbound WebSocket. No port forwarding is needed.
# Phone call agents (WhatsApp call / receptionist) always stay on the phone or
# the cloud server; everything else is executed here on the laptop.

from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

try:
    import websockets
except ImportError:
    raise SystemExit("websockets is missing. Run: pip install websockets")

# Windows consoles often default to cp1252; keep emoji logs from crashing.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def log(message: str) -> None:
    try:
        print(message, flush=True)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        print(message.encode(encoding, errors="replace").decode(encoding, errors="replace"), flush=True)


def ws_url(server: str, token: str, name: str) -> str:
    base = server.strip().rstrip("/")
    if base.startswith("https://"):
        base = "wss://" + base[len("https://"):]
    elif base.startswith("http://"):
        base = "ws://" + base[len("http://"):]
    elif not base.startswith(("ws://", "wss://")):
        base = "ws://" + base
    return f"{base}/api/connector/ws?token={quote(token)}&name={quote(name)}"


async def run(server: str, token: str, name: str) -> None:
    url = ws_url(server, token, name)
    log(f"🔗 Atlas laptop connector → {server}")
    log(f"   device: {name}")

    from command_handler import get_command_response

    delay = 2
    while True:
        try:
            async with websockets.connect(url, ping_interval=20, ping_timeout=20, max_size=16_000_000) as socket:
                log("✅ Connected. Waiting for commands from the phone...")
                delay = 2
                async for raw in socket:
                    try:
                        message = json.loads(raw)
                    except Exception:
                        continue
                    if not isinstance(message, dict):
                        continue
                    if message.get("type") != "command":
                        continue

                    req_id = message.get("id")
                    command = str(message.get("command", ""))
                    platform_name = str(message.get("platform", "desktop"))
                    log(f"📥 {command}")

                    try:
                        result = await asyncio.to_thread(
                            get_command_response, command, platform_name
                        )
                        payload = {
                            "type": "result",
                            "id": req_id,
                            "success": True,
                            "result": result,
                        }
                    except Exception as exc:
                        payload = {
                            "type": "result",
                            "id": req_id,
                            "success": False,
                            "error": str(exc),
                        }

                    await socket.send(json.dumps(payload, ensure_ascii=False, default=str))
                    if payload.get("success"):
                        summary = str((payload.get("result") or {}).get("response", ""))[:100]
                    else:
                        summary = str(payload.get("error", ""))[:100]
                    log(f"📤 {summary}")
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            log(f"⚠️  Disconnected: {exc}. Retrying in {delay}s...")
            await asyncio.sleep(delay)
            delay = min(delay * 2, 30)


def main() -> None:
    parser = argparse.ArgumentParser(description="Atlas 7 laptop connector")
    parser.add_argument("--server", default=os.getenv("ATLAS_SERVER", "http://localhost:8000"),
                        help="Atlas cloud server URL, e.g. https://user-atlas.hf.space")
    parser.add_argument("--token", default=os.getenv("ATLAS_PAIR_TOKEN", ""),
                        help="Pairing code from Atlas → Settings → Server connection")
    parser.add_argument("--name", default=os.getenv("ATLAS_LAPTOP_NAME", platform.node() or "laptop"),
                        help="Name shown in the Agent panel")
    args = parser.parse_args()

    if not args.token:
        raise SystemExit(
            "Pairing token missing. Open Atlas → Settings → Server connection to see "
            "the code, or set ATLAS_PAIR_TOKEN."
        )

    try:
        asyncio.run(run(args.server, args.token, args.name))
    except KeyboardInterrupt:
        log("\n👋 Connector stopped.")


if __name__ == "__main__":
    main()
