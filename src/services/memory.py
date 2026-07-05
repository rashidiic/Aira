import re
from dataclasses import dataclass

from src.db.database import Database
from src.db.models import Memory


@dataclass(frozen=True, slots=True)
class MemorySuggestion:
    category: str
    content: str


class MemoryService:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def save(self, user_id: int, category: str, content: str) -> Memory:
        if not content.strip():
            raise ValueError("Текст воспоминания пуст")
        return await self._database.add_memory(user_id, category.strip(), content.strip())

    async def suggest(self, user_id: int, text: str) -> MemorySuggestion | None:
        suggestion = self._extract_suggestion(text)
        if suggestion is None:
            return None

        memories = await self.list(user_id)
        normalized = suggestion.content.casefold()
        if any(memory.content.casefold() == normalized for memory in memories):
            return None
        return suggestion

    async def list(self, user_id: int) -> list[Memory]:
        return await self._database.list_memories(user_id)

    async def forget(self, user_id: int, memory_id: int) -> bool:
        return await self._database.delete_memory(user_id, memory_id)

    async def clear(self, user_id: int) -> int:
        return await self._database.clear_memories(user_id)

    @staticmethod
    def _extract_suggestion(text: str) -> MemorySuggestion | None:
        clean = " ".join(text.strip().split())
        if len(clean) < 8 or len(clean) > 220:
            return None

        rules = (
            (r"\b(?:меня зовут|мое имя|моё имя)\s+(.{2,60})", "profile"),
            (r"\b(?:я живу в|я из)\s+(.{2,80})", "profile"),
            (r"\b(?:я работаю|работаю|учусь|я учусь)\s+(.{2,120})", "profile"),
            (r"\b(?:я люблю|мне нравится|предпочитаю|я предпочитаю)\s+(.{2,120})", "preference"),
            (r"\b(?:я не люблю|мне не нравится)\s+(.{2,120})", "preference"),
            (r"\b(?:моя цель|я хочу научиться|хочу научиться)\s+(.{2,120})", "goal"),
        )
        for pattern, category in rules:
            if re.search(pattern, clean, flags=re.IGNORECASE):
                return MemorySuggestion(category=category, content=clean.rstrip("."))
        return None
