"""Общие зависимости API: текущий пользователь и проверка ролей.

Каркас для T1.1–T1.2 и T3.1. Пока пользователей нет — любой защищённый
эндпоинт отвечает 401. Логика подстановки пользователя появится вместе
с моделью `users` и таблицей `sessions` (ADR 0001).
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ROLE_LEVEL
from app.db.session import get_session

bearer_scheme = HTTPBearer(auto_error=False)

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> dict:
    """TODO(T1.1): декодировать токен, проверить сессию и вернуть пользователя."""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Не авторизован")
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Не авторизован")


async def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> dict | None:
    """Гость — это отсутствие токена, а не ошибка."""
    if credentials is None:
        return None
    return await get_current_user(credentials)


CurrentUser = Annotated[dict, Depends(get_current_user)]
OptionalUser = Annotated[dict | None, Depends(get_optional_user)]


def require_role(minimum: str):
    """Фабрика зависимостей для модераторов и администраторов (T3.1)."""

    async def checker(user: CurrentUser) -> dict:
        if ROLE_LEVEL.get(user.get("role", ""), 0) < ROLE_LEVEL[minimum]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")
        return user

    return checker
