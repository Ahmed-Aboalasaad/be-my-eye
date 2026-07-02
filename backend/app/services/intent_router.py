from __future__ import annotations

from dataclasses import dataclass

from app.schemas.common import VisionTask


@dataclass(frozen=True)
class RoutingDecision:
    vision_task: VisionTask
    use_ocr: bool
    grounding_query: str | None = None


class IntentRouter:
    OCR_KEYWORDS = (
        "read",
        "text",
        "document",
        "sign",
        "label",
        "receipt",
        "menu",
        "page",
    )
    CURRENCY_KEYWORDS = (
        "money",
        "cash",
        "bill",
        "banknote",
        "dollar",
        "how much",
        "denomination",
        "currency",
        "note",
    )
    COLOR_KEYWORDS = (
        "color",
        "colour",
        "shade",
    )
    PRODUCT_KEYWORDS = (
        "what am i holding",
        "brand",
        "package",
        "label",
        "product",
    )
    GROUNDING_KEYWORDS = (
        "where",
        "find",
        "locate",
        "which direction",
    )

    def route(self, user_message: str) -> RoutingDecision:
        normalized = user_message.lower()

        if any(keyword in normalized for keyword in self.CURRENCY_KEYWORDS):
            vision_task = VisionTask.currency
        elif any(keyword in normalized for keyword in self.COLOR_KEYWORDS):
            vision_task = VisionTask.color
        elif any(keyword in normalized for keyword in self.PRODUCT_KEYWORDS):
            vision_task = VisionTask.product
        else:
            vision_task = VisionTask.scene

        use_ocr = any(keyword in normalized for keyword in self.OCR_KEYWORDS)

        grounding_query = None
        if any(keyword in normalized for keyword in self.GROUNDING_KEYWORDS):
            grounding_query = user_message

        return RoutingDecision(
            vision_task=vision_task,
            use_ocr=use_ocr,
            grounding_query=grounding_query,
        )
