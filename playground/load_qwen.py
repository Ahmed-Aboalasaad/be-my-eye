import time
import torch
from PIL import Image
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info

# ==================================================
# Configuration
# ==================================================

MODEL_NAME = "Qwen/Qwen2.5-VL-3B-Instruct"

IMAGE_PATH = r"test.jpg"

# ==================================================
# Load model
# ==================================================

print("Loading model...")

load_start = time.perf_counter()

model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
    MODEL_NAME,
    local_files_only=True,
    torch_dtype=torch.float32,
    device_map="cpu",
    low_cpu_mem_usage=True,
)

processor = AutoProcessor.from_pretrained(
    MODEL_NAME,
    local_files_only=True,
)

load_end = time.perf_counter()

print(f"Model loaded in {load_end-load_start:.2f} seconds")

# ==================================================
# Load image
# ==================================================

image = Image.open(IMAGE_PATH).convert("RGB")

# Optional: reduce image size for faster inference
image.thumbnail((512, 512))

# ==================================================
# Prompt
# ==================================================

messages = [
    {
        "role": "user",
        "content": [
            {
                "type": "image",
                "image": image,
            },
            {
                "type": "text",
                "text": (
                    "Describe this image in Arabic. "
                    "This description is for a blind person. "
                    "Focus on important objects, people, obstacles, and their locations."
                ),
            },
        ],
    }
]

# ==================================================
# Preprocess
# ==================================================

text = processor.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True,
)

image_inputs, video_inputs = process_vision_info(messages)

inputs = processor(
    text=[text],
    images=image_inputs,
    videos=video_inputs,
    padding=True,
    return_tensors="pt",
)

# ==================================================
# Inference
# ==================================================

print("\nRunning inference...")

infer_start = time.perf_counter()

with torch.no_grad():
    generated_ids = model.generate(
        **inputs,
        max_new_tokens=128,
    )

infer_end = time.perf_counter()

generated_ids_trimmed = [
    out_ids[len(in_ids):]
    for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
]

response = processor.batch_decode(
    generated_ids_trimmed,
    skip_special_tokens=True,
    clean_up_tokenization_spaces=False,
)[0]

# ==================================================
# Output
# ==================================================

print("\n==============================")
print("Description")
print("==============================")
print(response)

print("\n==============================")
print("Performance")
print("==============================")
print(f"Model loading time : {load_end-load_start:.2f} s")
print(f"Inference time     : {infer_end-infer_start:.2f} s")