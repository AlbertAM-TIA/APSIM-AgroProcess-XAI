#!/usr/bin/env python3
"""Cross-validated process-driver models with model-agnostic Shapley values.

The models deliberately exclude the RA system name. This prevents SHAP from
merely ranking treatment labels and instead evaluates APSIM process variables.
Climate years are kept together in grouped cross-validation, so observations
from a held-out year are never split between training and test sets.

The Shapley calculation is an interventional Monte Carlo approximation:
features from a test row are added to randomly sampled training-background
rows in random order. It therefore works with scikit-learn models without
requiring the external ``shap`` package.
"""

from pathlib import Path
import os
import hashlib
import json
import math
import warnings

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold


ROOT = Path(os.environ.get("RA_PROJECT_ROOT", Path(__file__).resolve().parents[2]))
OUTDIR = ROOT / "outputs/anova_shap_raw"
OUTDIR.mkdir(parents=True, exist_ok=True)
SOC_FILE = OUTDIR / "RA_annual_SOC_process_data.csv"
YIELD_FILE = OUTDIR / "RA_annual_crop_yield_process_data.csv"
SEED = 20260726

COMMON_SYSTEMS = [
    "Baseline",
    "Simple cover crop",
    "Crop diversity",
    "Ideal farming system",
    "Most productive",
    "Least productive",
]

SOC_FEATURES = [
    "SOC_start_t_C_ha",
    "Soil_water_mean",
    "Soil_water_min",
    "Soil_N_mean",
    "Soil_N_min",
    "Nitrogen_applied_kg_ha",
    "Soil_evaporation_sum",
    "PAWC_mean",
    "OM_residue_mean",
    "OM_residue_change",
    "Total_crop_biomass_max",
    "Total_crop_yield_kg_ha",
    "Rotation_Spring",
    "Period_Future",
]

YIELD_FEATURES = [
    "Biomass_max_kg_ha",
    "LAI_max",
    "CO2_factor_mean",
    "N_stress_factor_mean",
    "N_stress_factor_min",
    "Temperature_factor_mean",
    "Temperature_factor_min",
    "VPD_factor_mean",
    "VPD_factor_min",
    "Water_stress_factor_mean",
    "Water_stress_factor_min",
    "Soil_water_mean",
    "Soil_water_min",
    "Soil_N_mean",
    "Soil_N_min",
    "Nitrogen_applied_kg_ha",
    "Soil_evaporation_active_sum",
    "PAWC_mean",
    "OM_residue_mean",
    "SOC_change_t_C_ha_yr",
    "Active_days",
    "Harvest_DOY",
    "Rotation_Spring",
    "Period_Future",
]

FEATURE_LABELS = {
    "SOC_start_t_C_ha": "Starting SOC",
    "Soil_water_mean": "Mean soil water",
    "Soil_water_min": "Minimum soil water",
    "Soil_N_mean": "Mean soil N",
    "Soil_N_min": "Minimum soil N",
    "Nitrogen_applied_kg_ha": "Mineral N applied",
    "Soil_evaporation_sum": "Annual soil evaporation",
    "Soil_evaporation_active_sum": "In-crop soil evaporation",
    "PAWC_mean": "Plant-available water capacity",
    "OM_residue_mean": "Mean surface residue C",
    "OM_residue_change": "Change in surface residue C",
    "Total_crop_biomass_max": "Annual maximum crop biomass",
    "Total_crop_yield_kg_ha": "Annual crop yield",
    "Biomass_max_kg_ha": "Maximum crop biomass",
    "LAI_max": "Maximum leaf-area index",
    "CO2_factor_mean": "Mean CO2 growth factor",
    "N_stress_factor_mean": "Mean N-stress factor",
    "N_stress_factor_min": "Minimum N-stress factor",
    "Temperature_factor_mean": "Mean temperature factor",
    "Temperature_factor_min": "Minimum temperature factor",
    "VPD_factor_mean": "Mean VPD factor",
    "VPD_factor_min": "Minimum VPD factor",
    "Water_stress_factor_mean": "Mean water-stress factor",
    "Water_stress_factor_min": "Minimum water-stress factor",
    "SOC_change_t_C_ha_yr": "Annual SOC change",
    "Active_days": "Crop active days",
    "Harvest_DOY": "Harvest day of year",
    "Rotation_Spring": "Spring rotation",
    "Period_Future": "Future period",
}


def candidate_models():
    return {
        "Extra trees": ExtraTreesRegressor(
            n_estimators=350,
            min_samples_leaf=3,
            max_features=0.80,
            n_jobs=-1,
            random_state=SEED,
        ),
        "Histogram gradient boosting": HistGradientBoostingRegressor(
            max_iter=300,
            learning_rate=0.05,
            max_leaf_nodes=15,
            min_samples_leaf=10,
            l2_regularization=1.0,
            random_state=SEED,
        ),
    }


def clone_model(name):
    return candidate_models()[name]


