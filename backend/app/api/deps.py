"""Общие зависимости API: текущий пользователь, сессия и проверка ролей.

Гость — это отсутствие токена. `get_current_user` отвечает 401, если токена нет
или сессия отозвана/истекла; `get_optional_user` в этом случае возвращает `None`.
Заблокированный пользователь получает 403 даже с валидным токеном (ТЗ 4.2.2).
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ROLE_LEVEL
from app.core.security import decode_token
from app.db.session import get_session
from app.models.user import Session as AuthSession
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@dataclass(slots=True)
class AuthContext:
    """Пара «пользователь + его сессия»: нужна logout и будущим проверкам."""

    user: User
    session: AuthSession


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не авторизован",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_auth(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: SessionDep,
) -> AuthContext:
    """Проверяем и подпись токена, и запись в `sessions` (ADR 0001)."""
    if credentials is None:
        raise _unauthorized()

    try:
        payload = decode_token(credentials.credentials)
        user_id = int(payload["sub"])
        jti = str(payload["jti"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        raise _unauthorized() from None

    session = await db.scalar(
        select(AuthSession).where(
            AuthSession.jti == jti,
            AuthSession.user_id == user_id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > datetime.now(UTC),
        )
    )
    if session is None:
        raise _unauthorized()

    user = await db.get(User, user_id)
    if user is None:
        raise _unauthorized()

    return AuthContext(user=user, session=session)


async def get_current_user(
    auth: Annotated[AuthContext, Depends(get_current_auth)],
) -> User:
    return auth.user


async def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: SessionDep,
) -> User | None:
    """Без токена — гость; с битым или отозванным токеном — всё равно 401."""
    if credentials is None:
        return None
    return (await get_current_auth(credentials, db)).user


CurrentAuth = Annotated[AuthContext, Depends(get_current_auth)]
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]


def require_role(minimum: str):
    """Фабрика зависимостей для модераторов и администраторов (T3.1)."""

    async def checker(user: CurrentUser) -> User:
        if ROLE_LEVEL.get(user.role, 0) < ROLE_LEVEL[minimum]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав",
            )
        return user

    return checker
