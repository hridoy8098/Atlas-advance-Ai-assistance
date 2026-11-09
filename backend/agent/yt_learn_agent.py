# backend/agent/yt_learn_agent.py — YouTube Learning Agent
# Resolve/search a video, fetch transcript, summarize, save notes and generate a quiz.
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

import config
from backend.study.youtube_ai import youtube_ai
from .advanced_common import (
    ask,
    ask_json,
    clean_text,
    extract_after,
    fail,
    ok,
    slugify,
    truncate,
)

_YOUTUBE_ID = re.compile(
    r"(?:youtube\.com/(?:watch\?[^ ]*v=|shorts/|embed/)|youtu\.be/)([A-Za-z0-9_-]{11})"
)


class YouTubeLearnAgent:
    name = "YouTube Learning Agent"

    def get_capabilities(self) -> List[str]:
        return ["yt_learn", "yt_summary", "yt_transcript", "yt_notes", "yt_quiz"]

    def handle(self, intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        entities = entities or {}
        command = str(entities.get("_command", ""))
        intent_lower = str(intent or "").lower()
        target = str(entities.get("url") or entities.get("query") or self._target(command)).strip()

        if not target:
            return fail("yt_learn", "YouTube URL বা topic দিন, যেমন: “youtube learn: transformer explained”।")

        try:
            if "transcript" in intent_lower or "transcript" in command.lower():
                return self.transcript(target)
            if "notes" in intent_lower or "notes" in command.lower():
                return self.learn(target, mode="notes")
            if "quiz" in intent_lower or "quiz" in command.lower():
                return self.learn(target, mode="quiz")
            return self.learn(target, mode="summary")
        except Exception as exc:
            return fail("yt_learn", f"YouTube Learning error: {exc}")

    # ---------------- actions ----------------
    def learn(self, target: str, mode: str = "summary") -> Dict[str, Any]:
        video = self._resolve_video(target)
        if not video.get("video_id"):
            return fail("yt_learn", f"Video পাওয়া যায়নি: {target}")

        video_id = video["video_id"]
        url = video.get("url") or f"https://www.youtube.com/watch?v={video_id}"
        info = youtube_ai.info(url)
        title = info.get("title") or video.get("title") or f"YouTube video {video_id}"
        author = info.get("author") or video.get("author") or ""

        transcript_text, transcript_error = self._transcript(video_id)
        context = (
            f"Transcript:\n{truncate(transcript_text, 30000)}"
            if transcript_text
            else f"No transcript available. A title-only summary is required. Title: {title}. Channel: {author}."
        )

        if mode == "quiz":
            data = ask_json(
                f"Create 6 exam-style questions from this YouTube video.\nTitle: {title}\n{context}\n"
                'Reply JSON only: {"questions":[{"q":"...","options":["a","b","c","d"],"answer":0}]}',
                system_prompt="You write questions strictly from the provided transcript. JSON only.",
                fallback=None,
            )
            questions = (data or {}).get("questions") if isinstance(data, dict) else None
            message = "🎓 Video quiz তৈরি হয়েছে।" if questions else "Quiz তৈরি করা যায়নি (AI unavailable)।"
            payload = {
                "video": {"id": video_id, "url": url, "title": title, "author": author},
                "transcript_available": bool(transcript_text),
                "transcript_error": transcript_error or None,
                "questions": questions or [],
            }
            return {"success": bool(questions), "agent": "yt_learn", "message": message, **payload}

        prompt = (
            f"Study this YouTube video.\nTitle: {title}\nChannel: {author}\n{context}\n\n"
            "Produce: 1) 5-8 key takeaways, 2) a structured summary with timestamps only if available, "
            "3) 3 review questions, 4) one practical action. Reply in the user's language."
        )
        summary = ask(prompt, system_prompt="You are a concise, accurate study assistant. Do not invent timestamps.")

        folder = config.DATA_DIR / "yt_notes"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{video_id}-{slugify(title, 'video')}.md"
        path.write_text(
            f"# {title}\n\n- Channel: {author}\n- URL: {url}\n"
            f"- Fetched: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            f"- Transcript: {'yes' if transcript_text else 'no'}\n\n"
            f"{summary or '(AI summary unavailable)'}\n",
            encoding="utf-8",
        )

        return ok(
            "yt_learn",
            f"🎓 {title} — notes saved.",
            video={"id": video_id, "url": url, "title": title, "author": author, "thumbnail": info.get("thumbnail")},
            summary=truncate(summary, 9000) if summary else "",
            transcript_available=bool(transcript_text),
            transcript_error=transcript_error or None,
            notes_path=str(path),
        )

    def transcript(self, target: str) -> Dict[str, Any]:
        video = self._resolve_video(target)
        if not video.get("video_id"):
            return fail("yt_learn", "Video পাওয়া যায়নি।")
        text, error = self._transcript(video["video_id"])
        if not text:
            return fail("yt_learn", f"Transcript পাওয়া যায়নি: {error or 'no captions'}", video=video)
        return ok(
            "yt_learn",
            f"📝 Transcript fetched ({len(text.split())} words).",
            video=video,
            transcript=truncate(text, 20000),
        )

    # ---------------- resolution ----------------
    def _resolve_video(self, target: str) -> Dict[str, str]:
        match = _YOUTUBE_ID.search(target)
        if match:
            return {"video_id": match.group(1), "url": f"https://www.youtube.com/watch?v={match.group(1)}"}

        query = clean_text(re.sub(
            r"(?i)\b(youtube|yt|learn|summary|summarize|summarise|transcript|notes|quiz|video|dekhao|খোঁজো|শিখো)\b",
            " ",
            target,
        ))
        try:
            response = requests.get(
                "https://www.youtube.com/results",
                params={"search_query": query or target},
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Atlas/7.0"},
                timeout=12,
            )
            ids = re.findall(r'"videoId":"([A-Za-z0-9_-]{11})"', response.text)
            if ids:
                return {"video_id": ids[0], "url": f"https://www.youtube.com/watch?v={ids[0]}", "title": query}
        except Exception:
            pass
        return {}

    @staticmethod
    def _transcript(video_id: str) -> tuple:
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
        except Exception as exc:
            return "", f"youtube-transcript-api missing: {exc}"

        languages = ["en", "bn", "hi", "ur", "auto"]
        try:
            api = YouTubeTranscriptApi()
            if hasattr(api, "fetch"):
                fetched = api.fetch(video_id, languages=languages)
                snippets = getattr(fetched, "snippets", fetched)
                lines = []
                for snippet in snippets:
                    text = getattr(snippet, "text", None)
                    if text is None and isinstance(snippet, dict):
                        text = snippet.get("text")
                    if text:
                        lines.append(clean_text(text))
                if lines:
                    return " ".join(lines), ""
        except Exception as exc:
            error = str(exc)
        else:
            error = ""

        try:
            legacy = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
            lines = [clean_text(item.get("text", "")) for item in legacy if item.get("text")]
            if lines:
                return " ".join(lines), ""
        except Exception as exc:
            error = str(exc)

        return "", error or "no captions available"

    @staticmethod
    def _target(command: str) -> str:
        url = _YOUTUBE_ID.search(command or "")
        if url:
            return url.group(0)
        return extract_after(command, ["youtube learn", "youtube", "video", "learn from", "summary of", "ট্রান্সক্রিপ্ট"])

    def test(self) -> Dict[str, Any]:
        try:
            import youtube_transcript_api  # noqa: F401
            transcript_api = True
        except Exception:
            transcript_api = False
        try:
            import yt_dlp  # noqa: F401
            ytdlp = True
        except Exception:
            ytdlp = False
        return {
            "success": True,
            "agent": "yt_learn",
            "transcript_api": transcript_api,
            "yt_dlp": ytdlp,
            "message": "YouTube Learning ready.",
        }


yt_learn_agent = YouTubeLearnAgent()
