# =============================================================================
# Supplementary figure. Direction and dispersion of SHAP contributions
#
# Standalone base-R script requiring no contributed R packages.
# Inputs:
#   RA_process_SHAP_values.csv
#   RA_process_SHAP_importance.csv
# Outputs:
#   PNG, TIFF, PDF and SVG versions of the refined SHAP beeswarm figure.
# =============================================================================

input_directory <- Sys.getenv("RA_RESULTS_DIR", "outputs/anova_shap_raw")
output_directory <- input_directory
dir.create(output_directory, recursive = TRUE, showWarnings = FALSE)

shap_file <- file.path(input_directory, "RA_process_SHAP_values.csv")
importance_file <- file.path(
  input_directory,
  "RA_process_SHAP_importance.csv"
)

shap_data <- read.csv(
  shap_file,
  stringsAsFactors = FALSE,
  check.names = FALSE,
  fileEncoding = "UTF-8"
)
importance <- read.csv(
  importance_file,
  stringsAsFactors = FALSE,
  check.names = FALSE,
  fileEncoding = "UTF-8"
)

task_information <- data.frame(
  Task = c(
    "Annual SOC change — six complete systems, both periods",
    "Wheat yield — six complete systems, both periods",
    "Barley yield — six complete systems, both periods",
    "Rapeseed oil yield — six complete systems, both periods"
  ),
  Panel = c("A", "B", "C", "D"),
  Outcome = c("SOC", "Wheat", "Barley", "Rapeseed oil"),
  X_limit = c(1.2, 1.2, 3.0, 2.0),
  Tick_step = c(0.5, 0.5, 1.0, 1.0),
  Show_x_title = c(FALSE, FALSE, TRUE, TRUE),
  stringsAsFactors = FALSE
)

short_labels <- c(
  "Annual soil evaporation" = "Soil evap.",
  "Mean surface residue C" = "Residue C",
  "Starting SOC" = "Initial SOC",
  "Minimum soil water" = "Min. soil water",
  "Change in surface residue C" = "Δ residue C",
  "Annual crop yield" = "Crop yield",
  "Maximum crop biomass" = "Max. biomass",
  "Minimum temperature factor" = "Min. temp. factor",
  "Plant-available water capacity" = "PAWC",
  "Mean soil water" = "Mean soil water",
  "Minimum water-stress factor" = "Min. water stress",
  "Minimum N-stress factor" = "Min. N stress",
  "Mean water-stress factor" = "Mean water stress",
  "Crop active days" = "Active days",
  "In-crop soil evaporation" = "Soil evap.",
  "Harvest day of year" = "Harvest DOY",
  "Annual SOC change" = "SOC change",
  "Maximum leaf-area index" = "Max. LAI",
  "Mean CO2 growth factor" = "CO₂ growth factor"
)

feature_colours <- grDevices::colorRampPalette(
  c("#2946B6", "#6F92F3", "#E6E6E6", "#F28E6B", "#B40426")
)(256)

top_features <- function(task) {
  result <- importance[
    importance$Task == task & importance$Rank <= 6,
    ,
    drop = FALSE
  ]
  result <- result[order(result$Rank), , drop = FALSE]
  result$Feature_label
}

feature_colour_index <- function(values) {
  finite_values <- values[is.finite(values)]
  if (
    length(finite_values) == 0 ||
      max(finite_values) <= min(finite_values)
  ) {
    return(rep(128L, length(values)))
  }
  scaled <- (values - min(finite_values)) /
    (max(finite_values) - min(finite_values))
  pmax(1L, pmin(256L, as.integer(round(1 + 255 * scaled))))
}

add_panel_strip <- function(panel, outcome, n_features) {
  user_coordinates <- par("usr")
  strip_bottom <- n_features + 0.79
  strip_top <- n_features + 1.65

  rect(
    xleft = user_coordinates[1],
    ybottom = strip_bottom,
    xright = user_coordinates[2],
    ytop = strip_top,
    col = "#D9D9D9",
    border = "black",
    lwd = 1.1,
    xpd = NA
  )
  text(
    x = user_coordinates[1] + 0.018 * diff(user_coordinates[1:2]),
    y = mean(c(strip_bottom, strip_top)),
    labels = panel,
    adj = c(0, 0.5),
    cex = 1.48,
    font = 2,
    col = "black",
    xpd = NA
  )
  text(
    x = mean(user_coordinates[1:2]),
    y = mean(c(strip_bottom, strip_top)),
    labels = outcome,
    cex = 1.48,
    font = 2,
    col = "black",
    xpd = NA
  )
}

