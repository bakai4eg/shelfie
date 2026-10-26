"""Социальный модуль: рецензии, комментарии, лайки, лента. Задачи T4.3–T4.4, T5.3–T5.4."""

from fastapi import APIRouter

router = APIRouter(tags=["social"])

# TODO(T4.3): PATCH/DELETE /reviews/{review_id}, GET/POST /reviews/{review_id}/comments
# TODO(T4.4): DELETE /comments/{comment_id}
# TODO(T5.3): POST /likes, DELETE /likes
# TODO(T5.4): GET /feed
# Контракт: docs/api.md, разделы 7–8.
