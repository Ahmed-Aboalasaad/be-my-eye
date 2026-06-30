import torch
import matplotlib.pyplot as plt
from PIL import Image
from transformers import pipeline


# Load Depth Anything model
depth_estimator = pipeline(
    task="depth-estimation",
    model="depth-anything/Depth-Anything-V2-Small-hf"
)


# Load your image
image_path = "test.jpg"
image = Image.open(image_path).convert("RGB")


# Run inference
result = depth_estimator(image)


# Extract depth map
depth = result["depth"]


# Display original + depth
plt.figure(figsize=(12, 5))

plt.subplot(1, 2, 1)
plt.imshow(image)
plt.title("Original Image")
plt.axis("off")


plt.subplot(1, 2, 2)
plt.imshow(depth, cmap="inferno")
plt.title("Predicted Depth")
plt.axis("off")


plt.show()