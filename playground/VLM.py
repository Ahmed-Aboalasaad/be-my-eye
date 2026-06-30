import time
import torch
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from transformers import AutoProcessor, AutoModelForCausalLM

# ==========================================================
# Hardware
# ==========================================================

device = "cuda" if torch.cuda.is_available() else "cpu"
dtype = torch.float16 if torch.cuda.is_available() else torch.float32

print(f"Device: {device}")

# ==========================================================
# Load Florence-2
# ==========================================================

model_id = "microsoft/Florence-2-base"

print("Loading model...")

model = AutoModelForCausalLM.from_pretrained(
    model_id,
    trust_remote_code=True,
    attn_implementation="eager"
).to(device, dtype)

processor = AutoProcessor.from_pretrained(
    model_id,
    trust_remote_code=True
)

model.eval()

print("Model Loaded.\n")

# ==========================================================
# Load Image
# ==========================================================

image_path = r"C:\Users\Admin\Downloads\Telegram Desktop\photo_2026-06-30_11-43-22.jpg"

image = Image.open(image_path).convert("RGB")

# ==========================================================
# CUDA Sync
# ==========================================================

def sync():
    if torch.cuda.is_available():
        torch.cuda.synchronize()

# ==========================================================
# Florence Runner
# ==========================================================

def run_florence(prompt):

    print("\n" + "=" * 70)
    print(prompt)
    print("=" * 70)

    total_start = time.perf_counter()

    # -------------------------
    # Preprocess
    # -------------------------

    preprocess_start = time.perf_counter()

    inputs = processor(
        text=prompt,
        images=image,
        return_tensors="pt"
    )

    inputs = {k: v.to(device) for k, v in inputs.items()}

    if dtype == torch.float16:
        inputs["pixel_values"] = inputs["pixel_values"].to(dtype)

    sync()

    preprocess_end = time.perf_counter()

    # -------------------------
    # Inference
    # -------------------------

    sync()
    inference_start = time.perf_counter()

    with torch.inference_mode():

        generated_ids = model.generate(
            **inputs,
            max_new_tokens=512,
            do_sample=False,
            num_beams=1,
            use_cache=False
        )

    sync()

    inference_end = time.perf_counter()

    # -------------------------
    # Decode
    # -------------------------

    post_start = time.perf_counter()

    generated_text = processor.batch_decode(
        generated_ids,
        skip_special_tokens=False
    )[0]

    # Try post-processing
    try:

        parsed = processor.post_process_generation(
            generated_text,
            task=prompt,
            image_size=(image.width, image.height)
        )

    except Exception:
        parsed = generated_text

    sync()

    post_end = time.perf_counter()

    total_end = time.perf_counter()

    print(f"\nPreprocessing : {preprocess_end-preprocess_start:.3f}s")
    print(f"Inference     : {inference_end-inference_start:.3f}s")
    print(f"Postprocess   : {post_end-post_start:.3f}s")
    print(f"Total         : {total_end-total_start:.3f}s")
    print(f"FPS           : {1/(inference_end-inference_start):.2f}")

    return parsed

# ==========================================================
# Caption
# ==========================================================

caption = run_florence("<MORE_DETAILED_CAPTION>")

print("\nCaption:\n")

if isinstance(caption, dict):
    print(caption["<MORE_DETAILED_CAPTION>"])
else:
    print(caption)

# ==========================================================
# Object Detection
# ==========================================================

detections = run_florence("<OD>")

if isinstance(detections, dict):

    result = detections["<OD>"]

    bboxes = result["bboxes"]
    labels = result["labels"]

    print(f"\nDetected {len(labels)} objects.\n")

    fig, ax = plt.subplots(figsize=(12, 10))
    ax.imshow(image)

    for bbox, label in zip(bboxes, labels):

        xmin, ymin, xmax, ymax = bbox

        rect = patches.Rectangle(
            (xmin, ymin),
            xmax - xmin,
            ymax - ymin,
            linewidth=2,
            edgecolor="lime",
            facecolor="none"
        )

        ax.add_patch(rect)

        ax.text(
            xmin,
            ymin - 5,
            label,
            color="white",
            fontsize=10,
            bbox=dict(facecolor="black", alpha=0.7)
        )

    plt.axis("off")
    plt.show()

# ==========================================================
# Visual Question Answering
# ==========================================================

question = "<VQA> How many people are in this image?"

answer = run_florence(question)

print("\nQuestion:")
print(question)

print("\nAnswer:")

if isinstance(answer, dict):
    print(answer)
else:
    print(answer)