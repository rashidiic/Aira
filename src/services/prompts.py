from pathlib import Path

from src.db.models import Memory, UserSettings


class PromptBuilder:
    def __init__(self, base_prompt: str) -> None:
        self._base_prompt = base_prompt.strip()

    @classmethod
    def from_file(cls, path: Path) -> "PromptBuilder":
        return cls(path.read_text(encoding="utf-8"))

    def build(self, settings: UserSettings, memories: list[Memory]) -> str:
        parts = [
            self._base_prompt,
            self._mode_instruction(settings.mode),
            self._style_instruction(settings.style),
            self._language_instruction(settings.language),
        ]
        if memories:
            parts.append(self._memory_section(memories))
        return "\n\n".join(part for part in parts if part)

    @staticmethod
    def _mode_instruction(mode: str) -> str:
        return {
            "normal": "Answer as a capable personal assistant.",
            "code": "Focus on correct, maintainable code and practical examples.",
            "study": "Teach step by step and check understanding.",
        }.get(mode, "Answer as a capable personal assistant.")

    @staticmethod
    def _style_instruction(style: str) -> str:
        return {
            "formal": "Use a formal tone.",
            "friendly": "Use a warm, friendly tone.",
            "brief": "Be concise and direct.",
            "detailed": "Give a thorough, structured answer.",
        }.get(style, "Use a warm, friendly tone.")

    @staticmethod
    def _language_instruction(language: str) -> str:
        names = {"ru": "Russian", "en": "English", "az": "Azerbaijani"}
        return f"Always answer in {names.get(language, 'Russian')}."

    @staticmethod
    def _memory_section(memories: list[Memory]) -> str:
        lines = [f"- [{memory.category}] {memory.content}" for memory in memories]
        return "Long-term user memory:\n" + "\n".join(lines)
