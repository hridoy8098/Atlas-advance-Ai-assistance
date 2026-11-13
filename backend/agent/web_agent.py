# backend/agent/web_agent.py — real web search, research, summaries and bookmarks.
#
# Uses DuckDuckGo HTML + Wikipedia (no API key) and the local AI engine for
# synthesis. Browser launching is skipped on the cloud server, where the reply
# includes clickable links instead.
from __future__ import annotations

import re
import time
import webbrowser
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import parse_qs, quote, urlparse

import requests
from bs4 import BeautifulSoup

import config
from .advanced_common import ask, clean_text, data_file, fail, ok, read_json, truncate, write_json
from .agent_i18n import is_bengali, tr
from .base_agent import BaseAgent

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Atlas/7.0 Web",
    "Accept-Language": "en-US,en;q=0.8,bn;q=0.6",
}
DDG_URL = "https://html.duckduckgo.com/html/?q={query}"
WIKI_API = "https://{lang}.wikipedia.org/w/api.php"
BOOKMARK_FILE = data_file("web_bookmarks.json")
HISTORY_FILE = data_file("web_history.json")
NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl={hl}&gl={gl}&ceid={gl}:{lang}"


class WebAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Web Agent",
            description="Real web search, page reading, summaries, translation, news and bookmarks",
        )

    def get_capabilities(self) -> List[str]:
        return [
            "web_search", "web_research", "web_summarize", "web_translate",
            "web_bookmark", "web_history", "web_news", "wikipedia_search", "open_url",
        ]

    # ---------------- browser ----------------
    def _can_open_browser(self) -> bool:
        return not bool(getattr(config, "ATLAS_CLOUD", False))

    def open_url(self, url: str, command: str = "") -> Dict[str, Any]:
        url = self._normalize_url(url)
        if not url:
            return fail("web", tr(command, "Which link should I open?", "কোন লিংক খুলব?"))
        self._record_history(url, "open")
        opened = False
        if self._can_open_browser():
            try:
                opened = bool(webbrowser.open(url))
            except Exception:
                opened = False
        if opened:
            message = tr(command, f"🌐 Opened {url}", f"🌐 খোলা হয়েছে: {url}")
        elif self._can_open_browser():
            message = tr(command, f"🌐 Link ready: {url}", f"🌐 লিংক প্রস্তুত: {url}")
        else:
            message = tr(command,
                         f"🌐 Opening a browser is a laptop action. Link: {url}",
                         f"🌐 ব্রাউজার খোলা ল্যাপটপের কাজ। লিংক: {url}")
        return {"success": True, "action": "open_url", "agent": "web",
                "message": message, "url": url, "opened": opened}

    # ---------------- search / research ----------------
    def search_web(self, query: str, command: str = "") -> Dict[str, Any]:
        query = clean_text(query)
        if not query:
            return fail("web", tr(command, "What should I search for?", "কী সার্চ করব?"))
        started = time.time()
        results = self._ddg_search(query, limit=6)
        if not results:
            summary = self._wiki_summary(query, command)
            if summary:
                results = [{"title": summary.get("title") or query,
                            "url": summary.get("url") or "",
                            "snippet": summary.get("extract") or ""}]
        if not results:
            return fail("web", tr(command, f"Nothing found for “{query}”. Try different words.",
                                   f"“{query}” নিয়ে কিছু পাওয়া যায়নি। অন্যভাবে বলুন।"),
                        query=query)

        if self._can_open_browser():
            try:
                webbrowser.open(f"https://duckduckgo.com/?q={quote(query)}")
            except Exception:
                pass
        self._record_history(f"https://duckduckgo.com/?q={quote(query)}", "search", query)
        for item in results:
            if item.get("url"):
                self._record_history(item["url"], "result", item.get("title", ""))

        top = results[:3]
        lines = [f"{index}. {item['title']} — {item['url']}" for index, item in enumerate(top, 1)]
        message = tr(command, f"🔎 Top results for “{query}”:\n", f"🔎 “{query}” এর শীর্ষ ফলাফল:\n") + "\n".join(lines)
        return {"success": True, "action": "web_search", "agent": "web", "message": message,
                "query": query, "results": results, "url": results[0].get("url", ""),
                "duration_ms": int((time.time() - started) * 1000)}

    def research(self, topic: str, command: str = "", max_sources: int = 4) -> Dict[str, Any]:
        topic = clean_text(topic)
        if not topic:
            return fail("web", tr(command, "What topic should I research?", "কোন বিষয়ে research করব?"))
        started = time.time()
        sources = self._ddg_search(topic, limit=max(1, min(max_sources, 5)))
        if not sources:
            wiki = self._wiki_summary(topic, command)
            if wiki:
                sources = [{"title": wiki.get("title") or topic, "url": wiki.get("url", ""),
                            "snippet": wiki.get("extract", ""), "text": wiki.get("extract", "")}]
        if not sources:
            answer = ask(
                f"Write a concise, careful briefing about: {topic}. Mark uncertain claims.",
                system_prompt="You are a research assistant. Reply in the user's language. Never invent citations.",
            )
            return fail("web", tr(command, "Live search failed; here is an AI briefing without citations.",
                                   "লাইভ সার্চ পাওয়া যায়নি; citation ছাড়া AI briefing দিচ্ছি।"),
                        topic=topic, summary=truncate(answer, 3000), sources=[])

        for source in sources[:3]:
            if source.get("url"):
                source["text"] = self._fetch_text(source["url"])
                if not source.get("snippet"):
                    source["snippet"] = truncate(source.get("text", ""), 240)

        blocks = []
        for index, source in enumerate(sources, 1):
            blocks.append(
                f"[{index}] {source.get('title') or 'Untitled'}\n"
                f"URL: {source.get('url')}\n"
                f"{truncate(source.get('snippet') or source.get('text') or '', 1400)}"
            )
        answer = ask(
            "Write a concise research briefing using ONLY the sources below. "
            f"Topic: {topic}\n\n" + "\n\n".join(blocks) + "\n\n"
            "Use short paragraphs and cite [n]. End with a Sources list. Reply in the user's language.",
            system_prompt="You are a careful research analyst. Do not invent facts or citations.",
        )
        if not answer:
            answer = "\n\n".join(
                f"[{index}] {source.get('title')} — {source.get('snippet') or truncate(source.get('text', ''), 300)}"
                for index, source in enumerate(sources, 1)
            )
        for item in sources:
            if item.get("url"):
                self._record_history(item["url"], "research", topic)

        summary = truncate(answer, 5000)
        message = tr(command, f"🔎 Research on “{topic}” ({len(sources)} sources):\n",
                     f"🔎 “{topic}” নিয়ে research ({len(sources)} সূত্র):\n") + truncate(answer, 700)
        return {"success": True, "action": "web_research", "agent": "web", "message": message,
                "topic": topic, "summary": summary, "sources": sources,
                "duration_ms": int((time.time() - started) * 1000)}

    def summarize_url(self, url: str, command: str = "") -> Dict[str, Any]:
        url = self._normalize_url(url)
        if not url:
            return fail("web", tr(command, "Which page should I summarize?", "কোন পেজের সারাংশ চাই?"))
        text = self._fetch_text(url, limit=12000)
        if not text:
            return fail("web", tr(command, f"Could not read {url}. The page may block bots.",
                                   f"{url} পড়া যায়নি। পেজটি bot আটকাতে পারে।"), url=url)
        title = self._page_title(url) or url
        summary = ask(
            f"Summarize this web page in 5-7 short bullets. Keep key numbers and dates.\n"
            f"Title: {title}\nURL: {url}\n\n{truncate(text, 9000)}",
            system_prompt="You are a precise summarizer. Reply in the user's language.",
        )
        if not summary:
            summary = truncate(text, 1200)
        self._record_history(url, "summarize", title)
        return {"success": True, "action": "web_summarize", "agent": "web",
                "message": tr(command, f"📄 Summary of {title}:\n", f"📄 {title} এর সারাংশ:\n") + truncate(summary, 900),
                "url": url, "title": title, "summary": truncate(summary, 5000)}

    def wikipedia_search(self, query: str, command: str = "") -> Dict[str, Any]:
        query = clean_text(query)
        if not query:
            return fail("web", tr(command, "What should I look up on Wikipedia?", "উইকিপিডিয়ায় কী খুঁজব?"))
        wiki = self._wiki_summary(query, command)
        if not wiki:
            return fail("web", tr(command, f"No Wikipedia article found for “{query}”.", f"“{query}” নিয়ে উইকিপিডিয়া আর্টিকেল পাওয়া যায়নি।"))
        return {"success": True, "action": "wikipedia_search", "agent": "web",
                "message": f"📚 {wiki.get('title')}: {truncate(wiki.get('extract', ''), 700)}\n{wiki.get('url', '')}",
                "query": query, **wiki}

    # ---------------- translate ----------------
    def translate(self, text: str, target_language: str = "", command: str = "") -> Dict[str, Any]:
        text = clean_text(text)
        if not text:
            return fail("web", tr(command, "What text should I translate?", "কোন লেখা অনুবাদ করব?"))
        target = clean_text(target_language) or ("Bengali" if is_bengali(command) else "English")
        translated = ask(
            f"Translate the following text into {target}. Return only the translation.\n\n{text}",
            system_prompt="You are a professional translator. Preserve meaning and tone.",
        )
        if not translated:
            return fail("web", tr(command, "Translation service is unavailable right now.", "এই মুহূর্তে অনুবাদ করা যাচ্ছে না।"))
        return {"success": True, "action": "web_translate", "agent": "web",
                "message": tr(command, f"🌐 {target}: {translated}", f"🌐 {target}: {translated}"),
                "text": text, "translation": translated, "target_language": target}

    # ---------------- news ----------------
    def news(self, query: str = "", command: str = "") -> Dict[str, Any]:
        topic = clean_text(query)
        bengali = is_bengali(command)
        search = topic or ("বাংলাদেশ" if bengali else "world")
        hl, gl, lang = ("bn", "BD", "bn") if bengali else ("en-US", "US", "en")
        url = NEWS_RSS.format(query=quote(search), hl=hl, gl=gl, lang=lang)
        items: List[Dict[str, str]] = []
        try:
            response = requests.get(url, headers=HEADERS, timeout=12)
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                for node in root.iter("item"):
                    title = clean_text(node.findtext("title") or "")
                    link = clean_text(node.findtext("link") or "")
                    published = clean_text(node.findtext("pubDate") or "")
                    if title:
                        items.append({"title": title, "url": link, "published": published})
                    if len(items) >= 8:
                        break
        except Exception:
            items = []
        if not items:
            results = self._ddg_search(f"{search} news", limit=5)
            items = [{"title": item["title"], "url": item["url"], "published": ""} for item in results]
        if not items:
            return fail("web", tr(command, "Could not fetch news right now.", "এই মুহূর্তে খবর আনা যাচ্ছে না।"))
        lines = [f"• {item['title']}" for item in items[:6]]
        return {"success": True, "action": "web_news", "agent": "web",
                "message": tr(command, f"📰 Top news ({search}):\n", f"📰 শীর্ষ খবর ({search}):\n") + "\n".join(lines),
                "query": search, "news": items}

    # ---------------- bookmarks / history ----------------
    def bookmark(self, url: str = "", title: str = "", command: str = "") -> Dict[str, Any]:
        url = self._normalize_url(url) or self._extract_url(command)
        if not url:
            return fail("web", tr(command, "Give me a URL to bookmark.", "বুকমার্ক করার জন্য একটি URL দিন।"))
        rows = self._bookmarks()
        existing = next((item for item in rows if item.get("url") == url), None)
        if existing:
            return {"success": True, "action": "web_bookmark", "agent": "web",
                    "message": tr(command, f"🔖 Already bookmarked: {url}", f"🔖 আগেই বুকমার্ক করা আছে: {url}"),
                    "bookmark": existing}
        item = {"url": url, "title": clean_text(title) or self._page_title(url) or url,
                "created_at": datetime.now().isoformat(timespec="seconds")}
        rows.append(item)
        write_json(BOOKMARK_FILE, {"bookmarks": rows[-500:]})
        return {"success": True, "action": "web_bookmark", "agent": "web",
                "message": tr(command, f"🔖 Bookmarked: {item['title']}", f"🔖 বুকমার্ক হয়েছে: {item['title']}"),
                "bookmark": item}

    def list_bookmarks(self, command: str = "") -> Dict[str, Any]:
        rows = self._bookmarks()
        if not rows:
            return {"success": True, "action": "web_bookmarks", "agent": "web",
                    "message": tr(command, "🔖 No bookmarks yet.", "🔖 এখনো কোনো বুকমার্ক নেই।"), "bookmarks": []}
        lines = [f"• {item.get('title')} — {item.get('url')}" for item in rows[-15:]]
        return {"success": True, "action": "web_bookmarks", "agent": "web",
                "message": tr(command, "🔖 Bookmarks:\n", "🔖 বুকমার্ক:\n") + "\n".join(lines), "bookmarks": rows[-50:]}

    def history(self, command: str = "") -> Dict[str, Any]:
        rows = self._history()
        if not rows:
            return {"success": True, "action": "web_history", "agent": "web",
                    "message": tr(command, "🕘 No browsing history yet.", "🕘 এখনো ব্রাউজিং হিস্টরি নেই।"), "history": []}
        lines = [f"• {item.get('title') or item.get('url')}" for item in rows[-10:]]
        return {"success": True, "action": "web_history", "agent": "web",
                "message": tr(command, "🕘 Recent pages:\n", "🕘 সাম্প্রতিক পেজ:\n") + "\n".join(lines), "history": rows[-30:]}

    # ---------------- dispatch ----------------
    def handle(self, intent: str, entities: Dict) -> Dict:
        entities = dict(entities or {})
        command = str(entities.get("_command", ""))
        intent_lower = str(intent or "").lower()
        query = clean_text(entities.get("query") or entities.get("topic") or "")
        url = str(entities.get("url") or self._extract_url(command) or "")
        lower = command.lower()

        try:
            if intent_lower in ("open_url", "open_website") or lower.startswith(("open ", "go to ", "visit ")):
                return self.open_url(url or query, command)
            if "summarize" in intent_lower or "summary" in intent_lower or re.search(r"\bsummari[sz]e\b|\btl;?dr\b|সারাংশ", lower):
                return self.summarize_url(url, command)
            if "translate" in intent_lower or "অনুবাদ" in command:
                target = str(entities.get("target_language") or "")
                return self.translate(str(entities.get("text") or query or command), target, command)
            if "bookmark" in intent_lower or re.search(r"\bbookmarks?\b", lower):
                if re.search(r"\b(?:list|show|my)\b.*\bbookmarks?\b", lower):
                    return self.list_bookmarks(command)
                return self.bookmark(url, str(entities.get("title") or ""), command)
            if "history" in intent_lower or "হিস্টরি" in command:
                return self.history(command)
            if "news" in intent_lower or "headline" in intent_lower or "খবর" in command:
                return self.news(query, command)
            if "wikipedia" in intent_lower or "উইকিপিডিয়া" in command:
                return self.wikipedia_search(query, command)
            if "research" in intent_lower:
                return self.research(query or command, command)
            if "search" in intent_lower or lower.startswith(("search ", "google ", "look up ")):
                return self.search_web(query or command, command)
            return self.summary_or_research(command)
        except Exception as exc:
            return fail("web", f"Web Agent error: {exc}")

    def summary_or_research(self, command: str) -> Dict[str, Any]:
        # Last resort inside the agent: a short AI answer beats "not supported".
        answer = ask(
            f"Answer the user's request using general knowledge. If it needs live data, say what to search.\n{command}",
            system_prompt="You are Atlas Web Agent. Reply in the user's language, concisely.",
        )
        if answer:
            return ok("web", answer, action="web_answer")
        return fail("web", "এই কমান্ডটি web agent বুঝতে পারেনি। উদাহরণ: “search web for AI news”।")

    # ---------------- network helpers ----------------
    def _ddg_search(self, query: str, limit: int = 6) -> List[Dict[str, str]]:
        results: List[Dict[str, str]] = []
        try:
            response = requests.get(DDG_URL.format(query=quote(query)), headers=HEADERS, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                for item in soup.select(".result"):
                    link = item.select_one(".result__a")
                    snippet = item.select_one(".result__snippet")
                    if not link or not link.get("href"):
                        continue
                    url = link["href"]
                    if "duckduckgo.com/l/?uddg=" in url:
                        url = (parse_qs(urlparse(url).query).get("uddg") or [url])[0]
                    results.append({
                        "title": clean_text(link.get_text(" ")),
                        "url": url,
                        "snippet": clean_text(snippet.get_text(" ")) if snippet else "",
                    })
                    if len(results) >= limit:
                        break
        except Exception:
            pass

        if len(results) < limit:
            try:
                lang = "bn" if re.search(r"[\u0980-\u09FF]", query) else "en"
                response = requests.get(
                    WIKI_API.format(lang=lang),
                    params={"action": "query", "list": "search", "srsearch": query,
                            "format": "json", "srlimit": limit - len(results)},
                    headers=HEADERS, timeout=10,
                )
                for item in (response.json().get("query", {}).get("search") or []):
                    title = item.get("title", "")
                    results.append({
                        "title": title,
                        "url": f"https://{lang}.wikipedia.org/wiki/" + title.replace(" ", "_"),
                        "snippet": clean_text(re.sub(r"<[^>]+>", " ", item.get("snippet", ""))),
                    })
            except Exception:
                pass
        return results[:limit]

    def _wiki_summary(self, query: str, command: str = "") -> Dict[str, Any]:
        lang = "bn" if is_bengali(command or query) else "en"
        try:
            response = requests.get(
                f"https://{lang}.wikipedia.org/w/api.php",
                params={"action": "query", "prop": "extracts", "exintro": 1, "explaintext": 1,
                        "titles": query, "format": "json", "redirects": 1},
                headers=HEADERS, timeout=10,
            )
            pages = response.json().get("query", {}).get("pages", {})
            page = next(iter(pages.values()), {})
            extract = clean_text(page.get("extract") or "")
            if extract:
                title = page.get("title") or query
                return {"title": title, "extract": truncate(extract, 2500),
                        "url": f"https://{lang}.wikipedia.org/wiki/" + quote(str(title).replace(" ", "_"))}
        except Exception:
            pass
        return {}

    def _fetch_text(self, url: str, limit: int = 12000) -> str:
        try:
            response = requests.get(url, headers=HEADERS, timeout=12, allow_redirects=True)
            if response.status_code != 200:
                return ""
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type and "text/plain" not in content_type:
                return ""
            if "text/plain" in content_type:
                return truncate(response.text, limit)
            soup = BeautifulSoup(response.content[:1_500_000], "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form", "noscript"]):
                tag.decompose()
            text = " ".join(soup.get_text(" ").split())
            return truncate(text, limit)
        except Exception:
            return ""

    def _page_title(self, url: str) -> str:
        try:
            response = requests.get(url, headers=HEADERS, timeout=8)
            if response.status_code == 200 and "text/html" in response.headers.get("Content-Type", ""):
                soup = BeautifulSoup(response.content[:200_000], "html.parser")
                if soup.title and soup.title.string:
                    return clean_text(soup.title.string)
        except Exception:
            pass
        return ""

    def _extract_url(self, text: str) -> str:
        match = re.search(r"https?://[^\s<>\"']+|www\.[^\s<>\"']+|[\w.-]+\.(?:com|org|net|io|dev|ai|edu|gov|co|bd)(?:/[^\s<>\"']*)?", text or "", re.I)
        if not match:
            return ""
        return self._normalize_url(match.group(0))

    @staticmethod
    def _normalize_url(url: str) -> str:
        value = clean_text(url).strip("<>\"'()[]")
        if not value:
            return ""
        if not value.lower().startswith(("http://", "https://")):
            if "." not in value and " " in value:
                return ""
            value = "https://" + value
        return value

    # ---------------- persistence ----------------
    def _bookmarks(self) -> List[Dict[str, Any]]:
        data = read_json(BOOKMARK_FILE, {"bookmarks": []})
        rows = data.get("bookmarks") if isinstance(data, dict) else data
        return [item for item in (rows or []) if isinstance(item, dict)]

    def _history(self) -> List[Dict[str, Any]]:
        data = read_json(HISTORY_FILE, {"history": []})
        rows = data.get("history") if isinstance(data, dict) else data
        return [item for item in (rows or []) if isinstance(item, dict)]

    def _record_history(self, url: str, action: str, title: str = "") -> None:
        if not url:
            return
        rows = self._history()
        rows.append({"url": url, "action": action, "title": clean_text(title),
                     "at": datetime.now().isoformat(timespec="seconds")})
        write_json(HISTORY_FILE, {"history": rows[-200:]})

    # ---------------- self test ----------------
    def test(self) -> Dict[str, Any]:
        network = False
        try:
            response = requests.get("https://html.duckduckgo.com/", headers=HEADERS, timeout=6)
            network = response.status_code < 500
        except Exception:
            network = False

        storage = True
        probe = "https://example.com/atlas-selftest"
        try:
            rows = self._bookmarks()
            original = list(rows)
            rows.append({"url": probe, "title": "Atlas self test",
                         "created_at": datetime.now().isoformat(timespec="seconds")})
            write_json(BOOKMARK_FILE, {"bookmarks": rows[-500:]})
            saved = any(item.get("url") == probe for item in self._bookmarks())
            write_json(BOOKMARK_FILE, {"bookmarks": original[-500:]})
            storage = saved
        except Exception:
            storage = False

        return {
            "success": bool(storage),
            "agent": "web",
            "message": ("Web search ready." if network else "Bookmark storage works; live network is unavailable.")
                       if storage else "Bookmark storage failed.",
            "network": network,
            "storage": storage,
            "capabilities": len(self.get_capabilities()),
        }


web_agent = WebAgent()
