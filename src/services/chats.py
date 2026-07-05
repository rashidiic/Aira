from __future__ import annotations

import logging
from collections import defaultdict, deque
from collections.abc import Sequence
from dataclasses import dataclass

from src.db.database import Database
from src.db.models import Chat, Message
from src.services.llm import BaseLLMService, LLMMessage
from src.services.memory import MemoryService
from src.services.prompts import PromptBuilder
from src.services.stats import StatsService

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AssistantReply:
    text: str
    chat: Chat


class ChatService:
    def __init__(
        self,
        database: Database,
        llm: BaseLLMService,
        memory: MemoryService,
        stats: StatsService,
        prompts: PromptBuilder,
        buffer_size: int = 15,
    ) -> None:
        self._database = database
        self._llm = llm
        self._memory = memory
        self._stats = stats
        self._prompts = prompts
        self._buffer_size = buffer_size
        self._buffers: dict[int, deque[LLMMessage]] = defaultdict(lambda: deque(maxlen=buffer_size))

    async def ask(self, user_id: int, prompt: str) -> AssistantReply:
        if not prompt.strip():
            raise ValueError("Сообщение пустое")
        chat, is_new = await self._active_or_new_chat(user_id)
        history = await self._history(chat.id)
        settings = await self._database.ensure_settings(user_id)
        memories = await self._memory.list(user_id)
        system_prompt = self._prompts.build(settings, memories)

        await self._database.add_message(chat.id, "user", prompt.strip())
        response = await self._llm.generate_response(prompt.strip(), history, system_prompt)
        await self._database.add_message(chat.id, "assistant", response.text)
        self._append_exchange(chat.id, prompt.strip(), response.text)
        await self._stats.record(user_id, response.input_tokens, response.output_tokens)

        if is_new:
            chat = await self._title_new_chat(user_id, chat, prompt)
        return AssistantReply(response.text, chat)

    async def ask_inline(self, prompt: str) -> str:
        response = await self._llm.generate_response(
            prompt=prompt,
            history=[],
            system_prompt="Answer the user's question directly and concisely.",
        )
        return response.text

    async def transcribe(self, audio: bytes, mime_type: str) -> str:
        return await self._llm.transcribe_audio(audio, mime_type)

    async def create(self, user_id: int, title: str = "Новый чат") -> Chat:
        return await self._database.create_chat(user_id, title)

    async def list(self, user_id: int, archived: bool = False) -> list[Chat]:
        return await self._database.list_chats(user_id, archived)

    async def active(self, user_id: int) -> Chat:
        chat, _ = await self._active_or_new_chat(user_id)
        return chat

    async def switch(self, user_id: int, chat_id: int) -> Chat | None:
        return await self._database.switch_chat(user_id, chat_id)

    async def rename(self, user_id: int, chat_id: int, title: str) -> bool:
        return await self._database.rename_chat(user_id, chat_id, title.strip())

    async def delete(self, user_id: int, chat_id: int) -> bool:
        self._buffers.pop(chat_id, None)
        return await self._database.delete_chat(user_id, chat_id)

    async def archive(self, user_id: int, chat_id: int) -> bool:
        self._buffers.pop(chat_id, None)
        return await self._database.archive_chat(user_id, chat_id)

    async def duplicate(self, user_id: int, chat_id: int) -> Chat | None:
        return await self._database.duplicate_chat(user_id, chat_id)

    async def toggle_pin(self, user_id: int, chat_id: int) -> bool:
        return await self._database.toggle_chat_pin(user_id, chat_id)

    async def tag(self, user_id: int, chat_id: int, tag: str | None) -> bool:
        return await self._database.set_chat_tag(user_id, chat_id, tag)

    async def search(self, user_id: int, term: str) -> list[Chat]:
        return await self._database.search_chats(user_id, term.strip())

    async def export(self, user_id: int, chat_id: int) -> str:
        messages = await self._database.get_all_messages(chat_id, user_id)
        return "\n\n".join(f"{item.role.upper()}: {item.content}" for item in messages)

    async def clear_cache(self, user_id: int) -> None:
        chats = await self._database.list_chats(user_id, include_archived=True)
        for chat in chats:
            self._buffers.pop(chat.id, None)

    async def _active_or_new_chat(self, user_id: int) -> tuple[Chat, bool]:
        chat = await self._database.get_active_chat(user_id)
        if chat:
            return chat, False
        return await self._database.create_chat(user_id, "Новый чат"), True

    async def _history(self, chat_id: int) -> Sequence[LLMMessage]:
        if not self._buffers[chat_id]:
            stored = await self._database.get_recent_messages(chat_id, self._buffer_size)
            self._buffers[chat_id].extend(self._to_llm_message(item) for item in stored)
        return list(self._buffers[chat_id])

    def _append_exchange(self, chat_id: int, prompt: str, answer: str) -> None:
        self._buffers[chat_id].append(LLMMessage("user", prompt))
        self._buffers[chat_id].append(LLMMessage("assistant", answer))

    async def _title_new_chat(self, user_id: int, chat: Chat, prompt: str) -> Chat:
        try:
            title = await self._llm.generate_chat_title(prompt)
            await self._database.rename_chat(user_id, chat.id, title)
            return (await self._database.get_active_chat(user_id)) or chat
        except Exception:
            logger.exception("Не удалось создать название чата %s", chat.id)
            return chat

    @staticmethod
    def _to_llm_message(message: Message) -> LLMMessage:
        role = "assistant" if message.role == "assistant" else "user"
        return LLMMessage(role, message.content)
