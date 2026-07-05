from io import BytesIO

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputFile, Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from src.handlers.panel import show_panel
from src.handlers.utils import get_services, get_user_id, reply_text


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await get_services(context).settings.get(get_user_id(update))
    if update.effective_message:
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✨ Открыть панель", callback_data="panel:main"),
                    InlineKeyboardButton("🧠 Память", callback_data="panel:memory"),
                ],
                [
                    InlineKeyboardButton("⚙️ Настройки", callback_data="panel:settings"),
                    InlineKeyboardButton("📚 Команды", callback_data="panel:help"),
                ],
            ]
        )
        await update.effective_message.reply_text(
            "✨ <b>Привет, я Aira</b>\n\n"
            "Я твой персональный AI-ассистент в Telegram: помогу думать, писать код, "
            "вести диалоги, помнить важное, задачи и напоминания.\n\n"
            "Как начать:\n"
            "1. Просто напиши мне вопрос обычным сообщением.\n"
            "2. Используй /panel как центр управления.\n"
            "3. Если скажешь важный факт о себе, я предложу аккуратно его запомнить.\n\n"
            "Например: <i>«Я Python-разработчик и учу FastAPI»</i>",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "✨ <b>Aira · Центр команд</b>\n"
        "<i>Выберите нужный раздел или откройте /panel</i>\n\n"
        "💬 <b>Диалоги</b>\n"
        "/newchat <code>[название]</code> — новый чат\n"
        "/chats — список диалогов\n"
        "/switch <code>ID</code> — переключиться\n"
        "/rename <code>название</code> — переименовать\n"
        "/archive · /deletechat · /duplicate\n"
        "/export · /search · /tag · /pin\n\n"
        "🧠 <b>Память</b>\n"
        "/save <code>категория текст</code> — запомнить\n"
        "/memories · /forget <code>ID</code> · /clear\n\n"
        "✅ <b>Задачи и время</b>\n"
        "/todo <code>текст</code> · /todos\n"
        "/done <code>ID</code> · /deltodo <code>ID</code>\n"
        "/remind <code>ГГГГ-ММ-ДД ЧЧ:ММ текст</code>\n"
        "/reminders\n\n"
        "⭐ <b>Инструменты</b>\n"
        "/fav · /favorites · /stats · /brief\n"
        "/reset — полный сброс данных\n\n"
        "⚙️ <b>Настройки ответа</b>\n"
        "/mode · /style · /language\n\n"
        "👥 <b>В группе</b>\n"
        "/ai <code>ваш вопрос</code>"
    )
    if update.effective_message:
        await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


async def new_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    title = " ".join(context.args).strip() or "Новый чат"
    chat = await get_services(context).chats.create(get_user_id(update), title)
    await update.effective_message.reply_text(f"✅ Активен чат #{chat.id}: {chat.title}")


async def chats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chats = await get_services(context).chats.list(get_user_id(update))
    text = (
        "\n".join(
            f"{'📌 ' if chat.is_pinned else ''}{'▶️ ' if chat.status == 'active' else ''}"
            f"#{chat.id} {chat.title}{f' [{chat.tag}]' if chat.tag else ''}"
            for chat in chats
        )
        or "Чатов пока нет"
    )
    await reply_text(update.effective_message, text)


async def switch_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = _integer_argument(context.args, "Использование: /switch ID")
    chat = await get_services(context).chats.switch(get_user_id(update), chat_id)
    text = f"▶️ Активен чат: {chat.title}" if chat else "Чат не найден"
    await update.effective_message.reply_text(text)


async def rename_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    title = " ".join(context.args).strip()
    if not title:
        raise ValueError("Использование: /rename новое название")
    services = get_services(context)
    active = await services.chats.active(get_user_id(update))
    await services.chats.rename(active.user_id, active.id, title)
    await update.effective_message.reply_text("✅ Чат переименован")


async def archive_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    services = get_services(context)
    active = await services.chats.active(get_user_id(update))
    await services.chats.archive(active.user_id, active.id)
    await update.effective_message.reply_text("📦 Чат архивирован")


