# backend/agent/media_agent.py — real media actions.
#
# Image generation via pollinations.ai, memes via Pillow, local music playback
# via pygame, YouTube search/info and optional downloads via yt-dlp. Browser
# and audio output are laptop-only; on the cloud server the reply carries a
# clickable link instead of pretending to open something.

from __future__ import annotations

import re
import webbrowser
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import quote

import config
from backend.media.background_remover import background_remover
from backend.media.image_generator import image_generator
from backend.media.meme_generator import meme_generator
from backend.media.music_player import music_player
from backend.media.subtitle_gen import subtitle_generator
from backend.media.video_downloader import video_downloader
from backend.study.youtube_ai import youtube_ai
from .advanced_common import clean_text, extract_quoted, find_existing_path, truncate
from .agent_i18n import is_bengali, tr
from .base_agent import BaseAgent

_YT_URL_RE = re.compile(r"https?://(?:www\.)?(?:youtube\.com|youtu\.be)/[^\s<>\"']+", re.I)


def _extract_url(text: str) -> str:
    match = _YT_URL_RE.search(text or "")
    if match:
        return match.group(0).rstrip(".,;!?।")
    generic = re.search(r"https?://[^\s<>\"']+", text or "", re.I)
    return generic.group(0).rstrip(".,;!?।") if generic else ""


class MediaAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Media Agent",
            description="YouTube, images, memes, music playback, subtitles and media downloads",
        )

    def get_capabilities(self) -> List[str]:
        return [
            "media_youtube", "media_image", "media_meme", "media_music",
            "media_download", "media_subtitle", "media_background_remove",
        ]

    # ---------------- browser / cloud helpers ----------------
    @staticmethod
    def _is_cloud() -> bool:
        return bool(getattr(config, "ATLAS_CLOUD", False))

    def _open(self, url: str) -> bool:
        if self._is_cloud():
            return False
        try:
            return bool(webbrowser.open(url))
        except Exception:
            return False

    # ---------------- YouTube ----------------
    def youtube_search(self, query: str, command: str = "") -> Dict[str, Any]:
        query = clean_text(query)
        if not query:
            return {"success": False, "action": "media_youtube", "agent": "media",
                    "message": tr(command, "What should I search on YouTube?", "ইউটিউবে কী খুঁজব?")}
        url = f"https://www.youtube.com/results?search_query={quote(query)}"
        opened = self._open(url)
        if opened:
            message = tr(command, f"🎬 Searching YouTube: {query}", f"🎬 ইউটিউবে খোঁজা হচ্ছে: {query}")
        else:
            message = tr(command, f"🎬 YouTube results for “{query}”: {url}",
                         f"🎬 “{query}” এর ইউটিউব ফলাফল: {url}")
        return {"success": True, "action": "media_youtube", "agent": "media",
                "message": message, "query": query, "url": url, "opened": opened}

    def youtube_info(self, url_or_query: str, command: str = "") -> Dict[str, Any]:
        target = clean_text(url_or_query)
        url = _extract_url(target)
        if not url:
            return self.youtube_search(target, command)
        info = youtube_ai.info(url)
        if not info.get("available"):
            return self.youtube_search(target, command)
        return {"success": True, "action": "media_youtube", "agent": "media",
                "message": tr(command,
                              f"🎬 {info.get('title')} — {info.get('author')}\n{url}",
                              f"🎬 {info.get('title')} — {info.get('author')}\n{url}"),
                "url": url, "title": info.get("title"), "author": info.get("author"),
                "thumbnail": info.get("thumbnail")}

    # ---------------- images ----------------
    def generate_image(self, prompt: str, size: str = "1024x1024", command: str = "") -> Dict[str, Any]:
        prompt = clean_text(prompt)
        if not prompt:
            return {"success": False, "action": "media_image", "agent": "media",
                    "message": tr(command, "What image should I generate? Example: “generate image of a cat astronaut”.",
                                  "কী ছবি বানাব? উদাহরণ: “generate image of a cat astronaut”।")}
        try:
            result = image_generator.generate(prompt, size=size)
        except Exception as exc:
            return {"success": False, "action": "media_image", "agent": "media",
                    "message": tr(command, f"Image generation failed: {exc}", f"ছবি বানানো যায়নি: {exc}")}
        if not result.get("success"):
            return {"success": False, "action": "media_image", "agent": "media",
                    "message": tr(command, f"Image generation failed: {result.get('error')}",
                                  f"ছবি বানানো যায়নি: {result.get('error')}")}
        link = result.get("url") or result.get("path", "")
        message = tr(command, f"🎨 Image ready: {link}", f"🎨 ছবি তৈরি: {link}")
        return {"success": True, "action": "media_image", "agent": "media",
                "message": message, "prompt": prompt, "path": result.get("path"),
                "url": result.get("url"), "size": result.get("size")}

    def generate_meme(self, top: str = "", bottom: str = "", prompt: str = "",
                      image_path: str = "", command: str = "") -> Dict[str, Any]:
        source = image_path or ""
        if not source:
            found = find_existing_path(command)
            if found and found.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
                source = str(found)
        if not source:
            # No image supplied: generate a base image from the prompt first.
            base_prompt = clean_text(prompt) or "funny reaction meme background"
            generated = image_generator.generate(base_prompt, size="1024x1024")
            if not generated.get("success"):
                return {"success": False, "action": "media_meme", "agent": "media",
                        "message": tr(command,
                                      "Meme needs an image or a working image generator. Example: “meme top: hello | bottom: world”.",
                                      "মিমের জন্য ছবি দরকার। উদাহরণ: “meme top: hello | bottom: world”।")}
            source = generated.get("path", "")
        try:
            result = meme_generator.make(source, top=top, bottom=bottom)
        except Exception as exc:
            return {"success": False, "action": "media_meme", "agent": "media",
                    "message": tr(command, f"Meme creation failed: {exc}", f"মিম বানানো যায়নি: {exc}")}
        if not result.get("success"):
            return {"success": False, "action": "media_meme", "agent": "media",
                    "message": tr(command, f"Meme creation failed: {result.get('error')}",
                                  f"মিম বানানো যায়নি: {result.get('error')}")}
        return {"success": True, "action": "media_meme", "agent": "media",
                "message": tr(command, f"😂 Meme ready: {result['output']}", f"😂 মিম তৈরি: {result['output']}"),
                "path": result["output"], "top": top, "bottom": bottom}

    def remove_background(self, image_path: str, command: str = "") -> Dict[str, Any]:
        source = image_path or ""
        if not source:
            found = find_existing_path(command)
            source = str(found) if found else ""
        if not source:
            return {"success": False, "action": "media_background_remove", "agent": "media",
                    "message": tr(command, "Which image should I process? Give the file path.",
                                  "কোন ছবির background সরাব? ফাইলের path দিন।")}
        try:
            result = background_remover.remove(source)
        except Exception as exc:
            return {"success": False, "action": "media_background_remove", "agent": "media",
                    "message": tr(command, f"Background removal failed: {exc}", f"Background সরানো যায়নি: {exc}")}
        if not result.get("success"):
            return {"success": False, "action": "media_background_remove", "agent": "media",
                    "message": tr(command, f"Background removal failed: {result.get('error')}",
                                  f"Background সরানো যায়নি: {result.get('error')}")}
        return {"success": True, "action": "media_background_remove", "agent": "media",
                "message": tr(command, f"✂️ Background removed: {result['output']}",
                              f"✂️ Background সরানো হয়েছে: {result['output']}"),
                "path": result["output"], "removed_pixels": result.get("removed_pixels")}

    # ---------------- music ----------------
    def play_music(self, query: str = "", command: str = "") -> Dict[str, Any]:
        if self._is_cloud():
            return {"success": False, "action": "media_music", "agent": "media",
                    "message": tr(command,
                                  "🔊 Music playback is a laptop action. Start the laptop connector, then ask again.",
                                  "🔊 গান বাজানো ল্যাপটপের কাজ। ল্যাপটপ connector চালু করে আবার বলুন।"),
                    "needs_connector": True}
        tracks = music_player.library()
        if not tracks:
            return {"success": False, "action": "media_music", "agent": "media",
                    "message": tr(command,
                                  "🎵 No music found. Put MP3 files in your Music folder or data/downloads/media/music.",
                                  "🎵 কোনো গান পাওয়া যায়নি। Music ফোল্ডারে বা data/downloads/media/music-এ MP3 রাখুন।"),
                    "tracks": 0}

        chosen = None
        needle = clean_text(query).lower()
        if needle:
            chosen = next((track for track in tracks if needle in track["name"].lower()), None)
        if not chosen:
            chosen = tracks[0]
        result = music_player.play(chosen["path"])
        if not result.get("playing"):
            return {"success": False, "action": "media_music", "agent": "media",
                    "message": tr(command, f"Music player failed: {result.get('error')}",
                                  f"মিউজিক প্লেয়ার চালু হয়নি: {result.get('error')}"),
                    "error": result.get("error")}
        return {"success": True, "action": "media_music", "agent": "media",
                "message": tr(command, f"🎵 Playing: {result.get('track')}", f"🎵 বাজছে: {result.get('track')}"),
                "track": result.get("track"), "path": result.get("path"), "tracks": len(tracks)}

    def control_music(self, action: str, command: str = "") -> Dict[str, Any]:
        if action == "pause":
            result = music_player.pause()
        elif action == "resume":
            result = music_player.resume()
        elif action == "stop":
            result = music_player.stop()
        else:
            result = music_player.status()
        message = tr(command, {
            "pause": "⏸️ Music paused.",
            "resume": "▶️ Music resumed.",
            "stop": "⏹️ Music stopped.",
            "status": "🎵 Music player status.",
        }.get(action, "🎵 Music player status."), {
            "pause": "⏸️ গান থামানো হয়েছে।",
            "resume": "▶️ গান আবার চালু হয়েছে।",
            "stop": "⏹️ গান বন্ধ হয়েছে।",
            "status": "🎵 মিউজিক প্লেয়ারের অবস্থা।",
        }.get(action, "🎵 মিউজিক প্লেয়ারের অবস্থা।"))
        return {"success": True, "action": f"media_music_{action}", "agent": "media",
                "message": message, **result}

    # ---------------- downloads / subtitles ----------------
    def download(self, url: str, audio_only: bool = False, command: str = "") -> Dict[str, Any]:
        url = _extract_url(url) or _extract_url(command)
        if not url:
            return {"success": False, "action": "media_download", "agent": "media",
                    "message": tr(command, "Give me a video URL to download.",
                                  "ডাউনলোড করার জন্য ভিডিও URL দিন।")}
        if self._is_cloud():
            return {"success": False, "action": "media_download", "agent": "media",
                    "message": tr(command,
                                  "⬇️ Downloads are a laptop action. Start the laptop connector, then ask again.",
                                  "⬇️ ডাউনলোড ল্যাপটপের কাজ। ল্যাপটপ connector চালু করে আবার বলুন।"),
                    "needs_connector": True, "url": url}
        result = video_downloader.download(url, audio_only=audio_only)
        if not result.get("success"):
            return {"success": False, "action": "media_download", "agent": "media",
                    "message": tr(command, f"Download failed: {result.get('error')}",
                                  f"ডাউনলোড ব্যর্থ: {result.get('error')}"),
                    "url": url}
        return {"success": True, "action": "media_download", "agent": "media",
                "message": tr(command, f"⬇️ Downloaded: {result.get('title')}",
                              f"⬇️ ডাউনলোড হয়েছে: {result.get('title')}"),
                "url": url, "title": result.get("title"), "path": result.get("path"),
                "audio_only": audio_only}

    def create_subtitle(self, url: str = "", file_path: str = "", command: str = "") -> Dict[str, Any]:
        source = file_path or ""
        if not source:
            found = find_existing_path(command)
            source = str(found) if found else ""
        if not source:
            return {"success": False, "action": "media_subtitle", "agent": "media",
                    "message": tr(command,
                                  "Subtitles need a local audio/video file. Example: “make subtitle from C:\\video.mp4”.",
                                  "সাবটাইটেলের জন্য লোকাল অডিও/ভিডিও ফাইল দরকার। উদাহরণ: “make subtitle from C:\\video.mp4”।"),
                    "url": url}
        try:
            result = subtitle_generator.srt(source)
        except Exception as exc:
            return {"success": False, "action": "media_subtitle", "agent": "media",
                    "message": tr(command, f"Subtitle failed: {exc}", f"সাবটাইটেল তৈরি হয়নি: {exc}")}
        if not result.get("success"):
            return {"success": False, "action": "media_subtitle", "agent": "media",
                    "message": tr(command, f"Subtitle failed: {result.get('error')}",
                                  f"সাবটাইটেল তৈরি হয়নি: {result.get('error')}")}
        return {"success": True, "action": "media_subtitle", "agent": "media",
                "message": tr(command, f"📝 Subtitle ready: {result.get('srt_path')}",
                              f"📝 সাবটাইটেল তৈরি: {result.get('srt_path')}"),
                "path": result.get("srt_path"), "lines": result.get("lines"),
                "text": truncate(result.get("text"), 1200)}

    # ---------------- dispatch ----------------
    def handle(self, intent: str, entities: Dict) -> Dict:
        entities = dict(entities or {})
        command = str(entities.get("_command", ""))
        intent_lower = str(intent or "").lower()
        query = clean_text(entities.get("query") or "")
        lower = command.lower()

        try:
            if intent_lower in ("media_music", "play_music") or re.search(
                r"\bplay\b.*\b(?:music|song|audio|playlist)\b|\bgan|gaan|music\b", lower
            ):
                if re.search(r"\b(?:pause|resume|stop)\b|\bstatus\b", lower) and "play music" not in lower:
                    action = "pause" if "pause" in lower else "resume" if "resume" in lower else "stop" if "stop" in lower else "status"
                    return self.control_music(action, command)
                return self.play_music(query or str(entities.get("track") or ""), command)

            if intent_lower == "media_image" or re.search(
                r"\b(?:generate|create|make|draw)\b.*\b(?:image|picture|photo)\b|ছবি\s*(?:বানাও|তৈরি)", lower
            ):
                return self.generate_image(
                    str(entities.get("prompt") or entities.get("query") or query or command),
                    str(entities.get("size") or "1024x1024"), command,
                )

            if intent_lower == "media_meme" or re.search(r"\bmeme\b|মিম", lower):
                top = str(entities.get("top_text") or "")
                bottom = str(entities.get("bottom_text") or "")
                return self.generate_meme(top, bottom, str(entities.get("prompt") or query), "", command)

            if intent_lower == "media_download" or re.search(r"\bdownload\b", lower):
                return self.download(
                    str(entities.get("url") or _extract_url(command)),
                    bool(entities.get("audio_only") or re.search(r"\b(?:song|audio|music|গান)\b", lower)),
                    command,
                )

            if intent_lower == "media_subtitle" or re.search(r"\b(?:subtitle|subtitles|caption|transcribe)\b|সাবটাইটেল", lower):
                return self.create_subtitle(str(entities.get("url") or ""), "", command)

            if intent_lower == "media_background_remove" or re.search(
                r"\b(?:remove|delete|erase)\b.*\bbackground\b|background\s*(?:remove|সরাও)", lower
            ):
                return self.remove_background(str(entities.get("path") or ""), command)

            # Default: YouTube search / info.
            url = str(entities.get("url") or _extract_url(command))
            if url:
                return self.youtube_info(url, command)
            return self.youtube_search(query or re.sub(r"^\s*(?:play|youtube|search)\s+", "", command), command)
        except Exception as exc:
            return {"success": False, "action": "media_error", "agent": "media",
                    "message": tr(command, f"Media Agent error: {exc}", f"মিডিয়া এজেন্টে সমস্যা: {exc}")}

    # ---------------- self test ----------------
    def test(self) -> Dict[str, Any]:
        tracks = music_player.library()
        pillow = True
        try:
            from PIL import Image  # noqa: F401
        except Exception:
            pillow = False
        ytdlp = video_downloader.available()
        checks = {
            "image_generator": True,
            "music_library": len(tracks),
            "pillow": pillow,
            "yt_dlp": ytdlp,
            "cloud": self._is_cloud(),
        }
        message = f"Media ready: {len(tracks)} track(s), Pillow={'yes' if pillow else 'no'}, yt-dlp={'yes' if ytdlp else 'no'}."
        return {"success": True, "agent": "media", "message": message, **checks}


media_agent = MediaAgent()
