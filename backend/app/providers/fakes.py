from __future__ import annotations

from typing import Sequence

from app.providers.base import ASRProvider, CurrencyDetectionProvider, GroundingProvider, LLMProvider, OCRProvider, ProductLookupProvider, TTSProvider, TTSUnavailableError, VisionProvider
from app.schemas.common import ConversationTurn, VisionTask
from app.schemas.currency import CurrencyDetectionResult
from app.schemas.product import ProductInfo


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
        grounding_result: str | None = None,
    ) -> str:
        _ = history
        if grounding_result:
            return f"It's {grounding_result}."
        if ocr_text:
            return f"I can read the text: {ocr_text}."
        if vision_summary:
            return f"You are looking at {vision_summary}."
        return f"You asked: {user_message}"


class FakeTTSProvider(TTSProvider):
    def synthesize_speech(self, text: str) -> bytes:
        return text.encode("utf-8")


class FakeFailingTTSProvider(TTSProvider):
    def synthesize_speech(self, text: str) -> bytes:
        raise TTSUnavailableError("fake TTS failure for testing")


class FakeProductLookupProvider(ProductLookupProvider):
    def lookup_by_barcode(self, barcode: str) -> ProductInfo | None:
        if barcode == "0000000000000":
            return None
        return ProductInfo(
            name="Sample Product",
            brand="Sample Brand",
            ingredients_text="water, sugar, salt",
            allergens=["milk"],
        )


class FakeCurrencyDetectionProvider(CurrencyDetectionProvider):
    def detect_currency(self, image_bytes: bytes) -> CurrencyDetectionResult | None:
        _ = image_bytes
        return CurrencyDetectionResult(denomination="20 EGP", confidence=0.92)

