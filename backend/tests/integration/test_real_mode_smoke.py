from __future__ import annotations

import base64
import io
import os
import wave

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import create_app


pytestmark = pytest.mark.skipif(
    (
        os.getenv("RUN_REAL_GROQ_SMOKE_TESTS", "false").lower() not in {"1", "true", "yes", "on"}
        or not os.getenv("GROQ_MULTIMODAL_MODEL")
        or os.getenv("GROQ_MULTIMODAL_MODEL", "").startswith("your_")
    ),
    reason="Real Groq smoke tests are disabled or GROQ_MULTIMODAL_MODEL is not configured",
)


def _make_png_bytes() -> bytes:
    image = Image.new("RGB", (32, 32), color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _make_wav_bytes() -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(b"\x00\x00" * 1600)
    return buffer.getvalue()


def test_real_mode_conversation_smoke():
    client = TestClient(create_app())

    payload = {
        "session_id": "real-mode-smoke",
        "image_base64": base64.b64encode(_make_png_bytes()).decode("ascii"),
        "audio_base64": base64.b64encode(_make_wav_bytes()).decode("ascii"),
        "debug": True,
    }

    response = client.post("/conversation", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == "real-mode-smoke"
    assert isinstance(body["text"], str) and body["text"]
    assert isinstance(body["audio_base64"], str) and body["audio_base64"]
