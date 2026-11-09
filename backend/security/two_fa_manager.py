# backend/security/two_fa_manager.py — TOTP (RFC 6238) without external deps

import base64
import hashlib
import hmac
import secrets
import struct
import threading
import time
from urllib.parse import quote

import config
from backend.core.domain_db import init, now

_DB = config.DATA_DIR / "atlas_security.db"
_SCHEMA = """
CREATE TABLE IF NOT EXISTS two_fa (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    secret TEXT,
    enabled INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT
);
"""


def _b32decode(secret: str) -> bytes:
    secret = secret.strip().replace(" ", "").upper()
    secret += "=" * (-len(secret) % 8)
    return base64.b32decode(secret, casefold=True)


class TwoFAManager:
    STEP = 30
    DIGITS = 6

    def __init__(self):
        self._lock = threading.Lock()
        self._conn = init(_DB, _SCHEMA)

    def generate_secret(self, account: str = "atlas"):
        secret = base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")
        return secret

    def provisioning_uri(self, secret: str, account: str = "atlas", issuer: str = "ATLAS"):
        label = quote(f"{issuer}:{account}")
        return (
            f"otpauth://totp/{label}?secret={secret}&issuer={quote(issuer)}"
            f"&algorithm=SHA1&digits={self.DIGITS}&period={self.STEP}"
        )

    def code(self, secret: str, timestamp: float = None) -> str:
        counter = int((timestamp or time.time()) // self.STEP)
        digest = hmac.new(_b32decode(secret), struct.pack(">Q", counter), hashlib.sha1).digest()
        offset = digest[-1] & 0x0F
        value = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
        return str(value % (10 ** self.DIGITS)).zfill(self.DIGITS)

    def verify(self, secret: str, code: str, window: int = 1) -> bool:
        if not secret or not code:
            return False
        code = str(code).strip()
        now_ts = time.time()
        try:
            return any(
                hmac.compare_digest(self.code(secret, now_ts + offset * self.STEP), code)
                for offset in range(-window, window + 1)
            )
        except Exception:
            return False

    def enable(self, secret: str):
        with self._lock:
            self._conn.execute(
                "INSERT INTO two_fa (id, secret, enabled, updated_at) VALUES (1, ?, 1, ?) "
                "ON CONFLICT(id) DO UPDATE SET secret = excluded.secret, enabled = 1, updated_at = excluded.updated_at",
                (secret, now()),
            )
            self._conn.commit()
        return {"enabled": True}

    def disable(self):
        with self._lock:
            self._conn.execute(
                "INSERT INTO two_fa (id, secret, enabled, updated_at) VALUES (1, NULL, 0, ?) "
                "ON CONFLICT(id) DO UPDATE SET secret = NULL, enabled = 0, updated_at = excluded.updated_at",
                (now(),),
            )
            self._conn.commit()
        return {"enabled": False}

    def status(self):
        with self._lock:
            row = self._conn.execute("SELECT secret, enabled, updated_at FROM two_fa WHERE id = 1").fetchone()
        return {
            "enabled": bool(row["enabled"]) if row else False,
            "configured": bool(row["secret"]) if row else False,
            "updated_at": row["updated_at"] if row else None,
        }


two_fa = TwoFAManager()
