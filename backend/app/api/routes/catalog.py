"""Каталог: поиск, фильтры, страница карточки, внешние источники. Задачи T2.1–T2.2, T3.4."""

from fastapi import APIRouter

router = APIRouter(prefix="/catalog", tags=["catalog"])

# TODO(T2.1): GET /, GET /filters
# TODO(T2.2): поиск по внешним источникам с кэшем в catalog_items
# TODO(T3.4): GET /{item_id} — рейтинг, рецензии, кнопки полок
# TODO(T4.3): GET /{item_id}/reviews, POST /{item_id}/reviews
# Контракт: docs/api.md, раздел 3.
