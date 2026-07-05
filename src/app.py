import logging
from pathlib import Path

from telegram import BotCommand, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    InlineQueryHandler,
    MessageHandler,
    TypeHandler,
    filters,
)

from src.config import Config, load_config
from src.container import Services
from src.db.database import Database
from src.handlers import commands, inline, messages, panel, voice
from src.handlers.middleware import access_middleware
from src.services.access import AccessService
from src.services.brief import BriefService
from src.services.chats import ChatService
from src.services.favorites import FavoriteService
from src.services.llm_factory import create_llm_service
from src.services.memory import MemoryService
from src.services.prompts import PromptBuilder
from src.services.reminders import ReminderService
from src.services.reset import ResetService
from src.services.settings import SettingsService
from src.services.stats import StatsService
from src.services.tasks import TaskService

logger = logging.getLogger(__name__)


def create_application(config: Config) -> Application:
    application = (
        Application.builder()
        .token(config.telegram_token)
        .post_init(_post_init)
        .post_shutdown(_post_shutdown)
        .build()
    )
    application.bot_data["services"] = _create_services(config, application)
    _register_handlers(application)
    application.add_error_handler(_error_handler)
    return application


def run() -> None:
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        level=logging.INFO,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    create_application(load_config()).run_polling(allowed_updates=Update.ALL_TYPES)


def _create_services(config: Config, application: Application) -> Services:
    database = Database(config.database_url)
    memory = MemoryService(database)
    stats = StatsService(database)
    tasks = TaskService(database)
    reminders = ReminderService(database, application.bot, config.timezone)
    prompts = PromptBuilder.from_file(Path(__file__).parent.parent / "system_prompt.txt")
    chats = ChatService(database, create_llm_service(config), memory, stats, prompts)
    return Services(
        database=database,
        access=AccessService(database, config.admin_user_id),
        chats=chats,
        memory=memory,
        tasks=tasks,
        reminders=reminders,
        favorites=FavoriteService(database),
        settings=SettingsService(database),
        stats=stats,
        brief=BriefService(chats, tasks, reminders, stats),
        reset=ResetService(database, chats, reminders),
    )


def _register_handlers(application: Application) -> None:
    private = filters.ChatType.PRIVATE
    application.add_handler(TypeHandler(Update, access_middleware), group=-1)
    for name, callback in _commands().items():
        application.add_handler(CommandHandler(name, callback, filters=private))
    application.add_handler(
        CommandHandler("ai", messages.handle_group_ai, filters=filters.ChatType.GROUPS)
    )
    for name, callback in {
        "allow": commands.allow_command,
        "deny": commands.deny_command,
        "whitelist": commands.whitelist_command,
    }.items():
        application.add_handler(CommandHandler(name, callback, filters=filters.ChatType.GROUPS))
    application.add_handler(
        CallbackQueryHandler(panel.handle_panel_callback, pattern=r"^(panel|chat|set):")
    )
    application.add_handler(InlineQueryHandler(inline.handle_inline_query))
    application.add_handler(MessageHandler(private & filters.VOICE, voice.handle_voice))
    application.add_handler(
        MessageHandler(private & filters.TEXT & ~filters.COMMAND, messages.handle_private_message)
    )


def _commands() -> dict[str, object]:
    return {
        "start": commands.start_command,
        "help": commands.help_command,
        "newchat": commands.new_chat_command,
        "chats": commands.chats_command,
        "switch": commands.switch_chat_command,
        "rename": commands.rename_chat_command,
        "archive": commands.archive_chat_command,
        "deletechat": commands.delete_chat_command,
        "duplicate": commands.duplicate_chat_command,
        "export": commands.export_chat_command,
        "search": commands.search_chats_command,
        "tag": commands.tag_chat_command,
        "pin": commands.pin_chat_command,
        "save": commands.save_memory_command,
        "memories": commands.memories_command,
        "forget": commands.forget_memory_command,
        "clear": commands.clear_memory_command,
        "todo": commands.add_todo_command,
        "todos": commands.todos_command,
        "done": commands.done_todo_command,
        "deltodo": commands.delete_todo_command,
        "remind": commands.remind_command,
        "reminders": commands.reminders_command,
        "fav": commands.favorite_command,
        "favorites": commands.favorites_command,
        "stats": commands.stats_command,
        "brief": commands.brief_command,
        "panel": commands.panel_command,
        "mode": commands.setting_command,
        "style": commands.setting_command,
        "language": commands.setting_command,
        "allow": commands.allow_command,
        "deny": commands.deny_command,
        "whitelist": commands.whitelist_command,
        "reset": commands.reset_command,
    }


async def _post_init(application: Application) -> None:
    services = application.bot_data["services"]
    await services.database.connect()
    await services.database.initialize_schema()
    await services.reminders.start()
    await application.bot.set_my_commands(_bot_commands())
    logger.info("Aira запущена")


async def _post_shutdown(application: Application) -> None:
    services = application.bot_data["services"]
    await services.reminders.stop()
    await services.database.close()


async def _error_handler(update: object, context: object) -> None:
    error = getattr(context, "error", None)
    if isinstance(error, (ValueError, PermissionError)):
        logger.warning("Некорректная команда: %s", error)
    elif isinstance(error, BaseException):
        logger.error(
            "Ошибка при обработке update",
            exc_info=(type(error), error, error.__traceback__),
        )
    else:
        logger.error("Неизвестная ошибка при обработке update: %r", error)
    if isinstance(update, Update) and update.effective_message:
        text = (
            str(error)
            if isinstance(error, (ValueError, PermissionError))
            else "Произошла ошибка. Попробуйте ещё раз."
        )
        await update.effective_message.reply_text(f"⚠️ {text}")


def _bot_commands() -> list[BotCommand]:
    return [
        BotCommand("newchat", "Новый чат"),
        BotCommand("chats", "Список чатов"),
        BotCommand("panel", "Панель управления"),
        BotCommand("todo", "Добавить задачу"),
        BotCommand("remind", "Создать напоминание"),
        BotCommand("memories", "Память"),
        BotCommand("brief", "Краткая сводка"),
        BotCommand("reset", "Начать с нуля"),
        BotCommand("help", "Все команды"),
    ]
