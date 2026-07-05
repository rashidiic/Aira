from src.db.database import Database
from src.db.models import Todo


class TaskService:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def create(self, user_id: int, text: str) -> Todo:
        if not text.strip():
            raise ValueError("Текст задачи пуст")
        return await self._database.add_todo(user_id, text.strip())

    async def list(self, user_id: int) -> list[Todo]:
        return await self._database.list_todos(user_id)

    async def complete(self, user_id: int, todo_id: int) -> bool:
        return await self._database.complete_todo(user_id, todo_id)

    async def delete(self, user_id: int, todo_id: int) -> bool:
        return await self._database.delete_todo(user_id, todo_id)
