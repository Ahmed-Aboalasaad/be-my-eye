from __future__ import annotations

from typing import Sequence

from app.providers.base import ASRProvider, GroundingProvider, LLMProvider, OCRProvider, TTSProvider, VisionProvider
from app.schemas.common import ConversationTurn, VisionTask


class FakeASRProvider(ASRProvider):
    def transcribe(self, audio_bytes: bytes) -> str:
        text = audio_bytes.decode("utf-8", errors="ignore").strip()
        return text or "What is in front of me?"


class FakeVisionProvider(VisionProvider):
    def analyze(
        self,
        image_bytes: bytes,
        question: str,
        history: Sequence[ConversationTurn],
        task: VisionTask = VisionTask.scene,
    ) -> str:
        _ = (image_bytes, question, history, task)
        return "a desk with a laptop and a mug"


class FakeGroundingProvider(GroundingProvider):
    def locate_object(self, image_bytes: bytes, object_query: str, history: Sequence[ConversationTurn]) -> str:
        _ = (image_bytes, object_query, history)
        return "on the kitchen counter"


class FakeOCRProvider(OCRProvider):
    def extract_text(self, image_bytes: bytes) -> str:
        _ = image_bytes
        return "sample printed text"


class FakeLLMProvider(LLMProvider):
    def generate_response(
        self,
        user_message: str,
        vision_summary: str | None,
        ocr_text: str | None,
        history: Sequence[ConversationTurn],
    ) -> str:
        _ = history
        if ocr_text:
            return f"I can read the text: {ocr_text}."
        if vision_summary:
            return f"You are looking at {vision_summary}."
        return f"You asked: {user_message}"


class FakeTTSProvider(TTSProvider):
    def synthesize_speech(self, text: str) -> bytes:
        return text.encode("utf-8")

