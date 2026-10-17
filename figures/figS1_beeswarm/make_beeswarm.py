#!/usr/bin/env python3
"""Create a journal-ready supplementary SHAP beeswarm figure."""

from pathlib import Path
import os

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
from matplotlib.patches import Rectangle


HERE = Path(os.environ.get("RA_RESULTS_DIR", Path(__file__).resolve().parents[2] / "outputs/anova_shap_raw"))
HERE.mkdir(parents=True, exist_ok=True)
SHAP_FILE = HERE / "RA_process_SHAP_values.csv"
IMPORTANCE_FILE = HERE / "RA_process_SHAP_importance.csv"
OUTPUT_STEM = HERE / "FigureS_SHAP_beeswarm_refined"

mpl.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 13,
        "axes.labelcolor": "black",
        "axes.edgecolor": "black",
        "xtick.color": "black",
        "ytick.color": "black",
        "text.color": "black",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
    }
)

TASKS = [
    (
        "Annual SOC change — six complete systems, both periods",
        "A",
        "SOC",
        1.2,
        0.5,
    ),
    (
        "Wheat yield — six complete systems, both periods",
        "B",
        "Wheat",
        1.2,
        0.5,
    ),
    (
        "Barley yield — six complete systems, both periods",
        "C",
        "Barley",
        3.0,
        1.0,
    ),
    (
        "Rapeseed oil yield — six complete systems, both periods",
        "D",
        "Rapeseed oil",
        2.0,
        1.0,
    ),
]

SHORT_LABELS = {
    "Annual soil evaporation": "Soil evap.",
    "Mean surface residue C": "Residue C",
    "Starting SOC": "Initial SOC",
    "Minimum soil water": "Min. soil water",
    "Change in surface residue C": "Δ residue C",
    "Annual crop yield": "Crop yield",
    "Maximum crop biomass": "Max. biomass",
    "Minimum temperature factor": "Min. temp. factor",
    "Plant-available water capacity": "PAWC",
    "Mean soil water": "Mean soil water",
    "Minimum water-stress factor": "Min. water stress",
    "Minimum N-stress factor": "Min. N stress",
    "Mean water-stress factor": "Mean water stress",
    "Crop active days": "Active days",
    "In-crop soil evaporation": "Soil evap.",
    "Harvest day of year": "Harvest DOY",
    "Annual SOC change": "SOC change",
    "Maximum leaf-area index": "Max. LAI",
    "Mean CO2 growth factor": "CO₂ growth factor",
}

FEATURE_CMAP = mpl.colors.LinearSegmentedColormap.from_list(
    "feature_value",
    ["#2946B6", "#6F92F3", "#E6E6E6", "#F28E6B", "#B40426"],
)


def top_features(importance: pd.DataFrame, task: str) -> list[str]:
    return (
        importance.loc[
            (importance["Task"] == task) & (importance["Rank"] <= 6)
        ]
        .sort_values("Rank")["Feature_label"]
        .tolist()
    )


def add_panel_strip(ax: plt.Axes, panel: str, outcome: str) -> None:
    strip = Rectangle(
        (0, 1.025),
        1,
        0.135,
        transform=ax.transAxes,
        facecolor="#D9D9D9",
        edgecolor="black",
        linewidth=1.05,
        clip_on=False,
        zorder=8,
    )
    ax.add_patch(strip)
    ax.text(
        0.018,
        1.092,
        panel,
        transform=ax.transAxes,
        ha="left",
        va="center",
        fontsize=18,
        fontweight="bold",
        color="black",
        clip_on=False,
        zorder=9,
    )
    ax.text(
        0.5,
        1.092,
        outcome,
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=18,
        fontweight="bold",
        color="black",
        clip_on=False,
        zorder=9,
    )


