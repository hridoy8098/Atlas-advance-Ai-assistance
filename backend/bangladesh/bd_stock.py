# backend/bangladesh/bd_stock.py — DSE latest prices (best-effort scrape)

import re
import time

import requests

_URL = "https://www.dsebd.org/latest_share_price_scroll_l.php"
_CACHE = {"at": 0, "items": [], "message": None}
_TTL = 300
_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
_CODE = re.compile(r"displayCompany\.php\?name=([A-Z0-9]+)", re.I)
_NUM = re.compile(r"-?\d[\d,]*\.?\d*")


class BDStock:
    def top(self, limit: int = 10):
        limit = max(1, min(int(limit), 30))
        if time.time() - _CACHE["at"] < _TTL and _CACHE["items"]:
            return _CACHE["items"][:limit]

        try:
            resp = requests.get(_URL, timeout=12, headers={"User-Agent": "Mozilla/5.0 Atlas/7.0"})
            if resp.status_code != 200:
                return self._unavailable(f"DSE returned {resp.status_code}")
            text = resp.text
        except Exception as e:
            return self._unavailable(f"DSE fetch failed: {type(e).__name__}")

        items = []
        for row in _ROW.findall(text):
            code = _CODE.search(row)
            if not code:
                continue
            ticker = code.group(1).upper()
            numbers = [n.replace(",", "") for n in _NUM.findall(re.sub(r"<[^>]+>", " ", row))]
            values = []
            for n in numbers:
                try:
                    values.append(float(n))
                except ValueError:
                    continue
            if not values:
                continue
            items.append({
                "ticker": ticker,
                "last_price": values[0],
                "change": values[5] if len(values) > 5 else None,
            })
            if len(items) >= 200:
                break

        if not items:
            return self._unavailable("DSE page layout changed")

        _CACHE.update({"at": time.time(), "items": items, "message": None})
        return items[:limit]

    @staticmethod
    def _unavailable(message):
        return []


bd_stock = BDStock()
