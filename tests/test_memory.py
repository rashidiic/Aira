from datetime import datetime

from src.db.models import Memory
from src.services.memory import MemoryService


class FakeDatabase:
    def __init__(self, memories: list[Memory] | None = None) -> None:
        self.memories = memories or []

    async def list_memories(self, user_id: int) -> list[Memory]:
        return self.memories


async def test_memory_suggests_personal_fact() -> None:
    service = MemoryService(FakeDatabase())  # type: ignore[arg-type]

    suggestion = await service.suggest(1, "Меня зовут Рашид")

    assert suggestion is not None
    assert suggestion.category == "profile"
    assert suggestion.content == "Меня зовут Рашид"


async def test_memory_does_not_suggest_duplicate() -> None:
    memory = Memory(1, 1, "profile", "Меня зовут Рашид", datetime.now())
    service = MemoryService(FakeDatabase([memory]))  # type: ignore[arg-type]

    suggestion = await service.suggest(1, "Меня зовут Рашид")

    assert suggestion is None
