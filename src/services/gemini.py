from collections.abc import Sequence

from google import genai
from google.genai import types

from src.services.llm import BaseLLMService, LLMMessage, LLMResponse


class GeminiService(BaseLLMService):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model

    async def generate_response(
        self,
        prompt: str,
        history: Sequence[LLMMessage],
        system_prompt: str,
    ) -> LLMResponse:
        contents = [self._to_content(message) for message in history]
        contents.append(self._user_content(prompt))
        config = types.GenerateContentConfig(system_instruction=system_prompt)

        response = await self._generate(contents, config)
        return self._to_llm_response(response)

    async def transcribe_audio(self, audio: bytes, mime_type: str) -> str:
        audio_part = types.Part.from_bytes(data=audio, mime_type=mime_type)
        instruction = "Transcribe this audio accurately. Return only the transcript."

        response = await self._generate([audio_part, instruction])
        return self._response_text(response)

    async def generate_chat_title(self, message: str) -> str:
        config = types.GenerateContentConfig(
            system_instruction="Create a concise chat title of at most six words.",
            temperature=0.2,
        )
        response = await self._generate(message, config)
        return self._response_text(response).strip('"')

    async def _generate(
        self,
        contents: types.ContentListUnion,
        config: types.GenerateContentConfig | None = None,
    ) -> types.GenerateContentResponse:
        return await self._client.aio.models.generate_content(
            model=self._model,
            contents=contents,
            config=config,
        )

    @staticmethod
    def _to_content(message: LLMMessage) -> types.Content:
        role = "model" if message.role == "assistant" else "user"
        return types.Content(
            role=role,
            parts=[types.Part.from_text(text=message.content)],
        )

    @staticmethod
    def _user_content(text: str) -> types.Content:
        return types.Content(
            role="user",
            parts=[types.Part.from_text(text=text)],
        )

    @classmethod
    def _to_llm_response(
        cls,
        response: types.GenerateContentResponse,
    ) -> LLMResponse:
        usage = response.usage_metadata
        return LLMResponse(
            text=cls._response_text(response),
            input_tokens=(usage.prompt_token_count or 0) if usage else 0,
            output_tokens=(usage.candidates_token_count or 0) if usage else 0,
        )

    @staticmethod
    def _response_text(response: types.GenerateContentResponse) -> str:
        try:
            text = response.text
        except ValueError as error:
            raise RuntimeError("Gemini не вернул текстовый ответ") from error
        if not text:
            raise RuntimeError("Gemini вернул пустой ответ")
        return text.strip()
