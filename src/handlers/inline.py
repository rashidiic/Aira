from uuid import uuid4

from telegram import InlineQueryResultArticle, InputTextMessageContent, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from src.handlers.formatting import markdown_to_html
from src.handlers.utils import get_services


async def handle_inline_query(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.inline_query
    if query is None or not query.query.strip():
        return
    answer = await get_services(context).chats.ask_inline(query.query.strip())
    formatted_answer = markdown_to_html(answer[:2800])
    result = InlineQueryResultArticle(
        id=str(uuid4()),
        title="Ответ Aira",
        description=answer[:120],
        input_message_content=InputTextMessageContent(
            formatted_answer,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        ),
    )
    await query.answer([result], cache_time=0, is_personal=True)
