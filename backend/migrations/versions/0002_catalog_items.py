"""Каталог книг, фильмов и сериалов (T2.1).

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "catalog_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column(
            "source", sa.String(length=32), server_default="local", nullable=False
        ),
        sa.Column("external_id", sa.String(length=64), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("original_title", sa.String(length=500), nullable=True),
        sa.Column(
            "title_normalized",
            sa.String(length=1000),
            server_default="",
            nullable=False,
        ),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("genres", sa.JSON(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("poster_path", sa.String(length=255), nullable=True),
        sa.Column("is_local", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "moderation_status",
            sa.String(length=16),
            server_default="approved",
            nullable=False,
        ),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column(
            "rating_avg", sa.Numeric(precision=4, scale=2), server_default="0", nullable=False
        ),
        sa.Column("ratings_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_catalog_items_created_by_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_catalog_items")),
        sa.UniqueConstraint(
            "source",
            "external_id",
            name=op.f("uq_catalog_items_source_external_id"),
        ),
    )
    op.create_index(op.f("ix_catalog_items_type"), "catalog_items", ["type"], unique=False)
    op.create_index(op.f("ix_catalog_items_year"), "catalog_items", ["year"], unique=False)
    op.create_index(
        op.f("ix_catalog_items_is_local"), "catalog_items", ["is_local"], unique=False
    )
    op.create_index(
        op.f("ix_catalog_items_title_normalized"),
        "catalog_items",
        ["title_normalized"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_catalog_items_title_normalized"), table_name="catalog_items")
    op.drop_index(op.f("ix_catalog_items_is_local"), table_name="catalog_items")
    op.drop_index(op.f("ix_catalog_items_year"), table_name="catalog_items")
    op.drop_index(op.f("ix_catalog_items_type"), table_name="catalog_items")
    op.drop_table("catalog_items")
