from __future__ import annotations

from pydantic import BaseModel, Field


class CurrencyDetectionResult(BaseModel):
    denomination: str
    confidence: float = Field(ge=0.0, le=1.0)


class CurrencyLookupRequest(BaseModel):
    image_base64: str = Field(min_length=1)


class CurrencyLookupResponse(BaseModel):
    found: bool
    denomination: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    spoken_text: str = Field(min_length=1)
    audio_base64: str = ""
    tts_fallback_required: bool = False
