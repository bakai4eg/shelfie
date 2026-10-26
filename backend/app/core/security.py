"""Безопасность: хэширование паролей и JWT.

Реализация — задача T1.1. Ниже каркас с рабочими примитивами,
чтобы не изобретать их в спешке в конце этапа.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import settings

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Хэшируем пароль через bcrypt. В БД попадает только результат."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(
    subject: str, jti: str, role: str, expires_minutes: int | None = None
) -> str:
    """JWT с jti: сам токен проверяется подписью, сессия — записью в таблице sessions."""
    minutes = expires_minutes or settings.access_token_expire_minutes
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "jti": jti,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Бросает jwt.InvalidTokenError, если токен просрочен или подпись не сходится."""
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
