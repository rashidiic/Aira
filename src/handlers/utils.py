from telegram import Message, Update
from telegram.ext import ContextTypes

from src.container import Services

TELEGRAM_TEXT_LIMIT = 4096


def get_services(context: ContextTypes.DEFAULT_TYPE) -> Services:
    services = context.application.bot_data.get("services")
    if not isinstance(services, Services):
        raise RuntimeError("Сервисы приложения не инициализированы")
    return services


def get_user_id(update: Update) -> int:
    if update.effective_user is None:
        raise ValueError("У обновления нет пользователя")
    return update.effective_user.id


async def reply_text(message: Message, text: str) -> None:
    for start in range(0, len(text), TELEGRAM_TEXT_LIMIT):
        await message.reply_text(text[start : start + TELEGRAM_TEXT_LIMIT])
