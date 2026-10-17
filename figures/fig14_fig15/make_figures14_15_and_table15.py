#!/usr/bin/env python3
"""Create journal-ready Figures 14–15 and source tables.

Inputs are the audited APSIM variance-decomposition and SHAP outputs stored
beside this script. Outputs are produced as publication raster and vector files.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import os

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch, Rectangle
from PIL import Image


HERE = Path(os.environ.get("RA_RESULTS_DIR", Path(__file__).resolve().parents[2] / "outputs/anova_shap_raw"))
HERE.mkdir(parents=True, exist_ok=True)

VARIANCE_FILE = HERE / "RA_improved_variance_decomposition.csv"
SHAP_FILE = HERE / "RA_process_SHAP_importance.csv"
CV_FILE = HERE / "RA_process_model_grouped_CV_metrics.csv"

FONT = "Nimbus Sans"
TEXT = "#000000"
GRID = "#D9D9D9"

COMPONENT_COLOURS = {
    "Management": "#7B2CBF",
    "Climate": "#E66101",
    "Management × climate": "#1F78B4",
    "Season": "#20BFC9",
    "Residual": "#2CA25F",
}

OUTCOME_COLOURS = {
    "SOC": "#8E2A8B",
    "Wheat": "#009E73",
    "Barley": "#E69F00",
    "Rapeseed oil": "#5975C1",
}

mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": [FONT, "Arial", "Liberation Sans", "DejaVu Sans"],
        "font.size": 12.5,
        "text.color": TEXT,
        "axes.labelcolor": TEXT,
        "axes.edgecolor": TEXT,
        "axes.linewidth": 1.1,
        "xtick.color": TEXT,
        "ytick.color": TEXT,
        "xtick.major.width": 1.1,
        "ytick.major.width": 1.1,
        "xtick.major.size": 4.5,
        "ytick.major.size": 4.5,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "savefig.facecolor": "white",
        "figure.facecolor": "white",
    }
)


def save_figure(fig: plt.Figure, stem: str) -> None:
    """Save a figure in journal and Word-friendly formats."""
    fig.savefig(HERE / f"{stem}.svg", bbox_inches="tight")
    fig.savefig(HERE / f"{stem}.pdf", bbox_inches="tight")
    png_path = HERE / f"{stem}.png"
    fig.savefig(png_path, dpi=600, bbox_inches="tight")
    with Image.open(png_path) as image:
        image.convert("RGB").save(
            HERE / f"{stem}.tiff",
            compression="tiff_lzw",
            dpi=(600, 600),
        )


def standardise_variance_terms(data: pd.DataFrame) -> pd.DataFrame:
    mapping = {
        "System": "Management",
        "Period": "Climate",
        "Climate year": "Climate",
        "Rotation": "Season",
        "System × Period": "Management × climate",
        "System × Climate year": "Management × climate",
        "System × Rotation": "Management × season",
        "Period × Rotation": "Climate × season",
        "Climate year × Rotation": "Climate × season",
        "Residual (omitted three-way term)": "Residual",
    }
    out = data.copy()
    out["Source"] = out["Term"].map(mapping)
    if out["Source"].isna().any():
        missing = sorted(out.loc[out["Source"].isna(), "Term"].unique())
        raise ValueError(f"Unmapped variance terms: {missing}")
    return out


def get_primary_variance_panels() -> pd.DataFrame:
    raw = pd.read_csv(VARIANCE_FILE)
    keep = raw["Analysis"].isin(
        [
            "31-year SOC accrual: six complete systems, both periods, higher fixed CO2",
            "Annual SOC change: six complete systems, both periods, higher fixed CO2",
        ]
    )
    data = standardise_variance_terms(raw.loc[keep].copy())
    data["Panel"] = np.where(
        data["Analysis"].str.startswith("31-year"), "A", "B"
    )
    data["Outcome"] = np.where(
        data["Panel"].eq("A"), "Cumulative SOC", "Annual SOC change"
    )
    panel_order = pd.CategoricalDtype(["A", "B"], ordered=True)
    source_order = pd.CategoricalDtype(
        [
            "Management",
            "Climate",
            "Season",
            "Management × climate",
            "Management × season",
            "Climate × season",
            "Residual",
        ],
        ordered=True,
    )
    data["Panel"] = data["Panel"].astype(panel_order)
    data["Source"] = data["Source"].astype(source_order)
    return data.sort_values(["Panel", "Source"])


def aggregate_for_donuts(data: pd.DataFrame) -> pd.DataFrame:
    """Aggregate all season-related SS terms into one compact figure category."""
    compact = data.copy()
    compact["Component"] = compact["Source"].astype(str)
    compact.loc[
        compact["Component"].isin(
            ["Season", "Management × season", "Climate × season"]
        ),
        "Component",
    ] = "Season"
    return (
        compact.groupby(["Panel", "Outcome", "Component"], observed=True)
        .agg(Percent=("Percent_total_SS", "sum"))
        .reset_index()
    )


def percent_text(value: float) -> str:
    if value < 0.1:
        return f"{value:.2f}%"
    return f"{value:.1f}%"


def draw_donut(
    ax: plt.Axes,
    values: dict[str, float],
    panel: str,
    centre_label: str,
    callout_positions: dict[str, tuple[float, float]] | None = None,
) -> None:
    components = list(COMPONENT_COLOURS)
    sizes = np.array([values.get(c, 0.0) for c in components], dtype=float)
    colours = [COMPONENT_COLOURS[c] for c in components]
    wedges, _ = ax.pie(
        sizes,
        startangle=90,
        counterclock=True,
        colors=colours,
        radius=1.0,
        wedgeprops={"width": 0.36, "edgecolor": "white", "linewidth": 1.4},
    )
    ax.text(
        0,
        0,
        centre_label,
        ha="center",
        va="center",
        fontsize=15,
        fontweight="bold",
        color=TEXT,
        linespacing=0.92,
    )
    ax.text(
        -1.18,
        1.15,
        panel,
        ha="left",
        va="top",
        fontsize=17,
        fontweight="bold",
        color=TEXT,
    )

    for component, value, wedge in zip(components, sizes, wedges):
        angle = math.radians((wedge.theta1 + wedge.theta2) / 2)
        if value >= 5.0:
            x, y = 0.82 * math.cos(angle), 0.82 * math.sin(angle)
            ax.text(
                x,
                y,
                percent_text(value),
                ha="center",
                va="center",
                fontsize=13,
                fontweight="bold",
                color=TEXT,
            )
            continue

        start = (0.99 * math.cos(angle), 0.99 * math.sin(angle))
        if callout_positions and component in callout_positions:
            end = callout_positions[component]
        else:
            end = (1.30 * math.cos(angle), 1.30 * math.sin(angle))
        ha = "left" if end[0] >= 0 else "right"
        ax.annotate(
            percent_text(value),
            xy=start,
            xytext=end,
            ha=ha,
            va="center",
            fontsize=11.5,
            fontweight="bold",
            color=TEXT,
            arrowprops={
                "arrowstyle": "-",
                "color": "#555555",
                "linewidth": 0.9,
                "shrinkA": 0,
                "shrinkB": 0,
                "connectionstyle": "arc3,rad=0",
            },
        )

    ax.set_aspect("equal")
    ax.set_xlim(-1.32, 1.72)
    ax.set_ylim(-1.30, 1.30)
    ax.axis("off")


def make_figure_14(variance: pd.DataFrame) -> None:
    compact = aggregate_for_donuts(variance)
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.75))
    fig.subplots_adjust(left=0.01, right=0.99, top=0.98, bottom=0.20, wspace=0.02)

    long_values = (
        compact.loc[compact["Panel"].astype(str).eq("A")]
        .set_index("Component")["Percent"]
        .to_dict()
    )
    annual_values = (
        compact.loc[compact["Panel"].astype(str).eq("B")]
        .set_index("Component")["Percent"]
        .to_dict()
    )

    draw_donut(
        axes[0],
        long_values,
        "A",
        "Cumulative\nSOC",
        {
            "Climate": (1.30, 0.48),
            "Management × climate": (1.48, 0.16),
            "Season": (1.39, -0.17),
            "Residual": (1.18, -0.50),
        },
    )
    draw_donut(
        axes[1],
        annual_values,
        "B",
        "Annual\nSOC change",
        {"Season": (1.30, -0.44)},
    )

    legend_handles = [
        Patch(
            facecolor=COMPONENT_COLOURS[c],
            edgecolor="black",
            linewidth=0.6,
            label=c,
        )
        for c in COMPONENT_COLOURS
    ]
    fig.legend(
        handles=legend_handles,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.01),
        ncol=3,
        frameon=False,
        fontsize=11.5,
        handlelength=1.05,
        handletextpad=0.45,
        columnspacing=1.05,
    )
    save_figure(fig, "Figure14_SOC_variance_decomposition")
    plt.close(fig)


SHORT_LABELS = {
    "Annual soil evaporation": "Soil evap.",
    "Mean surface residue C": "Residue C",
    "Starting SOC": "Initial SOC",
    "Minimum soil water": "Min. soil water",
    "Change in surface residue C": "Δ residue C",
    "Annual crop yield": "Crop yield",
    "Mineral N applied": "Mineral N",
    "Maximum crop biomass": "Max. biomass",
    "Minimum temperature factor": "Min. temp. factor",
    "Plant-available water capacity": "PAWC",
    "Mean soil water": "Mean soil water",
    "Minimum water-stress factor": "Min. water stress",
    "Minimum N-stress factor": "Min. N stress",
    "Maximum leaf-area index": "Max. LAI",
    "Mean water-stress factor": "Mean water stress",
    "Crop active days": "Active days",
    "In-crop soil evaporation": "Soil evap.",
    "Harvest day of year": "Harvest DOY",
    "Annual SOC change": "SOC change",
    "Mean CO2 growth factor": "CO2 growth factor",
}

TASKS = [
    (
        "Annual SOC change — six complete systems, both periods",
        "A",
        "SOC",
    ),
    ("Wheat yield — six complete systems, both periods", "B", "Wheat"),
    ("Barley yield — six complete systems, both periods", "C", "Barley"),
    (
        "Rapeseed oil yield — six complete systems, both periods",
        "D",
        "Rapeseed oil",
    ),
]


def add_strip(ax: plt.Axes, panel: str, label: str) -> None:
    strip = Rectangle(
        (0, 1.02),
        1,
        0.13,
        transform=ax.transAxes,
        facecolor="#D9D9D9",
        edgecolor="black",
        linewidth=1.0,
        clip_on=False,
    )
    ax.add_patch(strip)
    ax.text(
        0.02,
        1.085,
        panel,
        transform=ax.transAxes,
        ha="left",
        va="center",
        fontsize=14,
        fontweight="bold",
        color=TEXT,
    )
    ax.text(
        0.52,
        1.085,
        label,
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=14,
        fontweight="bold",
        color=TEXT,
    )


def make_figure_15() -> pd.DataFrame:
    data = pd.read_csv(SHAP_FILE)
    fig, axes = plt.subplots(2, 2, figsize=(7.4, 6.15))
    fig.subplots_adjust(
        left=0.17, right=0.985, top=0.94, bottom=0.10, wspace=0.53, hspace=0.48
    )

    abbreviation_rows: list[dict[str, str]] = []
    for ax, (task, panel, outcome) in zip(axes.flat, TASKS):
        plot = (
            data.loc[(data["Task"].eq(task)) & (data["Rank"].le(7))]
            .sort_values("Rank")
            .copy()
        )
        plot["Short_label"] = plot["Feature_label"].map(SHORT_LABELS)
        if plot["Short_label"].isna().any():
            missing = sorted(
                plot.loc[plot["Short_label"].isna(), "Feature_label"].unique()
            )
            raise ValueError(f"Missing abbreviated SHAP labels: {missing}")
        for _, row in plot.iterrows():
            abbreviation_rows.append(
                {
                    "Panel": panel,
                    "Outcome": outcome,
                    "Abbreviation": row["Short_label"],
                    "Full predictor": row["Feature_label"],
                }
            )

        y = np.arange(len(plot))
        bars = ax.barh(
            y,
            plot["Mean_abs_Shapley"],
            height=0.70,
            color=OUTCOME_COLOURS[outcome],
            edgecolor="black",
            linewidth=0.9,
        )
        ax.set_yticks(y, plot["Short_label"])
        ax.invert_yaxis()
        ax.set_xlim(0, plot["Mean_abs_Shapley"].max() * 1.18)
        ax.xaxis.grid(True, color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        ax.tick_params(axis="both", labelsize=11.5)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        add_strip(ax, panel, outcome)
        for bar, value in zip(bars, plot["Mean_abs_Shapley"]):
            ax.text(
                bar.get_width() + ax.get_xlim()[1] * 0.018,
                bar.get_y() + bar.get_height() / 2,
                f"{value:.2f}",
                ha="left",
                va="center",
                fontsize=10.5,
                color=TEXT,
            )

    fig.supxlabel("Mean |SHAP|", x=0.58, y=0.025, fontsize=14, color=TEXT)
    save_figure(fig, "Figure15_SHAP_global_importance")
    plt.close(fig)
    return pd.DataFrame(abbreviation_rows).drop_duplicates()


def make_table_data(variance: pd.DataFrame) -> None:
    table = variance[
        ["Panel", "Outcome", "Source", "df", "SS", "Percent_total_SS"]
    ].copy()
    table["Panel"] = table["Panel"].astype(str)
    table["Source"] = table["Source"].astype(str)
    table = table.rename(
        columns={
            "df": "df",
            "SS": "Sum of squares",
            "Percent_total_SS": "Share of total SS (%)",
        }
    )
    table.to_csv(HERE / "Table15_SOC_variance_decomposition.csv", index=False)

    cv = pd.read_csv(CV_FILE)
    wanted = [
        "Annual SOC change — six complete systems, both periods",
        "Wheat yield — six complete systems, both periods",
        "Barley yield — six complete systems, both periods",
        "Rapeseed oil yield — six complete systems, both periods",
    ]
    selected = cv.loc[cv["Selected"].eq(True) & cv["Task"].isin(wanted)].copy()
    selected["Outcome"] = (
        selected["Task"]
        .str.replace(" — six complete systems, both periods", "", regex=False)
        .replace(
            {
                "Annual SOC change": "Annual SOC change",
                "Wheat yield": "Wheat",
                "Barley yield": "Barley",
                "Rapeseed oil yield": "Rapeseed oil",
            }
        )
    )
    selected = selected[
        [
            "Outcome",
            "Model",
            "n",
            "n_groups",
            "Grouped_CV_R2",
            "Grouped_CV_RMSE",
            "Grouped_CV_MAE",
        ]
    ]
    selected.to_csv(HERE / "Figure15_grouped_CV_model_validation.csv", index=False)

    payload = {
        "table15": table.to_dict(orient="records"),
        "model_validation": selected.to_dict(orient="records"),
        "notes": [
            "Table 15 is a descriptive factorial decomposition of total sums of squares.",
            "Climate denotes climate period for cumulative SOC and climate year for annual SOC change.",
            "Season denotes the winter or spring rotation.",
            "Residual denotes the omitted Management × Climate × Season term; it is not independently replicated error.",
            "Accordingly, F tests and p-values are not reported.",
            "Analyses use the six complete management systems, both climate periods and the higher fixed CO₂ scenario.",
        ],
    }
    (HERE / "Table15_source_data.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )


def write_captions() -> None:
    text = """# Publication-ready captions

