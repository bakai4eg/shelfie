"""lists and list_items

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-07 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "lists",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("is_public", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("theme", sa.String(length=16), server_default="classic", nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_lists_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lists")),
    )
    op.create_index("ix_lists_user_id", "lists", ["user_id"])
    op.create_table(
        "list_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("list_id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["list_id"], ["lists.id"], name=op.f("fk_list_items_list_id_lists"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_id"], ["catalog_items.id"], name=op.f("fk_list_items_item_id_catalog_items"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_list_items")),
        sa.UniqueConstraint("list_id", "item_id", name="uq_list_items_list_item"),
    )
    op.create_index("ix_list_items_list_id", "list_items", ["list_id"])
    op.create_index("ix_list_items_item_id", "list_items", ["item_id"])


def downgrade() -> None:
    op.drop_table("list_items")
    op.drop_table("lists")
