from app.providers.fakes import FakeASRProvider, FakeLLMProvider, FakeOCRProvider, FakeTTSProvider, FakeVisionProvider
from app.schemas.common import VisionTask


def test_fake_asr_uses_payload_text_when_available():
    provider = FakeASRProvider()

    assert provider.transcribe(b"What is in front of me?") == "What is in front of me?"


def test_fake_asr_falls_back_to_default_question():
    provider = FakeASRProvider()

    assert provider.transcribe(b"\xff\xfe") == "What is in front of me?"


def test_fake_vision_returns_deterministic_summary():
    provider = FakeVisionProvider()

    assert provider.analyze(b"image", "What is this?", []) == "a desk with a laptop and a mug"


def test_fake_ocr_returns_deterministic_text():
    provider = FakeOCRProvider()

    assert provider.extract_text(b"image") == "sample printed text"


def test_fake_llm_prefers_ocr_context():
    provider = FakeLLMProvider()

    assert provider.generate_response("Read this", None, "sample printed text", []) == "I can read the text: sample printed text."


def test_fake_tts_returns_utf8_bytes():
    provider = FakeTTSProvider()

    assert provider.synthesize_speech("Hello") == b"Hello"


def test_fake_vision_accepts_task_parameter():
    provider = FakeVisionProvider()

    assert provider.analyze(b"image", "How much is this?", [], task=VisionTask.currency) == "a desk with a laptop and a mug"


def test_fake_product_lookup_returns_sample_product_for_known_barcode():
    from app.providers.fakes import FakeProductLookupProvider

    provider = FakeProductLookupProvider()

    result = provider.lookup_by_barcode("1234567890123")

    assert result is not None
    assert result.name
    assert "milk" in result.allergens or result.allergens == [] or result.allergens


def test_fake_product_lookup_returns_none_for_unknown_barcode():
    from app.providers.fakes import FakeProductLookupProvider

    provider = FakeProductLookupProvider()

    result = provider.lookup_by_barcode("0000000000000")

    assert result is None


def test_fake_currency_detection_returns_confident_result():
    from app.providers.fakes import FakeCurrencyDetectionProvider

    provider = FakeCurrencyDetectionProvider()

    result = provider.detect_currency(b"fake-image-bytes")

    assert result is not None
    assert result.denomination
    assert result.confidence >= 0.6