def prepare_numeric(data, features):
    x = data[features].copy()
    medians = x.median(numeric_only=True)
    x = x.fillna(medians)
    if x.isna().any().any():
        missing = x.columns[x.isna().any()].tolist()
        raise ValueError(f"Features remain missing after median filling: {missing}")
    return x.astype(float)


def grouped_cv_select(data, target, features, groups, n_splits=5):
    x = prepare_numeric(data, features)
    y = data[target].to_numpy(dtype=float)
    groups = pd.Series(groups).astype(str).to_numpy()
    cv = GroupKFold(n_splits=n_splits)

    rows = []
    oof_by_model = {}
    folds = np.full(len(data), -1, dtype=int)

    splits = list(cv.split(x, y, groups))
    for fold_id, (_, test_idx) in enumerate(splits):
        folds[test_idx] = fold_id

    for name in candidate_models():
        oof = np.full(len(data), np.nan, dtype=float)
        for train_idx, test_idx in splits:
            model = clone_model(name)
            model.fit(x.iloc[train_idx], y[train_idx])
            oof[test_idx] = model.predict(x.iloc[test_idx])
        metrics = {
            "Model": name,
            "n": len(data),
            "n_groups": int(pd.Series(groups).nunique()),
            "Grouped_CV_R2": r2_score(y, oof),
            "Grouped_CV_RMSE": math.sqrt(mean_squared_error(y, oof)),
            "Grouped_CV_MAE": mean_absolute_error(y, oof),
        }
        rows.append(metrics)
        oof_by_model[name] = oof

    metrics = pd.DataFrame(rows).sort_values(
        ["Grouped_CV_R2", "Grouped_CV_RMSE"], ascending=[False, True]
    )
    best = metrics.iloc[0]["Model"]
    return x, y, groups, splits, folds, metrics, best, oof_by_model[best]


def mc_shap_one(model, x, background, feature_names, rng, n_permutations):
    """Approximate interventional Shapley values for one observation."""
    p = len(feature_names)
    all_states = []
    orders = []
    for _ in range(n_permutations):
        bg = background[rng.integers(0, len(background))].copy()
        order = rng.permutation(p)
        states = [bg.copy()]
        current = bg.copy()
        for j in order:
            current = current.copy()
            current[j] = x[j]
            states.append(current)
        all_states.extend(states)
        orders.append(order)

    preds = model.predict(pd.DataFrame(all_states, columns=feature_names))
    phi = np.zeros(p, dtype=float)
    baselines = []
    cursor = 0
    for order in orders:
        path = preds[cursor : cursor + p + 1]
        baselines.append(path[0])
        differences = np.diff(path)
        for step, j in enumerate(order):
            phi[j] += differences[step]
        cursor += p + 1
    phi /= n_permutations
    prediction = float(model.predict(pd.DataFrame([x], columns=feature_names))[0])
    baseline = float(np.mean(baselines))
    additivity_error = float(phi.sum() - (prediction - baseline))
    return phi, prediction, baseline, additivity_error


def cross_validated_shap(
    data,
    task_name,
    target,
    features,
    groups,
    max_explained_rows=150,
    n_permutations=32,
):
    x, y, groups, splits, folds, metrics, best, oof = grouped_cv_select(
        data, target, features, groups
    )
    metrics.insert(0, "Task", task_name)
    metrics["Selected"] = metrics["Model"].eq(best)

    # Allocate approximately equal explanation samples to each fold.
    task_seed = int.from_bytes(
        hashlib.sha256(task_name.encode("utf-8")).digest()[:4], "little"
    )
    rng = np.random.default_rng(SEED + task_seed)
    per_fold = max(1, math.ceil(max_explained_rows / len(splits)))
    long_rows = []

    for fold_id, (train_idx, test_idx) in enumerate(splits):
        model = clone_model(best)
        model.fit(x.iloc[train_idx], y[train_idx])
        chosen = test_idx
        if len(chosen) > per_fold:
            chosen = rng.choice(chosen, size=per_fold, replace=False)
        background = x.iloc[train_idx].to_numpy(dtype=float)
        for row_idx in chosen:
            phi, prediction, baseline, error = mc_shap_one(
                model,
                x.iloc[row_idx].to_numpy(dtype=float),
                background,
                list(x.columns),
                rng,
                n_permutations,
            )
            for j, feature in enumerate(x.columns):
                long_rows.append(
                    {
                        "Task": task_name,
                        "Row_index": int(data.index[row_idx]),
                        "Fold": fold_id,
                        "Feature": feature,
                        "Feature_label": FEATURE_LABELS.get(feature, feature),
                        "Feature_value": float(x.iloc[row_idx, j]),
                        "Shapley_value": float(phi[j]),
                        "Prediction": prediction,
                        "Background_prediction": baseline,
                        "Observed": float(y[row_idx]),
                        "Additivity_error": error,
                    }
                )

    shap_long = pd.DataFrame(long_rows)
    importance_rows = []
    for (task, feature, label), group in shap_long.groupby(
        ["Task", "Feature", "Feature_label"], observed=True
    ):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            rho, pvalue = spearmanr(group["Feature_value"], group["Shapley_value"])
        importance_rows.append(
            {
                "Task": task,
                "Feature": feature,
                "Feature_label": label,
                "Mean_abs_Shapley": group["Shapley_value"].abs().mean(),
                "Mean_signed_Shapley": group["Shapley_value"].mean(),
                "Feature_SHAP_Spearman_rho": rho,
                "Feature_SHAP_Spearman_p": pvalue,
                "n_explained": group["Row_index"].nunique(),
            }
        )
    importance = pd.DataFrame(importance_rows).sort_values(
        ["Task", "Mean_abs_Shapley"], ascending=[True, False]
    )
    importance["Rank"] = (
        importance.groupby("Task")["Mean_abs_Shapley"]
        .rank(method="first", ascending=False)
        .astype(int)
    )

    predictions = data[
        ["Scope", "System", "Period", "Rotation", "CO2_scenario", "Year"]
        + (["Crop"] if "Crop" in data.columns else [])
    ].copy()
    predictions.insert(0, "Task", task_name)
    predictions["Observed"] = y
    predictions["OOF_prediction"] = oof
    predictions["Fold"] = folds

    meta = {
        "Task": task_name,
        "Target": target,
        "Features": features,
        "Selected_model": best,
        "n": int(len(data)),
        "n_groups": int(pd.Series(groups).nunique()),
        "n_explained": int(shap_long["Row_index"].nunique()),
        "n_permutations": n_permutations,
        "Maximum_abs_additivity_error": float(
            shap_long["Additivity_error"].abs().max()
        ),
    }
    return metrics, predictions, shap_long, importance, meta


