# Aira

Персональный Telegram AI-ассистент на Gemini, PostgreSQL и `python-telegram-bot`.

## Запуск

1. Создайте бота через `@BotFather` и включите inline mode командой `/setinline`.
2. Получите Gemini API key в Google AI Studio.
3. Скопируйте `.env.example` в `.env` и заполните секреты.
4. Укажите свой числовой Telegram ID в `ADMIN_USER_ID`.
5. Запустите Docker Desktop, затем выполните:

```bash
docker compose up --build -d
docker compose logs -f bot
```

Остановка:

```bash
docker compose down
```

Данные PostgreSQL сохраняются в named volume `postgres_data`.

## Разработка

```bash
uv sync
uv run ruff check src tests
uv run pytest -q
uv run python -m src.bot
```

Для локального запуска без Docker замените хост `db` в `DATABASE_URL` на `localhost` и
предварительно запустите PostgreSQL.

## Deploy на Render

Этот бот запускается через Telegram polling, поэтому на Render нужен Background Worker,
а не Web Service.

Build Command:

```bash
uv sync --frozen --no-dev
```

Start Command:

```bash
uv run --no-sync python -m src.bot
```

Environment Variables:

- `TELEGRAM_BOT_TOKEN`
- `GEMINI_API_KEY`
- `DATABASE_URL`
- `ADMIN_USER_ID`
- `GEMINI_MODEL` — опционально
- `LLM_PROVIDER` — опционально
- `TIMEZONE` — опционально

## Основные команды

- `/help` — полный список команд.
- `/panel` — закреплённая панель.
- `/newchat`, `/chats`, `/switch` — управление диалогами.
- `/save`, `/memories`, `/forget`, `/clear` — долгосрочная память.
- `/todo`, `/todos`, `/done`, `/deltodo` — задачи.
- `/remind`, `/reminders` — напоминания.
- `/allow`, `/deny`, `/whitelist` — доступ, только для администратора.
- `/ai вопрос` — обращение к Aira в групповом чате.

Секретный файл `.env` исключён из Git и Docker build context.
