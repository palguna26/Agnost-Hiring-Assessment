"""create core tables

Revision ID: 0001_create_core_tables
Revises: 
Create Date: 2026-05-24 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_create_core_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "topics",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("first_seen", sa.String(length=32), nullable=True),
        sa.Column("last_seen", sa.String(length=32), nullable=True),
        sa.Column("volume", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("negative_share", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("growth_24h", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("severity", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("centroid", sa.JSON(), nullable=True),
    )

    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("timestamp", sa.String(length=32), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("analysis_status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("topic_id", sa.Integer(), sa.ForeignKey("topics.id"), nullable=True),
        sa.Column("sentiment_label", sa.String(length=16), nullable=True),
        sa.Column("sentiment_score", sa.Float(), nullable=True),
        sa.UniqueConstraint("session_id", name="uq_conversations_session_id"),
    )
    op.create_index("ix_conversations_session_id", "conversations", ["session_id"])
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])
    op.create_index("ix_conversations_topic_id", "conversations", ["topic_id"])

    op.create_table(
        "topic_trend_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("topic_id", sa.Integer(), sa.ForeignKey("topics.id"), nullable=False),
        sa.Column("bucket_start", sa.String(length=32), nullable=False),
        sa.Column("conversation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("negative_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_sentiment", sa.Float(), nullable=False, server_default="0.0"),
    )
    op.create_index("ix_topic_trend_snapshots_topic_id", "topic_trend_snapshots", ["topic_id"])
    op.create_index("ix_topic_trend_snapshots_bucket_start", "topic_trend_snapshots", ["bucket_start"])


def downgrade() -> None:
    op.drop_index("ix_topic_trend_snapshots_bucket_start", table_name="topic_trend_snapshots")
    op.drop_index("ix_topic_trend_snapshots_topic_id", table_name="topic_trend_snapshots")
    op.drop_table("topic_trend_snapshots")

    op.drop_index("ix_conversations_topic_id", table_name="conversations")
    op.drop_index("ix_conversations_user_id", table_name="conversations")
    op.drop_index("ix_conversations_session_id", table_name="conversations")
    op.drop_table("conversations")

    op.drop_table("topics")
