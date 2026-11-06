"""Локальные карточки сообщества (T2.3, ТЗ 4.3.3).

Карточку создаёт авторизованный пользователь, она сразу уходит на проверку
(`pending`) и видна только автору и модераторам. Подтверждение — в T4.2.
"""

import json
import re
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status

from app.api.deps import CurrentUser, SessionDep
from app.core.config import settings
from app.schemas.catalog import CatalogType, LocalCardRead
from app.schemas.common import Page
from app.services.catalog import (
    create_local_card as create_local_card_service,
)
from app.services.catalog import (
    find_local_duplicates,
    list_my_local_cards,
)
from app.services.catalog import (
    update_local_card as update_local_card_service,
)

router = APIRouter(prefix="/cards", tags=["local-cards"])

GENRE_SPLIT = re.compile(r"[,;]")
MAX_GENRES = 20
GENRE_MAX_LENGTH = 100


def _parse_genres(raw: str | None) -> list[str]:
    """Принимает `драма, история` или JSON-массив — так удобнее и форме, и API."""
    if raw is None or not raw.strip():
        return []

    value = raw.strip()
    parsed: object = None
    if value.startswith("["):
        try:
            parsed = json.loads(value)
        except ValueError:
            parsed = None

    items = parsed if isinstance(parsed, list) else GENRE_SPLIT.split(value)
    genres: list[str] = []
    for item in items:
        genre = str(item).strip()
        if not genre or genre in genres:
            continue
        if len(genre) > GENRE_MAX_LENGTH:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                f"Жанр длиннее {GENRE_MAX_LENGTH} символов",
            )
        genres.append(genre)

    if len(genres) > MAX_GENRES:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Не больше {MAX_GENRES} жанров",
        )
    return genres


def _clean_title(value: str) -> str:
    title = value.strip()
    if not title:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Название не может быть пустым",
        )
    return title


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


async def _read_poster(file: UploadFile | None) -> tuple[bytes, str] | None:
    if file is None or not file.filename:
        return None
    limit = settings.max_upload_size_mb * 1024 * 1024
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Файл больше {settings.max_upload_size_mb} МБ",
        )
    return data, file.content_type or ""


@router.post(
    "/local",
    response_model=LocalCardRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать локальную карточку",
)
async def create_local_card(
    db: SessionDep,
    user: CurrentUser,
    item_type: Annotated[CatalogType, Form(alias="type")],
    title: Annotated[str, Form(max_length=500)],
    original_title: Annotated[str | None, Form(max_length=500)] = None,
    year: Annotated[int | None, Form(ge=0, le=3000)] = None,
    country: Annotated[str | None, Form(max_length=100)] = None,
    genres: Annotated[str | None, Form()] = None,
    description: Annotated[str | None, Form()] = None,
    is_local: Annotated[bool, Form()] = True,
    poster: Annotated[UploadFile | None, File()] = None,
) -> LocalCardRead:
    item = await create_local_card_service(
        db,
        user,
        item_type=item_type,
        title=_clean_title(title),
        original_title=_clean_optional(original_title),
        year=year,
        country=_clean_optional(country),
        genres=_parse_genres(genres),
        description=_clean_optional(description),
        is_local=is_local,
        poster=await _read_poster(poster),
    )
    return LocalCardRead.model_validate(item)


@router.get(
    "/local/mine",
    response_model=Page[LocalCardRead],
    summary="Мои локальные карточки",
)
async def get_my_local_cards(
    db: SessionDep,
    user: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[LocalCardRead]:
    items, total = await list_my_local_cards(db, user, page=page, size=size)
    return Page[LocalCardRead](
        items=[LocalCardRead.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
    )


@router.get(
    "/local/duplicates",
    response_model=list[LocalCardRead],
    summary="Похожие карточки перед созданием",
)
async def get_local_duplicates(
    db: SessionDep,
    user: CurrentUser,
    title: Annotated[str, Query(min_length=1, max_length=200)],
    year: Annotated[int | None, Query(ge=0, le=3000)] = None,
) -> list[LocalCardRead]:
    items = await find_local_duplicates(db, user, title=title, year=year)
    return [LocalCardRead.model_validate(item) for item in items]


@router.patch(
    "/local/{item_id}",
    response_model=LocalCardRead,
    summary="Исправить локальную карточку на проверке",
)
async def patch_local_card(
    item_id: int,
    db: SessionDep,
    user: CurrentUser,
    item_type: Annotated[CatalogType | None, Form(alias="type")] = None,
    title: Annotated[str | None, Form(max_length=500)] = None,
    original_title: Annotated[str | None, Form(max_length=500)] = None,
    year: Annotated[int | None, Form(ge=0, le=3000)] = None,
    country: Annotated[str | None, Form(max_length=100)] = None,
    genres: Annotated[str | None, Form()] = None,
    description: Annotated[str | None, Form()] = None,
    is_local: Annotated[bool | None, Form()] = None,
    poster: Annotated[UploadFile | None, File()] = None,
    remove_poster: Annotated[bool, Form()] = False,
) -> LocalCardRead:
    payload: dict[str, object] = {}
    if item_type is not None:
        payload["type"] = item_type
    if title is not None:
        payload["title"] = _clean_title(title)
    if original_title is not None:
        payload["original_title"] = _clean_optional(original_title)
    if year is not None:
        payload["year"] = year
    if country is not None:
        payload["country"] = _clean_optional(country)
    if genres is not None:
        payload["genres"] = _parse_genres(genres)
    if description is not None:
        payload["description"] = _clean_optional(description)
    if is_local is not None:
        payload["is_local"] = is_local

    item = await update_local_card_service(
        db,
        user,
        item_id,
        payload=payload,
        poster=await _read_poster(poster),
        remove_poster=remove_poster,
    )
    return LocalCardRead.model_validate(item)
