"""Variant 1: handcrafted tumor features + logistic regression.

A few simple numbers are measured on each tumor (size, shape, density) and fed,
together with age and sex, to one logistic regression per biomarker.

Usage: python variant1_features.py
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import SimpleITK as sitk
from scipy import ndimage
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

DATA = Path(__file__).parent / "data"
OUT = Path(__file__).parent / "results" / "variant1_features"
LABELS = ["egfr", "kras"]
SEED = 42


def tumor_features(pid: str) -> dict:
    ct = sitk.GetArrayFromImage(sitk.ReadImage(str(DATA / "crops" / f"{pid}_ct.nii.gz")))
    mask = sitk.GetArrayFromImage(sitk.ReadImage(str(DATA / "crops" / f"{pid}_mask.nii.gz"))) > 0
    hu = ct[mask].astype(float)
    volume = mask.sum()
    surface = (mask & ~ndimage.binary_erosion(mask)).sum()
    extent = np.ptp(np.argwhere(mask), axis=0) + 1
    return {
        "volume_ml": volume / 1000,
        "diameter_mm": extent.max(),
        "compactness": volume / max(surface, 1),
        "hu_mean": hu.mean(),
        "hu_std": hu.std(),
        "solid_fraction": (hu > -300).mean(),
        "ground_glass_fraction": ((hu > -800) & (hu <= -300)).mean(),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(DATA / "labels.csv")
    feats = pd.DataFrame([tumor_features(p) for p in df.patient_id])
    df = pd.concat([df, feats], axis=1)
    df["sex_m"] = (df.sex == "M").astype(int)
    columns = list(feats.columns) + ["age", "sex_m"]

    strat = df.egfr.fillna(-1).astype(str) + df.kras.fillna(-1).astype(str)
    strat = strat.where(strat.map(strat.value_counts()) >= 5, "rare")
    train, test = train_test_split(df, test_size=0.2, stratify=strat, random_state=SEED)

    results, preds = {}, test[["patient_id", "age", "sex"] + LABELS].copy()
    for label in LABELS:
        tr, te = train[train[label].notna()], test[test[label].notna()]
        model = make_pipeline(StandardScaler(),
                              LogisticRegression(C=0.5, class_weight="balanced", max_iter=1000))
        model.fit(tr[columns], tr[label])
        prob = model.predict_proba(te[columns])[:, 1]
        pred = (prob >= 0.5).astype(int)
        y = te[label].astype(int)
        results[label] = {
            "auc": roc_auc_score(y, prob),
            "accuracy": accuracy_score(y, pred),
            "sensitivity": recall_score(y, pred, zero_division=0),
            "specificity": recall_score(1 - y, 1 - pred, zero_division=0),
            "test_patients": len(y),
            "test_positives": int(y.sum()),
            "coefficients": dict(zip(columns, model[-1].coef_[0].round(3))),
        }
        preds.loc[te.index, f"{label}_prob"] = prob
        print(f"{label.upper()}: AUC {results[label]['auc']:.3f}  "
              f"accuracy {results[label]['accuracy']:.3f}  "
              f"sens {results[label]['sensitivity']:.2f}  spec {results[label]['specificity']:.2f}")

    preds.to_csv(OUT / "test_predictions.csv", index=False)
    (OUT / "metrics.json").write_text(json.dumps(results, indent=2, default=float))


if __name__ == "__main__":
    main()
