from src.db.database import Database
from src.db.models import UserSettings


class SettingsService:
    OPTIONS = {
        "mode": {"normal", "code", "study", "swearing"},
        "style": {"formal", "friendly", "brief", "detailed"},
        "language": {"ru", "en", "az"},
    }

    def __init__(self, database: Database) -> None:
        self._database = database

    async def get(self, user_id: int) -> UserSettings:
        return await self._database.ensure_settings(user_id)

    async def set(self, user_id: int, field: str, value: str) -> UserSettings:
        if value not in self.OPTIONS.get(field, set()):
            raise ValueError("Недопустимое значение настройки")
        return await self._database.update_setting(user_id, field, value)

    async def set_panel_message(self, user_id: int, message_id: int) -> None:
        await self._database.set_panel_message_id(user_id, message_id)
