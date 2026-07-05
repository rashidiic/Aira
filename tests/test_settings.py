import pytest

from src.services.settings import SettingsService


class FakeDatabase:
    async def update_setting(self, user_id: int, field: str, value: str) -> tuple:
        return user_id, field, value


async def test_settings_reject_unknown_value() -> None:
    service = SettingsService(FakeDatabase())  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="Недопустимое"):
        await service.set(1, "language", "fr")


async def test_settings_accept_supported_value() -> None:
    service = SettingsService(FakeDatabase())  # type: ignore[arg-type]

    result = await service.set(1, "language", "az")

    assert result == (1, "language", "az")
