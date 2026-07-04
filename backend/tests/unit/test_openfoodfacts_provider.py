import httpx

from app.providers.openfoodfacts import OpenFoodFactsProductLookupProvider


class FakeTransport(httpx.BaseTransport):
    def __init__(self, json_body: dict, status_code: int = 200):
        self._json_body = json_body
        self._status_code = status_code

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(self._status_code, json=self._json_body)


def make_client(json_body: dict, status_code: int = 200) -> httpx.Client:
    return httpx.Client(transport=FakeTransport(json_body, status_code))


def test_openfoodfacts_returns_product_info_when_found():
    client = make_client(
        {
            "status": 1,
            "product": {
                "product_name": "Juhayna Full Cream Milk",
                "brands": "Juhayna",
                "ingredients_text": "Full cream milk",
                "allergens_tags": ["en:milk"],
            },
        }
    )
    provider = OpenFoodFactsProductLookupProvider(client=client)

    result = provider.lookup_by_barcode("6224000123456")

    assert result is not None
    assert result.name == "Juhayna Full Cream Milk"
    assert result.brand == "Juhayna"
    assert result.allergens == ["milk"]


def test_openfoodfacts_returns_none_when_not_found():
    client = make_client({"status": 0})
    provider = OpenFoodFactsProductLookupProvider(client=client)

    result = provider.lookup_by_barcode("0000000000000")

    assert result is None


def test_openfoodfacts_returns_none_on_server_error_instead_of_raising():
    client = make_client({"error": "internal"}, status_code=503)
    provider = OpenFoodFactsProductLookupProvider(client=client)

    result = provider.lookup_by_barcode("6224000123456")

    assert result is None
