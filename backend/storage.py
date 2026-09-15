import sqlite3
import json
import os
import time
from contextlib import contextmanager

DB_PATH = os.getenv("KOS_DB_PATH", "knowledge_os.db")


def init_db():
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT,
                source_url TEXT,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                tags TEXT NOT NULL,          -- JSON array
                extraction_source TEXT,      -- 'api' | 'yt-dlp' | 'manual'
                created_at REAL NOT NULL
            )
        """)


@contextmanager
def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def save_card(video_id, source_url, title, summary, tags, extraction_source):
    with _conn() as c:
        cur = c.execute(
            """INSERT INTO cards (video_id, source_url, title, summary, tags, extraction_source, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (video_id, source_url, title, summary, json.dumps(tags), extraction_source, time.time()),
        )
        return cur.lastrowid


def list_cards(tag: str | None = None):
    with _conn() as c:
        rows = c.execute("SELECT * FROM cards ORDER BY created_at DESC").fetchall()
    cards = [_row_to_dict(r) for r in rows]
    if tag:
        cards = [card for card in cards if tag.lower() in [t.lower() for t in card["tags"]]]
    return cards


def get_card(card_id: int):
    with _conn() as c:
        row = c.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
    return _row_to_dict(row) if row else None


def all_tags():
    with _conn() as c:
        rows = c.execute("SELECT tags FROM cards").fetchall()
    tag_counts = {}
    for r in rows:
        for t in json.loads(r["tags"]):
            tag_counts[t] = tag_counts.get(t, 0) + 1
    return sorted(tag_counts.items(), key=lambda kv: -kv[1])


def _row_to_dict(row):
    d = dict(row)
    d["tags"] = json.loads(d["tags"])
    return d
