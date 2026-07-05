import logging

from telegram import Update
from telegram.ext import ApplicationHandlerStop, ContextTypes

from src.handlers.utils import get_services

logger = logging.getLogger(__name__)


async def access_middleware(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    user = update.effective_user
    if user is None:
        raise ApplicationHandlerStop

    logger.info("Получен update=%s от user_id=%s", update.update_id, user.id)
    if await get_services(context).access.is_allowed(user.id):
        return

    logger.warning("Доступ отклонён для user_id=%s", user.id)
    if update.effective_message:
        await update.effective_message.reply_text("⛔ Доступ запрещён")
    elif update.inline_query:
        await update.inline_query.answer([], cache_time=1, is_personal=True)
    raise ApplicationHandlerStop
