"""SQLite-backed user memory service for CoursePilot."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from app.db import get_connection, initialize_database, resolve_db_path


class MemoryService:
    """Provide simple structured user memory storage and retrieval."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = resolve_db_path(db_path)
        with get_connection(self.db_path) as connection:
            initialize_database(connection)

    def _timestamp(self) -> str:
        """Return a stable UTC timestamp string."""
        return datetime.now(timezone.utc).isoformat()

    def save_user_profile(self, user_id: str, profile: dict[str, Any]) -> None:
        """Insert or update a structured user profile payload."""
        with get_connection(self.db_path) as connection:
            initialize_database(connection)
            existing_row = connection.execute(
                "SELECT profile_json FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            existing_profile = json.loads(existing_row["profile_json"]) if existing_row else {}
            merged_profile = {**existing_profile, **profile}

            connection.execute(
                """
                INSERT INTO users (user_id, profile_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    profile_json = excluded.profile_json,
                    updated_at = excluded.updated_at
                """,
                (user_id, json.dumps(merged_profile), self._timestamp()),
            )
            connection.commit()

    def get_user_profile(self, user_id: str) -> dict[str, Any]:
        """Load a stored user profile or an empty profile."""
        with get_connection(self.db_path) as connection:
            initialize_database(connection)
            row = connection.execute(
                "SELECT profile_json FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()

        if row is None:
            return {}
        return json.loads(row["profile_json"])

    def upsert_memory(self, user_id: str, memory_type: str, key: str, value: Any) -> None:
        """Insert or update one structured memory item."""
        self.save_user_profile(user_id, {})
        with get_connection(self.db_path) as connection:
            initialize_database(connection)
            connection.execute(
                """
                INSERT INTO memories (user_id, memory_type, key, value_json, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id, memory_type, key) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at = excluded.updated_at
                """,
                (user_id, memory_type, key, json.dumps(value), self._timestamp()),
            )
            connection.commit()

    def get_memories(self, user_id: str, memory_type: str | None = None) -> list[dict[str, Any]]:
        """Load structured memory rows for a user."""
        with get_connection(self.db_path) as connection:
            initialize_database(connection)
            if memory_type is None:
                rows = connection.execute(
                    """
                    SELECT memory_type, key, value_json
                    FROM memories
                    WHERE user_id = ?
                    ORDER BY memory_type, key
                    """,
                    (user_id,),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT memory_type, key, value_json
                    FROM memories
                    WHERE user_id = ? AND memory_type = ?
                    ORDER BY key
                    """,
                    (user_id, memory_type),
                ).fetchall()

        return [
            {
                "memory_type": row["memory_type"],
                "key": row["key"],
                "value": json.loads(row["value_json"]),
            }
            for row in rows
        ]

    def get_preferences(self, user_id: str) -> dict[str, Any]:
        """Return stored preference memories keyed by preference name."""
        preference_memories = self.get_memories(user_id, memory_type="preference")
        return {memory["key"]: memory["value"] for memory in preference_memories}

    def record_rejected_course(self, user_id: str, course_id: str, reason: str) -> None:
        """Persist one rejected-course memory item."""
        self.upsert_memory(user_id, "rejected_course", course_id, reason)

    def load_user_context(self, user_id: str) -> dict[str, Any]:
        """Load the minimal profile and preference context used by planning."""
        profile = self.get_user_profile(user_id)
        preferences = self.get_preferences(user_id)
        rejected_courses = {
            memory["key"]: memory["value"]
            for memory in self.get_memories(user_id, memory_type="rejected_course")
        }
        return {
            "user_id": user_id,
            "profile": profile,
            "completed_courses": profile.get("completed_courses", []),
            "preferred_directions": preferences.get(
                "preferred_directions",
                profile.get("preferred_directions", []),
            ),
            "rejected_courses": rejected_courses,
        }

    def get_debug_view(self, user_id: str, memory_type: str | None = None) -> dict[str, Any]:
        """Return a read-only debug snapshot of stored user memory."""
        return {
            "user_id": user_id,
            "profile": self.get_user_profile(user_id),
            "entries": self.get_memories(user_id, memory_type=memory_type),
        }
