import base64

import pytest

from app.providers.fakes import (
    FakeASRProvider,
    FakeGroundingProvider,
    FakeLLMProvider,
    FakeOCRProvider,
    FakeTTSProvider,
    FakeVisionProvider,
)
from app.schemas.common import VisionTask
from app.schemas.conversation import ConversationRequest
from app.services.conversation_service import ConversationError, ConversationService
from app.services.intent_router import IntentRouter
from app.services.session_store import InMemorySessionStore


class RaisingASRProvider:
    def transcribe(self, audio_bytes: bytes) -> str:
        raise RuntimeError("could not process file - is it a valid media file?")


class RaisingVisionProvider:
    def analyze(self, image_bytes, user_message, history, task=None):
        raise RuntimeError("cannot identify image file")


class RaisingOCRProvider:
    def extract_text(self, image_bytes):
        raise RuntimeError("cannot identify image file")


class RaisingGroundingProvider:
    def locate_object(self, image_bytes, query, history):
        raise RuntimeError("cannot identify image file")


class RaisingLLMProvider:
    def generate_response(self, user_message, vision_summary, ocr_text, history, grounding_result=None):
        raise RuntimeError("upstream LLM call failed")


def make_service(
    currency_detector=None,
    asr=None,
    vision=None,
    ocr=None,
    grounding=None,
    llm=None,
) -> ConversationService:
    return ConversationService(
        asr=asr or FakeASRProvider(),
        vision=vision or FakeVisionProvider(),
        ocr=ocr or FakeOCRProvider(),
        llm=llm or FakeLLMProvider(),
        tts=FakeTTSProvider(),
        grounding=grounding or FakeGroundingProvider(),
        session_store=InMemorySessionStore(),
        router=IntentRouter(),
        currency_detector=currency_detector,
    )


def test_conversation_service_returns_response_and_debug():
    service = make_service()
    request = ConversationRequest(
        session_id="session-1",
        image_base64=base64.b64encode(b"image-bytes").decode("ascii"),
        audio_base64=base64.b64encode(b"Read this page").decode("ascii"),
        debug=True,
    )

    response = service.handle(request)

    assert response.session_id == "session-1"
    assert response.text == "I can read the text: sample printed text."
    assert base64.b64decode(response.audio_base64).decode("utf-8") == "I can read the text: sample printed text."
    assert response.debug is not None
    assert response.debug.transcript == "Read this page"
    assert response.debug.selected_providers == ["vision", "ocr"]
    assert response.debug.vision_task == VisionTask.scene.value


def test_conversation_service_raises_conversation_error_when_asr_rejects_audio():
    service = make_service(asr=RaisingASRProvider())
    request = ConversationRequest(
        session_id="session-1",
        image_base64=base64.b64encode(b"image-bytes").decode("ascii"),
        audio_base64=base64.b64encode(b"not a real audio file").decode("ascii"),
    )

    with pytest.raises(ConversationError):
        service.handle(request)


def test_conversation_service_raises_conversation_error_when_vision_rejects_image():
    service = make_service(vision=RaisingVisionProvider())
    request = ConversationRequest(
        session_id="session-1",
        image_base64=base64.b64encode(b"not a real image file").decode("ascii"),
        audio_base64=base64.b64encode(b"What is in front of me?").decode("ascii"),
    )

    with pytest.raises(ConversationError):
        service.handle(request)


def test_conversation_service_raises_conversation_error_when_ocr_rejects_image():
    service = make_service(ocr=RaisingOCRProvider())
    request = ConversationRequest(
        session_id="session-1",
        image_base64=base64.b64encode(b"not a real image file").decode("ascii"),
        audio_base64=base64.b64encode(b"Read this page").decode("ascii"),
    )

    with pytest.raises(ConversationError):
        service.handle(request)


def test_conversation_service_raises_conversation_error_when_grounding_fails():
    service = make_service(grounding=RaisingGroundingProvider())
    request = ConversationRequest(
        session_id="session-1",
        image_base64=base64.b64encode(b"not a real image file").decode("ascii"),
        audio_base64=base64.b64encode(b"Where are my keys?").decode("ascii"),
    )

    with pytest.raises(ConversationError):
        service.handle(request)


