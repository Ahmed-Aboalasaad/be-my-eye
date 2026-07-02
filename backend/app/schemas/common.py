from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class VisionTask(str, Enum):
    scene = "scene"
    currency = "currency"
    color = "color"
    product = "product"


class ConversationTurn(BaseModel):
    user_text: str = Field(min_length=1)
    assistant_text: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConversationDebug(BaseModel):
    transcript: str
    selected_providers: list[str]
    vision_summary: str | None = None
    ocr_text: str | None = None


class ConversationResponse(BaseModel):
    session_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    audio_base64: str = Field(min_length=1)
    debug: ConversationDebug | None = None


class ErrorResponse(BaseModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)

