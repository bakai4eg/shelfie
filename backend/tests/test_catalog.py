"""Каталог: поиск, фильтры, видимость и сортировка (T2.1)."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.constants import (
    ITEM_BOOK,
    ITEM_MOVIE,
    MODERATION_APPROVED,
    MODERATION_HIDDEN,
    MODERATION_PENDING,
    ROLE_ADMIN,
    ROLE_MODERATOR,
    ROLE_USER,
    SOURCE_LOCAL,
    SOURCE_TMDB,
)
from app.db.base import Base
from app.db.session import json_serializer
from app.models.catalog import CatalogItem
from app.models.user import User
from app.schemas.catalog import CatalogItemRead
from app.services.catalog import catalog_filters, search_catalog


@pytest.fixture
async def db():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        json_serializer=json_serializer,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


async def add_user(db, login: str, role: str = ROLE_USER) -> User:
    user = User(
        login=login,
        email=f"{login}@example.com",
        password_hash="not-a-real-hash",
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def add_item(db, **overrides) -> CatalogItem:
    data = {
        "type": ITEM_BOOK,
        "source": SOURCE_LOCAL,
        "title": "Без названия",
        "genres": [],
        "is_local": False,
        "moderation_status": MODERATION_APPROVED,
    }
    data.update(overrides)
    item = CatalogItem(**data)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def test_search_by_title_and_original_title(db):
    await add_item(db, title="Манас")
    await add_item(
        db,
        type=ITEM_MOVIE,
        source=SOURCE_TMDB,
        title="Начало",
        original_title="Inception",
    )

    by_title, total = await search_catalog(db, user=None, query="Манас")
    assert total == 1
    assert by_title[0].title == "Манас"

    by_original, total = await search_catalog(db, user=None, query="inception")
    assert total == 1
    assert by_original[0].original_title == "Inception"


async def test_filters_type_year_country_and_local(db):
    await add_item(db, title="Манас", year=2010, country="Кыргызстан", is_local=True)
    await add_item(
        db, type=ITEM_MOVIE, source=SOURCE_TMDB, title="Inception", year=2010, country="США"
    )
    await add_item(
        db, type=ITEM_MOVIE, source=SOURCE_TMDB, title="Old film", year=1950, country="США"
    )

    items, total = await search_catalog(
        db, user=None, item_type=ITEM_MOVIE, year_from=2000, year_to=2020, country="США"
    )
    assert total == 1
    assert items[0].title == "Inception"

    local, total = await search_catalog(db, user=None, local_only=True)
    assert total == 1
    assert local[0].title == "Манас"


async def test_genre_filter_handles_cyrillic(db):
    await add_item(db, title="Драма", genres=["драма", "история"])
    await add_item(db, title="Комедия", genres=["комедия"])

    items, total = await search_catalog(db, user=None, genre="драма")
    assert total == 1
    assert items[0].title == "Драма"


async def test_visibility_of_pending_and_hidden(db):
    author = await add_user(db, "author")
    other = await add_user(db, "other")
    moderator = await add_user(db, "moder", ROLE_MODERATOR)
    admin = await add_user(db, "admin", ROLE_ADMIN)

    await add_item(db, title="Одобрена", moderation_status=MODERATION_APPROVED)
    await add_item(
        db,
        title="На проверке",
        moderation_status=MODERATION_PENDING,
        created_by=author.id,
    )
    await add_item(
        db,
        title="Скрыта",
        moderation_status=MODERATION_HIDDEN,
        created_by=author.id,
    )

    async def titles(user):
        items, _ = await search_catalog(db, user=user)
        return {item.title for item in items}

    assert await titles(None) == {"Одобрена"}
    assert await titles(other) == {"Одобрена"}
    assert await titles(author) == {"Одобрена", "На проверке"}
    assert await titles(moderator) == {"Одобрена", "На проверке"}
    assert await titles(admin) == {"Одобрена", "На проверке"}


async def test_filters_hide_genres_of_invisible_cards(db):
    author = await add_user(db, "author")
    await add_item(db, title="Одобрена", genres=["драма"])
    await add_item(
        db,
        title="Чужая",
        genres=["секрет"],
        moderation_status=MODERATION_PENDING,
        created_by=author.id,
    )
    await add_item(db, title="Скрыта", genres=["тайна"], moderation_status=MODERATION_HIDDEN)

    guest_filters = await catalog_filters(db, user=None)
    assert guest_filters["genres"] == ["драма"]

    author_filters = await catalog_filters(db, user=author)
    assert author_filters["genres"] == ["драма", "секрет"]


async def test_sorting(db):
    await add_item(db, title="Б", year=2000, rating_avg=5, ratings_count=2)
    await add_item(db, title="А", year=2010, rating_avg=9, ratings_count=1)
    await add_item(db, title="В", year=1990, rating_avg=9, ratings_count=5)

    by_year, _ = await search_catalog(db, user=None, sort="year_desc")
    assert [item.title for item in by_year] == ["А", "Б", "В"]

    by_rating, _ = await search_catalog(db, user=None, sort="rating_desc")
    assert [item.title for item in by_rating] == ["В", "А", "Б"]

    by_title, _ = await search_catalog(db, user=None, sort="title_asc")
    assert [item.title for item in by_title] == ["А", "Б", "В"]


async def test_pagination(db):
    for index in range(5):
        await add_item(db, title=f"Книга {index}")

    first, total = await search_catalog(db, user=None, page=1, size=2)
    second, _ = await search_catalog(db, user=None, page=2, size=2)
    assert total == 5
    assert len(first) == 2
    assert len(second) == 2
    assert {item.id for item in first}.isdisjoint({item.id for item in second})


def test_poster_url_is_built_from_path():
    now = datetime.now(UTC)
    local = CatalogItem(
        id=1,
        type=ITEM_BOOK,
        source=SOURCE_LOCAL,
        title="Книга",
        genres=[],
        poster_path="posters/cover.jpg",
        is_local=True,
        moderation_status=MODERATION_APPROVED,
        rating_avg=0,
        ratings_count=0,
        created_at=now,
    )
    remote = CatalogItem(
        id=2,
        type=ITEM_MOVIE,
        source=SOURCE_TMDB,
        title="Фильм",
        genres=[],
        poster_path="https://image.tmdb.org/poster.jpg",
        is_local=False,
        moderation_status=MODERATION_APPROVED,
        rating_avg=0,
        ratings_count=0,
        created_at=now,
    )

    assert CatalogItemRead.model_validate(local).poster_url == "/media/posters/cover.jpg"
    assert CatalogItemRead.model_validate(remote).poster_url == "https://image.tmdb.org/poster.jpg"


def test_catalog_endpoint_returns_empty_page(client):
    response = client.get("/api/catalog")
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "page": 1, "size": 20}


def test_catalog_rejects_unknown_type_and_big_page(client):
    assert client.get("/api/catalog", params={"type": "music"}).status_code == 422
    assert client.get("/api/catalog", params={"size": 500}).status_code == 422


def test_filters_endpoint_shape(client):
    response = client.get("/api/catalog/filters")
    assert response.status_code == 200
    body = response.json()
    assert body["types"] == []
    assert body["genres"] == []
    assert body["year_min"] is None
