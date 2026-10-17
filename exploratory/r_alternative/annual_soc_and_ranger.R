# Improved ANOVA and SHAP workflow for annual APSIM outputs
# Muleke et al. regenerative-agriculture analysis
#
# Inputs are the harmonised annual files generated from the supplied APSIM
# DailyReport archives. This script does not treat missing historical systems
# as zero and does not report p-values from the unreplicated cumulative model.

rm(list = ls())
options(stringsAsFactors = F)

required_packages <- c(
  "dplyr", "tidyr", "readr", "purrr", "tibble", "ggplot2",
  "glmmTMB", "emmeans", "rsample", "ranger", "fastshap", "rlang"
)
missing_packages <- required_packages[
  !vapply(required_packages, requireNamespace, logical(1), quietly = TRUE)
]
if (length(missing_packages) > 0) {
  stop(
    "Install the following packages before running this script: ",
    paste(missing_packages, collapse = ", ")
  )
}

library(dplyr)
library(tidyr)
library(readr)
library(purrr)
library(tibble)
library(ggplot2)

library("devEMF")
library("dplyr")
library("data.table")
library("ggplot2")
library("lattice")
library("ggpubr")
library("gridExtra")
library("grid")
library("rio")
library("ggthemes")
library("writexl")
library("scales")
library("wesanderson")
library("ggsci")
library("viridis")
library("jcolors")
library("gplots")
library("tinytex")
library("readxl")
library("ggh4x")
library("lemon")
library("tidyr")
library("tidyverse")
library("tidytext")

set.seed(20260726)
options(contrasts = c("contr.sum", "contr.poly"))

output_dir <- Sys.getenv("RA_RESULTS_DIR", "outputs/anova_shap_raw")
soc_file <- file.path(output_dir, "RA_annual_SOC_process_data.csv")
yield_file <- file.path(
  output_dir, "RA_annual_crop_yield_process_data.csv"
)

soc <- readr::read_csv(soc_file, show_col_types = FALSE)
yield <- readr::read_csv(yield_file, show_col_types = FALSE)

common_systems <- c(
  "Baseline",
  "Simple cover crop",
  "Crop diversity",
  "Ideal farming system",
  "Most productive",
  "Least productive"
)

# ---------------------------------------------------------------------------
# Coverage checks
# ---------------------------------------------------------------------------

soc_coverage <- soc |>
  count(Period, System, CO2_scenario, Rotation, name = "n_years") |>
  arrange(Period, System, CO2_scenario, Rotation)

readr::write_csv(
  soc_coverage,
  file.path(output_dir, "RA_SOC_coverage_check_R.csv")
)

soc_common <- soc |>
  filter(
    CO2_scenario == "Higher fixed",
    System %in% common_systems,
    Period %in% c("Historical", "Future")
  ) |>
  mutate(
    System = factor(System, levels = common_systems),
    Period = factor(Period, levels = c("Historical", "Future")),
    Rotation = factor(Rotation, levels = c("Winter", "Spring")),
    ClimateYear = interaction(Period, Year, drop = TRUE),
    Series = interaction(System, Period, Rotation, drop = TRUE),
    Year_factor = factor(Year_index)
  )

cell_check <- soc_common |>
  count(System, Period, Rotation, name = "n_years")
stopifnot(nrow(cell_check) == length(common_systems) * 2L * 2L)
stopifnot(all(cell_check$n_years == 31L))

# ---------------------------------------------------------------------------
# Descriptive sum-of-squares decomposition
# ---------------------------------------------------------------------------

# Annual response: retain every main effect and two-way interaction; the
# omitted three-way term is the residual.
fit_annual_ss <- lm(
  SOC_change_t_C_ha_yr ~
    (System + ClimateYear + Rotation)^2,
  data = soc_common
)

