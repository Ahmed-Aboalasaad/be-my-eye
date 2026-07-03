from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.conversation import create_conversation_router
from app.api.product import create_product_router
from app.core.config import get_settings
from app.core.prompts import get_prompt_config
from app.providers.fakes import (
    FakeASRProvider,
    FakeGroundingProvider,
    FakeLLMProvider,
    FakeOCRProvider,
    FakeProductLookupProvider,
    FakeTTSProvider,
    FakeVisionProvider,
)
from app.providers.egyptian_tts import EgyptianTTSProvider
from app.providers.openfoodfacts import OpenFoodFactsProductLookupProvider
from app.providers.roboflow_currency import RoboflowCurrencyProvider
from app.providers.groq import (
    GroqASRProvider,
    GroqGroundingProvider,
    GroqLLMProvider,
    GroqOCRProvider,
    GroqTTSProvider,
    GroqVisionProvider,
)
from app.services.conversation_service import ConversationService
from app.services.intent_router import IntentRouter
from app.services.session_store import InMemorySessionStore


def create_app() -> FastAPI:
    settings = get_settings()
    prompts = get_prompt_config()

    if settings.use_real_providers:
        if not settings.groq_multimodal_model:
            raise RuntimeError("GROQ_MULTIMODAL_MODEL is required when real providers are enabled.")
        currency_detector = (
            RoboflowCurrencyProvider(
                project=settings.roboflow_currency_project,
                version=settings.roboflow_currency_version,
                api_key=settings.roboflow_api_key,
            )
            if settings.roboflow_api_key
            else None
        )
        service = ConversationService(
            asr=GroqASRProvider(model=settings.groq_asr_model, language=settings.groq_asr_language),
            vision=GroqVisionProvider(model=settings.groq_multimodal_model, prompts=prompts),
            ocr=GroqOCRProvider(model=settings.groq_multimodal_model, prompts=prompts),
            llm=GroqLLMProvider(model=settings.groq_llm_model, prompts=prompts),
            tts=EgyptianTTSProvider(space_id=settings.egyptian_tts_space_id),
            grounding=GroqGroundingProvider(model=settings.groq_multimodal_model, prompts=prompts),
            session_store=InMemorySessionStore(),
            router=IntentRouter(),
            currency_detector=currency_detector,
        )
    else:
        service = ConversationService(
            asr=FakeASRProvider(),
            vision=FakeVisionProvider(),
            ocr=FakeOCRProvider(),
            llm=FakeLLMProvider(),
            tts=FakeTTSProvider(),
            grounding=FakeGroundingProvider(),
            session_store=InMemorySessionStore(),
            router=IntentRouter(),
        )

    product_lookup_provider = (
        OpenFoodFactsProductLookupProvider() if settings.use_real_providers else FakeProductLookupProvider()
    )

    app = FastAPI(title=settings.app_name, debug=settings.debug)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(create_conversation_router(service))
    app.include_router(create_product_router(product_lookup_provider))

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
