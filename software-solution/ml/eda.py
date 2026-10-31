"""Exploratory data analysis of the prepared dataset.

Writes the report figures to documentation/figures/ and prints the summary
statistics quoted in the report.

Usage: python eda.py
"""

from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
import SimpleITK as sitk
from scipy import ndimage

matplotlib.use("Agg")
import matplotlib.pyplot as plt

DATA = Path(__file__).parent / "data"
FIGURES = Path(__file__).parents[2] / "documentation" / "figures"
STATUS = {1.0: "mutant", 0.0: "wildtype"}
COLORS = {"mutant": "#d1495b", "wildtype": "#30638e", "necunoscut": "#bbbbbb"}


def status(series: pd.Series) -> pd.Series:
    return series.map(STATUS).fillna("necunoscut")


def plot_labels(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(6, 3.2))
    rows = {name: status(df[col]).value_counts() for name, col in
            (("EGFR", "egfr"), ("KRAS", "kras"), ("ALK", "alk"))}
    left = np.zeros(3)
    for state in ("mutant", "wildtype", "necunoscut"):
        values = np.array([rows[n].get(state, 0) for n in rows])
        ax.barh(list(rows), values, left=left, color=COLORS[state], label=state)
        for y, (l, v) in enumerate(zip(left, values)):
            if v:
                ax.text(l + v / 2, y, str(v), ha="center", va="center", color="white", fontsize=9)
        left += values
    ax.set_xlabel("pacienți")
    ax.legend(loc="lower right", fontsize=8)
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(FIGURES / "eda_etichete.png", dpi=200)


def plot_clinical(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.2))
    for state in ("wildtype", "mutant"):
        ages = df.age[status(df.egfr) == state]
        axes[0].hist(ages, bins=np.arange(20, 95, 5), alpha=0.6, color=COLORS[state], label=f"EGFR {state}")
    axes[0].set_xlabel("vârstă (ani)")
    axes[0].set_ylabel("pacienți")
    axes[0].legend(fontsize=8)
    table = pd.crosstab(df.sex, status(df.egfr)).reindex(columns=["mutant", "wildtype"])
    share = table.div(table.sum(1), axis=0) * 100
    share.plot.bar(ax=axes[1], color=[COLORS["mutant"], COLORS["wildtype"]], rot=0)
    axes[1].set_ylabel("% din pacienți")
    axes[1].set_xlabel("sex")
    axes[1].legend(title="EGFR", fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGURES / "eda_clinic.png", dpi=200)


def tumor_stats(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for pid in df.patient_id:
        ct = sitk.GetArrayFromImage(sitk.ReadImage(str(DATA / "crops" / f"{pid}_ct.nii.gz")))
        mask = sitk.GetArrayFromImage(sitk.ReadImage(str(DATA / "crops" / f"{pid}_mask.nii.gz"))) > 0
        hu = ct[mask]
        rows.append({"patient_id": pid, "hu_mean": hu.mean(),
                     "solid_fraction": (hu > -300).mean(),
                     "ground_glass_fraction": ((hu > -800) & (hu <= -300)).mean()})
    return df.merge(pd.DataFrame(rows), on="patient_id")


def plot_tumor(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.2))
    specs = [("tumor_volume_ml", "volum tumoră (ml, log)", True),
             ("hu_mean", "densitate medie (HU)", False),
             ("ground_glass_fraction", "fracție sticlă mată", False)]
    for ax, (col, title, log) in zip(axes, specs):
        groups, names = [], []
        for marker in ("egfr", "kras"):
            for state in ("wildtype", "mutant"):
                groups.append(df[col][status(df[marker]) == state])
                names.append(f"{marker.upper()}\n{state}")
        box = ax.boxplot(groups, patch_artist=True, widths=0.6)
        for patch, name in zip(box["boxes"], names):
            patch.set_facecolor(COLORS[name.split("\n")[1]])
            patch.set_alpha(0.7)
        ax.set_xticks(range(1, 5), names, fontsize=8)
        ax.set_title(title, fontsize=10)
        if log:
            ax.set_yscale("log")
    fig.tight_layout()
    fig.savefig(FIGURES / "eda_tumora.png", dpi=200)


def plot_examples(df: pd.DataFrame) -> None:
    picks = (list(df[(df.egfr == 1) & (df.kras == 0)].patient_id[:2])
             + list(df[(df.kras == 1) & (df.egfr == 0)].patient_id[:2])
             + list(df[(df.egfr == 0) & (df.kras == 0)].patient_id[:2]))
    fig, axes = plt.subplots(1, len(picks), figsize=(2.2 * len(picks), 3.0))
    for ax, pid in zip(axes, picks):
        ct = sitk.GetArrayFromImage(sitk.ReadImage(str(DATA / "crops" / f"{pid}_ct.nii.gz")))
        mask = sitk.GetArrayFromImage(sitk.ReadImage(str(DATA / "crops" / f"{pid}_mask.nii.gz")))
        z = mask.sum(axis=(1, 2)).argmax()
        ax.imshow(np.clip(ct[z], -1350, 150), cmap="gray")
        ax.contour(mask[z], levels=[0.5], colors="#ffcc00", linewidths=1)
        row = df[df.patient_id == pid].iloc[0]
        ax.set_title(f"{pid}\nEGFR {STATUS.get(row.egfr, '?')}\nKRAS {STATUS.get(row.kras, '?')}", fontsize=7)
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(FIGURES / "eda_exemple.png", dpi=200)


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    df = tumor_stats(pd.read_csv(DATA / "labels.csv"))
    plot_labels(df)
    plot_clinical(df)
    plot_tumor(df)
    plot_examples(df)

    print("patients", len(df), "| age", df.age.describe().round(1).to_dict())
    print("sex", df.sex.value_counts().to_dict())
    print("histology", df.histology.value_counts().to_dict())
    print("smoking", df.smoking_status.value_counts().to_dict())
    print("EGFR & KRAS both mutant:", int(((df.egfr == 1) & (df.kras == 1)).sum()))
    print("tumor volume ml", df.tumor_volume_ml.describe().round(1).to_dict())
    print("slice thickness mm", df.spacing_z.value_counts().to_dict())
    print("pixel spacing mm", df.spacing_x.describe().round(2).to_dict())
    for marker in ("egfr", "kras"):
        print(f"\n{marker.upper()} mutant rate by group (%):")
        for col in ("sex", "smoking_status", "histology"):
            known = df[df[marker].notna()]
            print(" ", (known.groupby(col)[marker].agg(["mean", "count"])
                        .assign(mean=lambda t: (t["mean"] * 100).round(1))).to_dict("index"))
        known = df[df[marker].notna()]
        for col in ("age", "tumor_volume_ml", "hu_mean", "ground_glass_fraction"):
            print(f"  {col}: median mutant {known[col][known[marker] == 1].median():.2f} "
                  f"vs wildtype {known[col][known[marker] == 0].median():.2f}")
    print(f"\nfigures written to {FIGURES}")


if __name__ == "__main__":
    main()
