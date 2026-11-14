"""Stage 3: every model on real data, one shared experimental protocol.

Datasets
  stage2  the 119 patients with an expert tumor segmentation used in stage 2
  full    stage2 + the patients whose mask comes from the IDC AI PET segmentation
          (prepare_dataset.py --extend)

Protocol (identical for every model and both datasets)
  * one held-out test set (20 %), drawn once on the full dataset, stratified on
    EGFR/KRAS status and mask source; the stage2 dataset uses its expert-mask part,
    so both datasets are tested on overlapping patients and never trained on them
  * hyper-parameters are chosen by 5-fold stratified cross-validation (AUC) on the
    training part only
  * the decision threshold is chosen on the training part (Youden index on
    out-of-fold predictions), not fixed at 0.5
  * test metrics: AUC with a 95 % bootstrap interval, accuracy, balanced accuracy,
    sensitivity, specificity, F1 and Brier score
  * as a second, less noisy estimate: 5 x 5 repeated stratified cross-validation
    over the whole dataset (hyper-parameters re-tuned inside every fold)

Models
  clinical   logistic regression on age + sex only (baseline asked for in the report)
  radiomic   variant 1: hand-crafted tumor features + age + sex, logistic regression
  cnn3d      variant 2: small 3D CNN trained from scratch (CT + mask, age, sex)
  resnet2d   variant 3: frozen ImageNet ResNet-18 on the largest tumor slice
  fmcib      transfer learning from FMCIB, a 3D ResNet-50 foundation model
             pre-trained on 11,467 CT lesions (Pai et al., Nature Machine
             Intelligence 2024); frozen 4096-d features + age + sex, logistic regression

Usage: python stage3.py [--models clinical radiomic ...] [--datasets stage2 full] [--no-cnn-cv]
"""

import argparse
import json
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
import SimpleITK as sitk
import torch
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, brier_score_loss, f1_score,
                             recall_score, roc_auc_score, roc_curve)
from sklearn.model_selection import (GridSearchCV, RepeatedStratifiedKFold, StratifiedKFold,
                                     cross_val_predict, train_test_split)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

import variant1_features
import variant2_cnn3d
import variant3_resnet

ML = Path(__file__).parent
DATA = ML / "data"
OUT = ML / "results" / "stage3"
CACHE = OUT / "features"
WEIGHTS = ML / "weights" / "fmcib.torch"
FMCIB_URL = "https://zenodo.org/records/10528450/files/model_weights.torch?download=1"
LABELS = ["egfr", "kras"]
SEED = 42
TEST_SIZE = 0.2
CV_FOLDS = 5
CV_REPEATS = 5
BOOTSTRAP = 2000
CNN_SEEDS = 3

# Hyper-parameter grids searched by inner cross-validation (logistic models).
GRIDS = {
    "clinical": {"clf__C": [0.01, 0.1, 1.0]},
    "radiomic": {"clf__C": [0.01, 0.1, 0.5, 1.0, 10.0]},
    "resnet2d": {"pca__n_components": [8, 16, 32], "clf__C": [0.01, 0.1, 1.0]},
    "fmcib": {"pca__n_components": [8, 16, 32], "clf__C": [0.01, 0.1, 1.0]},
}
USES_PCA = {"resnet2d", "fmcib"}


# ---------------------------------------------------------------- data

def load_dataset() -> pd.DataFrame:
    df = pd.read_csv(DATA / "labels.csv")
    if "mask_source" not in df:
        df["mask_source"] = "expert"
    df["sex_m"] = (df.sex == "M").astype(float)
    return df


def split(df: pd.DataFrame) -> pd.Series:
    """True for the held-out test patients (drawn once, on the full dataset)."""
    strat = df.egfr.fillna(-1).astype(str) + df.kras.fillna(-1).astype(str) + df.mask_source
    strat = strat.where(strat.map(strat.value_counts()) >= 5, "rare")
    _, test = train_test_split(df.index, test_size=TEST_SIZE, stratify=strat, random_state=SEED)
    return df.index.isin(test)


def subset(df: pd.DataFrame, name: str) -> pd.DataFrame:
    return df if name == "full" else df[df.mask_source == "expert"]


# ---------------------------------------------------------------- features

def fmcib_model():
    from monai.networks.nets import resnet50
    if not WEIGHTS.exists():
        WEIGHTS.parent.mkdir(parents=True, exist_ok=True)
        print("downloading FMCIB weights (738 MB) ...")
        urllib.request.urlretrieve(FMCIB_URL, WEIGHTS)
    checkpoint = torch.load(WEIGHTS, map_location="cpu", weights_only=False)
    state = checkpoint.get("trunk_state_dict") or {
        k.replace("model.backbone.", ""): v for k, v in checkpoint["state_dict"].items()}
    model = resnet50(pretrained=False, n_input_channels=1, widen_factor=2, conv1_t_stride=2,
                     feed_forward=False)
    model.load_state_dict(state, strict=False)
    return model.eval()


