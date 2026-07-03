from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import ConversationTurn


class ConversationRequest(BaseModel):
    session_id: str = Field(min_length=1)
    image_base64: str = Field(min_length=1)
    audio_base64: str = Field(min_length=1)
    debug: bool = False
    history: list[ConversationTurn] = Field(default_factory=list)

