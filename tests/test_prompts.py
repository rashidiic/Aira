from datetime import datetime

from src.db.models import Memory, UserSettings
from src.services.prompts import PromptBuilder


def test_prompt_contains_settings_and_memory() -> None:
    settings = UserSettings(1, "brief", "az", "code", None)
    memory = Memory(1, 1, "profile", "Python developer", datetime.now())

    prompt = PromptBuilder("You are Aira.").build(settings, [memory])

    assert "maintainable code" in prompt
    assert "concise" in prompt
    assert "Azerbaijani" in prompt
    assert "Python developer" in prompt


def test_prompt_contains_swearing_mode_instruction() -> None:
    settings = UserSettings(1, "friendly", "ru", "swearing", None)

    prompt = PromptBuilder("You are Aira.").build(settings, [])

    assert "expressive profanity" in prompt
    assert "Do not use slurs" in prompt
