"""Key-free weather lookup shared by the API and the voice command handler.

OpenWeatherMap rejected the configured key with 401, and Render's shared egress
IP quickly exhausts Open-Meteo's free daily quota. The lookup therefore tries a
small chain of key-free providers:

1. Open-Meteo  - fast and structured (temperatures, humidity, wind)
2. wttr.in     - also provides feels-like temperature
3. MET Norway  - government service, needs a descriptive User-Agent
"""

from typing import Any, Dict, Optional, Tuple
from urllib.parse import quote

import requests


# Updated on every failure so the API can explain why a lookup returned 503.
LAST_ERROR: Dict[str, Any] = {}


def _fail(stage: str, message: Any, status: Optional[int] = None) -> None:
    entry = {
        "stage": stage,
        "status": status,
        "message": str(message)[:300],
    }
    attempts = LAST_ERROR.setdefault("attempts", [])
    attempts.append(entry)
    del attempts[:-5]
    LAST_ERROR.update(entry)


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


def _describe_bn(text: str) -> str:
    """Best-effort Bengali label for a provider's free-form description."""
    value = (text or "").lower()
    if "thunder" in value:
        return "বজ্রঝড়"
    if "heavy rain" in value:
        return "ভারী বৃষ্টি"
    if "moderate rain" in value:
        return "মাঝারি বৃষ্টি"
    if "light rain" in value or "drizzle" in value or "patchy rain" in value:
        return "হালকা বৃষ্টি"
    if "rain" in value:
        return "বৃষ্টি"
    if "heavy snow" in value:
        return "ভারী তুষারপাত"
    if "snow" in value or "sleet" in value:
        return "তুষারপাত"
    if "fog" in value or "mist" in value:
        return "কুয়াশা"
    if "haze" in value or "smoke" in value:
        return "ধোঁয়াশা"
    if "overcast" in value:
        return "মেঘাচ্ছন্ন"
    if "partly" in value:
        return "আংশিক মেঘলা"
    if "cloud" in value:
        return "মেঘলা"
    if "clear" in value or "sunny" in value:
        return "পরিষ্কার আকাশ"
    return "অজানা"


def _symbol_description(symbol: str) -> str:
    """Turn a MET Norway symbol (clearsky_day, heavyrain, ...) into text."""
    value = (symbol or "").lower()
    for suffix in ("_day", "_night", "_polartwilight"):
        value = value.replace(suffix, "")
    mapping = {
        "clearsky": "Clear sky",
        "fair": "Mainly clear",
        "partlycloudy": "Partly cloudy",
        "cloudy": "Cloudy",
        "fog": "Fog",
        "lightrain": "Light rain",
        "rain": "Rain",
        "heavyrain": "Heavy rain",
        "lightrainshowers": "Light rain showers",
        "rainshowers": "Rain showers",
        "heavyrainshowers": "Heavy rain showers",
        "lightsleet": "Light sleet",
        "sleet": "Sleet",
        "heavysleet": "Heavy sleet",
        "lightsnow": "Light snow",
        "snow": "Snow",
        "heavysnow": "Heavy snow",
        "lightsnowshowers": "Light snow showers",
        "snowshowers": "Snow showers",
        "heavysnowshowers": "Heavy snow showers",
        "rainandthunder": "Thunderstorm",
        "rainshowersandthunder": "Thunderstorm with rain showers",
        "sleetandthunder": "Thunderstorm with sleet",
        "snowandthunder": "Thunderstorm with snow",
    }
    return mapping.get(value, value.replace("_", " ").title() or "Unknown")


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


def _open_meteo(resolved: str, latitude: float, longitude: float, timeout: float) -> Optional[dict]:
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
            _fail("open-meteo", response.text[:200], response.status_code)
            return None
        current = (response.json() or {}).get("current") or {}
        code = int(current.get("weather_code", -1))
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
        _fail("open-meteo", repr(exc))
        return None
    except Exception as exc:
        print(f"⚠️ Open-Meteo lookup failed for {resolved}: {exc}")
        _fail("open-meteo", repr(exc))
        return None


