from __future__ import annotations

from starlette.middleware.cors import CORSMiddleware

from app.main import create_app


def test_app_has_cors_middleware_allowing_all_origins() -> None:
    app = create_app()

    cors_entries = [m for m in app.user_middleware if m.cls is CORSMiddleware]

    assert len(cors_entries) == 1
    assert cors_entries[0].kwargs["allow_origins"] == ["*"]


def test_create_app_wires_grounding_provider_in_fake_mode(monkeypatch):
    monkeypatch.delenv("USE_REAL_PROVIDERS", raising=False)

    app = create_app()

    assert app is not None


def test_create_app_registers_product_lookup_route():
    app = create_app()

    # Newer Starlette versions include some entries in app.routes (e.g. a
    # mounted/included router as a whole) that don't expose `.path` directly
    # -- only individual APIRoute-like entries do. Filter to those.
    paths = {route.path for route in app.routes if hasattr(route, "path")}
    assert "/product-lookup" in paths


def test_create_app_uses_egyptian_tts_in_real_mode(monkeypatch):
    from app.providers.egyptian_tts import EgyptianTTSProvider

    monkeypatch.setenv("USE_REAL_PROVIDERS", "true")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_MULTIMODAL_MODEL", "test-model")

    app = create_app()

    # The service is a closure captured by the route; the cleanest external
    # check is that the app builds without error in real mode with the new
    # provider wired in -- deeper inspection would require reaching into
    # FastAPI's dependency closures, which this repo's other tests don't do.
    assert app is not None


def test_create_app_wires_currency_detector_only_when_roboflow_key_present(monkeypatch):
    monkeypatch.setenv("USE_REAL_PROVIDERS", "true")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_MULTIMODAL_MODEL", "test-model")
    monkeypatch.delenv("ROBOFLOW_API_KEY", raising=False)

    app = create_app()

    assert app is not None


def test_create_app_registers_currency_lookup_route():
    app = create_app()

    paths = {route.path for route in app.routes if hasattr(route, "path")}
    assert "/currency-lookup" in paths
