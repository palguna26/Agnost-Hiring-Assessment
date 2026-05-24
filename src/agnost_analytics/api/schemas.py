from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Message(BaseModel):
    role: str
    content: str


class IngestPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    session_id: str
    user_id: str | None = None
    timestamp: str | None = None
    source: str = "agnost_sdk"
    messages: list[Message] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class IngestResponse(BaseModel):
    session_id: str
    status: str
    duplicate: bool = False

