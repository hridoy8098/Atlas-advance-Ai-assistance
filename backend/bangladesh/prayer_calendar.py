# backend/bangladesh/prayer_calendar.py — prayer times via aladhan.com

import time
from datetime import date

import requests

import config

_TODAY_API = "https://api.aladhan.com/v1/timingsByCity"
_MONTH_API = "https://api.aladhan.com/v1/calendarByCity/{year}/{month}"
_COUNTRY = getattr(config, "PRAYER_COUNTRY", "Bangladesh") or "Bangladesh"
_METHOD = 1
_CACHE = {}
_TTL = 6 * 3600


class PrayerCalendar:
    def today(self, city: str = None):
        city = city or getattr(config, "PRAYER_CITY", None) or config.DEFAULT_CITY
        key = ("today", city, date.today().isoformat())
        cached = _CACHE.get(key)
        if cached and time.time() - cached[0] < _TTL:
            return cached[1]

        try:
            resp = requests.get(
                _TODAY_API,
                params={"city": city, "country": _COUNTRY, "method": _METHOD},
                timeout=10,
            )
            resp.raise_for_status()
            payload = resp.json().get("data", {})
        except Exception as e:
            return {"city": city, "available": False, "timings": {}, "error": str(e)}

        timings = {k: v.split(" ")[0] for k, v in (payload.get("timings") or {}).items()
                   if k in ("Fajr", "Sunrise", "Dhuhr", "Asr", "Maghrib", "Isha")}
        result = {
            "city": city,
            "country": _COUNTRY,
            "available": True,
            "date": (payload.get("date") or {}).get("readable", date.today().isoformat()),
            "timings": timings,
        }
        _CACHE[key] = (time.time(), result)
        return result

    def month(self, city: str = None, year: int = None, month: int = None):
        city = city or getattr(config, "PRAYER_CITY", None) or config.DEFAULT_CITY
        today = date.today()
        year = int(year or today.year)
        month = int(month or today.month)
        key = ("month", city, year, month)
        cached = _CACHE.get(key)
        if cached and time.time() - cached[0] < _TTL:
            return cached[1]

        try:
            resp = requests.get(
                _MONTH_API.format(year=year, month=month),
                params={"city": city, "country": _COUNTRY, "method": _METHOD},
                timeout=12,
            )
            resp.raise_for_status()
            days = resp.json().get("data", [])
        except Exception as e:
            return {"city": city, "available": False, "days": [], "error": str(e)}

        result = {
            "city": city,
            "country": _COUNTRY,
            "year": year,
            "month": month,
            "available": True,
            "days": [
                {
                    "date": (day.get("date") or {}).get("gregorian", {}).get("date"),
                    "hijri": (day.get("date") or {}).get("hijri", {}).get("date"),
                    "timings": {k: v.split(" ")[0] for k, v in (day.get("timings") or {}).items()
                                if k in ("Fajr", "Sunrise", "Dhuhr", "Asr", "Maghrib", "Isha")},
                }
                for day in days
            ],
        }
        _CACHE[key] = (time.time(), result)
        return result


prayer_calendar = PrayerCalendar()
