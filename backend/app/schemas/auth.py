"""Схемы аутентификации. Контракт — docs/api.md, раздел 1."""

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.constants import LOGIN_MAX_LENGTH, LOGIN_MIN_LENGTH, PASSWORD_MIN_LENGTH

LOGIN_RE = re.compile(r"^[A-Za-z0-9_]+$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")

# bcrypt принимает не больше 72 байт и падает, если передать больше
PASSWORD_MAX_BYTES = 72


class RegisterRequest(BaseModel):
    """Регистрация: логин и e-mail уникальны, пароль не короче 8 символов."""

    login: str = Field(min_length=LOGIN_MIN_LENGTH, max_length=LOGIN_MAX_LENGTH)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=128)

    @field_validator("login")
    @classmethod
    def check_login(cls, value: str) -> str:
        if not LOGIN_RE.fullmatch(value):
            raise ValueError("Логин: только латиница, цифры и подчёркивание")
        return value

    @field_validator("email")
    @classmethod
    def check_email(cls, value: str) -> str:
        email = value.strip().lower()
        if not EMAIL_RE.fullmatch(email):
            raise ValueError("Некорректный e-mail")
        return email

    @field_validator("password")
    @classmethod
    def check_password(cls, value: str) -> str:
        if len(value.encode("utf-8")) > PASSWORD_MAX_BYTES:
            raise ValueError(f"Пароль длиннее {PASSWORD_MAX_BYTES} байт")
        return value


class LoginRequest(BaseModel):
    """Поле `login` принимает и логин, и e-mail — фронтенду не нужен переключатель."""

    login: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class UserRead(BaseModel):
    """Пользователь без служебных полей: хэш пароля наружу не отдаём никогда."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    login: str
    email: str
    role: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserRead
