import sqlite3
import json
import os
from pathlib import Path
from typing import Optional
from core.models import Asset


class Database:
    def __init__(self, db_path: str = "./database/clipforge.db"):
        self.db_path = db_path
        self._ensure_dir()
        self.conn: Optional[sqlite3.Connection] = None

    def _ensure_dir(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
        return self.conn

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def init_tables(self):
        conn = self.connect()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file TEXT NOT NULL UNIQUE,
                type TEXT NOT NULL CHECK(type IN ('video', 'image', 'bgm', 'voice')),
                duration REAL,
                width INTEGER DEFAULT 0,
                height INTEGER DEFAULT 0,
                tags TEXT DEFAULT '',
                file_size INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT DEFAULT (datetime('now', 'localtime'))
            );

            CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(type);
            CREATE INDEX IF NOT EXISTS idx_assets_file ON assets(file);

            CREATE TABLE IF NOT EXISTS scripts_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                content TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            );
        """)
        conn.commit()

    def add_asset(self, asset: Asset) -> int:
        conn = self.connect()
        tags_str = ",".join(asset.tags)
        cursor = conn.execute(
            """INSERT OR REPLACE INTO assets (file, type, duration, width, height, tags, file_size)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (asset.file, asset.type, asset.duration, asset.width, asset.height, tags_str, asset.file_size),
        )
        conn.commit()
        return cursor.lastrowid or 0

    def add_assets_batch(self, assets: list[Asset]) -> int:
        conn = self.connect()
        count = 0
        for asset in assets:
            try:
                tags_str = ",".join(asset.tags)
                conn.execute(
                    """INSERT OR REPLACE INTO assets (file, type, duration, width, height, tags, file_size)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (asset.file, asset.type, asset.duration, asset.width, asset.height, tags_str, asset.file_size),
                )
                count += 1
            except sqlite3.Error:
                pass
        conn.commit()
        return count

    def get_asset(self, asset_id: int) -> Optional[Asset]:
        conn = self.connect()
        row = conn.execute("SELECT * FROM assets WHERE id = ?", (asset_id,)).fetchone()
        return self._row_to_asset(row) if row else None

    def get_asset_by_file(self, file: str) -> Optional[Asset]:
        conn = self.connect()
        row = conn.execute("SELECT * FROM assets WHERE file = ?", (file,)).fetchone()
        return self._row_to_asset(row) if row else None

    def search_assets(self, keyword: str = "", type_filter: str = "", limit: int = 100) -> list[Asset]:
        conn = self.connect()
        query = "SELECT * FROM assets WHERE 1=1"
        params = []

        if keyword:
            query += " AND tags LIKE ?"
            params.append(f"%{keyword}%")
        if type_filter:
            query += " AND type = ?"
            params.append(type_filter)

        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        return [self._row_to_asset(r) for r in rows]

    def get_all_assets(self) -> list[Asset]:
        conn = self.connect()
        rows = conn.execute("SELECT * FROM assets ORDER BY updated_at DESC").fetchall()
        return [self._row_to_asset(r) for r in rows]

    def get_asset_count(self) -> dict[str, int]:
        conn = self.connect()
        total = conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0]
        rows = conn.execute("SELECT type, COUNT(*) as cnt FROM assets GROUP BY type").fetchall()
        by_type = {row["type"]: row["cnt"] for row in rows}
        return {"total": total, **by_type}

    def update_asset_tags(self, asset_id: int, tags: list[str]):
        conn = self.connect()
        tags_str = ",".join(tags)
        conn.execute(
            "UPDATE assets SET tags = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
            (tags_str, asset_id),
        )
        conn.commit()

    def delete_asset(self, asset_id: int):
        conn = self.connect()
        conn.execute("DELETE FROM assets WHERE id = ?", (asset_id,))
        conn.commit()

    def delete_asset_by_file(self, file: str):
        conn = self.connect()
        conn.execute("DELETE FROM assets WHERE file = ?", (file,))
        conn.commit()

    def file_exists(self, file: str) -> bool:
        conn = self.connect()
        row = conn.execute("SELECT 1 FROM assets WHERE file = ?", (file,)).fetchone()
        return row is not None

    def add_script_history(self, title: str, content: str):
        conn = self.connect()
        conn.execute("INSERT INTO scripts_history (title, content) VALUES (?, ?)", (title, content))
        conn.commit()

    def get_script_history(self, limit: int = 20) -> list[dict]:
        conn = self.connect()
        rows = conn.execute(
            "SELECT id, title, created_at FROM scripts_history ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def _row_to_asset(self, row: sqlite3.Row) -> Asset:
        return Asset(
            id=row["id"],
            file=row["file"],
            type=row["type"],
            duration=row["duration"],
            width=row["width"],
            height=row["height"],
            tags=row["tags"].split(",") if row["tags"] else [],
            file_size=row["file_size"],
            created_at=row["created_at"],
        )
