from dataclasses import dataclass

from src.db.database import Database
from src.services.access import AccessService
from src.services.brief import BriefService
from src.services.chats import ChatService
from src.services.favorites import FavoriteService
from src.services.memory import MemoryService
from src.services.reminders import ReminderService
from src.services.reset import ResetService
from src.services.settings import SettingsService
from src.services.stats import StatsService
from src.services.tasks import TaskService


@dataclass(frozen=True, slots=True)
class Services:
    database: Database
    access: AccessService
    chats: ChatService
    memory: MemoryService
    tasks: TaskService
    reminders: ReminderService
    favorites: FavoriteService
    settings: SettingsService
    stats: StatsService
    brief: BriefService
    reset: ResetService
