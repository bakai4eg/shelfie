"""Аутентификация: регистрация, вход, выход, текущий пользователь. Задача T1.1."""

from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["auth"])

# TODO(T1.1): POST /register, POST /login, POST /logout, GET /me
# Контракт: docs/api.md, раздел 1. Модели: users, sessions (ADR 0001).
