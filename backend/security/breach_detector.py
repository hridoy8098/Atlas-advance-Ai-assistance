# backend/security/breach_detector.py — email breach lookup (public API, no key)

import time
from urllib.parse import quote

import requests

_API = "https://api.xposedornot.com/v1/check-email/{email}"
_CACHE = {}
_TTL = 3600


class BreachDetector:
    def check(self, email: str):
        email = (email or "").strip().lower()
        if "@" not in email or "." not in email:
            return {"available": False, "breached": None, "count": 0, "message": "valid email required"}

        cached = _CACHE.get(email)
        if cached and time.time() - cached[0] < _TTL:
            return cached[1]

        result = self._lookup(email)
        _CACHE[email] = (time.time(), result)
        return result

    def _lookup(self, email):
        try:
            resp = requests.get(_API.format(email=quote(email)), timeout=8,
                                headers={"User-Agent": "Atlas/7.0"})
            if resp.status_code == 404:
                return {"available": True, "breached": False, "count": 0,
                        "message": "No breach found for this email"}
            if resp.status_code != 200:
                return {"available": False, "breached": None, "count": 0,
                        "message": f"breach service returned {resp.status_code}"}
            data = resp.json()
            breaches = data.get("breaches") or data.get("Breaches") or []
            if isinstance(breaches, list) and breaches and isinstance(breaches[0], list):
                breaches = breaches[0]
            count = len(breaches) if isinstance(breaches, list) else int(data.get("count", 0) or 0)
            return {
                "available": True,
                "breached": count > 0,
                "count": count,
                "breaches": breaches[:10] if isinstance(breaches, list) else [],
                "message": f"Found in {count} breach(es)" if count else "No breach found for this email",
            }
        except Exception as e:
            return {"available": False, "breached": None, "count": 0,
                    "message": f"breach lookup failed: {type(e).__name__}"}


breach_detector = BreachDetector()