draw_beeswarm_panel <- function(
  task,
  panel,
  outcome,
  x_limit,
  tick_step,
  show_x_title
) {
  features <- top_features(task)
  missing_labels <- features[!features %in% names(short_labels)]
  if (length(missing_labels) > 0) {
    stop(
      "Missing abbreviated labels: ",
      paste(missing_labels, collapse = ", ")
    )
  }

  n_features <- length(features)
  y_positions <- rev(seq_len(n_features))
  tick_limit <- if (isTRUE(all.equal(x_limit, 1.2))) 1.0 else x_limit
  x_ticks <- seq(-tick_limit, tick_limit, by = tick_step)

  bottom_margin <- if (show_x_title) 3.2 else 1.7
  par(
    mar = c(bottom_margin, 7.65, 3.35, 0.55),
    family = "sans",
    fg = "black",
    col.axis = "black",
    col.lab = "black",
    mgp = c(2.1, 0.48, 0),
    tcl = -0.22,
    xpd = FALSE
  )

  plot.new()
  plot.window(
    xlim = c(-x_limit, x_limit),
    ylim = c(0.35, n_features + 0.65),
    xaxs = "i",
    yaxs = "i"
  )

  abline(v = x_ticks, col = "#D9D9D9", lwd = 0.8)

  set.seed(20260726 + match(task, task_information$Task))
  for (feature_index in seq_along(features)) {
    feature <- features[feature_index]
    group <- shap_data[
      shap_data$Task == task &
        shap_data$Feature_label == feature,
      ,
      drop = FALSE
    ]
    colour_indices <- feature_colour_index(group$Feature_value)
    order_index <- sample(seq_len(nrow(group)))
    jitter <- stats::rnorm(nrow(group), mean = 0, sd = 0.085)

    points(
      x = group$Shapley_value[order_index],
      y = y_positions[feature_index] + jitter[order_index],
      pch = 16,
      cex = 0.82,
      col = grDevices::adjustcolor(
        feature_colours[colour_indices[order_index]],
        alpha.f = 0.82
      )
    )
  }

  abline(v = 0, col = "black", lwd = 1.15)
  axis(
    1,
    at = x_ticks,
    labels = format(x_ticks, trim = TRUE, nsmall = 0),
    cex.axis = 1.06,
    col.axis = "black",
    col = "black",
    lwd = 1.1,
    lwd.ticks = 1.1
  )
  axis(
    2,
    at = y_positions,
    labels = unname(short_labels[features]),
    las = 1,
    tick = TRUE,
    cex.axis = 1.22,
    col.axis = "black",
    col = "black",
    lwd = 1.1,
    lwd.ticks = 1.1,
    hadj = 1
  )

  segments(
    x0 = -x_limit,
    y0 = 0.35,
    x1 = x_limit,
    y1 = 0.35,
    col = "black",
    lwd = 1.1
  )
  segments(
    x0 = -x_limit,
    y0 = 0.35,
    x1 = -x_limit,
    y1 = n_features + 0.65,
    col = "black",
    lwd = 1.1
  )

  if (show_x_title) {
    mtext(
      "SHAP value",
      side = 1,
      line = 2.0,
      cex = 1.25,
      col = "black"
    )
  }

  add_panel_strip(panel, outcome, n_features)
}

draw_feature_legend <- function() {
  par(
    mar = c(4.8, 0.7, 4.0, 4.2),
    family = "sans",
    fg = "black",
    col.axis = "black",
    col.lab = "black"
  )
  plot.new()
  plot.window(xlim = c(0, 1), ylim = c(0, 1), xaxs = "i", yaxs = "i")

  boundaries <- seq(0.12, 0.88, length.out = 257)
  for (index in seq_len(256)) {
    rect(
      xleft = 0.18,
      ybottom = boundaries[index],
      xright = 0.52,
      ytop = boundaries[index + 1],
      col = feature_colours[index],
      border = NA
    )
  }
  rect(
    xleft = 0.18,
    ybottom = 0.12,
    xright = 0.52,
    ytop = 0.88,
    border = "black",
    lwd = 1.0
  )
  text(0.60, 0.12, "Low", adj = c(0, 0.5), cex = 1.06, col = "black")
  text(0.60, 0.88, "High", adj = c(0, 0.5), cex = 1.06, col = "black")
  text(
    0.93,
    0.50,
    "Feature value",
    srt = 90,
    cex = 1.20,
    col = "black"
  )
}

plot_beeswarm <- function() {
  old_par <- par(no.readonly = TRUE)
  on.exit(par(old_par), add = TRUE)

  layout(
    matrix(c(1, 2, 5, 3, 4, 5), nrow = 2, byrow = TRUE),
    widths = c(1, 1, 0.095),
    heights = c(1, 1)
  )

  for (index in seq_len(nrow(task_information))) {
    draw_beeswarm_panel(
      task = task_information$Task[index],
      panel = task_information$Panel[index],
      outcome = task_information$Outcome[index],
      x_limit = task_information$X_limit[index],
      tick_step = task_information$Tick_step[index],
      show_x_title = task_information$Show_x_title[index]
    )
  }
  draw_feature_legend()
}

save_beeswarm <- function(output_stem, width = 10.5, height = 7.4) {
  grDevices::png(
    filename = paste0(output_stem, ".png"),
    width = width,
    height = height,
    units = "in",
    res = 600,
    bg = "white",
    type = "cairo-png"
  )
  plot_beeswarm()
  grDevices::dev.off()

  grDevices::tiff(
    filename = paste0(output_stem, ".tiff"),
    width = width,
    height = height,
    units = "in",
    res = 600,
    compression = "lzw",
    bg = "white"
  )
  plot_beeswarm()
  grDevices::dev.off()

  grDevices::cairo_pdf(
    filename = paste0(output_stem, ".pdf"),
    width = width,
    height = height,
    family = "sans",
    bg = "white"
  )
  plot_beeswarm()
  grDevices::dev.off()

  grDevices::svg(
    filename = paste0(output_stem, ".svg"),
    width = width,
    height = height,
    bg = "white"
  )
  plot_beeswarm()
  grDevices::dev.off()
}

output_stem <- file.path(
  output_directory,
  "FigureS_SHAP_beeswarm_refined_R"
)

save_beeswarm(output_stem)
