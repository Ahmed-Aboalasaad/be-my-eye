from __future__ import annotations

import argparse
import base64
import os
import sys
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from groq import Groq


def _bootstrap_imports() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a live Groq smoke test against the backend.")
    parser.add_argument(
        "--image",
        default=str(Path(__file__).resolve().parents[2] / "playground" / "test.jpg"),
        help="Path to the image file to send.",
    )
    parser.add_argument(
        "--question",
        default="ما الموجود أمامي؟",
        help="Arabic question to synthesize into test audio.",
    )
    return parser.parse_args()


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    _bootstrap_imports()

    from app.main import create_app

    args = _parse_args()
    image_path = Path(args.image)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is missing.")

    multimodal_model = os.getenv("GROQ_MULTIMODAL_MODEL")
    if not multimodal_model:
        raise RuntimeError("GROQ_MULTIMODAL_MODEL is missing.")

    client = Groq(api_key=api_key)
    image_bytes = image_path.read_bytes()

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
        temp_audio_path = Path(temp_audio.name)

    tts_response = client.audio.speech.create(
        model=os.getenv("GROQ_TTS_MODEL", "canopylabs/orpheus-arabic-saudi"),
        voice=os.getenv("GROQ_TTS_VOICE", "abdullah"),
        input=args.question,
        response_format="wav",
    )
    tts_response.write_to_file(str(temp_audio_path))

    with temp_audio_path.open("rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            file=audio_file,
            model=os.getenv("GROQ_ASR_MODEL", "whisper-large-v3"),
            language=os.getenv("GROQ_ASR_LANGUAGE", "ar"),
            response_format="text",
        )

    transcribed_text = transcription if isinstance(transcription, str) else transcription.text
    print(f"ASR transcription: {transcribed_text!r}")

    app = create_app()
    response = TestClient(app).post(
        "/conversation",
        json={
            "session_id": "live-image-smoke",
            "image_base64": base64.b64encode(image_bytes).decode("ascii"),
            "audio_base64": base64.b64encode(temp_audio_path.read_bytes()).decode("ascii"),
            "debug": True,
        },
    )

    print(f"HTTP status: {response.status_code}")
    print("Response JSON:")
    print(response.json())

    temp_audio_path.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
