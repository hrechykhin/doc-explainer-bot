import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

DB_PATH = Path("data/app.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@dataclass
class DocRecord:
    file_hash: str
    filename: str
    text: str
    map_summaries_json: str  # JSON list of chunk summaries


def _conn() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.execute("""
    CREATE TABLE IF NOT EXISTS docs (
        file_hash TEXT PRIMARY KEY,
        filename TEXT NOT NULL,
        text TEXT NOT NULL,
        map_summaries_json TEXT
    )
    """)
    con.execute("""
    CREATE TABLE IF NOT EXISTS user_state (
        user_id INTEGER PRIMARY KEY,
        current_file_hash TEXT
    )
    """)
    return con


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def get_doc(file_hash: str) -> Optional[DocRecord]:
    con = _conn()
    row = con.execute(
        "SELECT file_hash, filename, text, map_summaries_json FROM docs WHERE file_hash=?",
        (file_hash,),
    ).fetchone()
    con.close()
    if not row:
        return None
    return DocRecord(*row)


def upsert_doc(
    file_hash: str, filename: str, text: str, map_summaries_json: str | None
) -> None:
    con = _conn()
    con.execute(
        "INSERT INTO docs(file_hash, filename, text, map_summaries_json) VALUES (?,?,?,?) "
        "ON CONFLICT(file_hash) DO UPDATE SET filename=excluded.filename, text=excluded.text, map_summaries_json=excluded.map_summaries_json",
        (file_hash, filename, text, map_summaries_json),
    )
    con.commit()
    con.close()


def set_user_current_doc(user_id: int, file_hash: str) -> None:
    con = _conn()
    con.execute(
        "INSERT INTO user_state(user_id, current_file_hash) VALUES (?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET current_file_hash=excluded.current_file_hash",
        (user_id, file_hash),
    )
    con.commit()
    con.close()


def get_user_current_doc(user_id: int) -> Optional[str]:
    con = _conn()
    row = con.execute(
        "SELECT current_file_hash FROM user_state WHERE user_id=?", (user_id,)
    ).fetchone()
    con.close()
    return row[0] if row else None
