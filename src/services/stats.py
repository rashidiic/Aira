from dataclasses import dataclass

from src.db.database import Database


@dataclass(frozen=True, slots=True)
class StatsSummary:
    requests: int
    tokens: int


class StatsService:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def record(self, user_id: int, input_tokens: int, output_tokens: int) -> None:
        await self._database.increment_stats(user_id, input_tokens + output_tokens)

    async def summary(self, user_id: int, days: int = 30) -> StatsSummary:
        rows = await self._database.get_stats(user_id, days)
        return StatsSummary(
            requests=sum(row.requests_count for row in rows),
            tokens=sum(row.tokens_count for row in rows),
        )
