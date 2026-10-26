"""Регистрация, вход и управление сессиями (ТЗ 4.2.1)."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import Session as AuthSession
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserRead,
)

INVALID_CREDENTIALS = "Неверный логин или пароль"
DUPLICATE = "Логин или e-mail уже заняты"
BLOCKED = "Аккаунт заблокирован"


async def _find_user(db: AsyncSession, identifier: str) -> User | None:
    """Ищем по логину или e-mail без учёта регистра."""
    needle = identifier.strip().lower()
    return await db.scalar(
        select(User)
        .where(or_(func.lower(User.login) == needle, func.lower(User.email) == needle))
        .limit(1)
    )


async def _ensure_unique(db: AsyncSession, login: str, email: str) -> None:
    clash = await db.scalar(
        select(User)
        .where(
            or_(
                func.lower(User.login) == login.lower(),
                func.lower(User.email) == email.lower(),
            )
        )
        .limit(1)
    )
    if clash is None:
        return
    if clash.login.lower() == login.lower():
        raise HTTPException(status.HTTP_409_CONFLICT, "Логин уже занят")
    raise HTTPException(status.HTTP_409_CONFLICT, "E-mail уже занят")


async def _issue_session(db: AsyncSession, user: User) -> TokenResponse:
    """Пишем сессию и выпускаем токен с её `jti` (ADR 0001)."""
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    jti = str(uuid4())
    db.add(AuthSession(user_id=user.id, jti=jti, expires_at=expires_at))

    try:
        await db.commit()
    except IntegrityError:
        # Между проверкой уникальности и вставкой мог проскочить дубль
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, DUPLICATE) from None

    await db.refresh(user)
    token = create_access_token(subject=str(user.id), jti=jti, role=user.role)
    return TokenResponse(
        access_token=token,
        expires_at=expires_at,
        user=UserRead.model_validate(user),
    )


async def register_user(db: AsyncSession, payload: RegisterRequest) -> TokenResponse:
    """Создаёт пользователя и сразу вводит его в систему."""
    await _ensure_unique(db, payload.login, payload.email)

    user = User(
        login=payload.login,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)

    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, DUPLICATE) from None

    return await _issue_session(db, user)


async def login_user(db: AsyncSession, payload: LoginRequest) -> TokenResponse:
    user = await _find_user(db, payload.login)

    # Сначала пароль, потом блокировка: не подсказываем, какие аккаунты существуют
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            INVALID_CREDENTIALS,
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.is_blocked:
        raise HTTPException(status.HTTP_403_FORBIDDEN, BLOCKED)

    return await _issue_session(db, user)


async def revoke_session(db: AsyncSession, session: AuthSession) -> None:
    """Logout: сессия помечается отозванной, повторный выход по тому же токену даст 401."""
    if session.revoked_at is not None:
        return
    session.revoked_at = datetime.now(UTC)
    await db.commit()


async def revoke_all_sessions(db: AsyncSession, user_id: int) -> None:
    """Смена пароля и блокировка закрывают все устройства (ТЗ 4.2.4, 4.6.4)."""
    await db.execute(
        update(AuthSession)
        .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    await db.commit()
