# backend/bangladesh/bd_currency.py — BDT exchange rates (open.er-api.com)

import time

import requests

_API = "https://open.er-api.com/v6/latest/{base}"
_MAJORS = ("USD", "EUR", "GBP", "INR", "SAR", "AED", "MYR", "JPY", "CNY", "KWD", "QAR")
_CACHE = {}
_TTL = 6 * 3600


class BDCurrency:
    def rates(self, base: str = "BDT"):
        base = (base or "BDT").upper()
        cached = _CACHE.get(base)
        if cached and time.time() - cached[0] < _TTL:
            return cached[1]

        try:
            resp = requests.get(_API.format(base=base), timeout=10, headers={"User-Agent": "Atlas/7.0"})
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            return {"base": base, "available": False, "rates": {}, "error": str(e)}

        raw = data.get("rates") or {}
        rates = {code: raw[code] for code in _MAJORS if code in raw}
        bdt_per_unit = {}
        if base == "BDT":
            bdt_per_unit = {code: round(1 / value, 4) for code, value in rates.items() if value}
        result = {
            "base": base,
            "available": True,
            "date": data.get("time_last_update_utc"),
            "rates": rates,
            "bdt_per_unit": bdt_per_unit,
        }
        _CACHE[base] = (time.time(), result)
        return result


currency = BDCurrency()
