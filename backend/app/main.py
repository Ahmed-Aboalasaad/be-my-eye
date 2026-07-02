from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.conversation import create_conversation_router
from app.core.config import get_settings
from app.core.prompts import get_prompt_config
from app.providers.fakes import FakeASRProvider, FakeLLMProvider, FakeOCRProvider, FakeTTSProvider, FakeVisionProvider
from app.providers.groq import GroqASRProvider, GroqLLMProvider, GroqOCRProvider, GroqTTSProvider, GroqVisionProvider
from app.services.conversation_service import ConversationService
from app.services.intent_router import IntentRouter
from app.services.session_store import InMemorySessionStore


def create_app() -> FastAPI:
    settings = get_settings()
    prompts = get_prompt_config()

    if settings.use_real_providers:
        if not settings.groq_multimodal_model:
            raise RuntimeError("GROQ_MULTIMODAL_MODEL is required when real providers are enabled.")
        service = ConversationService(
            asr=GroqASRProvider(model=settings.groq_asr_model, language=settings.groq_asr_language),
            vision=GroqVisionProvider(model=settings.groq_multimodal_model, prompts=prompts),
            ocr=GroqOCRProvider(model=settings.groq_multimodal_model, prompts=prompts),
            llm=GroqLLMProvider(model=settings.groq_llm_model, prompts=prompts),
            tts=GroqTTSProvider(model=settings.groq_tts_model, voice=settings.groq_tts_voice),
            session_store=InMemorySessionStore(),
            router=IntentRouter(),
        )
    else:
        service = ConversationService(
            asr=FakeASRProvider(),
            vision=FakeVisionProvider(),
            ocr=FakeOCRProvider(),
            llm=FakeLLMProvider(),
            tts=FakeTTSProvider(),
            session_store=InMemorySessionStore(),
            router=IntentRouter(),
        )

    app = FastAPI(title=settings.app_name, debug=settings.debug)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(create_conversation_router(service))

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
