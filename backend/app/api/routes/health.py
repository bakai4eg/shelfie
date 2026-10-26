"""Служебные эндпоинты: health-check для docker-compose и мониторинга."""

from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import SessionDep

router = APIRouter(tags=["service"])


@router.get("/health")
async def health(session: SessionDep) -> dict[str, str]:
    db_status = "ok"
    try:
        await session.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 — health не должен падать из-за БД
        db_status = "unavailable"
    return {"status": "ok", "db": db_status}
