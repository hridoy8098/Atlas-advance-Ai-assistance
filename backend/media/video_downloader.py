# backend/media/video_downloader.py — yt-dlp wrapper

import importlib.util
from pathlib import Path

import config

_MEDIA = config.DOWNLOADS_DIR / "media"


class VideoDownloader:
    def available(self):
        return importlib.util.find_spec("yt_dlp") is not None

    def download(self, url: str, out_dir: str = None, audio_only: bool = False):
        if not url or not url.lower().startswith(("http://", "https://")):
            raise ValueError("valid URL required")
        if not self.available():
            return {"success": False, "error": "yt-dlp not installed (pip install yt-dlp)"}

        import yt_dlp

        target_dir = Path(out_dir) if out_dir else _MEDIA / "downloads"
        target_dir.mkdir(parents=True, exist_ok=True)
        options = {
            "outtmpl": str(target_dir / "%(title).80s.%(ext)s"),
            "format": "bestaudio[ext=m4a]/bestaudio/best" if audio_only else "best[height<=1080]/best",
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
        }
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=True)
                path = ydl.prepare_filename(info)
            return {
                "success": True,
                "path": path,
                "title": info.get("title"),
                "duration": info.get("duration"),
            }
        except Exception as e:
            return {"success": False, "error": f"{type(e).__name__}: {e}"}


video_downloader = VideoDownloader()
