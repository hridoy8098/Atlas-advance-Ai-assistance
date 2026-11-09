# backend/media/podcast_creator.py — script to speech with edge-tts

import asyncio
import re
from datetime import datetime
from pathlib import Path

import config

_MEDIA = config.DOWNLOADS_DIR / "media" / "podcasts"
_BN = re.compile(r"[\u0980-\u09FF]")


class PodcastCreator:
    def create(self, script: str, voice: str = None, out: str = None):
        script = (script or "").strip()
        if not script:
            raise ValueError("script required")
        try:
            import edge_tts
        except ImportError:
            return {"success": False, "error": "edge-tts not installed (pip install edge-tts)"}

        voice = voice or ("bn-BD-NabanitaNeural" if _BN.search(script) else "en-US-AriaNeural")
        _MEDIA.mkdir(parents=True, exist_ok=True)
        target = Path(out) if out else _MEDIA / f"podcast_{datetime.now():%Y%m%d_%H%M%S}.mp3"

        async def _run():
            await edge_tts.Communicate(script, voice).save(str(target))

        try:
            asyncio.run(_run())
        except Exception as e:
            return {"success": False, "error": f"{type(e).__name__}: {e}"}

        if not target.exists():
            return {"success": False, "error": "audio file was not created"}
        return {
            "success": True,
            "path": str(target),
            "voice": voice,
            "chars": len(script),
            "size_kb": round(target.stat().st_size / 1024, 1),
        }


podcast_creator = PodcastCreator()
