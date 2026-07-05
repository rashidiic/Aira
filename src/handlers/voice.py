from telegram import Update
from telegram.ext import ContextTypes

from src.handlers.formatting import reply_markdown
from src.handlers.utils import get_services, get_user_id


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None or message.voice is None:
        return

    await message.chat.send_action("typing")
    telegram_file = await context.bot.get_file(message.voice.file_id)
    audio = bytes(await telegram_file.download_as_bytearray())
    services = get_services(context)
    transcript = await services.chats.transcribe(audio, message.voice.mime_type or "audio/ogg")
    await message.reply_text(f"🎙 {transcript}")
    reply = await services.chats.ask(get_user_id(update), transcript)
    await reply_markdown(message, reply.text)
