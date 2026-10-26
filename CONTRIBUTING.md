# Как контрибьютить

Всё, что нужно, чтобы поднять проект с нуля и не сломать `main`. Правила веток и ревью — в [`docs/git-workflow.md`](docs/git-workflow.md).

## 0. Что установить

| Инструмент | Версия | Зачем |
| --- | --- | --- |
| Git | 2.40+ | версии |
| Python | 3.11+ | бэкенд |
| Node.js | 20+ | фронтенд |
| Docker Desktop | 24+ | `docker compose up` (по желанию) |

## 1. Клонирование и настройка

```bash
git clone https://github.com/bakai4eg/shelfie.git
cd shelfie

# .env из шаблона
copy .env.example .env      # Windows
cp .env.example .env        # Linux/macOS
```

В `.env` минимум что меняем: `SECRET_KEY`, ключи `TMDB_API_KEY`, `GOOGLE_BOOKS_API_KEY`.
`DATABASE_URL` для локального запуска без Docker:

```
DATABASE_URL=sqlite+aiosqlite:///./shelfie.sqlite3
```

## 2. Бэкенд

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"

alembic upgrade head              # применить миграции
uvicorn app.main:app --reload     # http://localhost:8000/docs
```

Полезное:

```bash
pytest -q                 # тесты
ruff check . --fix        # линтер
alembic revision --autogenerate -m "add lists"
```

## 3. Фронтенд

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
npm run typecheck  # tsc --noEmit
npm run build      # проверка прод-сборки
npm run lint
```

Адрес API берётся из `VITE_API_URL` (по умолчанию `http://localhost:8000/api`).

## 4. Всё через Docker

```bash
docker compose up --build
docker compose exec api alembic upgrade head
docker compose logs -f api
```

- `frontend` — http://localhost:5173
- `api` + Swagger — http://localhost:8000/docs
- `db` — внутри сети compose, наружу не публикуется

## 5. Перед PR — чек-лист

- [ ] Ветка от свежего `main`, конфликтов нет.
- [ ] `ruff check .` и `pytest -q` в `backend/` проходят.
- [ ] `npm run typecheck` и `npm run build` в `frontend/` проходят.
- [ ] Новые эндпоинты описаны в `docs/api.md`.
- [ ] Миграция создана, `alembic upgrade head` работает на чистой БД.
- [ ] Секретов, паролей и ключей в диффе нет.
- [ ] В описании PR указано `Closes T?.?` и как проверить руками.

## 6. Частые проблемы

| Симптом | Что делать |
| --- | --- |
| `ModuleNotFoundError: app` | запускать команды из `backend/`, пакет ставится через `pip install -e ".[dev]"` |
| `sqlalchemy.exc.NoSuchModuleError: asyncpg` | либо ставим зависимость, либо переключаем `DATABASE_URL` на SQLite |
| CORS-ошибка в браузере | добавить адрес фронтенда в `CORS_ORIGINS` и перезапустить API |
| 401 сразу после входа | токен не подставляется в `Authorization` — смотреть `lib/api.ts` |
| Alembic «target database is not up to date» | `alembic upgrade head`, затем повторить `revision` |
| Порт 5432 занят | поменять проброс порта в `docker-compose.yml` (наружу БД не нужна) |
| Windows: `source` не работает | в PowerShell — `.venv\Scripts\Activate.ps1` |

## 7. Стиль

- Python: PEP 8 через `ruff`, длина строки 100, типы у публичных функций.
- TypeScript: strict, без `any` в новом коде, компоненты — функции.
- Комментарии и UI-тексты — по-русски, имена в коде — по-английски.
- Один компонент — один файл, один сервис — одна зона ответственности.
