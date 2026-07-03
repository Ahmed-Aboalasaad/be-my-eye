from __future__ import annotations

from fastapi import APIRouter

from app.providers.base import ProductLookupProvider
from app.schemas.product import ProductLookupRequest, ProductLookupResponse


def create_product_router(provider: ProductLookupProvider) -> APIRouter:
    router = APIRouter()

    @router.post("/product-lookup", response_model=ProductLookupResponse)
    def post_product_lookup(payload: ProductLookupRequest) -> ProductLookupResponse:
        product = provider.lookup_by_barcode(payload.barcode)
        return ProductLookupResponse(found=product is not None, product=product)

    return router
