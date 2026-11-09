"""Capture Atlas dashboard screenshots + demo GIF using headless Chrome (CDP).

Run from the project root:
    python tools/capture_demo.py
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import websockets

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "demo"
# Production build served by the backend is lighter and is what a user sees.
# Set ATLAS_DEMO_URL=http://localhost:5173/ to capture from the Vite dev server.
URL = os.environ.get("ATLAS_DEMO_URL", "http://localhost:8000/")
PORT = 9223
WIDTH, HEIGHT = 1600, 1000

# Freeze only looping animations (reactor rings, spinners). One-shot
# entrance animations such as jvPop / jvFadeUp must keep running, otherwise
# the panel and chat messages stay stuck at opacity 0.
FREEZE_JS = """
(() => {
  document.querySelectorAll('*').forEach(el => {
    const count = getComputedStyle(el).animationIterationCount || '';
    if (count.split(',').some(v => v.trim() === 'infinite')) {
      el.style.animationPlayState = 'paused';
    }
  });
  return true;
})()
"""

QUIET_CSS = """
*, *::before, *::after {
  transition: none !important;
  caret-color: transparent !important;
}
"""

CHROME_CANDIDATES = [
    Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
    Path(os.environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe",
    Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google/Chrome/Application/chrome.exe",
    Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft/Edge/Application/msedge.exe",
    Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft/Edge/Application/msedge.exe",
    Path("/usr/bin/google-chrome"),
    Path("/usr/bin/chromium"),
    Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
]


def find_browser() -> Path:
    for path in CHROME_CANDIDATES:
        if path and path.exists():
            return path
    raise SystemExit("Chrome/Edge not found. Install Chrome or edit CHROME_CANDIDATES.")


class CDP:
    def __init__(self, ws) -> None:
        self.ws = ws
        self.next_id = 0

    async def send(self, method: str, params: dict | None = None):
        self.next_id += 1
        message_id = self.next_id
        await self.ws.send(json.dumps({"id": message_id, "method": method, "params": params or {}}))
        while True:
            message = json.loads(await self.ws.recv())
            if message.get("id") == message_id:
                if "error" in message:
                    raise RuntimeError(f"{method}: {message['error']}")
                return message.get("result", {})

    async def eval(self, script: str):
        result = await self.send(
            "Runtime.evaluate",
            {"expression": script, "returnByValue": True, "awaitPromise": True},
        )
        return result.get("result", {}).get("value")

    async def wait_for(self, script: str, timeout: float = 30.0, label: str = "") -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                if await self.eval(script):
                    return True
            except Exception:
                pass
            await asyncio.sleep(0.4)
        print(f"  ! timed out waiting for {label or script[:60]}")
        return False

    async def shot(self, name: str) -> Path:
        result = await self.send(
            "Page.captureScreenshot",
            {"format": "png", "fromSurface": True, "captureBeyondViewport": False},
        )
        path = OUT / name
        path.write_bytes(base64.b64decode(result["data"]))
        print(f"  captured {name} ({path.stat().st_size / 1024:.0f} KB)")
        return path


async def connect_page() -> CDP:
    for _ in range(80):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/list", timeout=1) as response:
                tabs = json.loads(response.read().decode("utf-8"))
            pages = [tab for tab in tabs if tab.get("type") == "page"]
            if pages:
                return CDP(await websockets.connect(pages[0]["webSocketDebuggerUrl"], max_size=None))
        except Exception:
            pass
        await asyncio.sleep(0.25)
    raise SystemExit("Could not connect to headless browser.")


async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    browser = find_browser()
    profile = Path(tempfile.mkdtemp(prefix="atlas-demo-"))
    print(f"browser: {browser}")
    process = subprocess.Popen(
        [
            str(browser),
            "--headless=new",
            f"--remote-debugging-port={PORT}",
            f"--user-data-dir={profile}",
            "--remote-allow-origins=*",
            f"--window-size={WIDTH},{HEIGHT}",
            "--hide-scrollbars",
            "--force-device-scale-factor=1",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions",
            URL,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    cdp = await connect_page()
    try:
        await cdp.send("Page.enable")
        await cdp.send("Runtime.enable")
        await cdp.send(
            "Emulation.setDeviceMetricsOverride",
            {
                "width": WIDTH,
                "height": HEIGHT,
                "deviceScaleFactor": 1,
                "mobile": False,
                "screenWidth": WIDTH,
                "screenHeight": HEIGHT,
            },
        )
        await cdp.send("Page.navigate", {"url": URL})

        print("waiting for the dashboard...")
        await cdp.wait_for("document.readyState === 'complete'", 30, "page load")
        await cdp.wait_for(
            "document.body.innerText.includes('System online')",
            30,
            "system online",
        )
        # Stop the looping HUD animations before they make the CPU graph look busy.
        await cdp.eval(
            "(() => {"
            "  const style = document.createElement('style');"
            "  style.id = 'atlas-demo-quiet';"
            f"  style.textContent = {json.dumps(QUIET_CSS)};"
            "  document.head.appendChild(style);"
            "  return true;"
            "})()"
        )
        await cdp.eval(FREEZE_JS)
        await asyncio.sleep(8)

        print("1/5 dashboard")
        await cdp.shot("01-dashboard.png")

        print("2/5 agent panel")
        await cdp.eval("document.querySelector('[aria-label=\"Agent control\"]')?.click(); true")
        await cdp.wait_for("document.body.innerText.includes('AGENT CONTROL')", 10, "agent panel")
        await asyncio.sleep(0.8)
        await cdp.shot("02-agent-panel.png")

        print("3/5 call agents tab")
        await cdp.eval(
            """
            (() => {
              const btn = [...document.querySelectorAll('button')]
                .find(b => b.innerText.trim().startsWith('Call 2'));
              btn?.click();
              return !!btn;
            })()
            """
        )
        await asyncio.sleep(0.7)
        await cdp.shot("03-call-agents.png")

        print("4/5 WhatsApp agent detail")
        await cdp.eval(
            """
            (() => {
              const details = [...document.querySelectorAll('button[title="Details"]')];
              const target = details.find(btn => {
                let node = btn;
                for (let i = 0; i < 6 && node; i += 1) {
                  if ((node.innerText || '').includes('WhatsApp Call Agent')) return true;
                  node = node.parentElement;
                }
                return false;
              });
              target?.click();
              return !!target;
            })()
            """
        )
        await asyncio.sleep(3.0)
        await cdp.shot("04-agent-detail.png")

        print("5/5 chat command")
        await cdp.eval(
            """
            (() => {
              const close = document.querySelector('button[title="Close"]');
              close?.click();
              const input = document.querySelector('[aria-label="Message Atlas"]');
              input?.focus();
              return !!input;
            })()
            """
        )
        await asyncio.sleep(0.5)
        await cdp.send("Input.insertText", {"text": "system status"})
        await asyncio.sleep(0.3)
        await cdp.eval("document.querySelector('[aria-label=\"Send message\"]')?.click(); true")
        replied = await cdp.wait_for(
            "document.body.innerText.toLowerCase().includes('system status (windows)') || "
            "document.body.innerText.toLowerCase().includes('battery:')",
            150,
            "agent reply",
        )
        await asyncio.sleep(1.5)
        body = (await cdp.eval("document.body.innerText") or "").lower()
        if "server unreachable" in body or "connection" in body and "error" in body:
            print("  ! the chat shows a connection error; check the backend")
        elif not replied:
            print("  ! continuing without a confirmed agent reply")
        await cdp.shot("05-chat-command.png")

        print("done")
    finally:
        try:
            await cdp.ws.close()
        except Exception:
            pass
        process.terminate()
        try:
            process.wait(timeout=10)
        except Exception:
            process.kill()


if __name__ == "__main__":
    asyncio.run(main())
