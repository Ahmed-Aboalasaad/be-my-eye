import base64

from fastapi.testclient import TestClient

from app.main import create_app


def make_client() -> TestClient:
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
    assert body["debug"]["selected_providers"] == ["vision"]


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
