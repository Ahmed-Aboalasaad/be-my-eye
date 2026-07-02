from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class PromptConfig:
    vision_system: str
    vision_instruction: str
    ocr_system: str
    llm_system: str
    llm_answer_style: str
    grounding_system: str
    currency_instruction: str
    color_instruction: str
    product_instruction: str


def get_prompt_config() -> PromptConfig:
    return PromptConfig(
        vision_system=os.getenv(
            "BE_MY_EYE_VISION_SYSTEM_PROMPT",
            "You are an accessibility assistant for blind and low-vision users.",
        ),
        vision_instruction=os.getenv(
            "BE_MY_EYE_VISION_INSTRUCTION_PROMPT",
            "Answer the user's question about the image concisely, clearly, and without unnecessary detail.",
        ),
        ocr_system=os.getenv(
            "BE_MY_EYE_OCR_SYSTEM_PROMPT",
            "Extract the visible text from the image. Preserve line breaks when they help readability. If the text is unreadable, say so briefly.",
        ),
        llm_system=os.getenv(
            "BE_MY_EYE_LLM_SYSTEM_PROMPT",
            "You are an accessibility assistant. Use the user's transcript, the scene summary, OCR text, and conversation history to answer concisely.",
        ),
        llm_answer_style=os.getenv(
            "BE_MY_EYE_LLM_ANSWER_STYLE_PROMPT",
            "Respond in one short, natural sentence. Do not expose internal implementation details.",
        ),
        grounding_system=os.getenv(
            "BE_MY_EYE_GROUNDING_SYSTEM_PROMPT",
            "Identify where a user-referenced object is likely located in the image.",
        ),
        currency_instruction=os.getenv(
            "BE_MY_EYE_CURRENCY_INSTRUCTION_PROMPT",
            "Identify the currency and denomination shown in the image. State the amount plainly. Express uncertainty if the note or coin is unclear or partially visible.",
        ),
        color_instruction=os.getenv(
            "BE_MY_EYE_COLOR_INSTRUCTION_PROMPT",
            "Identify the dominant color of the specific item the user is asking about. Name the color plainly using common color names.",
        ),
        product_instruction=os.getenv(
            "BE_MY_EYE_PRODUCT_INSTRUCTION_PROMPT",
            "Identify the product the user is holding, including brand and type if visible on the packaging or label. Express uncertainty if the label is not clearly readable.",
        ),
    )
