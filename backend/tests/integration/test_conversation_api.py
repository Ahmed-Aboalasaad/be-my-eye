import base64

from fastapi.testclient import TestClient

from app.main import create_app


def make_client(api_key: str | None = None) -> TestClient:
    import os

    # Explicit about BE_MY_EYE_API_KEY rather than relying on ambient state:
    # a real key can exist in a developer's local .env, which would silently
    # 401 every test below that doesn't expect auth to be required.
    if api_key is not None:
        os.environ["BE_MY_EYE_API_KEY"] = api_key
    else:
        os.environ.pop("BE_MY_EYE_API_KEY", None)
    return TestClient(create_app())


def test_health_endpoint():
    import os

    os.environ["USE_REAL_PROVIDERS"] = "false"
    response = make_client().get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_conversation_endpoint_returns_response():
    import os

    os.environ["USE_REAL_PROVIDERS"] = "false"
    payload = {
        "session_id": "session-1",
        "image_base64": base64.b64encode(b"image-bytes").decode("ascii"),
        "audio_base64": base64.b64encode(b"What is in front of me?").decode("ascii"),
        "debug": True,
    }

    response = make_client().post("/conversation", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == "session-1"
    assert body["text"] == "You are looking at a desk with a laptop and a mug."
    assert body["transcript"]
    assert body["debug"]["selected_providers"] == ["vision"]


def test_conversation_endpoint_uses_client_supplied_history_for_next_turn():
    import os

    os.environ["USE_REAL_PROVIDERS"] = "false"
    payload = {
        "session_id": "session-multi-turn",
        "image_base64": base64.b64encode(b"image-bytes").decode("ascii"),
        "audio_base64": base64.b64encode(b"What is in front of me?").decode("ascii"),
        "history": [{"user_text": "What color is it?", "assistant_text": "It is red."}],
    }

    response = make_client().post("/conversation", json=payload)

    assert response.status_code == 200
    assert response.json()["transcript"]


def test_conversation_endpoint_rejects_invalid_base64():
    import os

    os.environ["USE_REAL_PROVIDERS"] = "false"
    payload = {
        "session_id": "session-1",
        "image_base64": "not-base64",
        "audio_base64": "still-not-base64",
    }

    response = make_client().post("/conversation", json=payload)

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "invalid_request"


def test_conversation_endpoint_rejects_missing_api_key_when_configured():
    import os

    os.environ["USE_REAL_PROVIDERS"] = "false"
    payload = {
        "session_id": "session-1",
        "image_base64": base64.b64encode(b"image-bytes").decode("ascii"),
        "audio_base64": base64.b64encode(b"What is in front of me?").decode("ascii"),
    }

    response = make_client(api_key="test-secret-key").post("/conversation", json=payload)

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "unauthorized"


def test_conversation_endpoint_allows_correct_api_key_when_configured():
    import os

    os.environ["USE_REAL_PROVIDERS"] = "false"
    payload = {
        "session_id": "session-1",
        "image_base64": base64.b64encode(b"image-bytes").decode("ascii"),
        "audio_base64": base64.b64encode(b"What is in front of me?").decode("ascii"),
    }

    response = make_client(api_key="test-secret-key").post(
        "/conversation", json=payload, headers={"X-API-Key": "test-secret-key"}
    )

    assert response.status_code == 200
