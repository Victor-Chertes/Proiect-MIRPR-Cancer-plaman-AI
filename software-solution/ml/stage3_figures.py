"""Figures for the stage-3 chapter of the report (run after stage3.py).

  stage3_auc.png       test AUC (95 % CI) and repeated-CV AUC, stage-2 vs full dataset
  stage3_roc.png       ROC curves of every model on the full-dataset test set
  stage3_exemple.png   correctly and wrongly predicted test patients (best EGFR model)

Usage: python stage3_figures.py [--best fmcib]
"""

import argparse
import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
import SimpleITK as sitk
from sklearn.metrics import roc_curve

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ML = Path(__file__).parent
RESULTS = ML / "results" / "stage3"
CROPS = ML / "data" / "crops"
FIGURES = ML.parents[1] / "documentation" / "figures"
MODELS = ["clinical", "radiomic", "cnn3d", "resnet2d", "fmcib"]
NAMES = {"clinical": "vârstă + sex", "radiomic": "V1 radiomic", "cnn3d": "V2 CNN 3D",
         "resnet2d": "V3 ResNet-18 2D", "fmcib": "V4 FMCIB"}
DATASETS = {"stage2": ("set etapa 2", "#2a78d6"), "full": ("set complet", "#eb6834")}
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
INK, MUTED, GRID = "#1f1f1e", "#6b6a63", "#e4e3dd"

plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False,
                     "axes.spines.right": False})


def load(dataset: str, model: str):
    path = RESULTS / dataset / model / "metrics.json"
    return json.loads(path.read_text()) if path.exists() else None


def plot_auc() -> None:
    models = [m for m in MODELS if load("full", m)]
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4), sharey=True)
    for ax, label in zip(axes, ["egfr", "kras"]):
        for d, (dataset, (name, color)) in enumerate(DATASETS.items()):
            for m, model in enumerate(models):
                r = load(dataset, model)
                if not r:
                    continue
                y = m + (d - 0.5) * 0.3
                t = r["test"][label]
                ax.plot(t["auc_ci95"], [y, y], color=color, lw=2, alpha=0.45, solid_capstyle="round")
                ax.plot(t["auc"], y, "o", ms=8, color=color, mec="white", mew=2,
                        label=f"{name}: test (IÎ 95%)" if m == 0 else None)
                cv = (r.get("repeated_cv") or {}).get(label)
                if cv:
                    ax.plot(cv["auc_mean"], y, "D", ms=6, mfc="white", mec=color, mew=2,
                            label=f"{name}: validare încrucișată" if m == 0 else None)
        ax.axvline(0.5, color=MUTED, lw=1, ls="--")
        ax.set_xlim(0.1, 1.0)
        ax.set_yticks(range(len(models)), [NAMES[m] for m in models])
        ax.invert_yaxis()
        ax.set_title(label.upper(), color=INK, fontsize=10, loc="left")
        ax.set_xlabel("AUC")
        ax.grid(axis="x", color=GRID, lw=0.8)
        ax.set_axisbelow(True)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, frameon=False, fontsize=8)
    fig.tight_layout(rect=(0, 0.1, 1, 1))
    fig.savefig(FIGURES / "stage3_auc.png", dpi=200)


def plot_roc() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.8))
    for ax, label in zip(axes, ["egfr", "kras"]):
        for model, color in zip(MODELS, SERIES):
            path = RESULTS / "full" / model / "test_predictions.csv"
            if not path.exists():
                continue
            p = pd.read_csv(path).dropna(subset=[label, f"{label}_prob"])
            fpr, tpr, _ = roc_curve(p[label].astype(int), p[f"{label}_prob"])
            auc = load("full", model)["test"][label]["auc"]
            ax.plot(fpr, tpr, color=color, lw=2, label=f"{NAMES[model]} ({auc:.2f})")
        ax.plot([0, 1], [0, 1], color=MUTED, lw=1, ls="--")
        ax.set_title(label.upper(), color=INK, fontsize=10, loc="left")
        ax.set_xlabel("1 − specificitate")
        ax.set_ylabel("sensibilitate")
        ax.set_aspect("equal")
        ax.legend(fontsize=7, frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(FIGURES / "stage3_roc.png", dpi=200)


def plot_examples(model: str) -> None:
    """Two true positives, two true negatives, one false positive, one false negative."""
    r = load("full", model)["test"]["egfr"]
    p = pd.read_csv(RESULTS / "full" / model / "test_predictions.csv").dropna(subset=["egfr"])
    p["pred"] = (p.egfr_prob >= r["threshold"]).astype(int)
    cases = []
    for (truth, pred), n, title in [((1, 1), 2, "corect: mutant"), ((0, 0), 2, "corect: wildtype"),
                                    ((0, 1), 1, "greșit: fals pozitiv"),
                                    ((1, 0), 1, "greșit: fals negativ")]:
        group = p[(p.egfr == truth) & (p.pred == pred)]
        # the most confident examples of each kind
        group = group.sort_values("egfr_prob", ascending=(pred == 0))
        cases += [(row, title) for _, row in group.head(n).iterrows()]
    fig, axes = plt.subplots(1, len(cases), figsize=(2.1 * len(cases), 2.9))
    for ax, (row, title) in zip(np.atleast_1d(axes), cases):
        ct = sitk.GetArrayFromImage(sitk.ReadImage(str(CROPS / f"{row.patient_id}_ct.nii.gz")))
        mask = sitk.GetArrayFromImage(sitk.ReadImage(str(CROPS / f"{row.patient_id}_mask.nii.gz")))
        z = mask.sum(axis=(1, 2)).argmax()
        ax.imshow(np.clip(ct[z], -1350, 150), cmap="gray")
        ax.contour(mask[z], levels=[0.5], colors="#ffcc00", linewidths=1)
        ax.set_title(f"{title}\n{row.patient_id} · P(EGFR+) = {row.egfr_prob:.2f}",
                     fontsize=7, color=INK)
        ax.axis("off")
    fig.suptitle(f"{NAMES[model]}, prag {r['threshold']:.2f}", fontsize=8, color=MUTED, y=0.02)
    fig.tight_layout()
    fig.savefig(FIGURES / "stage3_exemple.png", dpi=200)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--best", default="fmcib", help="model used for the example figure")
    args = parser.parse_args()
    FIGURES.mkdir(parents=True, exist_ok=True)
    plot_auc()
    plot_roc()
    plot_examples(args.best)
    print(f"figures written to {FIGURES}")


if __name__ == "__main__":
    main()
