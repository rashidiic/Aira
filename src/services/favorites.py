from src.db.database import Database
from src.db.models import Favorite


class FavoriteService:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def add(self, user_id: int, chat_id: int | None, content: str) -> Favorite:
        if not content.strip():
            raise ValueError("Нельзя сохранить пустое сообщение")
        return await self._database.add_favorite(user_id, chat_id, content.strip())

    async def list(self, user_id: int) -> list[Favorite]:
        return await self._database.list_favorites(user_id)
