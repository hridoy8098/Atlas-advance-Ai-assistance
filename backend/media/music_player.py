# backend/media/music_player.py — playlist scanning + playback via pygame

import threading
from pathlib import Path

import config

_AUDIO_EXT = {".mp3", ".wav", ".ogg", ".m4a", ".flac"}
_MEDIA_MUSIC = config.DOWNLOADS_DIR / "media" / "music"


class MusicPlayer:
    def __init__(self):
        self._lock = threading.Lock()
        self._current = None
        self._paused = False
        self._ready = False
        _MEDIA_MUSIC.mkdir(parents=True, exist_ok=True)

    def _ensure(self):
        if self._ready:
            return True
        try:
            import pygame
            pygame.mixer.init()
            self._ready = True
            return True
        except Exception as e:
            print(f"⚠️ MusicPlayer init failed: {e}")
            return False

    def library(self):
        folders = [_MEDIA_MUSIC, Path.home() / "Music"]
        tracks = []
        seen = set()
        for folder in folders:
            if not folder.exists():
                continue
            for path in folder.rglob("*"):
                if path.is_file() and path.suffix.lower() in _AUDIO_EXT and path not in seen:
                    seen.add(path)
                    tracks.append({
                        "name": path.stem,
                        "path": str(path),
                        "size_mb": round(path.stat().st_size / 1048576, 1),
                    })
        return sorted(tracks, key=lambda t: t["name"].lower())

    def play(self, path: str):
        if not self._ensure():
            return {"playing": False, "error": "pygame mixer unavailable"}
        target = self._resolve(path)
        if target is None:
            return {"playing": False, "error": f"track not found: {path}"}
        try:
            import pygame
            with self._lock:
                pygame.mixer.music.load(str(target))
                pygame.mixer.music.play()
                self._current = str(target)
                self._paused = False
            return {"playing": True, "track": target.stem, "path": str(target)}
        except Exception as e:
            return {"playing": False, "error": str(e)}

    def pause(self):
        if not self._ready:
            return {"paused": False, "error": "player not started"}
        try:
            import pygame
            pygame.mixer.music.pause()
            self._paused = True
            return {"paused": True, "track": Path(self._current).stem if self._current else None}
        except Exception as e:
            return {"paused": False, "error": str(e)}

    def resume(self):
        if not self._ready:
            return {"resumed": False, "error": "player not started"}
        try:
            import pygame
            pygame.mixer.music.unpause()
            self._paused = False
            return {"resumed": True}
        except Exception as e:
            return {"resumed": False, "error": str(e)}

    def stop(self):
        try:
            import pygame
            pygame.mixer.music.stop()
        except Exception:
            pass
        self._current = None
        self._paused = False
        return {"playing": False}

    def status(self):
        playing = False
        if self._ready:
            try:
                import pygame
                playing = bool(pygame.mixer.music.get_busy())
            except Exception:
                playing = False
        return {
            "playing": playing and not self._paused,
            "paused": self._paused,
            "track": Path(self._current).stem if self._current else None,
            "path": self._current,
        }

    def _resolve(self, path: str):
        if not path:
            return None
        candidate = Path(path)
        if candidate.exists():
            return candidate
        for track in self.library():
            if track["name"].lower() == str(path).lower() or Path(track["path"]).stem.lower() == Path(path).stem.lower():
                return Path(track["path"])
        return None


music_player = MusicPlayer()