def _wttr(city: str, display_city: str, timeout: float) -> Optional[dict]:
    try:
        response = requests.get(
            f"https://wttr.in/{quote(city)}",
            params={"format": "j1"},
            headers={"User-Agent": "AtlasAssistant/7.0"},
            timeout=timeout,
        )
        if response.status_code != 200:
            _fail("wttr.in", response.text[:200], response.status_code)
            return None
        body = response.json() or {}
        current = (body.get("current_condition") or [{}])[0]
        desc = ((current.get("weatherDesc") or [{}])[0].get("value") or "Unknown").strip()

        return {
            "temp": round(float(current["temp_C"])),
            "feels_like": round(float(current.get("FeelsLikeC", current["temp_C"]))),
            "humidity": int(current["humidity"]),
            "wind": round(float(current.get("windspeedKmph", 0)) / 3.6, 1),
            "desc": desc,
            "desc_bn": _describe_bn(desc),
            # wttr's nearest_area can be a neighbourhood (e.g. "Ahybnagar"
            # for Dhaka), which is confusing in a voice reply.
            "city": display_city or city,
            "source": "wttr.in",
        }
    except (KeyError, TypeError, ValueError) as exc:
        _fail("wttr.in", repr(exc))
        return None
    except Exception as exc:
        print(f"⚠️ wttr.in lookup failed for {city}: {exc}")
        _fail("wttr.in", repr(exc))
        return None


def _met_no(resolved: str, latitude: float, longitude: float, timeout: float) -> Optional[dict]:
    try:
        response = requests.get(
            "https://api.met.no/weatherapi/locationforecast/2.0/compact",
            params={"lat": latitude, "lon": longitude},
            headers={
                "User-Agent": (
                    "AtlasAssistant/7.0 "
                    "github.com/hridoy8098/Atlas-advance-Ai-assistance"
                )
            },
            timeout=timeout,
        )
        if response.status_code != 200:
            _fail("met.no", response.text[:200], response.status_code)
            return None
        series = (((response.json() or {}).get("properties") or {}).get("timeseries") or [])
        if not series:
            _fail("met.no", "empty timeseries")
            return None
        details = (((series[0].get("data") or {}).get("instant") or {}).get("details") or {})
        symbol = (
            (((series[0].get("data") or {}).get("next_1_hours") or {})
             .get("summary") or {})
            .get("symbol_code") or ""
        )
        desc = _symbol_description(symbol)
        temperature = float(details["air_temperature"])
        return {
            "temp": round(temperature),
            # MET Norway has no apparent temperature; the real value is still
            # reported separately so the UI keeps working.
            "feels_like": round(temperature),
            "humidity": int(details.get("relative_humidity", 0)),
            "wind": round(float(details.get("wind_speed", 0)), 1),
            "desc": desc,
            "desc_bn": _describe_bn(desc),
            "city": resolved,
            "source": "met.no",
        }
    except (KeyError, TypeError, ValueError) as exc:
        _fail("met.no", repr(exc))
        return None
    except Exception as exc:
        print(f"⚠️ MET Norway lookup failed for {resolved}: {exc}")
        _fail("met.no", repr(exc))
        return None


def get_weather(city: str = "Dhaka", timeout: float = 6) -> Optional[dict]:
    """Return current weather for `city`, or None when every provider fails."""
    city = (city or "Dhaka").strip()
    if not city:
        city = "Dhaka"

    known = _CITY_COORDS.get(city.lower())
    if known:
        resolved, latitude, longitude = known
    else:
        geocoded = _geocode(city, timeout)
        if geocoded:
            resolved, latitude, longitude = geocoded
        else:
            resolved, latitude, longitude = city, None, None

    providers = []
    if latitude is not None and longitude is not None:
        providers.append(lambda: _open_meteo(resolved, latitude, longitude, timeout))
    providers.append(lambda: _wttr(city, resolved, timeout))
    if latitude is not None and longitude is not None:
        providers.append(lambda: _met_no(resolved, latitude, longitude, timeout))

    for provider in providers:
        result = provider()
        if result:
            LAST_ERROR.clear()
            return result

    return None
