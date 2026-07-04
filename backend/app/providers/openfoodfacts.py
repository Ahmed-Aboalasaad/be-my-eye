from __future__ import annotations

from urllib.parse import quote

import httpx

from app.providers.base import ProductLookupProvider
from app.schemas.product import ProductInfo

OPEN_FOOD_FACTS_URL = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json"


class OpenFoodFactsProductLookupProvider(ProductLookupProvider):
    def __init__(self, client: httpx.Client | None = None, timeout: float = 5.0) -> None:
        self._client = client or httpx.Client(timeout=timeout)

    def lookup_by_barcode(self, barcode: str) -> ProductInfo | None:
        # ProductLookupRequest already restricts barcode to digits, but this
        # provider can be called directly (not only via the API layer), so
        # percent-encode here too rather than relying solely on the caller.
        try:
            response = self._client.get(OPEN_FOOD_FACTS_URL.format(barcode=quote(barcode, safe="")))
            response.raise_for_status()
            data = response.json()
        except Exception:  # noqa: BLE001 -- Open Food Facts being down means "not found", not a 500
            return None

        if data.get("status") != 1:
            return None

        product = data.get("product", {})
        return ProductInfo(
            name=product.get("product_name") or "Unknown product",
            brand=product.get("brands"),
            ingredients_text=product.get("ingredients_text"),
            allergens=[tag.removeprefix("en:") for tag in product.get("allergens_tags", [])],
        )
