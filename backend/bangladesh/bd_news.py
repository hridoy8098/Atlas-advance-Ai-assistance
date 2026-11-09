# backend/bangladesh/bd_news.py — Bangla/English news headlines from RSS

import time
import xml.etree.ElementTree as ET

import requests

_FEEDS = [
    "https://www.thedailystar.net/frontpage/rss.xml",
    "https://www.prothomalo.com/feed",
    "https://bdnews24.com/?widgetName=rssfeed&widgetId=1150&getXmlFeed=true",
]
_CACHE = {"at": 0, "items": []}
_TTL = 600


class BDNews:
    def latest(self, limit: int = 10):
        limit = max(1, min(int(limit), 30))
        if time.time() - _CACHE["at"] < _TTL and _CACHE["items"]:
            return _CACHE["items"][:limit]

        items = []
        for feed in _FEEDS:
            items.extend(self._fetch(feed))
            if len(items) >= limit * 2:
                break

        if items:
            _CACHE["at"] = time.time()
            _CACHE["items"] = items[:40]
        return items[:limit]

    @staticmethod
    def _fetch(url):
        try:
            resp = requests.get(url, timeout=10, headers={"User-Agent": "Atlas/7.0"})
            if resp.status_code != 200:
                return []
            root = ET.fromstring(resp.content)
            channel = root.find("channel") or root
            out = []
            for item in channel.findall("item")[:10]:
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                published = (item.findtext("pubDate") or "").strip()
                description = (item.findtext("description") or "").strip()
                if title:
                    out.append({
                        "title": title,
                        "link": link,
                        "published": published,
                        "summary": description[:240],
                    })
            return out
        except Exception as e:
            print(f"⚠️ BD news feed failed ({url[:40]}): {e}")
            return []


bd_news = BDNews()
