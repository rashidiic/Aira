from src.config import Config
from src.services.gemini import GeminiService
from src.services.llm import BaseLLMService


def create_llm_service(config: Config) -> BaseLLMService:
    if config.llm_provider == "gemini":
        return GeminiService(config.gemini_api_key, config.gemini_model)
    raise ValueError(f"Неподдерживаемый LLM_PROVIDER: {config.llm_provider}")
