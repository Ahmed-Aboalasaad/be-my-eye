from app.core.prompts import get_prompt_config


def test_prompt_config_uses_defaults(monkeypatch):
    monkeypatch.delenv("BE_MY_EYE_VISION_SYSTEM_PROMPT", raising=False)
    monkeypatch.delenv("BE_MY_EYE_OCR_SYSTEM_PROMPT", raising=False)
    monkeypatch.delenv("BE_MY_EYE_LLM_SYSTEM_PROMPT", raising=False)

    prompts = get_prompt_config()

    assert "accessibility assistant" in prompts.vision_system.lower()
    assert "extract the visible text" in prompts.ocr_system.lower()
    assert "conversation history" in prompts.llm_system.lower()


def test_prompt_config_forces_egyptian_arabic_only(monkeypatch):
    monkeypatch.delenv("BE_MY_EYE_VISION_SYSTEM_PROMPT", raising=False)
    monkeypatch.delenv("BE_MY_EYE_LLM_SYSTEM_PROMPT", raising=False)

    prompts = get_prompt_config()

    assert "egyptian arabic" in prompts.vision_system.lower()
    assert "egyptian arabic" in prompts.llm_system.lower()
    assert "never in english" in prompts.vision_system.lower()
    assert "never in english" in prompts.llm_system.lower()


def test_prompt_config_answer_style_keeps_responses_brief(monkeypatch):
    monkeypatch.delenv("BE_MY_EYE_LLM_ANSWER_STYLE_PROMPT", raising=False)

    prompts = get_prompt_config()

    assert "one short" not in prompts.llm_answer_style.lower()
    assert "1 to 2" in prompts.llm_answer_style.lower()


def test_prompt_config_requires_spelled_out_numbers(monkeypatch):
    monkeypatch.delenv("BE_MY_EYE_VISION_SYSTEM_PROMPT", raising=False)
    monkeypatch.delenv("BE_MY_EYE_LLM_SYSTEM_PROMPT", raising=False)
    monkeypatch.delenv("BE_MY_EYE_CURRENCY_INSTRUCTION_PROMPT", raising=False)

    prompts = get_prompt_config()

    assert "spell out" in prompts.vision_system.lower()
    assert "spell out" in prompts.llm_system.lower()
    assert "printed" in prompts.currency_instruction.lower()


def test_prompt_config_forbids_inventing_a_persona_name(monkeypatch):
    monkeypatch.delenv("BE_MY_EYE_VISION_SYSTEM_PROMPT", raising=False)
    monkeypatch.delenv("BE_MY_EYE_LLM_SYSTEM_PROMPT", raising=False)

    prompts = get_prompt_config()

    assert "does not have a personal name" in prompts.vision_system.lower() or "no personal name" in prompts.vision_system.lower()
    assert "does not have a personal name" in prompts.llm_system.lower() or "no personal name" in prompts.llm_system.lower()


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


def test_prompt_config_includes_new_accessibility_task_instructions(monkeypatch):
    monkeypatch.delenv("BE_MY_EYE_FOOD_INSTRUCTION_PROMPT", raising=False)
    monkeypatch.delenv("BE_MY_EYE_PEOPLE_INSTRUCTION_PROMPT", raising=False)
    monkeypatch.delenv("BE_MY_EYE_ENVIRONMENT_INSTRUCTION_PROMPT", raising=False)
    monkeypatch.delenv("BE_MY_EYE_CLOTHING_INSTRUCTION_PROMPT", raising=False)
    monkeypatch.delenv("BE_MY_EYE_LABEL_INSTRUCTION_PROMPT", raising=False)

    prompts = get_prompt_config()

    assert "dish" in prompts.food_instruction.lower()
    assert "allerg" in prompts.food_instruction.lower()
    assert "identify" not in prompts.people_instruction.lower()
    assert "light" in prompts.environment_instruction.lower()
    assert "match" in prompts.clothing_instruction.lower() or "stain" in prompts.clothing_instruction.lower()
    assert "expir" in prompts.label_instruction.lower() or "medicine" in prompts.label_instruction.lower()


def test_prompt_config_reads_new_accessibility_task_overrides(monkeypatch):
    monkeypatch.setenv("BE_MY_EYE_FOOD_INSTRUCTION_PROMPT", "food override")
    monkeypatch.setenv("BE_MY_EYE_PEOPLE_INSTRUCTION_PROMPT", "people override")
    monkeypatch.setenv("BE_MY_EYE_ENVIRONMENT_INSTRUCTION_PROMPT", "environment override")
    monkeypatch.setenv("BE_MY_EYE_CLOTHING_INSTRUCTION_PROMPT", "clothing override")
    monkeypatch.setenv("BE_MY_EYE_LABEL_INSTRUCTION_PROMPT", "label override")

    prompts = get_prompt_config()

    assert prompts.food_instruction == "food override"
    assert prompts.people_instruction == "people override"
    assert prompts.environment_instruction == "environment override"
    assert prompts.clothing_instruction == "clothing override"
    assert prompts.label_instruction == "label override"

