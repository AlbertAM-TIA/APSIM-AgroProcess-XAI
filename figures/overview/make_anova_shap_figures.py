#!/usr/bin/env python3
"""Create publication-ready diagnostic figures for the raw APSIM reanalysis."""

from pathlib import Path
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable


ROOT = Path(os.environ.get("RA_PROJECT_ROOT", Path(__file__).resolve().parents[2]))
OUT = ROOT / "outputs/anova_shap_raw"
OUT.mkdir(parents=True, exist_ok=True)
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 12,
        "axes.labelsize": 13,
        "axes.titlesize": 14,
        "xtick.labelsize": 11,
        "ytick.labelsize": 11,
        "legend.fontsize": 11,
        "axes.linewidth": 1.1,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)


def save_all(fig, stem):
    fig.savefig(OUT / f"{stem}.png", dpi=400, bbox_inches="tight", facecolor="white")
    fig.savefig(OUT / f"{stem}.pdf", bbox_inches="tight", facecolor="white")
    fig.savefig(
        OUT / f"{stem}.tiff",
        dpi=400,
        bbox_inches="tight",
        facecolor="white",
        pil_kwargs={"compression": "tiff_lzw"},
    )


def term_label(term):
    return {
        "System": "Management system",
        "Period": "Climate period",
        "Climate year": "Climate year",
        "Rotation": "Rotation",
        "System × Period": "System × period",
        "System × Climate year": "System × climate year",
        "System × Rotation": "System × rotation",
        "Period × Rotation": "Period × rotation",
        "Climate year × Rotation": "Climate year × rotation",
        "Residual (omitted three-way term)": "Three-way interaction / residual",
    }.get(term, term)


def term_color(term):
    if term == "System":
        return "#7A0177"
    if term in {"Period", "Climate year"}:
        return "#E6550D"
    if term == "Rotation":
        return "#737373"
    if "Residual" in term:
        return "#BDBDBD"
    return "#3182BD"


def variance_figure():
    d = pd.read_csv(OUT / "RA_improved_variance_decomposition.csv")
    analyses = [
        "31-year SOC accrual: six complete systems, both periods, higher fixed CO2",
        "Annual SOC change: six complete systems, both periods, higher fixed CO2",
    ]
    titles = [
        "A. Long-term endpoint: 31-year SOC accrual",
        "B. Annual process: year-to-year SOC change",
    ]
    fig, axes = plt.subplots(2, 1, figsize=(11.5, 9.0), constrained_layout=True)
    for ax, analysis, title in zip(axes, analyses, titles):
        x = d[d["Analysis"] == analysis].copy()
        x["Label"] = x["Term"].map(term_label)
        x = x.sort_values("Percent_total_SS", ascending=True)
        bars = ax.barh(
            x["Label"],
            x["Percent_total_SS"],
            color=[term_color(t) for t in x["Term"]],
            edgecolor="black",
            linewidth=0.7,
        )
        for bar, value in zip(bars, x["Percent_total_SS"]):
            ax.text(
                bar.get_width() + (0.7 if value >= 1 else 0.15),
                bar.get_y() + bar.get_height() / 2,
                f"{value:.1f}%" if value >= 0.1 else f"{value:.2f}%",
                va="center",
                fontsize=10.5,
            )
        ax.set_title(title, loc="left", fontweight="bold")
        ax.set_xlabel("Share of total sum of squares (%)")
        ax.set_xlim(0, max(60, x["Percent_total_SS"].max() * 1.16))
        ax.grid(axis="x", color="#DDDDDD", linewidth=0.7)
        ax.set_axisbelow(True)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    fig.suptitle(
        "Management dominates cumulative SOC differences, while annual responses are climate-dependent",
        fontsize=15,
        fontweight="bold",
    )
    save_all(fig, "RA_SOC_variance_decomposition_by_timescale")
    plt.close(fig)


TASK_ORDER = [
    "Annual SOC change — six complete systems, both periods",
    "Wheat yield — six complete systems, both periods",
    "Barley yield — six complete systems, both periods",
    "Rapeseed oil yield — six complete systems, both periods",
]
TASK_TITLES = [
    "A. Annual SOC change",
    "B. Wheat yield",
    "C. Barley yield",
    "D. Rapeseed-oil yield",
]
TASK_COLORS = ["#7A0177", "#1B9E77", "#D95F02", "#7570B3"]


