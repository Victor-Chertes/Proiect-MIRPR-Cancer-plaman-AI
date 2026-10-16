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
    start = time.perf_counter()
    time.sleep(1.2)  # simulate inference latency so the UI flow is realistic

    digest = hashlib.sha256(image_bytes).digest()
    label = LABELS[digest[0] % 2]
    confidence = 0.70 + (digest[1] / 255) * 0.29

    return {
        "prediction": label,
        "confidence": round(confidence, 4),
        "model": MODEL_NAME,
        "inference_ms": round((time.perf_counter() - start) * 1000),
    }
