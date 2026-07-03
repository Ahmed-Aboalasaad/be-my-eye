from __future__ import annotations

from dataclasses import dataclass

from app.schemas.common import VisionTask


@dataclass(frozen=True)
class RoutingDecision:
    vision_task: VisionTask
    use_ocr: bool
    grounding_query: str | None = None


class IntentRouter:
    # Keyword lists include Arabic variants because this app's ASR defaults
    # to Arabic (GROQ_ASR_LANGUAGE=ar in app/core/config.py) -- English-only
    # keywords would never match transcribed Arabic speech, silently
    # defaulting every request to the scene task regardless of intent.
    OCR_KEYWORDS = (
        "read",
        "text",
        "document",
        "sign",
        "label",
        "receipt",
        "menu",
        "page",
        "اقرأ",
        "نص",
        "مستند",
        "لافتة",
        "ملصق",
        "إيصال",
        "قائمة",
        "صفحة",
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
        "فلوس",
        "نقود",
        "كاش",
        "عملة",
        "ورقة نقدية",
        "دولار",
        "بكام",
        "كام سعر",
        "فئة",
    )
    COLOR_KEYWORDS = (
        "color",
        "colour",
        "shade",
        "لون",
        "لونه",
        "درجة اللون",
    )
    PRODUCT_KEYWORDS = (
        "what am i holding",
        "brand",
        "package",
        "label",
        "product",
        "ايه اللي في ايدي",
        "ماركة",
        "عبوة",
        "علبة",
        "منتج",
    )
    FOOD_KEYWORDS = (
        "eating",
        "eat",
        "food",
        "dish",
        "meal",
        "plate",
        "ingredient",
        "اكل",
        "أكل",
        "طعام",
        "طبق",
        "وجبة",
        "مكونات",
    )
    PEOPLE_KEYWORDS = (
        "anyone",
        "someone",
        "person",
        "people",
        "standing in front",
        "facing me",
        "حد",
        "شخص",
        "ناس",
        "واقف قدامي",
        "بيبصلي",
    )
    ENVIRONMENT_KEYWORDS = (
        "light on",
        "light off",
        "lights",
        "dark",
        "bright",
        "stove",
        "burner",
        "نور",
        "ضلمة",
        "مضي",
        "البوتاجاز",
        "الفرن مشغول",
    )
    CLOTHING_KEYWORDS = (
        "clothes match",
        "match",
        "clash",
        "stain",
        "outfit",
        "هدوم",
        "متناسقة",
        "بقعة",
        "لبس",
    )
    LABEL_KEYWORDS = (
        "expired",
        "expiry",
        "expire",
        "medicine",
        "medication",
        "pill",
        "انتهت الصلاحية",
        "صلاحية",
        "دواء",
        "علاج",
    )
    GROUNDING_KEYWORDS = (
        "where",
        "find",
        "locate",
        "which direction",
        "وين",
        "أين",
        "فين",
        "دور على",
        "ابحث عن",
        "حدد موقع",
        "في اي اتجاه",
    )

    def route(self, user_message: str) -> RoutingDecision:
        normalized = user_message.lower()

        if any(keyword in normalized for keyword in self.CURRENCY_KEYWORDS):
            vision_task = VisionTask.currency
        elif any(keyword in normalized for keyword in self.COLOR_KEYWORDS):
            vision_task = VisionTask.color
        elif any(keyword in normalized for keyword in self.PRODUCT_KEYWORDS):
            vision_task = VisionTask.product
        elif any(keyword in normalized for keyword in self.FOOD_KEYWORDS):
            vision_task = VisionTask.food
        elif any(keyword in normalized for keyword in self.PEOPLE_KEYWORDS):
            vision_task = VisionTask.people
        elif any(keyword in normalized for keyword in self.ENVIRONMENT_KEYWORDS):
            vision_task = VisionTask.environment
        elif any(keyword in normalized for keyword in self.CLOTHING_KEYWORDS):
            vision_task = VisionTask.clothing
        elif any(keyword in normalized for keyword in self.LABEL_KEYWORDS):
            vision_task = VisionTask.label
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
