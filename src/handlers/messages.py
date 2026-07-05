from telegram import Update
from telegram.ext import ContextTypes

from src.handlers.formatting import reply_markdown
from src.handlers.utils import get_services, get_user_id


async def handle_private_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    message = update.effective_message
    if message is None or not message.text:
        return
    await message.chat.send_action("typing")
    reply = await get_services(context).chats.ask(get_user_id(update), message.text)
    await reply_markdown(message, reply.text)


async def handle_group_ai(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    message = update.effective_message
    prompt = " ".join(context.args).strip()
    if message is None:
        return
    if not prompt:
        await message.reply_text("Использование: /ai ваш вопрос")
        return
    await message.chat.send_action("typing")
    reply = await get_services(context).chats.ask(get_user_id(update), prompt)
    await reply_markdown(message, reply.text)
