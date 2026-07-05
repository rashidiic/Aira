import html

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from src.handlers.utils import get_services, get_user_id


async def show_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None:
        return
    user_id = get_user_id(update)
    services = get_services(context)
    settings = await services.settings.get(user_id)
    text, keyboard = await _main_screen(user_id, context)

    if settings.panel_message_id:
        changed = True
        try:
            await context.bot.edit_message_text(
                chat_id=message.chat_id,
                message_id=settings.panel_message_id,
                text=text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML,
            )
        except BadRequest as error:
            if _is_missing_panel(error):
                await _create_panel(message, context, user_id, text, keyboard)
                return
            if not _is_message_unchanged(error):
                raise
            changed = False
        await _ensure_panel_is_pinned(context, message.chat_id, settings.panel_message_id)
        status = "Панель обновлена" if changed else "Панель уже актуальна"
        await message.reply_text(f"✅ {status} и закреплена сверху.")
        return

    await _create_panel(message, context, user_id, text, keyboard)


async def handle_panel_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query
    if query is None:
        return
    await query.answer()
    user_id = get_user_id(update)
    data = query.data or "panel:main"

    if data.startswith("chat:switch:"):
        await get_services(context).chats.switch(user_id, int(data.rsplit(":", 1)[1]))
        data = "panel:chats"
    elif data.startswith("set:"):
        _, field, value = data.split(":", 2)
        await get_services(context).settings.set(user_id, field, value)
        data = "panel:settings"

    text, keyboard = await _screen(data, user_id, context)
    if query.message and query.message.text == text and query.message.reply_markup == keyboard:
        return
    try:
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    except BadRequest as error:
        if not _is_message_unchanged(error):
            raise


async def _screen(
    data: str,
    user_id: int,
    context: ContextTypes.DEFAULT_TYPE,
) -> tuple[str, InlineKeyboardMarkup]:
    screens = {
        "panel:main": _main_screen,
        "panel:chats": _chats_screen,
        "panel:memory": _memory_screen,
        "panel:tasks": _tasks_screen,
        "panel:favorites": _favorites_screen,
        "panel:settings": _settings_screen,
        "panel:help": _help_screen,
    }
    return await screens.get(data, _main_screen)(user_id, context)


async def _main_screen(
    user_id: int,
    context: ContextTypes.DEFAULT_TYPE,
) -> tuple[str, InlineKeyboardMarkup]:
    brief = await get_services(context).brief.get(user_id)
    title = html.escape(brief.chat.title)
    text = (
        "✨ <b>AIRA · CONTROL CENTER</b>\n"
        "<i>Персональный AI-ассистент</i>\n\n"
        "💬 <b>Активный диалог</b>\n"
        f"└ {title}\n\n"
        "📍 <b>Сегодня</b>\n"
        f"├ Открытых задач: <b>{len(brief.todos)}</b>\n"
        f"└ Напоминаний: <b>{len(brief.reminders)}</b>\n\n"
        "Выберите раздел ниже ↓"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [_button("💬 Чаты", "panel:chats"), _button("🧠 Память", "panel:memory")],
            [_button("✅ Задачи", "panel:tasks"), _button("⭐ Избранное", "panel:favorites")],
            [_button("⚙️ Настройки", "panel:settings"), _button("📚 Команды", "panel:help")],
        ]
    )
    return text, keyboard


async def _chats_screen(
    user_id: int,
    context: ContextTypes.DEFAULT_TYPE,
) -> tuple[str, InlineKeyboardMarkup]:
    chats = await get_services(context).chats.list(user_id)
    rows = [
        [
            _button(
                f"{'▶️ ' if chat.status == 'active' else ''}{chat.title}", f"chat:switch:{chat.id}"
            )
        ]
        for chat in chats[:10]
    ]
    rows.append([_button("⬅️ Назад", "panel:main")])
    return "💬 <b>МОИ ДИАЛОГИ</b>\n\nВыберите активный чат:", InlineKeyboardMarkup(rows)


async def _memory_screen(
    user_id: int,
    context: ContextTypes.DEFAULT_TYPE,
) -> tuple[str, InlineKeyboardMarkup]:
    items = await get_services(context).memory.list(user_id)
    text = "🧠 <b>ДОЛГОСРОЧНАЯ ПАМЯТЬ</b>\n\n" + (
        "\n\n".join(
            f"<b>#{item.id} · {html.escape(item.category)}</b>\n{html.escape(item.content[:250])}"
            for item in items[:10]
        )
        or "<i>Пока пусто. Используйте /save.</i>"
    )
    return text, _back_keyboard()