def draw_panel(
    ax: plt.Axes,
    shap: pd.DataFrame,
    importance: pd.DataFrame,
    task: str,
    panel: str,
    outcome: str,
    x_limit: float,
    tick_step: float,
    show_x_title: bool,
    rng: np.random.Generator,
) -> None:
    features = top_features(importance, task)
    missing = [name for name in features if name not in SHORT_LABELS]
    if missing:
        raise ValueError(f"Missing shortened feature labels: {missing}")
    display_labels = [SHORT_LABELS[name] for name in features]

    y_positions = {
        feature: len(features) - 1 - index
        for index, feature in enumerate(features)
    }

    for feature in features:
        group = shap.loc[
            (shap["Task"] == task) & (shap["Feature_label"] == feature)
        ].copy()
        feature_values = group["Feature_value"].to_numpy(dtype=float)
        finite = np.isfinite(feature_values)
        if finite.any() and np.nanmax(feature_values) > np.nanmin(feature_values):
            scaled_values = (feature_values - np.nanmin(feature_values)) / (
                np.nanmax(feature_values) - np.nanmin(feature_values)
            )
        else:
            scaled_values = np.full(len(feature_values), 0.5)

        # Draw points in a deterministic random order so neither end of the
        # feature-value scale systematically obscures the other.
        order = rng.permutation(len(group))
        jitter = rng.normal(0, 0.085, len(group))
        ax.scatter(
            group["Shapley_value"].to_numpy()[order],
            y_positions[feature] + jitter[order],
            c=scaled_values[order],
            cmap=FEATURE_CMAP,
            norm=Normalize(0, 1),
            s=27,
            alpha=0.82,
            linewidths=0,
            rasterized=False,
            zorder=3,
        )

    ax.set_xlim(-x_limit, x_limit)
    ax.set_ylim(-0.60, len(features) - 0.40)
    tick_limit = 1.0 if np.isclose(x_limit, 1.2) else x_limit
    ax.set_xticks(
        np.arange(-tick_limit, tick_limit + tick_step / 2, tick_step)
    )
    ax.set_yticks(
        list(y_positions.values()),
        display_labels,
        fontsize=14.5,
        color="black",
    )
    ax.tick_params(
        axis="x",
        labelsize=12.5,
        direction="out",
        length=4.2,
        width=1.1,
        pad=4,
        colors="black",
    )
    ax.tick_params(
        axis="y",
        direction="out",
        length=4.2,
        width=1.1,
        pad=3.5,
        colors="black",
    )
    ax.axvline(0, color="black", linewidth=1.15, zorder=4)
    ax.grid(axis="x", color="#D9D9D9", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    if show_x_title:
        ax.set_xlabel("SHAP value", fontsize=15, color="black", labelpad=5)

    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("black")
        ax.spines[side].set_linewidth(1.15)

    add_panel_strip(ax, panel, outcome)


def main() -> None:
    shap = pd.read_csv(SHAP_FILE)
    importance = pd.read_csv(IMPORTANCE_FILE)
    rng = np.random.default_rng(20260726)

    figure, axes = plt.subplots(
        2,
        2,
        figsize=(10.5, 7.4),
        facecolor="white",
    )

    for index, (ax, (task, panel, outcome, x_limit, tick_step)) in enumerate(
        zip(axes.flat, TASKS)
    ):
        draw_panel(
            ax=ax,
            shap=shap,
            importance=importance,
            task=task,
            panel=panel,
            outcome=outcome,
            x_limit=x_limit,
            tick_step=tick_step,
            show_x_title=index >= 2,
            rng=rng,
        )

    figure.subplots_adjust(
        left=0.195,
        right=0.895,
        bottom=0.105,
        top=0.93,
        wspace=0.52,
        hspace=0.31,
    )

    colorbar_axis = figure.add_axes([0.925, 0.205, 0.020, 0.585])
    colorbar = figure.colorbar(
        ScalarMappable(norm=Normalize(0, 1), cmap=FEATURE_CMAP),
        cax=colorbar_axis,
    )
    colorbar.set_ticks([0, 1])
    colorbar.set_ticklabels(["Low", "High"])
    colorbar.set_label(
        "Feature value",
        fontsize=14.5,
        color="black",
        labelpad=8,
    )
    colorbar.ax.tick_params(
        labelsize=12.5,
        colors="black",
        width=1.0,
        length=4,
    )
    colorbar.outline.set_edgecolor("black")
    colorbar.outline.set_linewidth(1.0)

    figure.savefig(
        OUTPUT_STEM.with_suffix(".png"),
        dpi=600,
        facecolor="white",
        bbox_inches="tight",
    )
    figure.savefig(
        OUTPUT_STEM.with_suffix(".tiff"),
        dpi=600,
        facecolor="white",
        bbox_inches="tight",
        pil_kwargs={"compression": "tiff_lzw"},
    )
    figure.savefig(
        OUTPUT_STEM.with_suffix(".pdf"),
        facecolor="white",
        bbox_inches="tight",
    )
    figure.savefig(
        OUTPUT_STEM.with_suffix(".svg"),
        facecolor="white",
        bbox_inches="tight",
    )
    plt.close(figure)


if __name__ == "__main__":
    main()
