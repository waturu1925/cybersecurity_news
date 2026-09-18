import json
import sqlite3
from contextlib import closing
from datetime import datetime

from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
    channel TEXT NOT NULL DEFAULT 'news',
    source TEXT NOT NULL,
    kind TEXT NOT NULL,
    title_orig TEXT NOT NULL,
    summary_orig TEXT NOT NULL DEFAULT '',
    title_ja TEXT,
    summary_ja TEXT,
    body_ja TEXT,
    published TEXT NOT NULL,
    base_score INTEGER NOT NULL,
    reasons TEXT NOT NULL,
    category TEXT NOT NULL,
    cves TEXT NOT NULL,
    extra TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_items_published ON items(published);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""


def _connect():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def init():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(_connect()) as conn:
        conn.executescript(SCHEMA)
        columns = {r["name"] for r in conn.execute("PRAGMA table_info(items)")}
        if "channel" not in columns:
            conn.execute("ALTER TABLE items ADD COLUMN channel TEXT NOT NULL DEFAULT 'news'")
            conn.commit()


def _to_dict(row):
    item = dict(row)
    for key in ("reasons", "cves", "extra"):
        item[key] = json.loads(item[key])
    item["published"] = datetime.fromisoformat(item["published"])
    return item


def existing_urls(urls):
    if not urls:
        return set()
    with closing(_connect()) as conn:
        found = set()
        urls = list(urls)
        # SQLite のパラメータ数上限を避けるため分割して問い合わせる
        for i in range(0, len(urls), 500):
            part = urls[i:i + 500]
            marks = ",".join("?" * len(part))
            found |= {r[0] for r in conn.execute(f"SELECT url FROM items WHERE url IN ({marks})", part)}
        return found


def insert(item):
    with closing(_connect()) as conn, conn:
        conn.execute(
            """INSERT OR IGNORE INTO items
               (url, channel, source, kind, title_orig, summary_orig, published, base_score, reasons, category, cves, extra)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                item["url"], item["channel"], item["source"], item["kind"], item["title_orig"], item["summary_orig"],
                item["published"].isoformat(), item["base_score"],
                json.dumps(item["reasons"], ensure_ascii=False), item["category"],
                json.dumps(item["cves"]), json.dumps(item.get("extra", {}), ensure_ascii=False),
            ),
        )


def update_score(item):
    with closing(_connect()) as conn, conn:
        conn.execute(
            "UPDATE items SET base_score = ?, reasons = ?, category = ?, cves = ? WHERE id = ?",
            (
                item["base_score"], json.dumps(item["reasons"], ensure_ascii=False),
                item["category"], json.dumps(item["cves"]), item["id"],
            ),
        )


def untranslated():
    with closing(_connect()) as conn:
        return [dict(r) for r in conn.execute(
            "SELECT id, title_orig, summary_orig FROM items WHERE title_ja IS NULL ORDER BY published DESC"
        )]


def set_translation(item_id, title_ja, summary_ja):
    with closing(_connect()) as conn, conn:
        conn.execute("UPDATE items SET title_ja = ?, summary_ja = ? WHERE id = ?", (title_ja, summary_ja, item_id))


def set_body(item_id, body_ja):
    with closing(_connect()) as conn, conn:
        conn.execute("UPDATE items SET body_ja = ? WHERE id = ?", (body_ja, item_id))


def items_since(since, channel=None):
    sql, params = "SELECT * FROM items WHERE published >= ?", [since.isoformat()]
    if channel:
        sql += " AND channel = ?"
        params.append(channel)
    with closing(_connect()) as conn:
        return [_to_dict(r) for r in conn.execute(sql, params)]


def count(channel):
    with closing(_connect()) as conn:
        return conn.execute("SELECT COUNT(*) FROM items WHERE channel = ?", (channel,)).fetchone()[0]


def get(item_id):
    with closing(_connect()) as conn:
        row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
        return _to_dict(row) if row else None


def purge_before(before, channel):
    with closing(_connect()) as conn, conn:
        conn.execute("DELETE FROM items WHERE published < ? AND channel = ?", (before.isoformat(), channel))


def get_meta(key):
    with closing(_connect()) as conn:
        row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None


def set_meta(key, value):
    with closing(_connect()) as conn, conn:
        conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, value))
