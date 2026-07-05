from src.db.database import Database
from src.services.chats import ChatService
from src.services.reminders import ReminderService


class ResetService:
    def __init__(
        self,
        database: Database,
        chats: ChatService,
        reminders: ReminderService,
    ) -> None:
        self._database = database
        self._chats = chats
        self._reminders = reminders

    async def reset(self, user_id: int) -> None:
        await self._reminders.cancel_all(user_id)
        await self._chats.clear_cache(user_id)
        await self._database.reset_user_data(user_id)
