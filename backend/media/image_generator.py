# backend/media/image_generator.py — text-to-image via pollinations.ai (free, no key)

import re
import time
from pathlib import Path
from urllib.parse import quote

import requests

import config

_MEDIA = config.DOWNLOADS_DIR / "media" / "generated"


class ImageGenerator:
    def __init__(self):
        _MEDIA.mkdir(parents=True, exist_ok=True)

    def generate(self, prompt: str, size: str = "1024x1024"):
        prompt = (prompt or "").strip()
        if not prompt:
            raise ValueError("prompt required")

        width, height = self._parse_size(size)
        url = (
            f"https://image.pollinations.ai/prompt/{quote(prompt)}"
            f"?width={width}&height={height}&nologo=true&seed={int(time.time()) % 100000}"
        )
        try:
            resp = requests.get(url, timeout=90)
            if resp.status_code != 200 or not resp.content:
                return {"success": False, "error": f"image service returned {resp.status_code}"}
        except Exception as e:
            return {"success": False, "error": f"image generation failed: {type(e).__name__}"}

        slug = re.sub(r"[^a-z0-9]+", "-", prompt.lower())[:40].strip("-") or "image"
        target = _MEDIA / f"{slug}_{int(time.time())}.png"
        target.write_bytes(resp.content)
        return {"success": True, "path": str(target), "prompt": prompt, "size": f"{width}x{height}", "url": url}

    @staticmethod
    def _parse_size(size):
        match = re.fullmatch(r"(\d{2,4})x(\d{2,4})", str(size or ""))
        if not match:
            return 1024, 1024
        return int(match.group(1)), int(match.group(2))


image_generator = ImageGenerator()
