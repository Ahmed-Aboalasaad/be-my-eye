from __future__ import annotations

import base64
from dataclasses import dataclass

from app.providers.base import CurrencyDetectionProvider, TTSProvider, TTSUnavailableError, VisionProvider
from app.schemas.common import VisionTask
from app.schemas.currency import CurrencyLookupResponse


@dataclass
class CurrencyLookupService:
    vision: VisionProvider
    tts: TTSProvider
    currency_detector: CurrencyDetectionProvider | None = None

    CURRENCY_CONFIDENCE_THRESHOLD = 0.6

    def handle(self, image_bytes: bytes) -> CurrencyLookupResponse:
        currency_result = self.currency_detector.detect_currency(image_bytes) if self.currency_detector else None

        if currency_result is not None and currency_result.confidence >= self.CURRENCY_CONFIDENCE_THRESHOLD:
            found = True
            denomination = currency_result.denomination
            confidence = currency_result.confidence
            spoken_text = f"This looks like {currency_result.denomination}."
        else:
            found = False
            denomination = None
            confidence = None
            spoken_text = self.vision.analyze(
                image_bytes,
                "What Egyptian currency denomination is shown in this image?",
                [],
                task=VisionTask.currency,
            )

        tts_fallback_required = False
        try:
            speech_bytes = self.tts.synthesize_speech(spoken_text)
        except TTSUnavailableError:
            speech_bytes = b""
            tts_fallback_required = True

        return CurrencyLookupResponse(
            found=found,
            denomination=denomination,
            confidence=confidence,
            spoken_text=spoken_text,
            audio_base64=base64.b64encode(speech_bytes).decode("ascii"),
            tts_fallback_required=tts_fallback_required,
        )