async def _tasks_screen(
    user_id: int,
    context: ContextTypes.DEFAULT_TYPE,
) -> tuple[str, InlineKeyboardMarkup]:
    items = await get_services(context).tasks.list(user_id)
    text = "✅ <b>МОИ ЗАДАЧИ</b>\n\n" + (
        "\n".join(
            f"{'✅' if item.is_done else '▫️'} <b>#{item.id}</b> {html.escape(item.text)}"
            for item in items[:10]
        )
        or "<i>Пока пусто. Используйте /todo.</i>"
    )
    return text, _back_keyboard()


async def _favorites_screen(
    user_id: int,
    context: ContextTypes.DEFAULT_TYPE,
) -> tuple[str, InlineKeyboardMarkup]:
    items = await get_services(context).favorites.list(user_id)
    text = "⭐ <b>ИЗБРАННОЕ</b>\n\n" + (
        "\n\n".join(f"<b>#{item.id}</b>\n{html.escape(item.content[:250])}" for item in items[:5])
        or "<i>Пока пусто.</i>"
    )
    return text, _back_keyboard()


async def _settings_screen(
    user_id: int,
    context: ContextTypes.DEFAULT_TYPE,
) -> tuple[str, InlineKeyboardMarkup]:
    settings = await get_services(context).settings.get(user_id)
    text = (
        "⚙️ <b>НАСТРОЙКИ ОТВЕТА</b>\n\n"
        f"🎯 Режим: <b>{settings.mode}</b>\n"
        f"🎨 Стиль: <b>{settings.style}</b>\n"
        f"🌐 Язык: <b>{settings.language.upper()}</b>\n\n"
        "Нажмите кнопку, чтобы изменить:"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [
                _button("Обычный", "set:mode:normal"),
                _button("Код", "set:mode:code"),
                _button("Учёба", "set:mode:study"),
            ],
            [_button("Дружеский", "set:style:friendly"), _button("Краткий", "set:style:brief")],
            [
                _button("RU", "set:language:ru"),
                _button("EN", "set:language:en"),
                _button("AZ", "set:language:az"),
            ],
            [_button("⬅️ Назад", "panel:main")],
        ]
    )
    return text, keyboard


async def _help_screen(
    user_id: int,
    context: ContextTypes.DEFAULT_TYPE,
) -> tuple[str, InlineKeyboardMarkup]:
    await get_services(context).settings.get(user_id)
    text = (
        "📚 <b>БЫСТРЫЙ СТАРТ С AIRA</b>\n\n"
        "💬 <b>Диалоги</b>\n"
        "• Просто напишите сообщение — Aira ответит в активном чате.\n"
        "• /newchat — начать новый диалог.\n"
        "• /chats — посмотреть диалоги.\n\n"
        "🧠 <b>Память</b>\n"
        "• /save категория текст — сохранить вручную.\n"
        "• Если Aira заметит важный факт, она предложит запомнить его кнопкой.\n"
        "• /memories — посмотреть память.\n\n"
        "✅ <b>Задачи и напоминания</b>\n"
        "• /todo текст — добавить задачу.\n"
        "• /remind ГГГГ-ММ-ДД ЧЧ:ММ текст — создать напоминание.\n\n"
        "⚙️ <b>Настройки</b>\n"
        "• /mode — режим работы.\n"
        "• /style — стиль ответа.\n"
        "• /language — язык ответа."
    )
    return text, _back_keyboard()


def _back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[_button("⬅️ Назад", "panel:main")]])


def _button(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text, callback_data=data)


def _is_message_unchanged(error: BadRequest) -> bool:
    return "message is not modified" in str(error).lower()


def _is_missing_panel(error: BadRequest) -> bool:
    message = str(error).lower()
    return "message to edit not found" in message or "message can't be edited" in message


async def _create_panel(
    message: Message,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    text: str,
    keyboard: InlineKeyboardMarkup,
) -> None:
    panel = await message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await context.bot.pin_chat_message(message.chat_id, panel.message_id, disable_notification=True)
    await get_services(context).settings.set_panel_message(user_id, panel.message_id)


async def _ensure_panel_is_pinned(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    panel_message_id: int,
) -> None:
    chat = await context.bot.get_chat(chat_id)
    pinned = getattr(chat, "pinned_message", None)
    if pinned is None or pinned.message_id != panel_message_id:
        await context.bot.pin_chat_message(chat_id, panel_message_id, disable_notification=True)
