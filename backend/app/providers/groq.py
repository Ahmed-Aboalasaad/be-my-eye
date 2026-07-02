from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from io import BytesIO
from typing import Sequence

from PIL import Image

from app.core.prompts import PromptConfig, get_prompt_config
from app.providers.base import ASRProvider, GroundingProvider, LLMProvider, OCRProvider, TTSProvider, VisionProvider
from app.schemas.common import ConversationTurn, VisionTask


def _data_url(image_bytes: bytes) -> str:
    import base64

    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:image/png;base64,{encoded}"


@lru_cache(maxsize=1)
def _load_groq_client() -> object:
    from groq import Groq

    from app.core.config import get_settings

    settings = get_settings()
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is required when real providers are enabled.")
    return Groq(api_key=settings.groq_api_key)


def _client_chat_content(client: object, model: str, prompt: str, image_bytes: bytes | None) -> str:
    if image_bytes is None:
        messages = [{"role": "user", "content": prompt}]
    else:
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        image.thumbnail((1024, 1024))
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": _data_url(buffer.getvalue())}},
                ],
            }
        ]

    response = client.chat.completions.create(model=model, messages=messages)
    content = response.choices[0].message.content
    return content.strip() if isinstance(content, str) else str(content).strip()


@dataclass
class GroqVisionProvider(VisionProvider):
    model: str
    prompts: PromptConfig = field(default_factory=get_prompt_config)
    client: object | None = None

    def _instruction_for(self, task: VisionTask) -> str:
        return {
            VisionTask.scene: self.prompts.vision_instruction,
            VisionTask.currency: self.prompts.currency_instruction,
            VisionTask.color: self.prompts.color_instruction,
            VisionTask.product: self.prompts.product_instruction,
        }[task]

    def analyze(
        self,
        image_bytes: bytes,
        question: str,
        history: Sequence[ConversationTurn],
        task: VisionTask = VisionTask.scene,
    ) -> str:
        _ = history
        client = self.client or _load_groq_client()
        prompt = (
            f"{self.prompts.vision_system}\n"
            f"{self._instruction_for(task)}\n"
            f"User question: {question}"
        )
        return _client_chat_content(client, self.model, prompt, image_bytes)


@dataclass
class GroqGroundingProvider(GroundingProvider):
    model: str
    prompts: PromptConfig = field(default_factory=get_prompt_config)
    client: object | None = None

    def locate_object(self, image_bytes: bytes, object_query: str, history: Sequence[ConversationTurn]) -> str:
        _ = history
        client = self.client or _load_groq_client()
        prompt = (
            f"{self.prompts.grounding_system}\n"
            f"Object query: {object_query}\n"
            "Return a short natural-language location description."
        )
        return _client_chat_content(client, self.model, prompt, image_bytes)


@dataclass
class GroqOCRProvider(OCRProvider):
    model: str
    prompts: PromptConfig = field(default_factory=get_prompt_config)
    client: object | None = None

    def extract_text(self, image_bytes: bytes) -> str:
        client = self.client or _load_groq_client()
        prompt = self.prompts.ocr_system
        return _client_chat_content(client, self.model, prompt, image_bytes)


@dataclass
class GroqLLMProvider(LLMProvider):
    model: str
    prompts: PromptConfig = field(default_factory=get_prompt_config)
    client: object | None = None

    def generate_response(
        self,
        user_message: str,
        vision_summary: str | None,
        ocr_text: str | None,
        history: Sequence[ConversationTurn],
    ) -> str:
        client = self.client or _load_groq_client()
        history_lines = [
            f"User: {turn.user_text}\nAssistant: {turn.assistant_text}"
            for turn in history[-4:]
        ]
        prompt_parts = [
            self.prompts.llm_system,
            f"User message: {user_message}",
        ]
        if vision_summary:
            prompt_parts.append(f"Scene summary: {vision_summary}")
        if ocr_text:
            prompt_parts.append(f"OCR text: {ocr_text}")
        if history_lines:
            prompt_parts.append("Recent history:\n" + "\n".join(history_lines))
        prompt_parts.append(self.prompts.llm_answer_style)

        prompt = "\n\n".join(prompt_parts)
        return _client_chat_content(client, self.model, prompt, None)


@dataclass
class GroqASRProvider(ASRProvider):
    model: str
    language: str = "ar"
    client: object | None = None

    def transcribe(self, audio_bytes: bytes) -> str:
        client = self.client or _load_groq_client()
        audio_file = BytesIO(audio_bytes)
        audio_file.name = "audio.wav"  # type: ignore[attr-defined]
        transcription = client.audio.transcriptions.create(
            file=audio_file,
            model=self.model,
            language=self.language,
            response_format="text",
        )
        return transcription if isinstance(transcription, str) else getattr(transcription, "text", str(transcription))


@dataclass
class GroqTTSProvider(TTSProvider):
    model: str
    voice: str = "abdullah"
    client: object | None = None

    def synthesize_speech(self, text: str) -> bytes:
        client = self.client or _load_groq_client()
        response = client.audio.speech.create(
            model=self.model,
            voice=self.voice,
            input=text,
            response_format="wav",
        )
        if hasattr(response, "read"):
            return response.read()
        if hasattr(response, "content"):
            return response.content
        if isinstance(response, bytes):
            return response
        return bytes(response)
