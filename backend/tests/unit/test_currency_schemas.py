from app.schemas.currency import CurrencyLookupRequest, CurrencyLookupResponse


def test_currency_lookup_request_accepts_image():
    request = CurrencyLookupRequest(image_base64="aW1hZ2U=")

    assert request.image_base64 == "aW1hZ2U="


def test_currency_lookup_response_defaults():
    response = CurrencyLookupResponse(found=False, spoken_text="Not sure.")

    assert response.found is False
    assert response.denomination is None
    assert response.confidence is None
    assert response.audio_base64 == ""
    assert response.tts_fallback_required is False


def test_currency_lookup_response_with_detection():
    response = CurrencyLookupResponse(
        found=True,
        denomination="20 EGP",
        confidence=0.92,
        spoken_text="This looks like 20 EGP.",
        audio_base64="d2F2",
    )

    assert response.denomination == "20 EGP"
    assert response.confidence == 0.92
