from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal, Sequence

MessageRole = Literal["user", "assistant"]


@dataclass(frozen=True, slots=True)
class LLMMessage:
    role: MessageRole
    content: str


@dataclass(frozen=True, slots=True)
class LLMResponse:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0


class BaseLLMService(ABC):
    @abstractmethod
    async def generate_response(
        self,
        prompt: str,
        history: Sequence[LLMMessage],
        system_prompt: str,
    ) -> LLMResponse:
        pass

    @abstractmethod
    async def transcribe_audio(
        self,
        audio: bytes,
        mime_type: str,
    ) -> str:
        pass

    @abstractmethod
    async def generate_chat_title(self, message: str) -> str:
        pass
