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

    # Egyptian pound denominations, keyed by the numeric value extracted from
    # Roboflow's raw class label (whose exact format -- "20_egp", "20", etc.
    # -- is unconfirmed, see RoboflowCurrencyProvider's docstring). Speaking
    # the raw label directly ("This looks like 20_egp.") through an Egyptian
    # Arabic TTS voice would be an English sentence with an underscore token
    # in it -- this maps to a real Arabic phrase instead.
    DENOMINATION_PHRASES_AR = {
        "5": "خمسة جنيه",
        "10": "عشرة جنيه",
        "20": "عشرين جنيه",
        "50": "خمسين جنيه",
        "100": "مية جنيه",
        "200": "ميتين جنيه",
    }

    def _phrase_for_denomination(self, raw_label: str) -> str:
        digits = "".join(character for character in raw_label if character.isdigit())
        phrase = self.DENOMINATION_PHRASES_AR.get(digits)
        if phrase:
            return f"دي {phrase}."
        return "شكل عليها فئة مش متأكد منها، جرب تقرب الورقة أكتر."

    def handle(self, image_bytes: bytes) -> CurrencyLookupResponse:
        currency_result = self.currency_detector.detect_currency(image_bytes) if self.currency_detector else None

        if currency_result is not None and currency_result.confidence >= self.CURRENCY_CONFIDENCE_THRESHOLD:
            found = True
            denomination = currency_result.denomination
            confidence = currency_result.confidence
            spoken_text = self._phrase_for_denomination(currency_result.denomination)
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
