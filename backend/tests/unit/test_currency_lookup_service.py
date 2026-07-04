from app.schemas.currency import CurrencyDetectionResult
from app.providers.fakes import (
    FakeCurrencyDetectionProvider,
    FakeFailingTTSProvider,
    FakeTTSProvider,
    FakeVisionProvider,
)
from app.services.currency_lookup_service import CurrencyLookupService


def test_currency_lookup_uses_specialist_when_confident():
    service = CurrencyLookupService(
        vision=FakeVisionProvider(),
        tts=FakeTTSProvider(),
        currency_detector=FakeCurrencyDetectionProvider(),
    )

    response = service.handle(b"fake-image-bytes")

    assert response.found is True
    assert response.denomination == "20 EGP"
    assert response.spoken_text == "دي عشرين جنيه."
    assert response.audio_base64 != ""


def test_currency_lookup_speaks_hedged_arabic_for_unrecognized_denomination():
    class UnrecognizedDenominationProvider:
        def detect_currency(self, image_bytes: bytes):
            return CurrencyDetectionResult(denomination="999_egp", confidence=0.95)

    service = CurrencyLookupService(
        vision=FakeVisionProvider(),
        tts=FakeTTSProvider(),
        currency_detector=UnrecognizedDenominationProvider(),
    )

    response = service.handle(b"fake-image-bytes")

    assert response.found is True
    assert "999" not in response.spoken_text
    assert response.spoken_text  # hedged Arabic message, not a raw label


def test_currency_lookup_falls_back_to_vlm_when_detector_unconfident():
    class LowConfidenceCurrencyDetector:
        def detect_currency(self, image_bytes: bytes):
            return CurrencyDetectionResult(denomination="20 EGP", confidence=0.2)

    service = CurrencyLookupService(
        vision=FakeVisionProvider(),
        tts=FakeTTSProvider(),
        currency_detector=LowConfidenceCurrencyDetector(),
    )

    response = service.handle(b"fake-image-bytes")

    assert response.found is False
    assert response.denomination is None


def test_currency_lookup_falls_back_to_vlm_without_detector():
    service = CurrencyLookupService(
        vision=FakeVisionProvider(),
        tts=FakeTTSProvider(),
        currency_detector=None,
    )

    response = service.handle(b"fake-image-bytes")

    assert response.found is False
    assert response.denomination is None
    assert response.spoken_text  # VLM's fake summary still produces text


def test_currency_lookup_sets_fallback_flag_when_tts_unavailable():
    service = CurrencyLookupService(
        vision=FakeVisionProvider(),
        tts=FakeFailingTTSProvider(),
        currency_detector=FakeCurrencyDetectionProvider(),
    )

    response = service.handle(b"fake-image-bytes")

    assert response.tts_fallback_required is True
    assert response.audio_base64 == ""
    assert response.spoken_text  # text must still be present for the OS-voice fallback
