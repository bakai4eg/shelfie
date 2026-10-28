"""Файлы профиля: аватары (T1.4).

В БД храним относительный путь, наружу отдаём `/media/<path>`. Имя файла
генерируем сами (uuid), оригинальное не используем — так не бывает коллизий
и path traversal. Тип проверяем дважды: по Content-Type и по сигнатуре файла.
"""

from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status

from app.core.config import settings
from app.core.constants import ALLOWED_IMAGE_TYPES

AVATAR_SUBDIR = "avatars"
EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
INVALID_TYPE = "Поддерживаются только JPEG, PNG и WebP"
INVALID_CONTENT = "Файл не похож на изображение"
EMPTY_FILE = "Файл пустой"


def avatar_url(path: str | None) -> str | None:
    """Относительный путь из БД → публичный URL. Внешние ссылки не трогаем."""
    if not path:
        return None
    if path.startswith(("http://", "https://", "/")):
        return path
    return f"/media/{path}"


def _root() -> Path:
    return Path(settings.media_root)


def _matches(content_type: str, head: bytes) -> bool:
    if content_type == "image/jpeg":
        return head.startswith(b"\xff\xd8\xff")
    if content_type == "image/png":
        return head.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/webp":
        return head.startswith(b"RIFF") and head[8:12] == b"WEBP"
    return False


def save_avatar(data: bytes, content_type: str) -> str:
    """Проверяет файл и кладёт его в MEDIA_ROOT/avatars. Возвращает путь для БД."""
    if not data:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, EMPTY_FILE)
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, INVALID_TYPE)
    if not _matches(content_type, data[:16]):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, INVALID_CONTENT)

    relative = f"{AVATAR_SUBDIR}/{uuid4().hex}{EXTENSIONS[content_type]}"
    target = _root() / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return relative


def delete_avatar(path: str | None) -> None:
    """Удаляет старый файл. За пределы MEDIA_ROOT не выходим и не падаем."""
    if not path or path.startswith(("http://", "https://", "/")):
        return
    root = _root().resolve()
    target = (root / path).resolve()
    if target != root and root not in target.parents:
        return
    target.unlink(missing_ok=True)
