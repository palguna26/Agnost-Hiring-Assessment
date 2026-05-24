from __future__ import annotations

from typing import Any

from sqlalchemy import Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agnost_analytics.db.base import Base


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (UniqueConstraint("session_id", name="uq_conversations_session_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    timestamp: Mapped[str | None] = mapped_column(String(32), nullable=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    analysis_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id"), nullable=True, index=True)
    sentiment_label: Mapped[str | None] = mapped_column(String(16), nullable=True)
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    topic: Mapped["Topic | None"] = relationship(back_populates="conversations")


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    first_seen: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_seen: Mapped[str | None] = mapped_column(String(32), nullable=True)
    volume: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    negative_share: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    growth_24h: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    severity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    centroid: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)

    conversations: Mapped[list[Conversation]] = relationship(back_populates="topic")
    trend_snapshots: Mapped[list["TopicTrendSnapshot"]] = relationship(back_populates="topic")


class TopicTrendSnapshot(Base):
    __tablename__ = "topic_trend_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), nullable=False, index=True)
    bucket_start: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    conversation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    negative_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_sentiment: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    topic: Mapped[Topic] = relationship(back_populates="trend_snapshots")