def test_conversation_service_raises_conversation_error_when_llm_fails():
    service = make_service(llm=RaisingLLMProvider())
    request = ConversationRequest(
        session_id="session-1",
        image_base64=base64.b64encode(b"image-bytes").decode("ascii"),
        audio_base64=base64.b64encode(b"What is in front of me?").decode("ascii"),
    )

    with pytest.raises(ConversationError):
        service.handle(request)


def test_conversation_service_persists_history():
    service = make_service()
    request = ConversationRequest(
        session_id="session-1",
        image_base64=base64.b64encode(b"image-bytes").decode("ascii"),
        audio_base64=base64.b64encode(b"What is in front of me?").decode("ascii"),
    )

    service.handle(request)

    history = service.session_store.get_history("session-1")
    assert len(history) == 1
    assert history[0].user_text == "What is in front of me?"


def test_conversation_service_calls_grounding_when_query_present():
    service = make_service()
    request = ConversationRequest(
        session_id="session-1",
        image_base64=base64.b64encode(b"image-bytes").decode("ascii"),
        audio_base64=base64.b64encode(b"Where are my keys?").decode("ascii"),
        debug=True,
    )

    response = service.handle(request)

    assert response.debug.grounding_result == "on the kitchen counter"
    assert response.debug.selected_providers == ["vision", "grounding"]
    assert response.text == "It's on the kitchen counter."


def test_conversation_service_passes_grounding_result_to_llm():
    class SpyLLMProvider(FakeLLMProvider):
        def __init__(self) -> None:
            self.received_grounding_result: str | None = "not-called"

        def generate_response(self, user_message, vision_summary, ocr_text, history, grounding_result=None):
            self.received_grounding_result = grounding_result
            return super().generate_response(
                user_message, vision_summary, ocr_text, history, grounding_result=grounding_result
            )

    spy_llm = SpyLLMProvider()
    service = ConversationService(
        asr=FakeASRProvider(),
        vision=FakeVisionProvider(),
        ocr=FakeOCRProvider(),
        llm=spy_llm,
        tts=FakeTTSProvider(),
        grounding=FakeGroundingProvider(),
        session_store=InMemorySessionStore(),
        router=IntentRouter(),
    )
    request = ConversationRequest(
        session_id="session-1",
        image_base64=base64.b64encode(b"image-bytes").decode("ascii"),
        audio_base64=base64.b64encode(b"Where are my keys?").decode("ascii"),
    )

    service.handle(request)

    assert spy_llm.received_grounding_result == "on the kitchen counter"


def test_conversation_service_prefers_request_supplied_history():
    from app.schemas.common import ConversationTurn

    class SpyLLMProvider(FakeLLMProvider):
        def __init__(self) -> None:
            self.received_history: list[ConversationTurn] = []

        def generate_response(self, user_message, vision_summary, ocr_text, history, grounding_result=None):
            self.received_history = list(history)
            return super().generate_response(
                user_message, vision_summary, ocr_text, history, grounding_result=grounding_result
            )

    spy_llm = SpyLLMProvider()
    session_store = InMemorySessionStore()
    service = ConversationService(
        asr=FakeASRProvider(),
        vision=FakeVisionProvider(),
        ocr=FakeOCRProvider(),
        llm=spy_llm,
        tts=FakeTTSProvider(),
        grounding=FakeGroundingProvider(),
        session_store=session_store,
        router=IntentRouter(),
    )
    request_history = [ConversationTurn(user_text="What is this?", assistant_text="A red mug.")]
    request = ConversationRequest(
        session_id="session-without-store-entry",
        image_base64=base64.b64encode(b"image-bytes").decode("ascii"),
        audio_base64=base64.b64encode(b"What color is it now?").decode("ascii"),
        history=request_history,
    )
    assert session_store.get_history("session-without-store-entry") == []

    response = service.handle(request)

    assert response.session_id == "session-without-store-entry"
    assert spy_llm.received_history == request_history


