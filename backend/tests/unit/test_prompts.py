from app.core.prompts import get_prompt_config


def test_prompt_config_uses_defaults(monkeypatch):
    monkeypatch.delenv("BE_MY_EYE_VISION_SYSTEM_PROMPT", raising=False)
    monkeypatch.delenv("BE_MY_EYE_OCR_SYSTEM_PROMPT", raising=False)
    monkeypatch.delenv("BE_MY_EYE_LLM_SYSTEM_PROMPT", raising=False)

    prompts = get_prompt_config()

    assert "accessibility assistant" in prompts.vision_system.lower()
    assert "extract the visible text" in prompts.ocr_system.lower()
    assert "answer concisely" in prompts.llm_system.lower()


def test_prompt_config_reads_overrides(monkeypatch):
    monkeypatch.setenv("BE_MY_EYE_VISION_SYSTEM_PROMPT", "vision override")
    monkeypatch.setenv("BE_MY_EYE_VISION_INSTRUCTION_PROMPT", "instruction override")
    monkeypatch.setenv("BE_MY_EYE_OCR_SYSTEM_PROMPT", "ocr override")
    monkeypatch.setenv("BE_MY_EYE_LLM_SYSTEM_PROMPT", "llm override")
    monkeypatch.setenv("BE_MY_EYE_LLM_ANSWER_STYLE_PROMPT", "style override")
    monkeypatch.setenv("BE_MY_EYE_GROUNDING_SYSTEM_PROMPT", "grounding override")

    prompts = get_prompt_config()

    assert prompts.vision_system == "vision override"
    assert prompts.vision_instruction == "instruction override"
    assert prompts.ocr_system == "ocr override"
    assert prompts.llm_system == "llm override"
    assert prompts.llm_answer_style == "style override"
    assert prompts.grounding_system == "grounding override"


def test_prompt_config_includes_vision_task_instructions(monkeypatch):
    monkeypatch.delenv("BE_MY_EYE_CURRENCY_INSTRUCTION_PROMPT", raising=False)
    monkeypatch.delenv("BE_MY_EYE_COLOR_INSTRUCTION_PROMPT", raising=False)
    monkeypatch.delenv("BE_MY_EYE_PRODUCT_INSTRUCTION_PROMPT", raising=False)

    prompts = get_prompt_config()

    assert "currency" in prompts.currency_instruction.lower() or "money" in prompts.currency_instruction.lower()
    assert "color" in prompts.color_instruction.lower()
    assert "product" in prompts.product_instruction.lower()


def test_prompt_config_reads_vision_task_overrides(monkeypatch):
    monkeypatch.setenv("BE_MY_EYE_CURRENCY_INSTRUCTION_PROMPT", "currency override")
    monkeypatch.setenv("BE_MY_EYE_COLOR_INSTRUCTION_PROMPT", "color override")
    monkeypatch.setenv("BE_MY_EYE_PRODUCT_INSTRUCTION_PROMPT", "product override")

    prompts = get_prompt_config()

    assert prompts.currency_instruction == "currency override"
    assert prompts.color_instruction == "color override"
    assert prompts.product_instruction == "product override"

