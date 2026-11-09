# backend/study/youtube_ai.py — video info + study summary

import re

import requests

from backend.core.ai_text import ask

_OEMBED = "https://www.youtube.com/oembed?format=json&url={url}"


class YouTubeAI:
    def info(self, url: str):
        if not re.match(r"https?://", url or ""):
            raise ValueError("valid YouTube URL required")
        try:
            resp = requests.get(_OEMBED.format(url=url), timeout=8)
            if resp.status_code != 200:
                return {"url": url, "available": False, "title": None}
            data = resp.json()
            return {
                "url": url,
                "available": True,
                "title": data.get("title"),
                "author": data.get("author_name"),
                "thumbnail": data.get("thumbnail_url"),
            }
        except Exception as e:
            return {"url": url, "available": False, "title": None, "error": str(e)}

    def summarize(self, url_or_query: str):
        target = (url_or_query or "").strip()
        if not target:
            raise ValueError("url or query required")

        info = {"title": None, "author": None}
        if re.match(r"https?://", target):
            info = self.info(target)
            prompt = (
                f'Summarize the YouTube video titled "{info.get("title")}" by {info.get("author")}. '
                "Give 5 key takeaways and 3 study questions. Reply in the user's language."
            )
        else:
            prompt = f"Summarize the topic '{target}' as if teaching from a video. Give 5 key points and 3 questions."

        summary = ask(prompt, system_prompt="You are a concise study assistant. Reply in Bangla or English as the user prefers.")
        return {
            "query": target,
            "title": info.get("title"),
            "author": info.get("author"),
            "summary": summary.strip() if summary else "",
            "available": bool(summary),
        }


youtube_ai = YouTubeAI()
