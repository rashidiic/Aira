from src.db.database import Database


class AccessService:
    def __init__(self, database: Database, admin_user_id: int) -> None:
        self._database = database
        self._admin_user_id = admin_user_id

    def is_admin(self, user_id: int) -> bool:
        return user_id == self._admin_user_id

    async def is_allowed(self, user_id: int) -> bool:
        return await self._database.has_access(user_id, self._admin_user_id)

    async def allow(self, user_id: int, added_by: int) -> None:
        self._require_admin(added_by)
        await self._database.add_to_whitelist(user_id, added_by)

    async def deny(self, user_id: int, removed_by: int) -> bool:
        self._require_admin(removed_by)
        return await self._database.remove_from_whitelist(user_id)

    async def list(self, requested_by: int) -> list[int]:
        self._require_admin(requested_by)
        return await self._database.list_whitelist()

    def _require_admin(self, user_id: int) -> None:
        if not self.is_admin(user_id):
            raise PermissionError("Команда доступна только администратору")
