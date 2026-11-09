# backend/security/password_manager.py — password generator + strength meter (never stores passwords)

import math
import secrets
import string

_SETS = {
    "lower": string.ascii_lowercase,
    "upper": string.ascii_uppercase,
    "digits": string.digits,
    "symbols": "!@#$%^&*()-_=+[]{};:,.?/",
}


class PasswordManager:
    def generate(self, length: int = 16, symbols: bool = True):
        length = max(8, min(int(length), 128))
        pool = _SETS["lower"] + _SETS["upper"] + _SETS["digits"] + (_SETS["symbols"] if symbols else "")
        candidate = ""
        for _ in range(10):
            candidate = "".join(secrets.choice(pool) for _ in range(length))
            if self.strength(candidate)["score"] >= 80:
                return candidate
        return candidate

    def strength(self, password: str):
        password = password or ""
        classes = sum([
            any(c.islower() for c in password),
            any(c.isupper() for c in password),
            any(c.isdigit() for c in password),
            any(c in _SETS["symbols"] for c in password),
        ])
        pool_size = sum(len(_SETS[k]) for k, check in (
            ("lower", any(c.islower() for c in password)),
            ("upper", any(c.isupper() for c in password)),
            ("digits", any(c.isdigit() for c in password)),
            ("symbols", any(c in _SETS["symbols"] for c in password)),
        ) if check) or 1
        entropy = len(password) * math.log2(pool_size) if password else 0
        score = round(min(100, entropy / 100 * 100))
        if len(password) < 8:
            score = min(score, 30)
        label = "weak" if score < 40 else "medium" if score < 65 else "strong" if score < 85 else "excellent"
        return {
            "score": int(score),
            "label": label,
            "length": len(password),
            "classes": classes,
            "entropy_bits": round(entropy, 1),
            "suggestions": self._suggestions(password, classes),
        }

    @staticmethod
    def _suggestions(password, classes):
        tips = []
        if len(password) < 12:
            tips.append("Use at least 12 characters")
        if classes < 3:
            tips.append("Mix upper/lower case, digits and symbols")
        if password.lower() in ("password", "123456", "qwerty", "admin", "atlas"):
            tips.append("This is a commonly used password")
        return tips


password_manager = PasswordManager()
