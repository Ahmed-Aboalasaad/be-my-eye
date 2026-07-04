from app.schemas.common import VisionTask
from app.services.intent_router import IntentRouter, RoutingDecision


def test_intent_router_selects_scene_task_by_default():
    router = IntentRouter()

    decision = router.route("What is in front of me?")

    assert decision == RoutingDecision(vision_task=VisionTask.scene, use_ocr=False, grounding_query=None)


def test_intent_router_adds_ocr_for_text_requests():
    router = IntentRouter()

    decision = router.route("Please read this document")

    assert decision.vision_task == VisionTask.scene
    assert decision.use_ocr is True


def test_intent_router_selects_currency_task():
    router = IntentRouter()

    decision = router.route("How much money is this?")

    assert decision.vision_task == VisionTask.currency


def test_intent_router_selects_color_task():
    router = IntentRouter()

    decision = router.route("What color is my shirt?")

    assert decision.vision_task == VisionTask.color


def test_intent_router_selects_product_task():
    router = IntentRouter()

    decision = router.route("What brand is this product?")

    assert decision.vision_task == VisionTask.product


def test_intent_router_sets_grounding_query():
    router = IntentRouter()

    decision = router.route("Where are my keys?")

    assert decision.grounding_query == "Where are my keys?"


def test_intent_router_has_no_grounding_query_by_default():
    router = IntentRouter()

    decision = router.route("What is in front of me?")

    assert decision.grounding_query is None


def test_intent_router_priority_currency_over_color():
    router = IntentRouter()

    decision = router.route("What color is this dollar bill?")

    assert decision.vision_task == VisionTask.currency


def test_intent_router_selects_currency_task_in_arabic():
    router = IntentRouter()

    decision = router.route("كم سعر هذه العملة؟")

    assert decision.vision_task == VisionTask.currency


def test_intent_router_selects_color_task_in_arabic():
    router = IntentRouter()

    decision = router.route("ما لون هذا القميص؟")

    assert decision.vision_task == VisionTask.color


def test_intent_router_sets_grounding_query_in_arabic():
    router = IntentRouter()

    decision = router.route("وين مفاتيحي؟")

    assert decision.grounding_query == "وين مفاتيحي؟"


def test_intent_router_adds_ocr_for_arabic_text_requests():
    router = IntentRouter()

    decision = router.route("اقرأ هذا المستند من فضلك")

    assert decision.use_ocr is True


def test_intent_router_selects_food_task():
    router = IntentRouter()

    decision = router.route("What am I eating?")

    assert decision.vision_task == VisionTask.food


def test_intent_router_selects_food_task_in_arabic():
    router = IntentRouter()

    decision = router.route("ايه ده اللي قدامي في الطبق؟")

    assert decision.vision_task == VisionTask.food


def test_intent_router_selects_people_task():
    router = IntentRouter()

    decision = router.route("Is anyone standing in front of me?")

    assert decision.vision_task == VisionTask.people


def test_intent_router_selects_environment_task():
    router = IntentRouter()

    decision = router.route("Is the light on in this room?")

    assert decision.vision_task == VisionTask.environment


def test_intent_router_selects_clothing_task():
    router = IntentRouter()

    decision = router.route("Do my clothes match?")

    assert decision.vision_task == VisionTask.clothing


def test_intent_router_selects_label_task_for_expiry():
    router = IntentRouter()

    decision = router.route("Has this expired?")

    assert decision.vision_task == VisionTask.label


def test_intent_router_priority_food_over_scene():
    router = IntentRouter()

    decision = router.route("What food is on this plate?")

    assert decision.vision_task == VisionTask.food


def test_intent_router_selects_currency_task_for_egyptian_colloquial_phrasing():
    router = IntentRouter()

    decision = router.route("الورقة دي كام جنيه؟")

    assert decision.vision_task == VisionTask.currency


def test_intent_router_selects_color_task_for_egyptian_colloquial_phrasing():
    router = IntentRouter()

    decision = router.route("لونها ايه؟")

    assert decision.vision_task == VisionTask.color


def test_intent_router_selects_food_task_for_egyptian_colloquial_phrasing():
    router = IntentRouter()

    decision = router.route("دي اكلة ايه؟")

    assert decision.vision_task == VisionTask.food


def test_intent_router_selects_people_task_for_egyptian_colloquial_phrasing():
    router = IntentRouter()

    decision = router.route("فيه حد قدامي؟")

    assert decision.vision_task == VisionTask.people


def test_intent_router_selects_environment_task_for_egyptian_colloquial_phrasing():
    router = IntentRouter()

    decision = router.route("النور مفتوح؟")

    assert decision.vision_task == VisionTask.environment


def test_intent_router_sets_grounding_query_for_egyptian_colloquial_phrasing():
    router = IntentRouter()

    decision = router.route("الشنطة بتاعتي هي فين؟")

    assert decision.grounding_query == "الشنطة بتاعتي هي فين؟"


def test_intent_router_adds_ocr_for_egyptian_colloquial_phrasing():
    router = IntentRouter()

    decision = router.route("اقرالي اللافتة دي")

    assert decision.use_ocr is True