annual_ss <- as.data.frame(anova(fit_annual_ss)) |>
  rownames_to_column("Term") |>
  transmute(
    Term,
    df = Df,
    SS = `Sum Sq`,
    Percent_total_SS = 100 * SS / sum(SS)
  )

# Cumulative endpoint: one 31-year value per complete cell.
soc_total <- soc_common |>
  arrange(System, Period, Rotation, Year) |>
  group_by(System, Period, Rotation) |>
  summarise(
    SOC_start_t_C_ha = first(SOC_start_t_C_ha),
    SOC_end_t_C_ha = last(SOC_end_t_C_ha),
    n_years = n_distinct(Year),
    .groups = "drop"
  ) |>
  mutate(
    SOC_accrual_31yr_t_C_ha =
      SOC_end_t_C_ha - SOC_start_t_C_ha
  )
stopifnot(all(soc_total$n_years == 31L))

fit_total_ss <- lm(
  SOC_accrual_31yr_t_C_ha ~
    (System + Period + Rotation)^2,
  data = soc_total
)

total_ss <- as.data.frame(anova(fit_total_ss)) |>
  rownames_to_column("Term") |>
  transmute(
    Term,
    df = Df,
    SS = `Sum Sq`,
    Percent_total_SS = 100 * SS / sum(SS)
  )

variance_table <- bind_rows(
  mutate(
    annual_ss,
    Analysis = "Annual SOC change"
  ),
  mutate(
    total_ss,
    Analysis = "31-year SOC accrual"
  )
) |>
  select(Analysis, everything())

readr::write_csv(
  variance_table,
  file.path(output_dir, "RA_variance_decomposition_R.csv")
)

# ---------------------------------------------------------------------------
# Repeated annual model
# ---------------------------------------------------------------------------

# The shared ClimateYear random intercept accounts for all systems being
# exposed to the same simulated climate year. The AR(1) term represents serial
# correlation within each system-period-rotation trajectory.
fit_soc_mixed <- glmmTMB::glmmTMB(
  SOC_change_t_C_ha_yr ~ System * Period * Rotation +
    (1 | ClimateYear) +
    ar1(Year_factor + 0 | Series),
  data = soc_common,
  REML = TRUE,
  family = gaussian()
)

capture.output(
  summary(fit_soc_mixed),
  file = file.path(output_dir, "RA_SOC_mixed_model_summary.txt")
)

soc_emmeans <- emmeans::emmeans(
  fit_soc_mixed,
  ~ System | Period * Rotation
) |>
  as.data.frame()

readr::write_csv(
  soc_emmeans,
  file.path(output_dir, "RA_SOC_mixed_model_emmeans.csv")
)

# ---------------------------------------------------------------------------
# Grouped-cross-validation and SHAP helper
# ---------------------------------------------------------------------------

