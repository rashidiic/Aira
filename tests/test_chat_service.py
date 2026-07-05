from datetime import datetime

from src.db.models import Chat, UserSettings
from src.services.chats import ChatService
from src.services.llm import BaseLLMService, LLMResponse
from src.services.prompts import PromptBuilder


class FakeLLM(BaseLLMService):
    async def generate_response(self, prompt, history, system_prompt):
        assert prompt == "Привет"
        assert history == []
        assert "Russian" in system_prompt
        return LLMResponse("Привет!", 10, 5)

    async def transcribe_audio(self, audio: bytes, mime_type: str) -> str:
        return "текст"

    async def generate_chat_title(self, message: str) -> str:
        return "Приветствие"


class FakeDatabase:
    def __init__(self) -> None:
        self.chat = None
        self.messages = []

    async def get_active_chat(self, user_id):
        return self.chat

    async def create_chat(self, user_id, title):
        now = datetime.now()
        self.chat = Chat(1, user_id, title, None, "active", False, now, now)
        return self.chat

    async def get_recent_messages(self, chat_id, limit):
        return []

    async def ensure_settings(self, user_id):
        return UserSettings(user_id, "friendly", "ru", "normal", None)

    async def add_message(self, chat_id, role, content):
        self.messages.append((role, content))

    async def rename_chat(self, user_id, chat_id, title):
        self.chat = Chat(
            self.chat.id,
            user_id,
            title,
            None,
            "active",
            False,
            self.chat.created_at,
            self.chat.updated_at,
        )
        return True


class FakeMemory:
    async def list(self, user_id):
        return []


class FakeStats:
    def __init__(self):
        self.tokens = 0

    async def record(self, user_id, input_tokens, output_tokens):
        self.tokens = input_tokens + output_tokens


async def test_first_message_creates_chat_and_saves_exchange() -> None:
    database = FakeDatabase()
    stats = FakeStats()
    service = ChatService(
        database,  # type: ignore[arg-type]
        FakeLLM(),
        FakeMemory(),  # type: ignore[arg-type]
        stats,  # type: ignore[arg-type]
        PromptBuilder("You are Aira."),
    )

    reply = await service.ask(42, "Привет")

    assert reply.text == "Привет!"
    assert reply.chat.title == "Приветствие"
    assert database.messages == [("user", "Привет"), ("assistant", "Привет!")]
    assert stats.tokens == 15