async def delete_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    services = get_services(context)
    user_id = get_user_id(update)
    chat_id = int(context.args[0]) if context.args else (await services.chats.active(user_id)).id
    deleted = await services.chats.delete(user_id, chat_id)
    await update.effective_message.reply_text("🗑 Чат удалён" if deleted else "Чат не найден")


async def duplicate_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    services = get_services(context)
    user_id = get_user_id(update)
    chat_id = int(context.args[0]) if context.args else (await services.chats.active(user_id)).id
    chat = await services.chats.duplicate(user_id, chat_id)
    await update.effective_message.reply_text(
        f"✅ Создан чат #{chat.id}: {chat.title}" if chat else "Чат не найден"
    )


async def export_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    services = get_services(context)
    user_id = get_user_id(update)
    chat = await services.chats.active(user_id)
    content = await services.chats.export(user_id, chat.id)
    document = InputFile(BytesIO(content.encode()), filename=f"chat-{chat.id}.txt")
    await update.effective_message.reply_document(document)


async def search_chats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    term = " ".join(context.args).strip()
    if not term:
        raise ValueError("Использование: /search запрос")
    chats = await get_services(context).chats.search(get_user_id(update), term)
    text = "\n".join(f"#{chat.id} {chat.title}" for chat in chats) or "Ничего не найдено"
    await update.effective_message.reply_text(text)


async def tag_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    services = get_services(context)
    active = await services.chats.active(get_user_id(update))
    tag = " ".join(context.args).strip() or None
    await services.chats.tag(active.user_id, active.id, tag)
    await update.effective_message.reply_text("✅ Тег обновлён")


async def pin_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    services = get_services(context)
    active = await services.chats.active(get_user_id(update))
    await services.chats.toggle_pin(active.user_id, active.id)
    await update.effective_message.reply_text("📌 Статус закрепления изменён")


async def save_memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 2:
        raise ValueError("Использование: /save категория текст")
    memory = await get_services(context).memory.save(
        get_user_id(update), context.args[0], " ".join(context.args[1:])
    )
    await update.effective_message.reply_text(f"🧠 Сохранено воспоминание #{memory.id}")


async def memories_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    memories = await get_services(context).memory.list(get_user_id(update))
    text = (
        "\n".join(f"#{item.id} [{item.category}] {item.content}" for item in memories)
        or "Память пуста"
    )
    await reply_text(update.effective_message, text)


async def forget_memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    memory_id = _integer_argument(context.args, "Использование: /forget ID")
    deleted = await get_services(context).memory.forget(get_user_id(update), memory_id)
    await update.effective_message.reply_text("🗑 Удалено" if deleted else "Запись не найдена")


async def clear_memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    count = await get_services(context).memory.clear(get_user_id(update))
    await update.effective_message.reply_text(f"🧹 Удалено записей: {count}")


async def add_todo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    todo = await get_services(context).tasks.create(get_user_id(update), " ".join(context.args))
    await update.effective_message.reply_text(f"✅ Задача #{todo.id} добавлена")


async def todos_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    todos = await get_services(context).tasks.list(get_user_id(update))
    text = (
        "\n".join(f"{'✅' if item.is_done else '⬜'} #{item.id} {item.text}" for item in todos)
        or "Задач нет"
    )
    await reply_text(update.effective_message, text)


async def done_todo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    todo_id = _integer_argument(context.args, "Использование: /done ID")
    done = await get_services(context).tasks.complete(get_user_id(update), todo_id)
    await update.effective_message.reply_text("✅ Готово" if done else "Задача не найдена")


async def delete_todo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    todo_id = _integer_argument(context.args, "Использование: /deltodo ID")
    done = await get_services(context).tasks.delete(get_user_id(update), todo_id)
    await update.effective_message.reply_text("🗑 Удалено" if done else "Задача не найдена")


async def remind_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 3:
        raise ValueError("Использование: /remind ГГГГ-ММ-ДД ЧЧ:ММ текст")
    date_text = " ".join(context.args[:2])
    reminder = await get_services(context).reminders.create(
        get_user_id(update), date_text, " ".join(context.args[2:])
    )
    await update.effective_message.reply_text(f"⏰ Напоминание #{reminder.id} создано")


