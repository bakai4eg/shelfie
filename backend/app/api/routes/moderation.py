"""Модерация и жалобы. Задачи T4.1–T4.2."""

from fastapi import APIRouter

router = APIRouter(prefix="/moderation", tags=["moderation"])

# TODO(T4.1): POST /reports, GET /me/reports (перенести в users/ или сюда — решить в PR)
# TODO(T4.2): GET /reports, POST /reports/{report_id}/resolve
#             POST /content/{target_type}/{target_id}/hide|delete
#             GET /cards, POST /cards/{item_id}/approve|reject
# Контракт: docs/api.md, разделы 9–10.
