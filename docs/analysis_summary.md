# Analysis summary

## 1. Annual data and completeness

`build_annual_ra_dataset.py` aggregates source APSIM daily reports into annual soil-carbon and crop-process datasets. It retains system, scope, climate period, rotation, CO₂ scenario and year identifiers, and writes coverage audits. The source daily reports/workbooks are not in this public release. Missing historical systems must not be treated as zero or silently imputed.

## 2. Timescale-dependent SOC variance decomposition

`improved_variance_analysis.py` fits sum-to-zero main-effect and two-way interaction blocks using least squares. Term sums of squares are calculated by dropping each block from the full model. Shares use corrected total sums of squares as denominator. Annual change and end-minus-start 31-year stock change are different response definitions.

The historical/future comparison uses six complete systems; the future-only sensitivity uses eleven. Annual climate-year factors differ from the climate-period factor used for long-term change. The omitted three-way interaction is residual, not independently replicated experimental error. The routine assumes a complete balanced factorial design; its built-in group-count check alone does not detect every entirely absent cell, so inspect coverage audits before use.

## 3. Grouped process prediction and Shapley explanations

`process_shap_analysis.py` compares Extra Trees and histogram gradient boosting using five folds grouped by climate period/year. SOC and each crop yield are modelled separately. System identity is excluded from predictors. Candidate selection uses pooled out-of-fold R² with RMSE and MAE also reported.

Held-out observations are explained using Monte Carlo interventional Shapley estimates, training-fold background rows and random feature orderings. This implementation does not require the external `shap` package. Global importance averages absolute contributions; the beeswarm adds signed contributions and feature values. A telescoping additivity check tests numerical reconstruction of each prediction.

### Boundaries of interpretation

- Predictions concern APSIM-generated responses, not independent field observations.
- Correlated process variables and interventional feature substitutions complicate causal interpretation.
- Candidate selection and reported out-of-fold performance use the same folds; this is not nested model-selection validation.
- The supplied Python implementation calculates median filling before splitting into folds. If inputs contain missing predictors, preprocessing should be fitted within training folds before claiming leakage-free validation. This behaviour is documented, not silently changed in this packaging task.
- Reported Shapley estimates use sampling and depend on background choice and random seed.
- The older R alternative uses ranger/fastshap and mixed modelling; it does not reproduce the selected Extra Trees/gradient-boosting pipeline identically.

## 4. Presentation and table production

Separate scripts handle variance donuts, global predictor importance, signed beeswarms and Word table formatting. The public release contains the code, not final images or manuscript result tables. The preparation changes file organisation and local paths; it does not rerun or update the scientific findings.
