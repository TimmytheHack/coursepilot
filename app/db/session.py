"""SQLite session helpers for CoursePilot persistence."""

from __future__ import annotations

import os
from pathlib import Path
import sqlite3

DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "coursepilot.db"


def resolve_db_path(db_path: str | Path | None = None) -> Path:
    """Resolve the SQLite database path from an override or environment."""
    if db_path is not None:
        return Path(db_path)

    configured_path = os.getenv("COURSEPILOT_DB_PATH")
    if configured_path:
        return Path(configured_path)
    return DEFAULT_DB_PATH


def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Open a SQLite connection with row access enabled."""
    path = resolve_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database(connection: sqlite3.Connection) -> None:
    """Create the MVP persistence schema if it does not already exist."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            profile_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            memory_type TEXT NOT NULL,
            key TEXT NOT NULL,
            value_json TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(user_id, memory_type, key),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );
        """
    )
    connection.commit()