def shap_importance_figure():
    imp = pd.read_csv(OUT / "RA_process_SHAP_importance.csv")
    metrics = pd.read_csv(OUT / "RA_process_model_grouped_CV_metrics.csv")
    selected = metrics[metrics["Selected"].astype(str).str.lower().eq("true")]
    r2 = dict(zip(selected["Task"], selected["Grouped_CV_R2"]))

    fig, axes = plt.subplots(2, 2, figsize=(14.0, 10.5), constrained_layout=True)
    for ax, task, title, color in zip(
        axes.ravel(), TASK_ORDER, TASK_TITLES, TASK_COLORS
    ):
        x = imp[(imp["Task"] == task) & (imp["Rank"] <= 8)].copy()
        x = x.sort_values("Mean_abs_Shapley", ascending=True)
        bars = ax.barh(
            x["Feature_label"],
            x["Mean_abs_Shapley"],
            color=color,
            alpha=0.88,
            edgecolor="black",
            linewidth=0.6,
        )
        for bar, value in zip(bars, x["Mean_abs_Shapley"]):
            ax.text(
                value + x["Mean_abs_Shapley"].max() * 0.02,
                bar.get_y() + bar.get_height() / 2,
                f"{value:.3f}",
                va="center",
                fontsize=9.5,
            )
        ax.set_xlim(0, x["Mean_abs_Shapley"].max() * 1.24)
        ax.set_title(
            f"{title} (grouped-CV R² = {r2.get(task, np.nan):.2f})",
            loc="left",
            fontweight="bold",
        )
        ax.set_xlabel("Mean absolute Shapley value (outcome units)")
        ax.grid(axis="x", color="#E0E0E0", linewidth=0.7)
        ax.set_axisbelow(True)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    fig.suptitle(
        "APSIM process variables associated with annual SOC change and crop yield",
        fontsize=15,
        fontweight="bold",
    )
    save_all(fig, "RA_process_SHAP_global_importance")
    plt.close(fig)


def shap_beeswarm_figure():
    shap = pd.read_csv(OUT / "RA_process_SHAP_values.csv")
    imp = pd.read_csv(OUT / "RA_process_SHAP_importance.csv")
    rng = np.random.default_rng(20260726)
    fig, axes = plt.subplots(2, 2, figsize=(14.0, 11.0), constrained_layout=True)
    cmap = plt.get_cmap("coolwarm")

    for ax, task, title in zip(axes.ravel(), TASK_ORDER, TASK_TITLES):
        top = (
            imp[(imp["Task"] == task) & (imp["Rank"] <= 6)]
            .sort_values("Rank")["Feature_label"]
            .tolist()
        )
        x = shap[(shap["Task"] == task) & shap["Feature_label"].isin(top)].copy()
        y_positions = {label: len(top) - 1 - i for i, label in enumerate(top)}
        for label in top:
            g = x[x["Feature_label"] == label].copy()
            values = g["Feature_value"].to_numpy(dtype=float)
            if np.nanmax(values) > np.nanmin(values):
                scaled = (values - np.nanmin(values)) / (
                    np.nanmax(values) - np.nanmin(values)
                )
            else:
                scaled = np.full(len(values), 0.5)
            jitter = rng.normal(0, 0.105, len(g))
            ax.scatter(
                g["Shapley_value"],
                y_positions[label] + jitter,
                c=scaled,
                cmap=cmap,
                norm=Normalize(0, 1),
                s=18,
                alpha=0.72,
                linewidths=0,
            )
        ax.axvline(0, color="black", linewidth=0.9)
        ax.set_yticks(list(y_positions.values()), list(y_positions.keys()))
        ax.set_title(title, loc="left", fontweight="bold")
        ax.set_xlabel("Shapley value (effect on model prediction)")
        ax.grid(axis="x", color="#E0E0E0", linewidth=0.7)
        ax.set_axisbelow(True)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    colorbar = fig.colorbar(
        ScalarMappable(norm=Normalize(0, 1), cmap=cmap),
        ax=axes,
        location="right",
        shrink=0.65,
        pad=0.02,
    )
    colorbar.set_ticks([0, 1])
    colorbar.set_ticklabels(["Low", "High"])
    colorbar.set_label("Feature value")
    fig.suptitle(
        "Direction and dispersion of process-driver contributions",
        fontsize=15,
        fontweight="bold",
    )
    save_all(fig, "RA_process_SHAP_beeswarm")
    plt.close(fig)


def main():
    variance_figure()
    shap_importance_figure()
    shap_beeswarm_figure()
    print("Figures written to", OUT)


if __name__ == "__main__":
    main()
