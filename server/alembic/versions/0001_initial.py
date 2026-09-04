"""initial schema: users, refresh_tokens, articles, tags, article_tags, annotations, jobs

Revision ID: 0001
Revises:
Create Date: 2026-09-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql as pg

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("username", sa.String(length=32), nullable=False),
        sa.Column("password_hash", sa.String(length=128), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("settings", pg.JSONB(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_unique_constraint("uq_users_username", "users", ["username"])

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_refresh_tokens_user_id_users"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("idx_refresh_tokens_user_id", "refresh_tokens", ["user_id"])

    op.create_table(
        "articles",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_articles_user_id_users"),
            nullable=False,
        ),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("url_hash", sa.String(length=64), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("author", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lang", sa.String(length=16), nullable=True),
        sa.Column("content_md", sa.Text(), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("word_count", sa.Integer(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("snapshot_path", sa.Text(), nullable=True),
        sa.Column("search_tsv", pg.TSVECTOR(), nullable=True),
        sa.Column("embedding", Vector(512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_unique_constraint("uq_articles_user_url_hash", "articles", ["user_id", "url_hash"])
    op.create_index(
        "idx_articles_user_created", "articles", ["user_id", sa.text("created_at DESC")]
    )
    op.create_index("idx_articles_tsv", "articles", ["search_tsv"], postgresql_using="gin")
    op.create_index(
        "idx_articles_vec",
        "articles",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_index(
        "idx_articles_title_trgm",
        "articles",
        ["title"],
        postgresql_using="gin",
        postgresql_ops={"title": "gin_trgm_ops"},
    )
    op.create_index("idx_articles_domain", "articles", ["user_id", "domain"])

    op.create_table(
        "tags",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_tags_user_id_users"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=64), nullable=False),
    )
    op.create_unique_constraint("uq_tags_user_id_name", "tags", ["user_id", "name"])

    op.create_table(
        "article_tags",
        sa.Column(
            "article_id",
            sa.BigInteger(),
            sa.ForeignKey(
                "articles.id", ondelete="CASCADE", name="fk_article_tags_article_id_articles"
            ),
            primary_key=True,
        ),
        sa.Column(
            "tag_id",
            sa.BigInteger(),
            sa.ForeignKey("tags.id", ondelete="CASCADE", name="fk_article_tags_tag_id_tags"),
            primary_key=True,
        ),
    )
    op.create_index("idx_article_tags_tag", "article_tags", ["tag_id"])

    op.create_table(
        "annotations",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "article_id",
            sa.BigInteger(),
            sa.ForeignKey(
                "articles.id", ondelete="CASCADE", name="fk_annotations_article_id_articles"
            ),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_annotations_user_id_users"),
            nullable=False,
        ),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("quote_text", sa.Text(), nullable=True),
        sa.Column("anchor", pg.JSONB(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("ai_result", sa.Text(), nullable=True),
        sa.Column("color", sa.String(length=8), server_default="'#ffd54f'"),
        sa.Column("status", sa.String(length=16), server_default="'done'"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("idx_annotations_article", "annotations", ["article_id", "created_at"])

    op.create_table(
        "jobs",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("article_id", sa.BigInteger(), nullable=True),
        sa.Column("type", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="queued"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("payload", pg.JSONB(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "idx_jobs_claim",
        "jobs",
        ["priority", "id"],
        postgresql_where=sa.text("status = 'queued'"),
    )


def downgrade() -> None:
    op.drop_table("jobs")
    op.drop_table("annotations")
    op.drop_table("article_tags")
    op.drop_table("tags")
    op.drop_table("articles")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
