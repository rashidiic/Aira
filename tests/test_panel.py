from telegram.error import BadRequest

from src.handlers.panel import _is_message_unchanged, _is_missing_panel


def test_unchanged_panel_error_is_recognized() -> None:
    error = BadRequest("Message is not modified: content is exactly the same")

    assert _is_message_unchanged(error)


def test_other_bad_request_is_not_hidden() -> None:
    error = BadRequest("Message to edit not found")

    assert not _is_message_unchanged(error)


def test_missing_panel_error_is_recognized() -> None:
    error = BadRequest("Message to edit not found")

    assert _is_missing_panel(error)
