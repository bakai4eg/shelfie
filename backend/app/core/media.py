"""Пути к файлам профиля.

Аватары лежат в `MEDIA_ROOT`, в БД хранится относительный путь. Наружу
отдаём URL `/media/<path>`, чтобы фронтенд не знал про файловую систему.
"""

from app.core.config import settings


def avatar_url(path: str | None) -> str | None:
    """Относительный путь из БД → публичный URL. Внешние ссылки не трогаем."""
    if not path:
        return None
    if path.startswith(("http://", "https://", "/")):
        return path
    return f"/media/{path}"


def media_root() -> str:
    return settings.media_root
