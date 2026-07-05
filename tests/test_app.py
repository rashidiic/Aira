from src.app import _commands
from src.handlers.commands import reset_command


def test_reset_is_registered_as_private_command() -> None:
    assert _commands()["reset"] is reset_command
