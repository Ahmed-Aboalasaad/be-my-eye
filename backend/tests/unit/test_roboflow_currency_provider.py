import httpx

from app.providers.roboflow_currency import RoboflowCurrencyProvider


class FakeTransport(httpx.BaseTransport):
    def __init__(self, json_body: dict, status_code: int = 200):
        self._json_body = json_body
        self._status_code = status_code

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(self._status_code, json=self._json_body)


def make_client(json_body: dict, status_code: int = 200) -> httpx.Client:
    return httpx.Client(transport=FakeTransport(json_body, status_code))


def test_roboflow_currency_returns_highest_confidence_prediction():
    client = make_client(
        {
            "predictions": [
                {"class": "10_egp", "confidence": 0.55},
                {"class": "20_egp", "confidence": 0.91},
            ]
        }
    )
    provider = RoboflowCurrencyProvider(project="egyptian-currency-psnkr", version="1", api_key="test-key", client=client)

    result = provider.detect_currency(b"fake-image-bytes")

    assert result is not None
    assert result.denomination == "20_egp"
    assert result.confidence == 0.91


def test_roboflow_currency_returns_none_when_no_predictions():
    client = make_client({"predictions": []})
    provider = RoboflowCurrencyProvider(project="egyptian-currency-psnkr", version="1", api_key="test-key", client=client)

    result = provider.detect_currency(b"fake-image-bytes")

    assert result is None


def test_roboflow_currency_returns_none_on_request_failure():
    client = make_client({"error": "not found"}, status_code=404)
    provider = RoboflowCurrencyProvider(project="egyptian-currency-psnkr", version="1", api_key="test-key", client=client)

    result = provider.detect_currency(b"fake-image-bytes")

    assert result is None
