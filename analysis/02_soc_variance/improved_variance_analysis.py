#!/usr/bin/env python3
"""Balanced variance decompositions for annual APSIM SOC outputs.

The original manuscript ANOVA used one 31-year summary value per
Period x Rotation x RA-practice cell. This script retains the annual APSIM
replicates and analyses only complete, balanced subsets. Because there is one
observation per highest-order cell, results are reported as descriptive sums
of squares (SS) and variance shares; the omitted three-way term is the
residual and is not used for confirmatory p-values.
"""

from pathlib import Path
import os
import json
import numpy as np
import pandas as pd


ROOT = Path(os.environ.get("RA_PROJECT_ROOT", Path(__file__).resolve().parents[2]))
INFILE = ROOT / "outputs/anova_shap_raw/RA_annual_SOC_process_data.csv"
OUTDIR = ROOT / "outputs/anova_shap_raw"
OUTDIR.mkdir(parents=True, exist_ok=True)

COMMON_SYSTEMS = [
    "Baseline",
    "Simple cover crop",
    "Crop diversity",
    "Ideal farming system",
    "Most productive",
    "Least productive",
]

ALL_FUTURE_SYSTEMS = [
    "Baseline",
    "Simple cover crop",
    "Crop diversity",
    "Fertiliser reduction (10%)",
    "Fertiliser reduction (30%)",
    "Fertiliser reduction (50%)",
    "Herbal leys",
    "Integrate livestock",
    "Ideal farming system",
    "Most productive",
    "Least productive",
]


def effect_code(series, levels=None):
    """Sum-to-zero coding with the final level represented by -1."""
    s = pd.Series(series).astype(str)
    levels = list(levels) if levels is not None else sorted(s.unique())
    if len(levels) < 2:
        raise ValueError("A factor must have at least two levels.")
    arr = np.zeros((len(s), len(levels) - 1), dtype=float)
    for j, level in enumerate(levels[:-1]):
        arr[s.to_numpy() == level, j] = 1.0
    arr[s.to_numpy() == levels[-1], :] = -1.0
    names = [f"{s.name}[{level}]" for level in levels[:-1]]
    return arr, names, levels


def interaction_block(a, b, anames, bnames):
    block = (a[:, :, None] * b[:, None, :]).reshape(len(a), -1)
    names = [f"{x}:{y}" for x in anames for y in bnames]
    return block, names


def fit_rss(x, y):
    coef, _, _, _ = np.linalg.lstsq(x, y, rcond=None)
    resid = y - x @ coef
    return float(resid @ resid), int(np.linalg.matrix_rank(x))


def balanced_two_way_ss(data, outcome, factors, levels, analysis_name):
    """Fit main effects and every two-way interaction using effect coding."""
    y = data[outcome].to_numpy(dtype=float)
    blocks = {"Intercept": np.ones((len(data), 1), dtype=float)}
    block_names = {"Intercept": ["Intercept"]}
    encoded = {}

    for factor in factors:
        matrix, names, _ = effect_code(data[factor], levels[factor])
        blocks[factor] = matrix
        block_names[factor] = names
        encoded[factor] = (matrix, names)

    for i, factor_a in enumerate(factors):
        for factor_b in factors[i + 1 :]:
            term = f"{factor_a} × {factor_b}"
            matrix, names = interaction_block(
                encoded[factor_a][0],
                encoded[factor_b][0],
                encoded[factor_a][1],
                encoded[factor_b][1],
            )
            blocks[term] = matrix
            block_names[term] = names

    terms = list(blocks)
    full_x = np.column_stack([blocks[t] for t in terms])
    full_rss, full_rank = fit_rss(full_x, y)
    total_ss = float(((y - y.mean()) ** 2).sum())

    rows = []
    for term in terms:
        if term == "Intercept":
            continue
        reduced_terms = [t for t in terms if t != term]
        reduced_x = np.column_stack([blocks[t] for t in reduced_terms])
        reduced_rss, reduced_rank = fit_rss(reduced_x, y)
        ss = max(0.0, reduced_rss - full_rss)
        rows.append(
            {
                "Analysis": analysis_name,
                "Term": term,
                "df": full_rank - reduced_rank,
                "SS": ss,
                "Percent_total_SS": 100.0 * ss / total_ss,
            }
        )

    residual_df = len(y) - full_rank
    rows.append(
        {
            "Analysis": analysis_name,
            "Term": "Residual (omitted three-way term)",
            "df": residual_df,
            "SS": full_rss,
            "Percent_total_SS": 100.0 * full_rss / total_ss,
        }
    )
    out = pd.DataFrame(rows)

    # In a balanced orthogonal design, term SS plus residual equals total SS.
    diagnostics = {
        "Analysis": analysis_name,
        "n": int(len(data)),
        "Outcome": outcome,
        "Factors": factors,
        "Levels": levels,
        "Full_model_rank": full_rank,
        "Residual_df": residual_df,
        "Total_SS": total_ss,
        "Model_SS": total_ss - full_rss,
        "R_squared": 1.0 - full_rss / total_ss,
        "SS_closure_error": float(out["SS"].sum() - total_ss),
    }
    return out, diagnostics


