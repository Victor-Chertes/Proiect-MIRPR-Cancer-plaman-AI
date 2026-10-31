"""Variant 3: transfer learning with a frozen ImageNet ResNet-18.

The axial slice with the largest tumor area is turned into an RGB image
(lung window, soft-tissue window, tumor mask). A ResNet-18 pre-trained on
ImageNet, used without any re-training, turns that image into 512 features.
Those features plus age and sex go into one logistic regression per biomarker.

Usage: python variant3_resnet.py
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import SimpleITK as sitk
import torch
import torch.nn.functional as F
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from torchvision.models import ResNet18_Weights, resnet18

DATA = Path(__file__).parent / "data"
OUT = Path(__file__).parent / "results" / "variant3_resnet"
LABELS = ["egfr", "kras"]
SEED = 42
MEAN = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
STD = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)


def window(ct: np.ndarray, low: float, high: float) -> np.ndarray:
    return np.clip((ct - low) / (high - low), 0, 1)


def tumor_slice(pid: str) -> torch.Tensor:
    ct = sitk.GetArrayFromImage(sitk.ReadImage(str(DATA / "crops" / f"{pid}_ct.nii.gz"))).astype(np.float32)
    mask = sitk.GetArrayFromImage(sitk.ReadImage(str(DATA / "crops" / f"{pid}_mask.nii.gz"))).astype(np.float32)
    z = mask.sum(axis=(1, 2)).argmax()
    rgb = np.stack([window(ct[z], -1350, 150), window(ct[z], -160, 240), mask[z]])
    img = F.interpolate(torch.from_numpy(rgb)[None], size=(224, 224), mode="bilinear")[0]
    return (img - MEAN) / STD


@torch.no_grad()
def embed(ids) -> np.ndarray:
    net = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)
    net.fc = torch.nn.Identity()
    net.eval()
    images = torch.stack([tumor_slice(p) for p in ids])
    return torch.cat([net(images[i:i + 32]) for i in range(0, len(images), 32)]).numpy()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(DATA / "labels.csv")
    features = embed(df.patient_id)
    clinical = np.c_[df.age, df.sex == "M"].astype(float)
    X = np.hstack([features, clinical])

    strat = df.egfr.fillna(-1).astype(str) + df.kras.fillna(-1).astype(str)
    strat = strat.where(strat.map(strat.value_counts()) >= 5, "rare")
    train, test = train_test_split(df.index, test_size=0.2, stratify=strat, random_state=SEED)

    results, preds = {}, df.loc[test, ["patient_id", "age", "sex"] + LABELS].copy()
    for label in LABELS:
        tr = [i for i in train if not np.isnan(df.at[i, label])]
        te = [i for i in test if not np.isnan(df.at[i, label])]
        model = make_pipeline(StandardScaler(), PCA(n_components=16, random_state=SEED),
                              LogisticRegression(C=0.1, class_weight="balanced", max_iter=1000))
        model.fit(X[tr], df.loc[tr, label])
        prob = model.predict_proba(X[te])[:, 1]
        pred = (prob >= 0.5).astype(int)
        y = df.loc[te, label].astype(int)
        results[label] = {
            "auc": roc_auc_score(y, prob),
            "accuracy": accuracy_score(y, pred),
            "sensitivity": recall_score(y, pred, zero_division=0),
            "specificity": recall_score(1 - y, 1 - pred, zero_division=0),
            "test_patients": len(y),
            "test_positives": int(y.sum()),
        }
        preds.loc[te, f"{label}_prob"] = prob
        print(f"{label.upper()}: AUC {results[label]['auc']:.3f}  "
              f"accuracy {results[label]['accuracy']:.3f}  "
              f"sens {results[label]['sensitivity']:.2f}  spec {results[label]['specificity']:.2f}")

    preds.to_csv(OUT / "test_predictions.csv", index=False)
    (OUT / "metrics.json").write_text(json.dumps(results, indent=2, default=float))


if __name__ == "__main__":
    main()
