# Backend

FastAPI + SQLAlchemy 2 (async) + Alembic + Pydantic v2. Правила архитектуры — [`docs/architecture.md`](../docs/architecture.md), контракт — [`docs/api.md`](../docs/api.md), схема БД — [`docs/data-model.md`](../docs/data-model.md).

## Запуск

```bash
python -m venv .venv
.venv\Scripts\activate            # Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"

# локально на SQLite (быстро, без Docker)
# в .env: DATABASE_URL=sqlite+aiosqlite:///./shelfie.sqlite3
alembic upgrade head
uvicorn app.main:app --reload
```

Swagger — http://localhost:8000/docs, health — http://localhost:8000/api/health.

## Проверки

```bash
ruff check . --fix
ruff format .
pytest -q
```

Тесты идут на SQLite в памяти (фикстура в `tests/conftest.py`), PostgreSQL для них не нужен.

## Миграции

```bash
alembic revision --autogenerate -m "add users and sessions"
alembic upgrade head
alembic downgrade -1
```

Сгенерированный файл **читаем и правим руками**: autogenerate не видит переименования и не расставляет каскады. Имя миграции — по смыслу (`0001_users_sessions`).

## Структура

```
app/
├── main.py              # приложение, CORS, подключение роутеров
├── core/
│   ├── config.py        # настройки из .env
│   ├── constants.py     # числа и перечисления из ТЗ
│   └── security.py      # bcrypt + JWT
├── db/
│   ├── base.py          # Base, TimestampMixin, соглашения имён
│   ├── session.py       # движок, фабрика сессий, зависимость get_session
│   └── seed.py          # данные для локальной разработки
├── models/              # ORM-модели по подсистемам
├── schemas/             # Pydantic-схемы (общие — в common.py)
├── api/
│   ├── deps.py          # текущий пользователь, проверка ролей
│   ├── router.py        # сборка роутеров
│   └── routes/          # по файлу на подсистему, с TODO по задачам
└── services/            # бизнес-логика
    └── providers/       # клиенты TMDB / OpenLibrary / Google Books
```

## Куда что писать

| Что | Куда |
| --- | --- |
| Новый эндпоинт | `api/routes/<подсистема>.py` + строка в `api/router.py` |
| Правило (статус, оценка, права) | `services/`, не в маршруте |
| Новая таблица | `models/<подсистема>.py`, импорт в `models/__init__.py`, миграция |
| Число или перечисление из ТЗ | `core/constants.py` |
| Внешний API | `services/providers/<источник>.py`, только через `httpx.AsyncClient` |
| Общая схема ответа | `schemas/common.py` |

## Договорённости

- Только `async def` в маршрутах и никаких блокирующих вызовов.
- Коммит делает сервис, маршрут не вызывает `session.commit()` вразнобой.
- Ошибки — через `HTTPException` со статусами из `docs/architecture.md`, п. 10.
- Все секреты — в `.env`; в коде только `settings.*`.
- `print` в коде нет: логируем через `logging`.
