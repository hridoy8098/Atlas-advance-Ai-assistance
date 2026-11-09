# backend/media/subtitle_gen.py — transcribe audio and build an SRT file

import re
from datetime import datetime, timedelta
from pathlib import Path

import config

_MEDIA = config.DOWNLOADS_DIR / "media" / "subtitles"


class SubtitleGenerator:
    def transcribe(self, path: str):
        source = Path(path or "")
        if not source.exists():
            raise FileNotFoundError(f"media not found: {path}")
        try:
            from backend.core.ai_engine import ai_engine
        except Exception as e:
            return {"success": False, "text": "", "error": f"AI engine unavailable: {e}"}

        text = ai_engine.transcribe_audio(source.read_bytes()) or ""
        if not text:
            return {"success": False, "text": "", "error": "transcription failed or empty"}
        return {"success": True, "text": text.strip(), "source": str(source)}

    def srt(self, path: str, seconds_per_line: float = 4.0):
        result = self.transcribe(path)
        if not result.get("success"):
            return result

        chunks = self._chunks(result["text"])
        lines = []
        for index, chunk in enumerate(chunks, start=1):
            start = timedelta(seconds=(index - 1) * seconds_per_line)
            end = timedelta(seconds=index * seconds_per_line)
            lines.append(f"{index}\n{self._ts(start)} --> {self._ts(end)}\n{chunk}\n")

        _MEDIA.mkdir(parents=True, exist_ok=True)
        target = _MEDIA / f"{Path(path).stem}_{datetime.now():%H%M%S}.srt"
        target.write_text("\n".join(lines), encoding="utf-8")
        return {"success": True, "srt_path": str(target), "lines": len(chunks), "text": result["text"]}

    @staticmethod
    def _chunks(text, max_chars=70):
        sentences = [s.strip() for s in re.split(r"(?<=[.!?।])\s+", text) if s.strip()]
        chunks, current = [], ""
        for sentence in sentences or [text]:
            if len(current) + len(sentence) + 1 <= max_chars:
                current = f"{current} {sentence}".strip()
            else:
                if current:
                    chunks.append(current)
                current = sentence[:max_chars]
        if current:
            chunks.append(current)
        return chunks

    @staticmethod
    def _ts(delta):
        total = int(delta.total_seconds())
        millis = int((delta.total_seconds() - total) * 1000)
        return f"{total // 3600:02d}:{(total % 3600) // 60:02d}:{total % 60:02d},{millis:03d}"


subtitle_generator = SubtitleGenerator()
