from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from app.schemas.common import ConversationTurn, VisionTask
from app.schemas.currency import CurrencyDetectionResult
from app.schemas.product import ProductInfo


class TTSUnavailableError(Exception):
    """Raised by a TTSProvider when speech synthesis could not be completed."""


class ASRProvider(ABC):
    @abstractmethod
    def transcribe(self, audio_bytes: bytes) -> str:
        raise NotImplementedError


class VisionProvider(ABC):
    @abstractmethod
    def analyze(
        self,
        image_bytes: bytes,
        question: str,
        history: Sequence[ConversationTurn],
        task: VisionTask = VisionTask.scene,
    ) -> str:
        raise NotImplementedError


class GroundingProvider(ABC):
    @abstractmethod
    def locate_object(self, image_bytes: bytes, object_query: str, history: Sequence[ConversationTurn]) -> str:
        raise NotImplementedError


class OCRProvider(ABC):
    @abstractmethod
    def extract_text(self, image_bytes: bytes) -> str:
        raise NotImplementedError


class LLMProvider(ABC):
    @abstractmethod
    def generate_response(
        self,
        user_message: str,
        vision_summary: str | None,
        ocr_text: str | None,
        history: Sequence[ConversationTurn],
        grounding_result: str | None = None,
    ) -> str:
        raise NotImplementedError


class TTSProvider(ABC):
    @abstractmethod
    def synthesize_speech(self, text: str) -> bytes:
        raise NotImplementedError


class ProductLookupProvider(ABC):
    @abstractmethod
    def lookup_by_barcode(self, barcode: str) -> ProductInfo | None:
        raise NotImplementedError


class CurrencyDetectionProvider(ABC):
    @abstractmethod
    def detect_currency(self, image_bytes: bytes) -> CurrencyDetectionResult | None:
        raise NotImplementedError