fit_grouped_ranger_shap <- function(
  data,
  outcome,
  features,
  group_column,
  task_name,
  v = 5,
  nsim = 64
) {
  analysis_data <- data |>
    select(
      Scope, System, Period, Rotation, CO2_scenario,
      Year, any_of("Crop"), all_of(outcome), all_of(features),
      all_of(group_column)
    ) |>
    mutate(
      across(all_of(features), as.numeric)
    ) |>
    drop_na(all_of(outcome), all_of(features), all_of(group_column))

  folds <- rsample::group_vfold_cv(
    analysis_data,
    group = !!rlang::sym(group_column),
    v = v
  )

  fold_results <- purrr::imap(
    folds$splits,
    function(split, fold_number) {
      train <- rsample::analysis(split)
      test <- rsample::assessment(split)

      model_data <- train |>
        select(all_of(outcome), all_of(features))

      model <- ranger::ranger(
        formula = reformulate(features, response = outcome),
        data = model_data,
        num.trees = 600,
        mtry = max(1L, floor(sqrt(length(features)))),
        min.node.size = 5,
        importance = "none",
        seed = 20260726 + fold_number
      )

      pred_wrapper <- function(object, newdata) {
        predict(object, data = newdata)$predictions
      }

      prediction <- pred_wrapper(model, test[, features, drop = FALSE])

      shap_matrix <- fastshap::explain(
        object = model,
        X = train[, features, drop = FALSE],
        pred_wrapper = pred_wrapper,
        newdata = test[, features, drop = FALSE],
        nsim = nsim,
        adjust = TRUE
      )

      shap_long <- as.data.frame(shap_matrix) |>
        mutate(.row = row_number()) |>
        pivot_longer(
          cols = all_of(features),
          names_to = "Feature",
          values_to = "Shapley_value"
        ) |>
        left_join(
          test |>
            select(all_of(features)) |>
            mutate(.row = row_number()) |>
            pivot_longer(
              cols = all_of(features),
              names_to = "Feature",
              values_to = "Feature_value"
            ),
          by = c(".row", "Feature")
        ) |>
        mutate(Task = task_name, Fold = fold_number)

      list(
        predictions = test |>
          mutate(
            Task = task_name,
            Fold = fold_number,
            Observed = .data[[outcome]],
            OOF_prediction = prediction
          ),
        shap = shap_long
      )
    }
  )

  predictions <- bind_rows(map(fold_results, "predictions"))
  shap_values <- bind_rows(map(fold_results, "shap"))

  metrics <- tibble(
    Task = task_name,
    n = nrow(predictions),
    Grouped_CV_R2 =
      1 - sum((predictions$Observed - predictions$OOF_prediction)^2) /
      sum((predictions$Observed - mean(predictions$Observed))^2),
    Grouped_CV_RMSE =
      sqrt(mean((predictions$Observed - predictions$OOF_prediction)^2)),
    Grouped_CV_MAE =
      mean(abs(predictions$Observed - predictions$OOF_prediction))
  )

  importance <- shap_values |>
    group_by(Task, Feature) |>
    summarise(
      Mean_abs_Shapley = mean(abs(Shapley_value)),
      Mean_signed_Shapley = mean(Shapley_value),
      .groups = "drop"
    ) |>
    arrange(desc(Mean_abs_Shapley))

  list(
    metrics = metrics,
    predictions = predictions,
    shap = shap_values,
    importance = importance
  )
}

soc_features <- c(
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
  "Total_crop_yield_kg_ha"
)

soc_shap <- fit_grouped_ranger_shap(
  data = soc_common,
  outcome = "SOC_change_t_C_ha_yr",
  features = soc_features,
  group_column = "ClimateYear",
  task_name = "Annual SOC change"
)

yield_common <- yield |>
  filter(
    CO2_scenario == "Higher fixed",
    System %in% common_systems,
    Period %in% c("Historical", "Future")
  ) |>
  mutate(
    ClimateYear = interaction(Period, Year, drop = TRUE),
    Rotation_Spring = as.numeric(Rotation == "Spring"),
    Period_Future = as.numeric(Period == "Future")
  )

yield_features <- c(
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
  "Period_Future"
)

yield_shap <- c("Wheat", "Barley", "Rapeseed oil") |>
  set_names() |>
  map(
    ~ fit_grouped_ranger_shap(
      data = filter(yield_common, Crop == .x),
      outcome = "Yield_t_ha",
      features = yield_features,
      group_column = "ClimateYear",
      task_name = paste(.x, "yield")
    )
  )

all_shap_results <- c(list(SOC = soc_shap), yield_shap)

readr::write_csv(
  bind_rows(map(all_shap_results, "metrics")),
  file.path(output_dir, "RA_SHAP_grouped_CV_metrics_R.csv")
)
readr::write_csv(
  bind_rows(map(all_shap_results, "importance")),
  file.path(output_dir, "RA_SHAP_importance_R.csv")
)
readr::write_csv(
  bind_rows(map(all_shap_results, "shap")),
  file.path(output_dir, "RA_SHAP_values_R.csv")
)
