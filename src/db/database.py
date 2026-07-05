from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import TypeVar

import asyncpg

from src.db.models import (
    Chat,
    DailyStats,
    Favorite,
    Memory,
    Message,
    Reminder,
    Todo,
    UserSettings,
)

ModelT = TypeVar("ModelT")


class Database:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        self._pool = await asyncpg.create_pool(self._database_url, min_size=1, max_size=10)

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def initialize_schema(self) -> None:
        schema_path = Path(__file__).with_name("schema.sql")
        await self.pool.execute(schema_path.read_text(encoding="utf-8"))

    @property
    def pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("База данных не подключена")
        return self._pool

    async def has_access(self, user_id: int, admin_user_id: int) -> bool:
        if user_id == admin_user_id:
            return True
        query = "SELECT EXISTS(SELECT 1 FROM whitelist WHERE user_id = $1)"
        return bool(await self.pool.fetchval(query, user_id))

    async def add_to_whitelist(self, user_id: int, added_by: int) -> None:
        query = """
            INSERT INTO whitelist (user_id, added_by) VALUES ($1, $2)
            ON CONFLICT (user_id) DO NOTHING
        """
        await self.pool.execute(query, user_id, added_by)

    async def remove_from_whitelist(self, user_id: int) -> bool:
        result = await self.pool.execute("DELETE FROM whitelist WHERE user_id = $1", user_id)
        return result == "DELETE 1"

    async def list_whitelist(self) -> list[int]:
        rows = await self.pool.fetch("SELECT user_id FROM whitelist ORDER BY created_at")
        return [row["user_id"] for row in rows]

    async def ensure_settings(self, user_id: int) -> UserSettings:
        query = """
            INSERT INTO settings (user_id) VALUES ($1)
            ON CONFLICT (user_id) DO UPDATE SET user_id = EXCLUDED.user_id
            RETURNING *
        """
        return self._model(UserSettings, await self.pool.fetchrow(query, user_id))

    async def update_setting(self, user_id: int, field: str, value: str) -> UserSettings:
        allowed = {"style", "language", "mode"}
        if field not in allowed:
            raise ValueError("Неизвестная настройка")
        await self.ensure_settings(user_id)
        query = f"UPDATE settings SET {field} = $2 WHERE user_id = $1 RETURNING *"
        return self._model(UserSettings, await self.pool.fetchrow(query, user_id, value))

    async def set_panel_message_id(self, user_id: int, message_id: int) -> None:
        await self.ensure_settings(user_id)
        query = "UPDATE settings SET panel_message_id = $2 WHERE user_id = $1"
        await self.pool.execute(query, user_id, message_id)

    async def create_chat(self, user_id: int, title: str) -> Chat:
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute(
                    "UPDATE chats SET status = 'idle' WHERE user_id = $1 AND status = 'active'",
                    user_id,
                )
                row = await connection.fetchrow(
                    "INSERT INTO chats (user_id, title) VALUES ($1, $2) RETURNING *",
                    user_id,
                    title,
                )
        return self._model(Chat, row)

    async def get_active_chat(self, user_id: int) -> Chat | None:
        row = await self.pool.fetchrow(
            "SELECT * FROM chats WHERE user_id = $1 AND status = 'active'", user_id
        )
        return self._optional_model(Chat, row)

    async def list_chats(self, user_id: int, include_archived: bool = False) -> list[Chat]:
        condition = "" if include_archived else "AND status <> 'archived'"
        query = f"""
            SELECT * FROM chats WHERE user_id = $1 {condition}
            ORDER BY is_pinned DESC, updated_at DESC
        """
        return self._models(Chat, await self.pool.fetch(query, user_id))

    async def switch_chat(self, user_id: int, chat_id: int) -> Chat | None:
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                exists = await connection.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM chats WHERE id = $1 AND user_id = $2)",
                    chat_id,
                    user_id,
                )
                if not exists:
                    return None
                await connection.execute(
                    "UPDATE chats SET status = 'idle' WHERE user_id = $1 AND status = 'active'",
                    user_id,
                )
                row = await connection.fetchrow(
                    "UPDATE chats SET status = 'active', updated_at = NOW() WHERE id = $1 RETURNING *",
                    chat_id,
                )
        return self._optional_model(Chat, row)

    async def rename_chat(self, user_id: int, chat_id: int, title: str) -> bool:
        query = """
            UPDATE chats SET title = $3, updated_at = NOW()
            WHERE id = $1 AND user_id = $2
        """
        return await self.pool.execute(query, chat_id, user_id, title) == "UPDATE 1"

    async def delete_chat(self, user_id: int, chat_id: int) -> bool:
        query = "DELETE FROM chats WHERE id = $1 AND user_id = $2"
        return await self.pool.execute(query, chat_id, user_id) == "DELETE 1"

    async def archive_chat(self, user_id: int, chat_id: int) -> bool:
        query = """
            UPDATE chats SET status = 'archived', updated_at = NOW()
            WHERE id = $1 AND user_id = $2
        """
        return await self.pool.execute(query, chat_id, user_id) == "UPDATE 1"

    async def toggle_chat_pin(self, user_id: int, chat_id: int) -> bool:
        query = """
            UPDATE chats SET is_pinned = NOT is_pinned, updated_at = NOW()
            WHERE id = $1 AND user_id = $2
        """
        return await self.pool.execute(query, chat_id, user_id) == "UPDATE 1"

    async def set_chat_tag(self, user_id: int, chat_id: int, tag: str | None) -> bool:
        query = """
            UPDATE chats SET tag = $3, updated_at = NOW()
            WHERE id = $1 AND user_id = $2
        """
        return await self.pool.execute(query, chat_id, user_id, tag) == "UPDATE 1"

    async def search_chats(self, user_id: int, term: str) -> list[Chat]:
        query = """
            SELECT DISTINCT c.* FROM chats c
            LEFT JOIN messages m ON m.chat_id = c.id
            WHERE c.user_id = $1 AND (c.title ILIKE $2 OR m.content ILIKE $2)
            ORDER BY c.updated_at DESC LIMIT 20
        """
        return self._models(Chat, await self.pool.fetch(query, user_id, f"%{term}%"))

    async def duplicate_chat(self, user_id: int, chat_id: int) -> Chat | None:
        source = await self.pool.fetchrow(
            "SELECT * FROM chats WHERE id = $1 AND user_id = $2", chat_id, user_id
        )
        if source is None:
            return None
        duplicate = await self.create_chat(user_id, f"{source['title']} (копия)")
        query = """
            INSERT INTO messages (chat_id, role, content, created_at)
            SELECT $1, role, content, created_at FROM messages WHERE chat_id = $2
        """
        await self.pool.execute(query, duplicate.id, chat_id)
        return duplicate

    async def add_message(self, chat_id: int, role: str, content: str) -> Message:
        query = """
            INSERT INTO messages (chat_id, role, content) VALUES ($1, $2, $3)
            RETURNING *
        """
        row = await self.pool.fetchrow(query, chat_id, role, content)
        await self.pool.execute("UPDATE chats SET updated_at = NOW() WHERE id = $1", chat_id)
        return self._model(Message, row)

    async def get_recent_messages(self, chat_id: int, limit: int) -> list[Message]:
        query = """
            SELECT * FROM (
                SELECT * FROM messages WHERE chat_id = $1
                ORDER BY created_at DESC LIMIT $2
            ) recent ORDER BY created_at
        """
        return self._models(Message, await self.pool.fetch(query, chat_id, limit))

    async def get_all_messages(self, chat_id: int, user_id: int) -> list[Message]:
        query = """
            SELECT m.* FROM messages m JOIN chats c ON c.id = m.chat_id
            WHERE m.chat_id = $1 AND c.user_id = $2 ORDER BY m.created_at
        """
        return self._models(Message, await self.pool.fetch(query, chat_id, user_id))

    async def add_memory(self, user_id: int, category: str, content: str) -> Memory:
        query = """
            INSERT INTO memories (user_id, category, content) VALUES ($1, $2, $3)
            RETURNING *
        """
        return self._model(Memory, await self.pool.fetchrow(query, user_id, category, content))

    async def list_memories(self, user_id: int) -> list[Memory]:
        rows = await self.pool.fetch(
            "SELECT * FROM memories WHERE user_id = $1 ORDER BY created_at DESC", user_id
        )
        return self._models(Memory, rows)

    async def delete_memory(self, user_id: int, memory_id: int) -> bool:
        query = "DELETE FROM memories WHERE id = $1 AND user_id = $2"
        return await self.pool.execute(query, memory_id, user_id) == "DELETE 1"

    async def clear_memories(self, user_id: int) -> int:
        result = await self.pool.execute("DELETE FROM memories WHERE user_id = $1", user_id)
        return int(result.split()[-1])

    async def add_todo(self, user_id: int, text: str) -> Todo:
        query = "INSERT INTO todos (user_id, text) VALUES ($1, $2) RETURNING *"
        return self._model(Todo, await self.pool.fetchrow(query, user_id, text))

    async def list_todos(self, user_id: int, include_done: bool = True) -> list[Todo]:
        condition = "" if include_done else "AND is_done = FALSE"
        query = f"SELECT * FROM todos WHERE user_id = $1 {condition} ORDER BY created_at"
        return self._models(Todo, await self.pool.fetch(query, user_id))

    async def complete_todo(self, user_id: int, todo_id: int) -> bool:
        query = "UPDATE todos SET is_done = TRUE WHERE id = $1 AND user_id = $2"
        return await self.pool.execute(query, todo_id, user_id) == "UPDATE 1"

    async def delete_todo(self, user_id: int, todo_id: int) -> bool:
        query = "DELETE FROM todos WHERE id = $1 AND user_id = $2"
        return await self.pool.execute(query, todo_id, user_id) == "DELETE 1"

    async def add_reminder(self, user_id: int, text: str, remind_at: datetime) -> Reminder:
        query = """
            INSERT INTO reminders (user_id, text, remind_at) VALUES ($1, $2, $3)
            RETURNING *
        """
        return self._model(Reminder, await self.pool.fetchrow(query, user_id, text, remind_at))

    async def list_reminders(self, user_id: int, active_only: bool = True) -> list[Reminder]:
        condition = "AND is_active = TRUE" if active_only else ""
        query = f"""
            SELECT * FROM reminders WHERE user_id = $1 {condition}
            ORDER BY remind_at
        """
        return self._models(Reminder, await self.pool.fetch(query, user_id))

    async def list_active_reminders(self) -> list[Reminder]:
        rows = await self.pool.fetch(
            "SELECT * FROM reminders WHERE is_active = TRUE ORDER BY remind_at"
        )
        return self._models(Reminder, rows)

    async def deactivate_reminder(self, reminder_id: int) -> None:
        await self.pool.execute("UPDATE reminders SET is_active = FALSE WHERE id = $1", reminder_id)

    async def add_favorite(self, user_id: int, chat_id: int | None, content: str) -> Favorite:
        query = """
            INSERT INTO favorites (user_id, chat_id, content) VALUES ($1, $2, $3)
            RETURNING *
        """
        return self._model(Favorite, await self.pool.fetchrow(query, user_id, chat_id, content))

    async def list_favorites(self, user_id: int) -> list[Favorite]:
        rows = await self.pool.fetch(
            "SELECT * FROM favorites WHERE user_id = $1 ORDER BY created_at DESC", user_id
        )
        return self._models(Favorite, rows)

    async def increment_stats(self, user_id: int, tokens: int) -> None:
        query = """
            INSERT INTO stats (user_id, requests_count, tokens_count) VALUES ($1, 1, $2)
            ON CONFLICT (user_id, date) DO UPDATE SET
                requests_count = stats.requests_count + 1,
                tokens_count = stats.tokens_count + EXCLUDED.tokens_count
        """
        await self.pool.execute(query, user_id, tokens)

    async def get_stats(self, user_id: int, days: int = 30) -> list[DailyStats]:
        query = """
            SELECT date, requests_count, tokens_count FROM stats
            WHERE user_id = $1 AND date >= CURRENT_DATE - $2::integer
            ORDER BY date DESC
        """
        return self._models(DailyStats, await self.pool.fetch(query, user_id, days))

    async def reset_user_data(self, user_id: int) -> None:
        tables = ("favorites", "reminders", "todos", "memories", "stats", "chats", "settings")
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                for table in tables:
                    await connection.execute(f"DELETE FROM {table} WHERE user_id = $1", user_id)

    @staticmethod
    def _model(model: type[ModelT], row: asyncpg.Record | None) -> ModelT:
        if row is None:
            raise RuntimeError("Ожидаемая запись не найдена")
        return model(**dict(row))

    @classmethod
    def _optional_model(cls, model: type[ModelT], row: asyncpg.Record | None) -> ModelT | None:
        return cls._model(model, row) if row else None

    @classmethod
    def _models(cls, model: type[ModelT], rows: Sequence[asyncpg.Record]) -> list[ModelT]:
        return [cls._model(model, row) for row in rows]
