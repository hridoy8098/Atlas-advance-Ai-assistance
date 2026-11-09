# backend/security/privacy_mode.py — privacy flag + screen/mic hints

import threading

import config
from backend.core.domain_db import init, now

_DB = config.DATA_DIR / "atlas_security.db"
_SCHEMA = """
CREATE TABLE IF NOT EXISTS privacy (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    enabled INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT
);
"""


class PrivacyMode:
    def __init__(self):
        self._lock = threading.Lock()
        self._conn = init(_DB, _SCHEMA)
        self._conn.execute("INSERT OR IGNORE INTO privacy (id, enabled) VALUES (1, 0)")
        self._conn.commit()

    def _set(self, enabled: bool):
        with self._lock:
            self._conn.execute(
                "UPDATE privacy SET enabled = ?, updated_at = ? WHERE id = 1", (1 if enabled else 0, now())
            )
            self._conn.commit()
        return {
            "enabled": enabled,
            "actions": ["microphone listening paused" if enabled else "microphone listening allowed",
                        "screen watermark recommended" if enabled else "watermark optional"],
        }

    def enable(self):
        return self._set(True)

    def disable(self):
        return self._set(False)

    def status(self):
        with self._lock:
            row = self._conn.execute("SELECT enabled, updated_at FROM privacy WHERE id = 1").fetchone()
        return {"enabled": bool(row["enabled"]) if row else False,
                "updated_at": row["updated_at"] if row else None}


privacy_mode = PrivacyMode()
