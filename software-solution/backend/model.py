"""Placeholder for the lung cancer classifier.

The real model will be trained in the next stages of the project. Until then
`predict` returns a hard-coded POSITIVE/NEGATIVE result. The label is derived
from the image hash so the same scan always gets the same answer, which keeps
demos reproducible.
"""

import hashlib
import time

MODEL_NAME = "mock-v0"
LABELS = ("NEGATIVE", "POSITIVE")


def predict(image_bytes: bytes) -> dict:
    time.sleep(0.8)  # simulate inference latency so the UI flow is realistic
    digest = hashlib.sha256(image_bytes).digest()
    return {"prediction": LABELS[digest[0] % 2], "model": MODEL_NAME}
