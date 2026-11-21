"""Лента активности (ТЗ 4.5.4)."""

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import MODERATION_APPROVED
from app.core.media import avatar_url
from app.models.catalog import CatalogItem
from app.models.lists import UserList
from app.models.social import ActivityEvent, Follow, Review
from app.models.user import User
from app.schemas.catalog import CatalogItemRead
from app.schemas.common import Page
from app.schemas.social import FeedEvent, FeedItemRef, UserShort

REVIEW_CREATED = "review_created"
ITEM_FINISHED = "item_finished"
RATING_SET = "rating_set"
LIST_PUBLISHED = "list_published"


def record(
    db: AsyncSession,
    user_id: int,
    event_type: str,
    *,
    item_id: int | None = None,
    review_id: int | None = None,
    list_id: int | None = None,
    value: int | None = None,
) -> None:
    """Событие пишем в той же транзакции, что и действие: коммитит вызывающий."""
    db.add(
        ActivityEvent(
            user_id=user_id,
            event_type=event_type,
            item_id=item_id,
            review_id=review_id,
            list_id=list_id,
            value=value,
        )
    )


async def list_published_recorded(db: AsyncSession, list_id: int) -> bool:
    """Повторная публикация того же списка новым событием не считается."""
    found = await db.scalar(
        select(ActivityEvent.id).where(
            ActivityEvent.event_type == LIST_PUBLISHED, ActivityEvent.list_id == list_id
        )
    )
    return found is not None


async def feed(db: AsyncSession, viewer: User, page: int, size: int) -> Page[FeedEvent]:
    """События тех, на кого подписан viewer. Скрытое модератором и приватное не попадает."""
    following = select(Follow.following_id).where(Follow.follower_id == viewer.id)
    condition = and_(
        ActivityEvent.user_id.in_(following),
        or_(ActivityEvent.review_id.is_(None), Review.is_hidden.is_(False)),
        or_(
            ActivityEvent.item_id.is_(None),
            CatalogItem.moderation_status == MODERATION_APPROVED,
        ),
        or_(ActivityEvent.list_id.is_(None), UserList.is_public.is_(True)),
        User.is_blocked.is_(False),
    )
    joined = (
        select(ActivityEvent, User, CatalogItem, Review, UserList)
        .join(User, User.id == ActivityEvent.user_id)
        .outerjoin(CatalogItem, CatalogItem.id == ActivityEvent.item_id)
        .outerjoin(Review, Review.id == ActivityEvent.review_id)
        .outerjoin(UserList, UserList.id == ActivityEvent.list_id)
        .where(condition)
    )
    total = (
        await db.scalar(
            select(func.count()).select_from(joined.with_only_columns(ActivityEvent.id).subquery())
        )
        or 0
    )
    rows = (
        await db.execute(
            joined.order_by(ActivityEvent.created_at.desc(), ActivityEvent.id.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
    ).all()

    items = []
    for event, author, item, review, lst in rows:
        poster = CatalogItemRead.model_validate(item).poster_url if item else None
        items.append(
            FeedEvent(
                id=event.id,
                event_type=event.event_type,
                created_at=event.created_at,
                user=UserShort(login=author.login, avatar_url=avatar_url(author.avatar_path)),
                item=FeedItemRef(id=item.id, title=item.title, type=item.type, poster_url=poster)
                if item
                else None,
                review=FeedItemRef(id=review.id, title=review.title) if review else None,
                list=FeedItemRef(id=lst.id, title=lst.title) if lst else None,
                value=event.value,
            )
        )
    return Page[FeedEvent](items=items, total=total, page=page, size=size)
