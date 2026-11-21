"""comments, likes, activity_events

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-16 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _now(name: str) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "comments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("review_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("body", sa.String(length=1000), nullable=False),
        sa.Column("is_hidden", sa.Boolean(), server_default=sa.false(), nullable=False),
        _now("created_at"),
        _now("updated_at"),
        sa.ForeignKeyConstraint(["review_id"], ["reviews.id"], name=op.f("fk_comments_review_id_reviews"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_comments_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_comments")),
    )
    op.create_index("ix_comments_review_id", "comments", ["review_id"])
    op.create_index("ix_comments_user_id", "comments", ["user_id"])

    op.create_table(
        "likes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("target_type", sa.String(length=16), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        _now("created_at"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_likes_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_likes")),
        sa.UniqueConstraint("user_id", "target_type", "target_id", name="uq_likes_user_target"),
    )
    op.create_index("ix_likes_target", "likes", ["target_type", "target_id"])

    op.create_table(
        "activity_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=24), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=True),
        sa.Column("review_id", sa.Integer(), nullable=True),
        sa.Column("list_id", sa.Integer(), nullable=True),
        sa.Column("value", sa.Integer(), nullable=True),
        _now("created_at"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_activity_events_user_id_users"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_id"], ["catalog_items.id"], name=op.f("fk_activity_events_item_id_catalog_items"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["review_id"], ["reviews.id"], name=op.f("fk_activity_events_review_id_reviews"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["list_id"], ["lists.id"], name=op.f("fk_activity_events_list_id_lists"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_activity_events")),
    )
    op.create_index("ix_activity_events_user_id", "activity_events", ["user_id"])
    op.create_index("ix_activity_events_created_at", "activity_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("activity_events")
    op.drop_table("likes")
    op.drop_table("comments")
