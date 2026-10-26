"""Аутентификация: регистрация, вход, выход, текущий пользователь. Задача T1.1."""

from fastapi import APIRouter, Response, status

from app.api.deps import CurrentAuth, CurrentUser, SessionDep
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserRead
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация с автоматическим входом",
)
async def register(payload: RegisterRequest, db: SessionDep) -> TokenResponse:
    return await auth_service.register_user(db, payload)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Вход по логину или e-mail",
)
async def login(payload: LoginRequest, db: SessionDep) -> TokenResponse:
    return await auth_service.login_user(db, payload)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Отозвать текущую сессию",
)
async def logout(auth: CurrentAuth, db: SessionDep) -> Response:
    await auth_service.revoke_session(db, auth.session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserRead, summary="Текущий пользователь")
async def me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)
