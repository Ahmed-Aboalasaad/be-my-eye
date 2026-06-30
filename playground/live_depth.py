import cv2
import numpy as np
from PIL import Image
from transformers import pipeline

depth_estimator = pipeline(
    task="depth-estimation",
    model="depth-anything/Depth-Anything-V2-Small-hf"
)

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()

    if not ret:
        break

    img = Image.fromarray(
        cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    )

    depth = depth_estimator(img)["depth"]

    depth = np.array(depth)

    depth = cv2.normalize(
        depth,
        None,
        0,
        255,
        cv2.NORM_MINMAX
    ).astype("uint8")


    cv2.imshow(
        "Depth",
        depth
    )

    if cv2.waitKey(1) == 27:
        break


cap.release()
cv2.destroyAllWindows()