from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True, slots=True)
class Chat:
    id: int
    user_id: int
    title: str
    tag: str | None
    status: str
    is_pinned: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class Message:
    id: int
    chat_id: int
    role: str
    content: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Memory:
    id: int
    user_id: int
    category: str
    content: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Todo:
    id: int
    user_id: int
    text: str
    is_done: bool
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Reminder:
    id: int
    user_id: int
    text: str
    remind_at: datetime
    is_active: bool


@dataclass(frozen=True, slots=True)
class Favorite:
    id: int
    user_id: int
    chat_id: int | None
    content: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class UserSettings:
    user_id: int
    style: str
    language: str
    mode: str
    panel_message_id: int | None


@dataclass(frozen=True, slots=True)
class DailyStats:
    date: date
    requests_count: int
    tokens_count: int