**Figure 14. Relative contributions of management, climate and season to cumulative and annual soil organic carbon (SOC) variation.** Donut sectors show each component's share of the total sum of squares for (A) cumulative SOC accrual over the simulation period and (B) annual SOC change. Analyses used the six management systems with complete coverage of the historical and future climate periods under the higher fixed CO₂ scenario. Climate represents climate period in panel A and climate year in panel B. Season combines the season main effect with management × season and climate × season terms. Residual represents the omitted management × climate × season term. Percentages are descriptive variance shares and may not sum to exactly 100% because of rounding.

**Figure 15. Global importance of physiological, soil and management predictors of regenerative-system performance.** Bars show mean absolute SHAP values for models of (A) annual SOC change and the yields of (B) wheat, (C) barley and (D) rapeseed oil. Larger values indicate a greater average contribution to model predictions, irrespective of direction. Models were evaluated using grouped cross-validation by climate year and explained 85% of out-of-fold variation in annual SOC change, 75% in wheat yield, 84% in barley yield and 91% in rapeseed-oil yield. Analyses used the six management systems with complete coverage of both climate periods under the higher fixed CO₂ scenario. SHAP, Shapley additive explanations; SOC, soil organic carbon; PAWC, plant-available water capacity; LAI, leaf-area index; DOY, day of year; Δ, change; N, nitrogen.

**Table 15. Descriptive factorial decomposition of variation in cumulative and annual SOC responses under regenerative management.** The table reports degrees of freedom (df), sums of squares (SS) and the percentage share of total SS. Climate denotes climate period for cumulative SOC and climate year for annual SOC change; season denotes the winter or spring rotation. Residual is the omitted management × climate × season term and does not provide independently replicated error. F tests and p-values are therefore not reported. Analyses used the six complete management systems, both climate periods and the higher fixed CO₂ scenario.
"""
    (HERE / "Figure14_15_Table15_captions.md").write_text(text, encoding="utf-8")


def main() -> None:
    variance = get_primary_variance_panels()
    make_figure_14(variance)
    abbreviations = make_figure_15()
    abbreviations.to_csv(HERE / "Figure15_predictor_abbreviations.csv", index=False)
    make_table_data(variance)
    write_captions()


if __name__ == "__main__":
    main()
