from app.schemas.common import ConversationDebug, ConversationResponse, ConversationTurn, VisionTask


def test_conversation_turn_defaults_created_at():
    turn = ConversationTurn(user_text="Hello", assistant_text="Hi")

    assert turn.user_text == "Hello"
    assert turn.assistant_text == "Hi"
    assert turn.created_at is not None


def test_conversation_debug_model():
    debug = ConversationDebug(
        transcript="What is this?",
        selected_providers=["vision"],
        vision_summary="a desk",
    )

    assert debug.transcript == "What is this?"
    assert debug.selected_providers == ["vision"]
    assert debug.ocr_text is None


def test_conversation_response_model():
    response = ConversationResponse(
        session_id="session-1",
        text="A desk with a laptop.",
        audio_base64="YWJj",
    )

    assert response.session_id == "session-1"
    assert response.text == "A desk with a laptop."
    assert response.audio_base64 == "YWJj"


def test_vision_task_has_four_members():
    assert {member.value for member in VisionTask} == {"scene", "currency", "color", "product"}


def test_vision_task_default_is_scene():
    assert VisionTask.scene.value == "scene"
