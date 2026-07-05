import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True, slots=True)
class Config:
    telegram_token: str
    gemini_api_key: str
    gemini_model: str
    database_url: str
    admin_user_id: int
    llm_provider: str
    timezone: str


def get_required_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise ValueError(f"Переменная {name} не задана")

    return value


def load_config() -> Config:
    load_dotenv()

    return Config(
        telegram_token=get_required_env("TELEGRAM_BOT_TOKEN"),
        gemini_api_key=get_required_env("GEMINI_API_KEY"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        database_url=get_required_env("DATABASE_URL"),
        admin_user_id=parse_admin_user_id(),
        llm_provider=os.getenv("LLM_PROVIDER", "gemini").lower(),
        timezone=os.getenv("TIMEZONE", "Asia/Baku"),
    )


def parse_admin_user_id() -> int:
    raw_user_id = get_required_env("ADMIN_USER_ID")

    try:
        return int(raw_user_id)
    except ValueError as error:
        raise ValueError("ADMIN_USER_ID должен быть целым числом") from error
