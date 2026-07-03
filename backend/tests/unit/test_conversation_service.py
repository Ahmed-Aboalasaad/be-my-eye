import base64

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
from app.services.conversation_service import ConversationService
from app.services.intent_router import IntentRouter
from app.services.session_store import InMemorySessionStore


def make_service() -> ConversationService:
    return ConversationService(
        asr=FakeASRProvider(),
        vision=FakeVisionProvider(),
        ocr=FakeOCRProvider(),
        llm=FakeLLMProvider(),
        tts=FakeTTSProvider(),
        grounding=FakeGroundingProvider(),
        session_store=InMemorySessionStore(),
        router=IntentRouter(),
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
    assert response.text  # the text answer must still be present