def assert_complete(data, cell_factors, expected_n):
    counts = data.groupby(cell_factors, observed=True).size()
    if counts.empty or counts.min() != expected_n or counts.max() != expected_n:
        raise ValueError(
            f"Unbalanced subset for {cell_factors}: "
            f"min={counts.min()}, max={counts.max()}, expected={expected_n}"
        )


def main():
    d = pd.read_csv(INFILE)
    d = d.loc[np.isfinite(d["SOC_change_t_C_ha_yr"])].copy()

    results = []
    diagnostics = []

    # 1) Primary historical-future comparison at higher fixed CO2.
    # ClimateYear is a 62-level factor and captures the climate trajectory
    # (including the period distinction) without treating years as replicates
    # of an identical climate.
    common = d[
        (d["CO2_scenario"] == "Higher fixed")
        & d["System"].isin(COMMON_SYSTEMS)
        & d["Period"].isin(["Historical", "Future"])
    ].copy()
    assert_complete(common, ["System", "Period", "Rotation"], 31)
    common["Climate year"] = common["Period"] + "-" + common["Year"].astype(str)
    ss, diag = balanced_two_way_ss(
        common,
        "SOC_change_t_C_ha_yr",
        ["System", "Climate year", "Rotation"],
        {
            "System": COMMON_SYSTEMS,
            "Climate year": (
                [f"Historical-{y}" for y in range(1993, 2024)]
                + [f"Future-{y}" for y in range(2030, 2061)]
            ),
            "Rotation": ["Winter", "Spring"],
        },
        "Annual SOC change: six complete systems, both periods, higher fixed CO2",
    )
    results.append(ss)
    diagnostics.append(diag)

    # 2) All 11 systems can be compared without missing cells in the future.
    future = d[
        (d["CO2_scenario"] == "Higher fixed")
        & (d["Period"] == "Future")
        & d["System"].isin(ALL_FUTURE_SYSTEMS)
    ].copy()
    assert_complete(future, ["System", "Rotation"], 31)
    future["Climate year"] = future["Year"].astype(str)
    ss, diag = balanced_two_way_ss(
        future,
        "SOC_change_t_C_ha_yr",
        ["System", "Climate year", "Rotation"],
        {
            "System": ALL_FUTURE_SYSTEMS,
            "Climate year": [str(y) for y in range(2030, 2061)],
            "Rotation": ["Winter", "Spring"],
        },
        "Annual SOC change: all 11 systems, future period, higher fixed CO2",
    )
    results.append(ss)
    diagnostics.append(diag)

    # 3) Directly comparable 31-year cumulative SOC response. This is closest
    # to the original manuscript endpoint but keeps a balanced six-system set.
    totals = (
        common.sort_values("Year")
        .groupby(["System", "Period", "Rotation"], observed=True)
        .agg(
            SOC_start_t_C_ha=("SOC_start_t_C_ha", "first"),
            SOC_end_t_C_ha=("SOC_end_t_C_ha", "last"),
            n_years=("Year", "nunique"),
        )
        .reset_index()
    )
    totals["SOC_accrual_31yr_t_C_ha"] = (
        totals["SOC_end_t_C_ha"] - totals["SOC_start_t_C_ha"]
    )
    if not (totals["n_years"] == 31).all():
        raise ValueError("A cumulative SOC cell does not contain 31 years.")
    ss, diag = balanced_two_way_ss(
        totals,
        "SOC_accrual_31yr_t_C_ha",
        ["System", "Period", "Rotation"],
        {
            "System": COMMON_SYSTEMS,
            "Period": ["Historical", "Future"],
            "Rotation": ["Winter", "Spring"],
        },
        "31-year SOC accrual: six complete systems, both periods, higher fixed CO2",
    )
    results.append(ss)
    diagnostics.append(diag)

    all_results = pd.concat(results, ignore_index=True)
    all_results.to_csv(OUTDIR / "RA_improved_variance_decomposition.csv", index=False)
    totals.to_csv(OUTDIR / "RA_31yr_SOC_accrual_complete_systems.csv", index=False)
    (OUTDIR / "RA_improved_variance_diagnostics.json").write_text(
        json.dumps(diagnostics, indent=2), encoding="utf-8"
    )

    print(all_results.to_string(index=False))
    print("\nDiagnostics:")
    print(json.dumps(diagnostics, indent=2))


if __name__ == "__main__":
    main()
