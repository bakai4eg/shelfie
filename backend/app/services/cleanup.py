"""Каскадное удаление материалов и пользователей (ТЗ 4.6.3, 4.6.4).

Каскад выполняем явно, а не полагаемся на `ON DELETE CASCADE`: жалобы указывают
на объекты полиморфно (тип + id, без внешнего ключа), а тесты идут на SQLite,
где внешние ключи по умолчанию не проверяются.

Функции только готовят изменения в сессии и возвращают список файлов к удалению:
файлы стираем после успешного коммита, чтобы откат не оставил карточку без обложки.
"""

from decimal import Decimal

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.catalog import CatalogItem
from app.models.library import Rating, ShelfEntry
from app.models.lists import ListItem, UserList
from app.models.moderation import Report
from app.models.social import Follow, Review
from app.models.user import Session as AuthSession
from app.models.user import User


async def _drop_reports(db: AsyncSession, target_type: str, target_ids: list[int]) -> None:
    if target_ids:
        await db.execute(
            delete(Report).where(
                Report.target_type == target_type, Report.target_id.in_(target_ids)
            )
        )


async def delete_reviews(db: AsyncSession, review_ids: list[int]) -> None:
    """Рецензия уносит жалобы на себя. Комментарии и лайки подключатся к этой же точке."""
    if not review_ids:
        return
    await _drop_reports(db, "review", review_ids)
    await db.execute(delete(Review).where(Review.id.in_(review_ids)))


async def delete_card(db: AsyncSession, item: CatalogItem) -> list[str]:
    """Карточка уносит рецензии, оценки, полки, позиции списков и жалобы. Возвращает файлы."""
    review_ids = list(await db.scalars(select(Review.id).where(Review.item_id == item.id)))
    await delete_reviews(db, review_ids)
    await db.execute(delete(Rating).where(Rating.item_id == item.id))
    await db.execute(delete(ShelfEntry).where(ShelfEntry.item_id == item.id))
    await db.execute(delete(ListItem).where(ListItem.item_id == item.id))
    await _drop_reports(db, "card", [item.id])
    files = [item.poster_path] if item.is_local and item.poster_path else []
    await db.delete(item)
    return files


async def _recompute_ratings(db: AsyncSession, item_ids: list[int]) -> None:
    """Средний рейтинг карточек пересчитываем без коммита: он часть той же транзакции."""
    for item_id in set(item_ids):
        avg_value, count_value = (
            await db.execute(
                select(func.avg(Rating.value), func.count(Rating.id)).where(
                    Rating.item_id == item_id
                )
            )
        ).one()
        await db.execute(
            update(CatalogItem)
            .where(CatalogItem.id == item_id)
            .values(
                rating_avg=Decimal(str(round(float(avg_value or 0.0), 2))),
                ratings_count=int(count_value or 0),
            )
        )


async def delete_user(db: AsyncSession, user: User) -> list[str]:
    """Удаляет пользователя со всеми его данными. Возвращает файлы (аватар, обложки)."""
    files: list[str] = [user.avatar_path] if user.avatar_path else []

    # Локальные карточки автора вместе с обложками.
    own_cards = (
        await db.scalars(select(CatalogItem).where(CatalogItem.created_by == user.id))
    ).all()
    for card in own_cards:
        files += await delete_card(db, card)

    review_ids = list(await db.scalars(select(Review.id).where(Review.user_id == user.id)))
    await delete_reviews(db, review_ids)

    list_ids = list(await db.scalars(select(UserList.id).where(UserList.user_id == user.id)))
    if list_ids:
        await db.execute(delete(ListItem).where(ListItem.list_id.in_(list_ids)))
        await db.execute(delete(UserList).where(UserList.id.in_(list_ids)))

    rated_items = list(await db.scalars(select(Rating.item_id).where(Rating.user_id == user.id)))
    await db.execute(delete(Rating).where(Rating.user_id == user.id))
    await _recompute_ratings(db, rated_items)
    await db.execute(delete(ShelfEntry).where(ShelfEntry.user_id == user.id))
    await db.execute(
        delete(Follow).where((Follow.follower_id == user.id) | (Follow.following_id == user.id))
    )
    await db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
    # Жалобы пользователя и жалобы на его профиль.
    await db.execute(delete(Report).where(Report.reporter_id == user.id))
    await _drop_reports(db, "profile", [user.id])

    # Следы в чужих данных обнуляем: журнал и решения модератора остаются читаемыми.
    await db.execute(update(AuditLog).where(AuditLog.actor_id == user.id).values(actor_id=None))
    await db.execute(update(Report).where(Report.resolved_by == user.id).values(resolved_by=None))

    await db.delete(user)
    return files
