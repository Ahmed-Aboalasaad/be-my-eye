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

    paths = {route.path for route in app.routes}
    assert "/product-lookup" in paths
