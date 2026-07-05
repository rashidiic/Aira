from src.services.reset import ResetService


class FakeDatabase:
    def __init__(self) -> None:
        self.reset_user_id = None

    async def reset_user_data(self, user_id: int) -> None:
        self.reset_user_id = user_id


class FakeChats:
    def __init__(self) -> None:
        self.cleared_user_id = None

    async def clear_cache(self, user_id: int) -> None:
        self.cleared_user_id = user_id


class FakeReminders:
    def __init__(self) -> None:
        self.cancelled_user_id = None

    async def cancel_all(self, user_id: int) -> None:
        self.cancelled_user_id = user_id


async def test_reset_clears_runtime_and_persistent_data() -> None:
    database = FakeDatabase()
    chats = FakeChats()
    reminders = FakeReminders()
    service = ResetService(database, chats, reminders)  # type: ignore[arg-type]

    await service.reset(42)

    assert reminders.cancelled_user_id == 42
    assert chats.cleared_user_id == 42
    assert database.reset_user_id == 42
