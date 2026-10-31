"""Variant 2: small 3D CNN trained from scratch.

The network looks at a 64 mm cube centred on the tumor at full 1 mm resolution
(CT + tumor mask as two channels) and learns its own features. Age and sex are added before the last
layer. One network predicts both biomarkers at once (multi-label).

Usage: python variant2_cnn3d.py
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import SimpleITK as sitk
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.metrics import accuracy_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split

DATA = Path(__file__).parent / "data"
OUT = Path(__file__).parent / "results" / "variant2_cnn3d"
LABELS = ["egfr", "kras"]
SEED = 42
SIZE = 64
EPOCHS = 60
BATCH = 8
LR = 3e-4


def load(pid: str) -> torch.Tensor:
    ct = sitk.GetArrayFromImage(sitk.ReadImage(str(DATA / "crops" / f"{pid}_ct.nii.gz"))).astype(np.float32)
    mask = sitk.GetArrayFromImage(sitk.ReadImage(str(DATA / "crops" / f"{pid}_mask.nii.gz"))).astype(np.float32)
    ct = (np.clip(ct, -1000, 400) + 1000) / 1400
    start = (ct.shape[0] - SIZE) // 2
    cube = slice(start, start + SIZE)
    return torch.from_numpy(np.stack([ct, mask])[:, cube, cube, cube].copy())


def tensors(frame: pd.DataFrame, volumes: dict):
    x = torch.stack([volumes[p] for p in frame.patient_id])
    clin = torch.tensor(np.c_[(frame.age - 68) / 10, frame.sex == "M"], dtype=torch.float32)
    y = torch.tensor(frame[LABELS].to_numpy(np.float32))
    return x, clin, y


class SmallCNN(nn.Module):
    def __init__(self):
        super().__init__()
        def block(cin, cout):
            return nn.Sequential(nn.Conv3d(cin, cout, 3, padding=1), nn.BatchNorm3d(cout),
                                 nn.ReLU(), nn.MaxPool3d(2))
        self.features = nn.Sequential(block(2, 8), block(8, 16), block(16, 32))
        self.head = nn.Sequential(nn.Dropout(0.5), nn.Linear(32 + 2, len(LABELS)))

    def forward(self, x, clin):
        x = self.features(x).mean(dim=(2, 3, 4))
        return self.head(torch.cat([x, clin], 1))


def masked_loss(logits, y, pos_weight):
    known = ~torch.isnan(y)
    loss = F.binary_cross_entropy_with_logits(logits, torch.nan_to_num(y), pos_weight=pos_weight,
                                              reduction="none")
    return (loss * known).sum() / known.sum()


def macro_auc(y: np.ndarray, prob: np.ndarray) -> float:
    aucs = []
    for k in range(y.shape[1]):
        known = ~np.isnan(y[:, k])
        aucs.append(roc_auc_score(y[known, k], prob[known, k]))
    return float(np.mean(aucs))


def main() -> None:
    torch.manual_seed(SEED)
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(DATA / "labels.csv")
    strat = df.egfr.fillna(-1).astype(str) + df.kras.fillna(-1).astype(str)
    strat = strat.where(strat.map(strat.value_counts()) >= 5, "rare")
    trainval, test = train_test_split(df, test_size=0.2, stratify=strat, random_state=SEED)
    train, val = train_test_split(trainval, test_size=0.2, stratify=strat[trainval.index],
                                  random_state=SEED)

    volumes = {p: load(p) for p in df.patient_id}
    xtr, ctr, ytr = tensors(train, volumes)
    xva, cva, yva = tensors(val, volumes)
    xte, cte, yte = tensors(test, volumes)
    pos = torch.nansum(ytr, 0)
    pos_weight = (torch.sum(~torch.isnan(ytr), 0) - pos) / pos.clamp(min=1)

    model = SmallCNN()
    opt = torch.optim.Adam(model.parameters(), lr=LR, weight_decay=1e-3)
    best = -1.0
    for epoch in range(EPOCHS):
        model.train()
        order = torch.randperm(len(xtr))
        for i in range(0, len(order), BATCH):
            idx = order[i:i + BATCH]
            x = xtr[idx]
            if torch.rand(1) < 0.5:
                x = torch.flip(x, (4,))
            if torch.rand(1) < 0.5:
                x = torch.flip(x, (3,))
            x = torch.rot90(x, int(torch.randint(4, (1,))), (3, 4))
            loss = masked_loss(model(x, ctr[idx]), ytr[idx], pos_weight)
            opt.zero_grad()
            loss.backward()
            opt.step()
        model.eval()
        with torch.no_grad():
            logits = model(xva, cva)
        val_loss = masked_loss(logits, yva, pos_weight).item()
        val_auc = macro_auc(yva.numpy(), torch.sigmoid(logits).numpy())
        if val_auc >= best:
            best = val_auc
            torch.save(model.state_dict(), OUT / "model.pt")
        print(f"epoch {epoch + 1:2d}  val loss {val_loss:.3f}  val AUC {val_auc:.3f}  best {best:.3f}")

    model.load_state_dict(torch.load(OUT / "model.pt"))
    model.eval()
    with torch.no_grad():
        prob = torch.sigmoid(model(xte, cte)).numpy()

    results, preds = {}, test[["patient_id", "age", "sex"] + LABELS].reset_index(drop=True)
    for k, label in enumerate(LABELS):
        known = ~np.isnan(yte[:, k].numpy())
        y, p = yte[known, k].numpy().astype(int), prob[known, k]
        pred = (p >= 0.5).astype(int)
        results[label] = {
            "auc": roc_auc_score(y, p),
            "accuracy": accuracy_score(y, pred),
            "sensitivity": recall_score(y, pred, zero_division=0),
            "specificity": recall_score(1 - y, 1 - pred, zero_division=0),
            "test_patients": int(known.sum()),
            "test_positives": int(y.sum()),
        }
        preds[f"{label}_prob"] = prob[:, k]
        print(f"{label.upper()}: AUC {results[label]['auc']:.3f}  "
              f"accuracy {results[label]['accuracy']:.3f}  "
              f"sens {results[label]['sensitivity']:.2f}  spec {results[label]['specificity']:.2f}")

    preds.to_csv(OUT / "test_predictions.csv", index=False)
    (OUT / "metrics.json").write_text(json.dumps(results, indent=2, default=float))


if __name__ == "__main__":
    main()