def test_conversation_service_sets_fallback_flag_when_tts_unavailable():
    from app.providers.fakes import FakeFailingTTSProvider

    service = ConversationService(
        asr=FakeASRProvider(),
        vision=FakeVisionProvider(),
        ocr=FakeOCRProvider(),
        llm=FakeLLMProvider(),
        tts=FakeFailingTTSProvider(),
        grounding=FakeGroundingProvider(),
        session_store=InMemorySessionStore(),
        router=IntentRouter(),
    )
    request = ConversationRequest(
        session_id="session-1",
        image_base64=base64.b64encode(b"image-bytes").decode("ascii"),
        audio_base64=base64.b64encode(b"What is in front of me?").decode("ascii"),
    )

    response = service.handle(request)

    assert response.tts_fallback_required is True
    assert response.audio_base64 == ""


def test_conversation_service_sets_fallback_flag_when_tts_returns_empty_audio():
    from app.providers.fakes import FakeEmptyAudioTTSProvider

    service = ConversationService(
        asr=FakeASRProvider(),
        vision=FakeVisionProvider(),
        ocr=FakeOCRProvider(),
        llm=FakeLLMProvider(),
        tts=FakeEmptyAudioTTSProvider(),
        grounding=FakeGroundingProvider(),
        session_store=InMemorySessionStore(),
        router=IntentRouter(),
    )
    request = ConversationRequest(
        session_id="session-1",
        image_base64=base64.b64encode(b"image-bytes").decode("ascii"),
        audio_base64=base64.b64encode(b"What is in front of me?").decode("ascii"),
    )

    response = service.handle(request)

    assert response.tts_fallback_required is True
    assert response.audio_base64 == ""
    assert response.text  # the text answer must still be present


def test_conversation_service_uses_currency_detector_when_confident():
    from app.providers.fakes import FakeCurrencyDetectionProvider

    service = make_service(currency_detector=FakeCurrencyDetectionProvider())
    request = ConversationRequest(
        session_id="session-1",
        image_base64=base64.b64encode(b"image-bytes").decode("ascii"),
        audio_base64=base64.b64encode(b"How much money is this?").decode("ascii"),
        debug=True,
    )

    response = service.handle(request)

    assert response.debug.selected_providers == ["currency_detector"]
    assert "20 EGP" in response.debug.vision_summary


def test_conversation_service_falls_back_to_vlm_when_currency_detector_returns_none():
    class NoneReturningCurrencyDetector:
        def detect_currency(self, image_bytes: bytes):
            return None

    service = make_service(currency_detector=NoneReturningCurrencyDetector())
    request = ConversationRequest(
        session_id="session-1",
        image_base64=base64.b64encode(b"image-bytes").decode("ascii"),
        audio_base64=base64.b64encode(b"How much money is this?").decode("ascii"),
        debug=True,
    )

    response = service.handle(request)

    assert response.debug.selected_providers == ["vision"]


def test_conversation_service_falls_back_to_vlm_when_currency_detector_unconfident():
    from app.schemas.currency import CurrencyDetectionResult

    class LowConfidenceCurrencyDetector:
        def detect_currency(self, image_bytes: bytes):
            return CurrencyDetectionResult(denomination="10 EGP", confidence=0.2)

    service = make_service(currency_detector=LowConfidenceCurrencyDetector())
    request = ConversationRequest(
        session_id="session-1",
        image_base64=base64.b64encode(b"image-bytes").decode("ascii"),
        audio_base64=base64.b64encode(b"How much money is this?").decode("ascii"),
        debug=True,
    )

    response = service.handle(request)

    assert response.debug.selected_providers == ["vision"]


def test_conversation_service_ignores_currency_detector_for_non_currency_tasks():
    from app.providers.fakes import FakeCurrencyDetectionProvider

    service = make_service(currency_detector=FakeCurrencyDetectionProvider())
    request = ConversationRequest(
        session_id="session-1",
        image_base64=base64.b64encode(b"image-bytes").decode("ascii"),
        audio_base64=base64.b64encode(b"What is in front of me?").decode("ascii"),
        debug=True,
    )

    response = service.handle(request)

    assert response.debug.selected_providers == ["vision"]