def fmcib_input(pid: str) -> torch.Tensor:
    """50 mm cube around the tumor centre, scaled like FMCIB's own preprocessing."""
    ct = sitk.GetArrayFromImage(sitk.ReadImage(str(DATA / "crops" / f"{pid}_ct.nii.gz")))
    start = (ct.shape[0] - 50) // 2
    cube = ct[start:start + 50, start:start + 50, start:start + 50].astype(np.float32)
    return torch.from_numpy(np.clip((cube + 1024) / 4096, 0, 1))[None]


@torch.no_grad()
def fmcib_features(ids) -> np.ndarray:
    model = fmcib_model()
    out = []
    for i in range(0, len(ids), 8):
        out.append(model(torch.stack([fmcib_input(p) for p in ids[i:i + 8]])).numpy())
    return np.concatenate(out)


def image_features(model: str, ids: pd.Series) -> pd.DataFrame:
    """Per-patient image features, cached so every run reuses them."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{model}.csv"
    cached = pd.read_csv(path, index_col=0) if path.exists() else pd.DataFrame()
    missing = [p for p in ids if p not in cached.index]
    if missing:
        print(f"{model}: extracting features for {len(missing)} patients")
        if model == "radiomic":
            new = pd.DataFrame([variant1_features.tumor_features(p) for p in missing], index=missing)
        elif model == "resnet2d":
            new = pd.DataFrame(variant3_resnet.embed(missing), index=missing)
        else:
            new = pd.DataFrame(fmcib_features(missing), index=missing)
        new.columns = new.columns.astype(str)
        cached = pd.concat([cached, new])
        cached.to_csv(path)
    return cached.loc[list(ids)]


def design_matrix(model: str, df: pd.DataFrame) -> np.ndarray:
    clinical = df[["age", "sex_m"]].to_numpy(float)
    if model == "clinical":
        return clinical
    return np.hstack([image_features(model, df.patient_id).to_numpy(float), clinical])


# ---------------------------------------------------------------- metrics

def youden(y, prob) -> float:
    fpr, tpr, thr = roc_curve(y, prob)
    return float(np.clip(thr[np.argmax(tpr - fpr)], 0, 1))


def metrics(y, prob, threshold: float) -> dict:
    y, prob = np.asarray(y, int), np.asarray(prob, float)
    pred = (prob >= threshold).astype(int)
    rng = np.random.default_rng(SEED)
    boot = []
    for _ in range(BOOTSTRAP):
        idx = rng.integers(0, len(y), len(y))
        if 0 < y[idx].sum() < len(idx):
            boot.append(roc_auc_score(y[idx], prob[idx]))
    return {
        "auc": roc_auc_score(y, prob),
        "auc_ci95": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
        "accuracy": accuracy_score(y, pred),
        "balanced_accuracy": balanced_accuracy_score(y, pred),
        "sensitivity": recall_score(y, pred, zero_division=0),
        "specificity": recall_score(1 - y, 1 - pred, zero_division=0),
        "f1": f1_score(y, pred, zero_division=0),
        "brier": brier_score_loss(y, prob),
        "threshold": threshold,
        "patients": len(y),
        "positives": int(y.sum()),
    }


# ---------------------------------------------------------------- logistic models

def pipeline(model: str) -> Pipeline:
    steps = [("scale", StandardScaler())]
    if model in USES_PCA:
        steps.append(("pca", PCA(random_state=SEED)))
    steps.append(("clf", LogisticRegression(class_weight="balanced", max_iter=5000)))
    return Pipeline(steps)


def fit_logistic(model: str, X, y, seed=SEED):
    inner = StratifiedKFold(CV_FOLDS, shuffle=True, random_state=seed)
    search = GridSearchCV(pipeline(model), GRIDS[model], scoring="roc_auc", cv=inner)
    search.fit(X, y)
    oof = cross_val_predict(search.best_estimator_, X, y, cv=inner, method="predict_proba")[:, 1]
    return search.best_estimator_, search.best_params_, youden(y, oof)


def run_logistic(model: str, train: pd.DataFrame, test: pd.DataFrame):
    Xtr, Xte = design_matrix(model, train), design_matrix(model, test)
    results, probs, params = {}, {}, {}
    for label in LABELS:
        tr, te = train[label].notna().to_numpy(), test[label].notna().to_numpy()
        est, best, thr = fit_logistic(model, Xtr[tr], train[label][tr].astype(int))
        prob = est.predict_proba(Xte[te])[:, 1]
        results[label] = metrics(test[label][te], prob, thr)
        probs[label] = pd.Series(prob, index=test.index[te])
        params[label] = best
    return results, probs, params


def repeated_cv_logistic(model: str, df: pd.DataFrame) -> dict:
    X = design_matrix(model, df)
    out = {}
    for label in LABELS:
        known = df[label].notna().to_numpy()
        Xk, yk = X[known], df[label][known].astype(int).to_numpy()
        aucs = []
        outer = RepeatedStratifiedKFold(n_splits=CV_FOLDS, n_repeats=CV_REPEATS, random_state=SEED)
        for i, (a, b) in enumerate(outer.split(Xk, yk)):
            est, _, _ = fit_logistic(model, Xk[a], yk[a], seed=i)
            aucs.append(roc_auc_score(yk[b], est.predict_proba(Xk[b])[:, 1]))
        out[label] = {"auc_mean": float(np.mean(aucs)), "auc_std": float(np.std(aucs)),
                      "folds": len(aucs)}
    return out


# ---------------------------------------------------------------- 3D CNN

def train_cnn(train: pd.DataFrame, volumes: dict, seed: int):
    """Stage-2 training loop: Adam, flips/rotations, early stopping on a validation split."""
    torch.manual_seed(seed)
    strat = train.egfr.fillna(-1).astype(str) + train.kras.fillna(-1).astype(str)
    strat = strat.where(strat.map(strat.value_counts()) >= 5, "rare")
    tr, va = train_test_split(train, test_size=0.2, stratify=strat, random_state=seed)
    xtr, ctr, ytr = variant2_cnn3d.tensors(tr, volumes)
    xva, cva, yva = variant2_cnn3d.tensors(va, volumes)
    pos = torch.nansum(ytr, 0)
    pos_weight = (torch.sum(~torch.isnan(ytr), 0) - pos) / pos.clamp(min=1)
    model = variant2_cnn3d.SmallCNN()
    opt = torch.optim.Adam(model.parameters(), lr=variant2_cnn3d.LR, weight_decay=1e-3)
    best, best_state = -1.0, None
    for _ in range(variant2_cnn3d.EPOCHS):
        model.train()
        order = torch.randperm(len(xtr))
        for i in range(0, len(order), variant2_cnn3d.BATCH):
            idx = order[i:i + variant2_cnn3d.BATCH]
            x = xtr[idx]
            if torch.rand(1) < 0.5:
                x = torch.flip(x, (4,))
            if torch.rand(1) < 0.5:
                x = torch.flip(x, (3,))
            x = torch.rot90(x, int(torch.randint(4, (1,))), (3, 4))
            loss = variant2_cnn3d.masked_loss(model(x, ctr[idx]), ytr[idx], pos_weight)
            opt.zero_grad()
            loss.backward()
            opt.step()
        model.eval()
        with torch.no_grad():
            val_prob = torch.sigmoid(model(xva, cva)).numpy()
        val_auc = variant2_cnn3d.macro_auc(yva.numpy(), val_prob)
        if val_auc >= best:
            best = val_auc
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
            best_val = val_prob
    model.load_state_dict(best_state)
    model.eval()
    return model, va, best_val


def run_cnn(train: pd.DataFrame, test: pd.DataFrame, volumes: dict):
    """Average of CNN_SEEDS networks; threshold from their validation predictions."""
    xte, cte, _ = variant2_cnn3d.tensors(test, volumes)
    test_prob, val_rows = [], []
    for seed in range(CNN_SEEDS):
        model, va, val_prob = train_cnn(train, volumes, SEED + seed)
        with torch.no_grad():
            test_prob.append(torch.sigmoid(model(xte, cte)).numpy())
        val_rows.append((va, val_prob))
    test_prob = np.mean(test_prob, 0)
    results, probs = {}, {}
    for k, label in enumerate(LABELS):
        yv = np.concatenate([va[label].to_numpy() for va, _ in val_rows])
        pv = np.concatenate([p[:, k] for _, p in val_rows])
        known = ~np.isnan(yv)
        thr = youden(yv[known].astype(int), pv[known])
        te = test[label].notna().to_numpy()
        results[label] = metrics(test[label][te], test_prob[te, k], thr)
        probs[label] = pd.Series(test_prob[te, k], index=test.index[te])
    params = {"epochs": variant2_cnn3d.EPOCHS, "batch": variant2_cnn3d.BATCH,
              "lr": variant2_cnn3d.LR, "weight_decay": 1e-3, "dropout": 0.5,
              "input": f"{variant2_cnn3d.SIZE}^3 mm CT + mask", "ensemble_seeds": CNN_SEEDS}
    return results, probs, params


def repeated_cv_cnn(df: pd.DataFrame, volumes: dict) -> dict:
    """Single 5-fold CV (one seed per fold) — a full 5 x 5 is too slow on CPU."""
    strat = df.egfr.fillna(-1).astype(str) + df.kras.fillna(-1).astype(str)
    strat = strat.where(strat.map(strat.value_counts()) >= 5, "rare")
    aucs = {label: [] for label in LABELS}
    for i, (a, b) in enumerate(StratifiedKFold(CV_FOLDS, shuffle=True, random_state=SEED)
                               .split(df, strat)):
        model, _, _ = train_cnn(df.iloc[a], volumes, SEED + i)
        x, c, _ = variant2_cnn3d.tensors(df.iloc[b], volumes)
        with torch.no_grad():
            prob = torch.sigmoid(model(x, c)).numpy()
        for k, label in enumerate(LABELS):
            y = df.iloc[b][label].to_numpy()
            known = ~np.isnan(y)
            aucs[label].append(roc_auc_score(y[known].astype(int), prob[known, k]))
    return {label: {"auc_mean": float(np.mean(v)), "auc_std": float(np.std(v)), "folds": len(v)}
            for label, v in aucs.items()}


# ---------------------------------------------------------------- main

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+",
                        default=["clinical", "radiomic", "cnn3d", "resnet2d", "fmcib"])
    parser.add_argument("--datasets", nargs="+", default=["stage2", "full"])
    parser.add_argument("--no-cv", action="store_true", help="skip the repeated cross-validation")
    parser.add_argument("--no-cnn-cv", action="store_true",
                        help="skip cross-validation for the CNN only (slow on CPU)")
    args = parser.parse_args()

    df = load_dataset()
    df["test"] = split(df)
    OUT.mkdir(parents=True, exist_ok=True)
    df[["patient_id", "mask_source", "test"]].to_csv(OUT / "split.csv", index=False)
    volumes = None

    for name in args.datasets:
        data = subset(df, name).reset_index(drop=True)
        train, test = data[~data.test], data[data.test]
        print(f"\n=== dataset {name}: {len(train)} train / {len(test)} test patients")
        for model in args.models:
            out = OUT / name / model
            out.mkdir(parents=True, exist_ok=True)
            if model == "cnn3d":
                volumes = volumes or {p: variant2_cnn3d.load(p) for p in df.patient_id}
                results, probs, params = run_cnn(train, test, volumes)
                cv = None if args.no_cv or args.no_cnn_cv else repeated_cv_cnn(data, volumes)
            else:
                results, probs, params = run_logistic(model, train, test)
                cv = None if args.no_cv else repeated_cv_logistic(model, data)

            preds = test[["patient_id", "mask_source", "age", "sex"] + LABELS].copy()
            for label in LABELS:
                preds[f"{label}_prob"] = probs[label]
            preds.to_csv(out / "test_predictions.csv", index=False)
            (out / "metrics.json").write_text(json.dumps(
                {"test": results, "repeated_cv": cv, "hyperparameters": params},
                indent=2, default=float))
            for label in LABELS:
                r = results[label]
                extra = f"  CV AUC {cv[label]['auc_mean']:.3f}±{cv[label]['auc_std']:.3f}" if cv else ""
                print(f"{model:9s} {label.upper():4s} AUC {r['auc']:.3f} "
                      f"[{r['auc_ci95'][0]:.2f}-{r['auc_ci95'][1]:.2f}]  "
                      f"sens {r['sensitivity']:.2f} spec {r['specificity']:.2f} "
                      f"F1 {r['f1']:.2f}{extra}", flush=True)

    summarise()


def summarise() -> None:
    """One table with every dataset x model x label, read back from metrics.json."""
    rows = []
    for path in sorted(OUT.glob("*/*/metrics.json")):
        data = json.loads(path.read_text())
        for label, r in data["test"].items():
            cv = (data.get("repeated_cv") or {}).get(label, {})
            rows.append({"dataset": path.parts[-3], "model": path.parts[-2], "label": label,
                         **{k: v for k, v in r.items() if k != "auc_ci95"},
                         "auc_ci_low": r["auc_ci95"][0], "auc_ci_high": r["auc_ci95"][1],
                         "cv_auc_mean": cv.get("auc_mean"), "cv_auc_std": cv.get("auc_std")})
    pd.DataFrame(rows).round(3).to_csv(OUT / "summary.csv", index=False)
    print(f"\nsummary written to {OUT / 'summary.csv'}")


if __name__ == "__main__":
    main()
