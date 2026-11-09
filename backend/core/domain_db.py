# backend/core/domain_db.py — shared SQLite helper for phase-1 domain modules

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path


def connect(db_path):
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init(db_path, schema: str):
    conn = connect(db_path)
    conn.executescript(schema)
    conn.commit()
    return conn


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def since(days: float) -> str:
    return (datetime.now() - timedelta(days=days)).isoformat(timespec="seconds")


def day_start(offset_days: int = 0) -> str:
    d = datetime.now() - timedelta(days=offset_days)
    return d.replace(hour=0, minute=0, second=0, microsecond=0).isoformat(timespec="seconds")


def clamp(value: float, low: float = 0, high: float = 100) -> float:
    return max(low, min(high, value))