async def reminders_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    reminders = await get_services(context).reminders.list(get_user_id(update))
    text = (
        "\n".join(f"#{item.id} {item.remind_at:%Y-%m-%d %H:%M} — {item.text}" for item in reminders)
        or "Активных напоминаний нет"
    )
    await reply_text(update.effective_message, text)


async def favorite_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    replied = message.reply_to_message if message else None
    if replied is None or not replied.text or not replied.from_user or not replied.from_user.is_bot:
        raise ValueError("Ответь командой /fav на сообщение бота")
    services = get_services(context)
    chat = await services.chats.active(get_user_id(update))
    favorite = await services.favorites.add(chat.user_id, chat.id, replied.text)
    await message.reply_text(f"⭐ Добавлено в избранное #{favorite.id}")


async def favorites_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    items = await get_services(context).favorites.list(get_user_id(update))
    text = "\n\n".join(f"⭐ #{item.id}\n{item.content}" for item in items) or "Избранное пусто"
    await reply_text(update.effective_message, text)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    stats = await get_services(context).stats.summary(get_user_id(update))
    await update.effective_message.reply_text(
        f"📊 За 30 дней\nЗапросов: {stats.requests}\nТокенов: {stats.tokens}\n"
        "Квота Gemini управляется в Google AI Studio."
    )


async def brief_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    brief = await get_services(context).brief.get(get_user_id(update))
    await update.effective_message.reply_text(
        f"🗂 Активный чат: {brief.chat.title}\n"
        f"⬜ Открытых задач: {len(brief.todos)}\n"
        f"⏰ Напоминаний: {len(brief.reminders)}\n"
        f"📊 Запросов за 30 дней: {brief.stats.requests}"
    )


async def setting_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    command = update.effective_message.text.split()[0].split("@")[0].lstrip("/")
    field = {"mode": "mode", "style": "style", "language": "language"}[command]
    if not context.args:
        settings = await get_services(context).settings.get(get_user_id(update))
        await update.effective_message.reply_text(f"Текущее значение: {getattr(settings, field)}")
        return
    settings = await get_services(context).settings.set(
        get_user_id(update), field, context.args[0].lower()
    )
    await update.effective_message.reply_text(f"✅ Новое значение: {getattr(settings, field)}")


async def allow_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = _integer_argument(context.args, "Использование: /allow USER_ID")
    await get_services(context).access.allow(user_id, get_user_id(update))
    await update.effective_message.reply_text(f"✅ Пользователь {user_id} добавлен")


async def deny_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = _integer_argument(context.args, "Использование: /deny USER_ID")
    deleted = await get_services(context).access.deny(user_id, get_user_id(update))
    await update.effective_message.reply_text(
        "✅ Доступ закрыт" if deleted else "Пользователь не найден"
    )


async def whitelist_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    users = await get_services(context).access.list(get_user_id(update))
    await update.effective_message.reply_text(
        "Whitelist:\n" + ("\n".join(map(str, users)) or "пуст")
    )


async def panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await show_panel(update, context)


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None:
        return
    if [argument.lower() for argument in context.args] != ["confirm"]:
        await message.reply_text(
            "⚠️ <b>Полный сброс Aira</b>\n\n"
            "Будут удалены все чаты, сообщения, память, задачи, напоминания, "
            "избранное, настройки и статистика.\n\n"
            "Для подтверждения отправьте: /reset confirm",
            parse_mode=ParseMode.HTML,
        )
        return

    services = get_services(context)
    settings = await services.settings.get(get_user_id(update))
    await services.reset.reset(get_user_id(update))
    await _remove_old_panel(update, context, settings.panel_message_id)
    await message.reply_text("✅ Данные Aira очищены. Теперь вы начинаете с нуля.")


async def _remove_old_panel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    panel_message_id: int | None,
) -> None:
    if panel_message_id is None or update.effective_chat is None:
        return
    try:
        await context.bot.unpin_chat_message(update.effective_chat.id, panel_message_id)
        await context.bot.delete_message(update.effective_chat.id, panel_message_id)
    except TelegramError:
        return


def _integer_argument(arguments: list[str], usage: str) -> int:
    if not arguments:
        raise ValueError(usage)
    try:
        return int(arguments[0])
    except ValueError as error:
        raise ValueError(usage) from error
