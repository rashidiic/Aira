from src.db.database import Database
from src.db.models import Memory


class MemoryService:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def save(self, user_id: int, category: str, content: str) -> Memory:
        if not content.strip():
            raise ValueError("Текст воспоминания пуст")
        return await self._database.add_memory(user_id, category.strip(), content.strip())

    async def list(self, user_id: int) -> list[Memory]:
        return await self._database.list_memories(user_id)

    async def forget(self, user_id: int, memory_id: int) -> bool:
        return await self._database.delete_memory(user_id, memory_id)

    async def clear(self, user_id: int) -> int:
        return await self._database.clear_memories(user_id)