def main():
    soc = pd.read_csv(SOC_FILE)
    yld = pd.read_csv(YIELD_FILE)

    for data in (soc, yld):
        data["Rotation_Spring"] = (data["Rotation"] == "Spring").astype(int)
        data["Period_Future"] = (data["Period"] == "Future").astype(int)

    tasks = []

    soc_common = soc[
        (soc["CO2_scenario"] == "Higher fixed")
        & soc["System"].isin(COMMON_SYSTEMS)
        & soc["Period"].isin(["Historical", "Future"])
    ].copy()
    tasks.append(
        (
            soc_common,
            "Annual SOC change — six complete systems, both periods",
            "SOC_change_t_C_ha_yr",
            SOC_FEATURES,
            soc_common["Period"] + "-" + soc_common["Year"].astype(str),
        )
    )

    soc_future = soc[
        (soc["CO2_scenario"] == "Higher fixed") & (soc["Period"] == "Future")
    ].copy()
    # Period_Future is constant in this sensitivity analysis and is removed.
    tasks.append(
        (
            soc_future,
            "Annual SOC change — all 11 systems, future period",
            "SOC_change_t_C_ha_yr",
            [f for f in SOC_FEATURES if f != "Period_Future"],
            soc_future["Year"].astype(str),
        )
    )

    yield_common = yld[
        (yld["CO2_scenario"] == "Higher fixed")
        & yld["System"].isin(COMMON_SYSTEMS)
        & yld["Period"].isin(["Historical", "Future"])
    ].copy()
    for crop in ["Wheat", "Barley", "Rapeseed oil"]:
        crop_data = yield_common[yield_common["Crop"] == crop].copy()
        tasks.append(
            (
                crop_data,
                f"{crop} yield — six complete systems, both periods",
                "Yield_t_ha",
                YIELD_FEATURES,
                crop_data["Period"] + "-" + crop_data["Year"].astype(str),
            )
        )

    all_metrics = []
    all_predictions = []
    all_shap = []
    all_importance = []
    metadata = []
    for data, name, target, features, groups in tasks:
        print(f"Running {name} (n={len(data)})")
        result = cross_validated_shap(
            data.reset_index(drop=True),
            name,
            target,
            features,
            groups.reset_index(drop=True),
        )
        metrics, predictions, shap_long, importance, meta = result
        all_metrics.append(metrics)
        all_predictions.append(predictions)
        all_shap.append(shap_long)
        all_importance.append(importance)
        metadata.append(meta)
        print(metrics.to_string(index=False))
        print(importance.head(8).to_string(index=False))

    pd.concat(all_metrics, ignore_index=True).to_csv(
        OUTDIR / "RA_process_model_grouped_CV_metrics.csv", index=False
    )
    pd.concat(all_predictions, ignore_index=True).to_csv(
        OUTDIR / "RA_process_model_OOF_predictions.csv", index=False
    )
    pd.concat(all_shap, ignore_index=True).to_csv(
        OUTDIR / "RA_process_SHAP_values.csv", index=False
    )
    pd.concat(all_importance, ignore_index=True).to_csv(
        OUTDIR / "RA_process_SHAP_importance.csv", index=False
    )
    (OUTDIR / "RA_process_SHAP_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
