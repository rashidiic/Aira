from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot

from src.db.database import Database
from src.db.models import Reminder


class ReminderService:
    def __init__(self, database: Database, bot: Bot, timezone: str) -> None:
        self._database = database
        self._bot = bot
        self._timezone = ZoneInfo(timezone)
        self._scheduler = AsyncIOScheduler(timezone=self._timezone)

    async def start(self) -> None:
        self._scheduler.start()
        for reminder in await self._database.list_active_reminders():
            self._schedule(reminder)

    async def stop(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)

    async def create(self, user_id: int, date_text: str, text: str) -> Reminder:
        remind_at = self._parse_datetime(date_text)
        if remind_at <= datetime.now(self._timezone):
            raise ValueError("Время напоминания уже прошло")
        reminder = await self._database.add_reminder(user_id, text.strip(), remind_at)
        self._schedule(reminder)
        return reminder

    async def list(self, user_id: int) -> list[Reminder]:
        return await self._database.list_reminders(user_id)

    async def cancel_all(self, user_id: int) -> None:
        reminders = await self._database.list_reminders(user_id, active_only=False)
        for reminder in reminders:
            job = self._scheduler.get_job(f"reminder:{reminder.id}")
            if job:
                job.remove()

    def _schedule(self, reminder: Reminder) -> None:
        self._scheduler.add_job(
            self._deliver,
            trigger="date",
            run_date=reminder.remind_at,
            args=[reminder],
            id=f"reminder:{reminder.id}",
            replace_existing=True,
            misfire_grace_time=None,
        )

    async def _deliver(self, reminder: Reminder) -> None:
        await self._bot.send_message(reminder.user_id, f"⏰ {reminder.text}")
        await self._database.deactivate_reminder(reminder.id)

    def _parse_datetime(self, value: str) -> datetime:
        try:
            parsed = datetime.strptime(value, "%Y-%m-%d %H:%M")
        except ValueError as error:
            raise ValueError("Дата должна быть в формате ГГГГ-ММ-ДД ЧЧ:ММ") from error
        return parsed.replace(tzinfo=self._timezone)
