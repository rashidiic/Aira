import html
from uuid import uuid4

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from src.handlers.formatting import reply_markdown
from src.handlers.utils import get_services, get_user_id
from src.services.memory import MemorySuggestion


async def handle_private_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    message = update.effective_message
    if message is None or not message.text:
        return
    await message.chat.send_action("typing")
    services = get_services(context)
    user_id = get_user_id(update)
    reply = await services.chats.ask(user_id, message.text)
    await reply_markdown(message, reply.text)
    suggestion = await services.memory.suggest(user_id, message.text)
    if suggestion:
        await _offer_memory(update, context, suggestion)


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


async def handle_memory_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query
    if query is None:
        return

    data = query.data or ""
    action, _, token = data.partition(":")[2].partition(":")
    pending = context.user_data.setdefault("pending_memories", {})
    suggestion = pending.pop(token, None)

    if suggestion is None:
        await query.answer("Это предложение памяти уже устарело.", show_alert=False)
        return

    if action == "save":
        await get_services(context).memory.save(
            get_user_id(update),
            suggestion["category"],
            suggestion["content"],
        )
        await query.answer("Запомнила 🧠", show_alert=False)
        if query.message:
            await query.edit_message_text(
                "🧠 <b>Запомнила</b>\n"
                f"<i>{html.escape(suggestion['content'])}</i>",
                parse_mode=ParseMode.HTML,
            )
        return

    await query.answer("Не запоминаю.", show_alert=False)
    if query.message:
        await query.edit_message_text("👌 Не буду это запоминать.")


async def _offer_memory(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    suggestion: MemorySuggestion,
) -> None:
    message = update.effective_message
    if message is None:
        return

    token = uuid4().hex[:10]
    pending = context.user_data.setdefault("pending_memories", {})
    pending[token] = {"category": suggestion.category, "content": suggestion.content}

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🧠 Запомнить", callback_data=f"mem:save:{token}"),
                InlineKeyboardButton("Не надо", callback_data=f"mem:skip:{token}"),
            ]
        ]
    )
    await message.reply_text(
        "🧠 <b>Aira заметила важный факт</b>\n\n"
        f"<i>{html.escape(suggestion.content)}</i>\n\n"
        "Запомнить это для будущих диалогов?",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML,
    )
