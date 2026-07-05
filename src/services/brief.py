from dataclasses import dataclass

from src.db.models import Chat, Reminder, Todo
from src.services.chats import ChatService
from src.services.reminders import ReminderService
from src.services.stats import StatsService, StatsSummary
from src.services.tasks import TaskService


@dataclass(frozen=True, slots=True)
class Brief:
    chat: Chat
    todos: list[Todo]
    reminders: list[Reminder]
    stats: StatsSummary


class BriefService:
    def __init__(
        self,
        chats: ChatService,
        tasks: TaskService,
        reminders: ReminderService,
        stats: StatsService,
    ) -> None:
        self._chats = chats
        self._tasks = tasks
        self._reminders = reminders
        self._stats = stats

    async def get(self, user_id: int) -> Brief:
        todos = [todo for todo in await self._tasks.list(user_id) if not todo.is_done]
        return Brief(
            chat=await self._chats.active(user_id),
            todos=todos,
            reminders=await self._reminders.list(user_id),
            stats=await self._stats.summary(user_id),
        )
