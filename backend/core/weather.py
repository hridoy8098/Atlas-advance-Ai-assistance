"""Key-free weather lookup shared by the API and the voice command handler.

OpenWeatherMap rejected the configured key with 401, so `/api/system/weather`
silently fell back to hard-coded values. Open-Meteo needs no key and returns
current temperature, feels-like, humidity and wind. Geocoding is used for
cities that are not in the small built-in table.
"""

from typing import Any, Dict, Optional, Tuple

import requests


# Updated on every failure so the API can explain why a lookup returned 503.
LAST_ERROR: Dict[str, Any] = {}


def _fail(stage: str, message: Any, status: Optional[int] = None) -> None:
    LAST_ERROR.clear()
    LAST_ERROR.update({
        "stage": stage,
        "status": status,
        "message": str(message)[:300],
    })


# name -> (display name, latitude, longitude)
_CITY_COORDS: Dict[str, Tuple[str, float, float]] = {
    "dhaka": ("Dhaka", 23.8103, 90.4125),
    "chittagong": ("Chittagong", 22.3569, 91.7832),
    "sylhet": ("Sylhet", 24.8949, 91.8687),
    "kolkata": ("Kolkata", 22.5726, 88.3639),
    "delhi": ("Delhi", 28.6139, 77.2090),
    "london": ("London", 51.5074, -0.1278),
    "new york": ("New York", 40.7128, -74.0060),
    "tokyo": ("Tokyo", 35.6762, 139.6503),
    "dubai": ("Dubai", 25.2048, 55.2708),
}

# WMO weather interpretation codes used by Open-Meteo.
_DESCRIPTIONS = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Light rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Light snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Light rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Light snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}

_DESCRIPTIONS_BN = {
    0: "পরিষ্কার আকাশ",
    1: "প্রধানত পরিষ্কার",
    2: "আংশিক মেঘলা",
    3: "মেঘাচ্ছন্ন",
    45: "কুয়াশা",
    48: "ঘন কুয়াশা",
    51: "হালকা গুঁড়ি বৃষ্টি",
    53: "মাঝারি গুঁড়ি বৃষ্টি",
    55: "ঘন গুঁড়ি বৃষ্টি",
    56: "হালকা হিমশীতল গুঁড়ি",
    57: "ঘন হিমশীতল গুঁড়ি",
    61: "হালকা বৃষ্টি",
    63: "মাঝারি বৃষ্টি",
    65: "ভারী বৃষ্টি",
    66: "হালকা হিমশীতল বৃষ্টি",
    67: "ভারী হিমশীতল বৃষ্টি",
    71: "হালকা তুষারপাত",
    73: "মাঝারি তুষারপাত",
    75: "ভারী তুষারপাত",
    77: "তুষারকণা",
    80: "হালকা বৃষ্টির ঝাপটা",
    81: "মাঝারি বৃষ্টির ঝাপটা",
    82: "প্রবল বৃষ্টির ঝাপটা",
    85: "হালকা তুষার ঝাপটা",
    86: "ভারী তুষার ঝাপটা",
    95: "বজ্রঝড়",
    96: "হালকা শিলাসহ বজ্রঝড়",
    99: "ভারী শিলাসহ বজ্রঝড়",
}


def _geocode(city: str, timeout: float) -> Optional[Tuple[str, float, float]]:
    try:
        response = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "en", "format": "json"},
            timeout=timeout,
        )
        if response.status_code != 200:
            _fail("geocode", response.text[:200], response.status_code)
            return None
        results = (response.json() or {}).get("results") or []
    except Exception as exc:
        print(f"⚠️ Weather geocoding failed for {city}: {exc}")
        _fail("geocode", repr(exc))
        return None

    if not results:
        _fail("geocode", f"No results for {city}")
        return None
    best = results[0]
    try:
        return (
            str(best.get("name") or city),
            float(best["latitude"]),
            float(best["longitude"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        _fail("geocode", repr(exc))
        return None


def get_weather(city: str = "Dhaka", timeout: float = 6) -> Optional[dict]:
    """Return current weather for `city`, or None when it cannot be resolved."""
    city = (city or "Dhaka").strip()
    if not city:
        city = "Dhaka"

    known = _CITY_COORDS.get(city.lower())
    if known:
        resolved, latitude, longitude = known
    else:
        geocoded = _geocode(city, timeout)
        if not geocoded:
            return None
        resolved, latitude, longitude = geocoded

    try:
        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": (
                    "temperature_2m,relative_humidity_2m,"
                    "apparent_temperature,weather_code,wind_speed_10m"
                ),
                "wind_speed_unit": "ms",
                "timezone": "auto",
            },
            timeout=timeout,
        )
        if response.status_code != 200:
            print(f"⚠️ Open-Meteo returned {response.status_code} for {city}")
            _fail("forecast", response.text[:200], response.status_code)
            return None
        current = (response.json() or {}).get("current") or {}
    except Exception as exc:
        print(f"⚠️ Open-Meteo lookup failed for {city}: {exc}")
        _fail("forecast", repr(exc))
        return None

    try:
        code = int(current.get("weather_code", -1))
        LAST_ERROR.clear()
        return {
            "temp": round(float(current["temperature_2m"])),
            "feels_like": round(float(current["apparent_temperature"])),
            "humidity": int(current["relative_humidity_2m"]),
            "wind": round(float(current.get("wind_speed_10m", 0)), 1),
            "desc": _DESCRIPTIONS.get(code, "Unknown"),
            "desc_bn": _DESCRIPTIONS_BN.get(code, "অজানা"),
            "city": resolved,
            "source": "open-meteo",
        }
    except (KeyError, TypeError, ValueError) as exc:
        print(f"⚠️ Incomplete weather data for {city}: {exc}")
        _fail("forecast", repr(exc))
        return None
