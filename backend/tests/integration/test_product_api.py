from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.api.product import create_product_router
from app.providers.fakes import FakeProductLookupProvider


def make_client() -> TestClient:
    app = FastAPI()
    app.include_router(create_product_router(FakeProductLookupProvider()))
    return TestClient(app)


def test_product_lookup_returns_product_for_known_barcode():
    client = make_client()

    response = client.post("/product-lookup", json={"barcode": "1234567890123"})

    assert response.status_code == 200
    body = response.json()
    assert body["found"] is True
    assert body["product"]["name"] == "Sample Product"


def test_product_lookup_returns_not_found_for_unknown_barcode():
    client = make_client()

    response = client.post("/product-lookup", json={"barcode": "0000000000000"})

    assert response.status_code == 200
    body = response.json()
    assert body["found"] is False
    assert body["product"] is None
