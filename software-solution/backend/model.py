"""Placeholder for the biomarker classifier ("virtual biopsy").

The real model (3D CNN on the segmented CT volume, fused with age and sex) will
be trained in the next stages of the project. Until then `predict` returns the
hard-coded probabilities from the project report. The signature already takes
the inputs of the final model, so the real one can replace it without changes
to the API or the frontend.
"""

import time

MODEL_NAME = "mock-v1"

# name, description, probability (hard-coded), decision threshold
BIOMARKERS = (
    ("EGFR", "Mutație EGFR", 0.82, 0.5),
    ("ALK", "Rearanjare ALK", 0.12, 0.5),
    ("KRAS", "Mutație KRAS", 0.35, 0.5),
    ("PD-L1", "Expresie PD-L1", 0.67, 0.5),
)


def predict(volume: bytes, age: int, sex: str) -> dict:
    """Return the probability that each biomarker is positive.

    volume: the uploaded CT file (NIfTI, DICOM or a 2D slice), unparsed.
    age: patient age in years. sex: "M" or "F".
    """
    time.sleep(1.5)  # simulate inference latency so the UI flow is realistic
    return {
        "model": MODEL_NAME,
        "biomarkers": [
            {
                "name": name,
                "description": description,
                "probability": probability,
                "threshold": threshold,
                "positive": probability >= threshold,
            }
            for name, description, probability, threshold in BIOMARKERS
        ],
    }
