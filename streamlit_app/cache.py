"""SQLite cache of finished answers, so a repeated question costs no tokens."""
import hashlib
import json
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path(__file__).resolve().parent / ".state" / "answers.sqlite"
MAX_ROWS = 1000


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS answers (key TEXT PRIMARY KEY, payload TEXT NOT NULL, created REAL NOT NULL)")
    return conn


def _normalize(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9$ ]+", " ", text.lower()).split())


def make_key(*parts: Any, questions: List[str]) -> str:
    raw = "|".join([*map(str, parts), *(_normalize(q) for q in questions)])
    return hashlib.sha256(raw.encode()).hexdigest()


def get(key: str) -> Optional[Dict[str, Any]]:
    with _connect() as conn:
        row = conn.execute("SELECT payload FROM answers WHERE key = ?", (key,)).fetchone()
    return json.loads(row[0]) if row else None


def put(key: str, payload: Dict[str, Any]) -> None:
    with _connect() as conn:
        conn.execute("INSERT OR REPLACE INTO answers VALUES (?, ?, ?)", (key, json.dumps(payload), time.time()))
        conn.execute("DELETE FROM answers WHERE key NOT IN (SELECT key FROM answers ORDER BY created DESC LIMIT ?)", (MAX_ROWS,))


def clear() -> int:
    with _connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM answers").fetchone()[0]
        conn.execute("DELETE FROM answers")
    return count


def size() -> int:
    with _connect() as conn:
        return conn.execute("SELECT COUNT(*) FROM answers").fetchone()[0]
