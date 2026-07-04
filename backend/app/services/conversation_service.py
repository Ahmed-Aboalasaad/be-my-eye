from __future__ import annotations

import base64
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

from app.providers.base import (
    ASRProvider,
    CurrencyDetectionProvider,
    GroundingProvider,
    LLMProvider,
    OCRProvider,
    TTSProvider,
    TTSUnavailableError,
    VisionProvider,
)
from app.schemas.common import ConversationDebug, ConversationResponse, ConversationTurn, VisionTask
from app.schemas.conversation import ConversationRequest
from app.schemas.currency import CurrencyDetectionResult
from app.services.intent_router import IntentRouter
from app.services.session_store import InMemorySessionStore


class ConversationError(ValueError):
    pass


T = TypeVar("T")


@dataclass
class ConversationService:
    asr: ASRProvider
    vision: VisionProvider
    ocr: OCRProvider
    llm: LLMProvider
    tts: TTSProvider
    grounding: GroundingProvider
    session_store: InMemorySessionStore
    router: IntentRouter
    currency_detector: CurrencyDetectionProvider | None = None

    CURRENCY_CONFIDENCE_THRESHOLD = 0.6

    def handle(self, request: ConversationRequest) -> ConversationResponse:
        audio_bytes = self._decode_base64(request.audio_base64, "audio_base64")
        image_bytes = self._decode_base64(request.image_base64, "image_base64")

        transcript = self._guarded("process the provided audio", lambda: self.asr.transcribe(audio_bytes))
        history = request.history or self.session_store.get_history(request.session_id)
        decision = self.router.route(transcript)

        currency_result: CurrencyDetectionResult | None = None
        if decision.vision_task == VisionTask.currency and self.currency_detector is not None:
            currency_result = self.currency_detector.detect_currency(image_bytes)

        used_currency_detector = (
            currency_result is not None and currency_result.confidence >= self.CURRENCY_CONFIDENCE_THRESHOLD
        )
        if used_currency_detector:
            vision_summary = (
                f"Detected currency: {currency_result.denomination} "
                f"(confidence {currency_result.confidence:.0%})"
            )
        else:
            vision_summary = self._guarded(
                "analyze the provided image",
                lambda: self.vision.analyze(image_bytes, transcript, history, task=decision.vision_task),
            )

        ocr_text = None
        if decision.use_ocr:
            ocr_text = self._guarded("read text from the provided image", lambda: self.ocr.extract_text(image_bytes))

        grounding_result = None
        if decision.grounding_query:
            grounding_result = self._guarded(
                "locate the requested object",
                lambda: self.grounding.locate_object(image_bytes, decision.grounding_query, history),
            )

        selected_providers = ["currency_detector"] if used_currency_detector else ["vision"]
        if decision.use_ocr:
            selected_providers.append("ocr")
        if grounding_result is not None:
            selected_providers.append("grounding")

        response_text = self._guarded(
            "generate a response",
            lambda: self.llm.generate_response(
                transcript, vision_summary, ocr_text, history, grounding_result=grounding_result
            ),
        )
        tts_fallback_required = False
        try:
            speech_bytes = self.tts.synthesize_speech(response_text)
            if not speech_bytes:
                # The provider returned successfully but produced no actual
                # audio (e.g. a valid-but-empty file from the TTS service) --
                # treat this the same as an outright failure so the client
                # falls back to speaking the text locally instead of trying
                # (and silently failing) to play empty audio.
                raise TTSUnavailableError("TTS provider returned empty audio")
        except TTSUnavailableError:
            speech_bytes = b""
            tts_fallback_required = True

        self.session_store.append_turn(
            request.session_id,
            ConversationTurn(user_text=transcript, assistant_text=response_text),
        )

        debug = None
        if request.debug:
            debug = ConversationDebug(
                transcript=transcript,
                selected_providers=selected_providers,
                vision_summary=vision_summary,
                ocr_text=ocr_text,
                vision_task=decision.vision_task.value,
                grounding_result=grounding_result,
            )

        return ConversationResponse(
            session_id=request.session_id,
            text=response_text,
            transcript=transcript,
            audio_base64=base64.b64encode(speech_bytes).decode("ascii"),
            tts_fallback_required=tts_fallback_required,
            debug=debug,
        )

    @staticmethod
    def _decode_base64(value: str, field_name: str) -> bytes:
        try:
            return base64.b64decode(value, validate=True)
        except Exception as exc:  # noqa: BLE001
            raise ConversationError(f"Invalid base64 payload for {field_name}") from exc

    @staticmethod
    def _guarded(description: str, call: Callable[[], T]) -> T:
        try:
            return call()
        except Exception as exc:  # noqa: BLE001 -- upstream provider rejected the input
            raise ConversationError(f"Could not {description}.") from exc
