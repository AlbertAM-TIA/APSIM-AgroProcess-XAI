# Mixed-effects/repeated-measures reanalysis for Table 15
# Muleke et al. regenerative-agriculture manuscript
#
# This script uses base R only. It therefore avoids the rlang-version conflict
# encountered with lmerTest/glmmTMB installations.
#
# Fixed effects:
#   Management × Climate period × Season
#
# Random blocking factor:
#   Climate year nested within climate period
#
# Management and Season are repeated within each climate year. The Error()
# structure supplies the correct denominator mean square for every fixed test.

options(contrasts = c("contr.sum", "contr.poly"))

input_file <- file.path("outputs", "anova_shap_raw", "RA_annual_SOC_process_data.csv")
output_dir <- file.path("outputs", "exploratory_repeated_measures")
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

systems <- c(
  "Baseline",
  "Simple cover crop",
  "Crop diversity",
  "Ideal farming system",
  "Most productive",
  "Least productive"
)

raw <- read.csv(input_file, check.names = FALSE, stringsAsFactors = FALSE)

dat <- raw[
  raw$System %in% systems &
    raw$Period %in% c("Historical", "Future") &
    raw$Rotation %in% c("Winter", "Spring") &
    raw$CO2_scenario == "Higher fixed",
]

dat$Management <- factor(dat$System, levels = systems)
dat$Period <- factor(dat$Period, levels = c("Historical", "Future"))
dat$Season <- factor(dat$Rotation, levels = c("Winter", "Spring"))
dat$ClimateYear <- interaction(
  dat$Period,
  dat$Year_index,
  drop = TRUE
)
dat$Annual_crop_output_t_ha <- dat$Total_crop_yield_kg_ha / 1000

# Balanced-design checks
cell_n <- with(dat, table(Management, Period, Season))
stopifnot(length(unique(as.vector(cell_n))) == 1L)
stopifnot(unique(as.vector(cell_n)) == 31L)
stopifnot(nrow(dat) == 744L)
stopifnot(!anyNA(dat$SOC_change_t_C_ha_yr))
stopifnot(!anyNA(dat$Annual_crop_output_t_ha))

fit_repeated <- function(response, data = dat) {
  formula_text <- paste0(
    response,
    " ~ Period * Management * Season + ",
    "Error(ClimateYear / (Management * Season))"
  )
  aov(as.formula(formula_text), data = data)
}

fit_soc <- fit_repeated("SOC_change_t_C_ha_yr")
fit_crop_output <- fit_repeated("Annual_crop_output_t_ha")

capture.output(
  summary(fit_soc),
  file = file.path(output_dir, "Table15_SOC_aov_summary_R.txt")
)
capture.output(
  summary(fit_crop_output),
  file = file.path(output_dir, "Table15_crop_output_aov_summary_R.txt")
)

# Extract the fixed-effect tests from the appropriate random-error strata.
extract_stratum <- function(summary_object, stratum, outcome) {
  tab <- as.data.frame(
    summary_object[[stratum]][[1]],
    check.names = FALSE
  )
  tab$Effect_R <- rownames(tab)
  rownames(tab) <- NULL
  tab <- tab[tab$Effect_R != "Residuals", , drop = FALSE]

  denominator_df <- summary_object[[stratum]][[1]][
    "Residuals",
    "Df"
  ]

  data.frame(
    Outcome = outcome,
    Effect_R = tab$Effect_R,
    Numerator_df = tab$Df,
    Denominator_df = denominator_df,
    F = tab[["F value"]],
    p_value = tab[["Pr(>F)"]],
    Error_stratum = sub("^Error: ", "", stratum),
    stringsAsFactors = FALSE
  )
}

extract_fixed_tests <- function(fit, outcome) {
  sm <- summary(fit)
  pieces <- list(
    extract_stratum(sm, "Error: ClimateYear", outcome),
    extract_stratum(
      sm,
      "Error: ClimateYear:Management",
      outcome
    ),
    extract_stratum(
      sm,
      "Error: ClimateYear:Season",
      outcome
    ),
    extract_stratum(
      sm,
      "Error: ClimateYear:Management:Season",
      outcome
    )
  )
  out <- do.call(rbind, pieces)

  labels <- c(
    "Management" = "Management",
    "Period" = "Climate period",
    "Season" = "Season",
    "Period:Management" = "Management × Climate period",
    "Management:Period" = "Management × Climate period",
    "Management:Season" = "Management × Season",
    "Period:Season" = "Climate period × Season",
    "Season:Period" = "Climate period × Season",
    "Period:Management:Season" =
      "Management × Climate period × Season",
    "Management:Period:Season" =
      "Management × Climate period × Season"
  )
  out$Effect <- unname(labels[out$Effect_R])
  out
}

results <- rbind(
  extract_fixed_tests(fit_soc, "Annual SOC change"),
  extract_fixed_tests(
    fit_crop_output,
    "Annual crop output"
  )
)

effect_order <- c(
  "Management",
  "Climate period",
  "Season",
  "Management × Climate period",
  "Management × Season",
  "Climate period × Season",
  "Management × Climate period × Season"
)
results$Effect <- factor(
  results$Effect,
  levels = effect_order,
  ordered = TRUE
)
results <- results[
  order(results$Outcome, results$Effect),
  c(
    "Outcome",
    "Effect",
    "Numerator_df",
    "Denominator_df",
    "F",
    "p_value",
    "Error_stratum"
  )
]

write.csv(
  results,
  file.path(
    output_dir,
    "Table15_mixed_effects_inferential_results_R.csv"
  ),
  row.names = FALSE
)

print(results, row.names = FALSE)

# Interpretation of the crop-output panel:
# Annual_crop_output_t_ha includes zero-crop years and excludes forage/ley
# biomass. It is a whole-system annual crop-output sensitivity analysis, not a
# crop-specific wheat/barley/oilseed-rape harvest-yield test. Crop-specific
# harvest years are not synchronized across management systems, so a direct
# crop-specific repeated-measures F test would confound Management with
# ClimateYear.
