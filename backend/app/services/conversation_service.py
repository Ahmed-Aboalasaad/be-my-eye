from __future__ import annotations

import base64
from dataclasses import dataclass

from app.providers.base import ASRProvider, GroundingProvider, LLMProvider, OCRProvider, TTSProvider, VisionProvider
from app.schemas.common import ConversationDebug, ConversationResponse, ConversationTurn
from app.schemas.conversation import ConversationRequest
from app.services.intent_router import IntentRouter
from app.services.session_store import InMemorySessionStore


class ConversationError(ValueError):
    pass


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

    def handle(self, request: ConversationRequest) -> ConversationResponse:
        audio_bytes = self._decode_base64(request.audio_base64, "audio_base64")
        image_bytes = self._decode_base64(request.image_base64, "image_base64")

        transcript = self.asr.transcribe(audio_bytes)
        history = request.history or self.session_store.get_history(request.session_id)
        decision = self.router.route(transcript)

        vision_summary = self.vision.analyze(image_bytes, transcript, history, task=decision.vision_task)

        ocr_text = None
        if decision.use_ocr:
            ocr_text = self.ocr.extract_text(image_bytes)

        grounding_result = None
        if decision.grounding_query:
            grounding_result = self.grounding.locate_object(image_bytes, decision.grounding_query, history)

        selected_providers = ["vision"]
        if decision.use_ocr:
            selected_providers.append("ocr")
        if grounding_result is not None:
            selected_providers.append("grounding")

        response_text = self.llm.generate_response(transcript, vision_summary, ocr_text, history)
        speech_bytes = self.tts.synthesize_speech(response_text)

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
            audio_base64=base64.b64encode(speech_bytes).decode("ascii"),
            debug=debug,
        )

    @staticmethod
    def _decode_base64(value: str, field_name: str) -> bytes:
        try:
            return base64.b64decode(value, validate=True)
        except Exception as exc:  # noqa: BLE001
            raise ConversationError(f"Invalid base64 payload for {field_name}") from exc
