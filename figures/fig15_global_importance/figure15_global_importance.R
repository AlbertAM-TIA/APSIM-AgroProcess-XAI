# =============================================================================
# Figure 15. Global SHAP importance with a common 0–1 scale
#
# Standalone, dependency-free base-R script.
# Input:  RA_process_SHAP_importance.csv
# Output: PNG, TIFF, PDF and SVG versions of Figure 15.
# =============================================================================
rm(list = ls())
options(stringsAsFactors = F)

input_directory <- Sys.getenv("RA_RESULTS_DIR", "outputs/anova_shap_raw")
output_directory <- input_directory
dir.create(output_directory, recursive = TRUE, showWarnings = FALSE)

shap_file <- file.path(
  input_directory,
  "RA_process_SHAP_importance.csv"
)

text_colour <- "black"
grid_colour <- "#D8D8D8"
strip_colour <- "#D9D9D9"

# Bright Plasma colours sampled away from the near-black lower endpoint.
# The ten saturated shades map to the common x-axis intervals
# (0.0, 0.1], ..., (0.9, 1.0]. Values are included directly so the script
# remains dependency-free.
plasma_bright <- c(
  "#38049A",
  "#6100A7",
  "#8606A6",
  "#A72197",
  "#C33D80",
  "#DA5A6A",
  "#EB7655",
  "#F9973F",
  "#FEBB2B",
  "#F7E425"
)

shap <- read.csv(
  shap_file,
  stringsAsFactors = FALSE,
  check.names = FALSE,
  fileEncoding = "UTF-8"
)

required_columns <- c(
  "Task",
  "Feature_label",
  "Mean_abs_Shapley",
  "Rank"
)

missing_columns <- setdiff(required_columns, names(shap))
if (length(missing_columns) > 0L) {
  stop(
    "SHAP input is missing: ",
    paste(missing_columns, collapse = ", ")
  )
}

short_labels <- c(
  "Annual soil evaporation" = "Soil evap.",
  "Mean surface residue C" = "Residue C",
  "Starting SOC" = "Initial SOC",
  "Minimum soil water" = "Min. soil water",
  "Change in surface residue C" = "\u0394 residue C",
  "Annual crop yield" = "Crop yield",
  "Mineral N applied" = "Mineral N",
  "Maximum crop biomass" = "Max. biomass",
  "Minimum temperature factor" = "Min. temp. factor",
  "Plant-available water capacity" = "PAWC",
  "Mean soil water" = "Mean soil water",
  "Minimum water-stress factor" = "Min. water stress",
  "Minimum N-stress factor" = "Min. N stress",
  "Maximum leaf-area index" = "Max. LAI",
  "Mean water-stress factor" = "Mean water stress",
  "Crop active days" = "Active days",
  "In-crop soil evaporation" = "Soil evap.",
  "Harvest day of year" = "Harvest DOY",
  "Annual SOC change" = "SOC change",
  "Mean CO2 growth factor" = "CO2 growth factor"
)

task_information <- data.frame(
  Task = c(
    "Annual SOC change \u2014 six complete systems, both periods",
    "Wheat yield \u2014 six complete systems, both periods",
    "Barley yield \u2014 six complete systems, both periods",
    "Rapeseed oil yield \u2014 six complete systems, both periods"
  ),
  Panel = c("A", "B", "C", "D"),
  Outcome = c("SOC", "Wheat", "Barley", "Rapeseed oil"),
  Show_x_axis = c(FALSE, FALSE, TRUE, TRUE),
  stringsAsFactors = FALSE
)

top_shap <- do.call(
  rbind,
  lapply(seq_len(nrow(task_information)), function(index) {
    task <- task_information$Task[index]
    result <- shap[
      shap$Task == task & shap$Rank <= 7,
      ,
      drop = FALSE
    ]
    result <- result[order(result$Rank), , drop = FALSE]
    result$Abbreviation <- unname(short_labels[result$Feature_label])

    if (anyNA(result$Abbreviation)) {
      stop(
        "Missing SHAP abbreviations: ",
        paste(
          unique(result$Feature_label[is.na(result$Abbreviation)]),
          collapse = ", "
        )
      )
    }

    result
  })
)

draw_shap_panel <- function(
  panel_data,
  panel_label,
  outcome,
  show_x_axis
) {
  panel_data <- panel_data[order(panel_data$Rank), , drop = FALSE]
  n_features <- nrow(panel_data)
  y_positions <- rev(seq_len(n_features))
  values <- panel_data$Mean_abs_Shapley
  x_ticks <- seq(0, 1, by = 0.1)

  # Top panels use a smaller bottom margin because their x scale is suppressed.
  bottom_margin <- if (show_x_axis) 3.15 else 0.85

  par(
    mar = c(bottom_margin, 8.35, 3.25, 0.55),
    family = "sans",
    fg = text_colour,
    col.axis = text_colour,
    col.lab = text_colour,
    mgp = c(2.1, 0.42, 0),
    tcl = -0.22,
    xpd = FALSE
  )

  plot.new()
  plot.window(
    xlim = c(0, 1),
    ylim = c(0.35, n_features + 0.65),
    xaxs = "i",
    yaxs = "i"
  )

  abline(
    v = x_ticks,
    col = grid_colour,
    lwd = 0.85
  )

  # Each bar uses the same horizontal colour mapping. Colours therefore
  # correspond to Mean |SHAP| positions, rather than predictor categories.
  for (bar_index in seq_along(values)) {
    for (band_index in seq_along(plasma_bright)) {
      x_left <- (band_index - 1) / 10
      x_right <- min(values[bar_index], band_index / 10)

      if (x_right > x_left) {
        rect(
          xleft = x_left,
          ybottom = y_positions[bar_index] - 0.34,
          xright = x_right,
          ytop = y_positions[bar_index] + 0.34,
          col = plasma_bright[band_index],
          border = NA
        )
      }
    }

    rect(
      xleft = 0,
      ybottom = y_positions[bar_index] - 0.34,
      xright = values[bar_index],
      ytop = y_positions[bar_index] + 0.34,
      col = NA,
      border = "black",
      lwd = 1.0
    )
  }

  if (show_x_axis) {
    axis(
      1,
      at = x_ticks,
      labels = sprintf("%.1f", x_ticks),
      cex.axis = 1.06,
      col.axis = text_colour,
      col = text_colour,
      lwd = 1.1,
      lwd.ticks = 1.1
    )
  }

  # Category ticks are visible, and labels sit close to the y-axis line.
  axis(
    2,
    at = y_positions,
    labels = panel_data$Abbreviation,
    las = 1,
    tick = TRUE,
    cex.axis = 1.25,
    col.axis = text_colour,
    col = text_colour,
    lwd = 1.1,
    lwd.ticks = 1.1,
    hadj = 1
  )

  segments(
    x0 = 0,
    y0 = 0.35,
    x1 = 1,
    y1 = 0.35,
    col = text_colour,
    lwd = 1.1
  )

  segments(
    x0 = 0,
    y0 = 0.35,
    x1 = 0,
    y1 = n_features + 0.65,
    col = text_colour,
    lwd = 1.1
  )

  for (label_index in seq_along(values)) {
    if (values[label_index] >= 0.96) {
      label_text <- sprintf("%.2f", values[label_index])
      label_x <- values[label_index] - 0.012
      label_adj <- c(1, 0.5)
      label_xpd <- FALSE

      label_width <- strwidth(label_text, cex = 1.12, units = "user")
      label_height <- strheight(label_text, cex = 1.12, units = "user")
      rect(
        xleft = label_x - label_width - 0.006,
        ybottom = y_positions[label_index] - 0.62 * label_height,
        xright = label_x + 0.004,
        ytop = y_positions[label_index] + 0.62 * label_height,
        col = "white",
        border = NA
      )
    } else {
      label_text <- sprintf("%.2f", values[label_index])
      label_x <- min(values[label_index] + 0.014, 0.985)
      label_adj <- c(0, 0.5)
      label_xpd <- FALSE
    }

    text(
      x = label_x,
      y = y_positions[label_index],
      labels = label_text,
      adj = label_adj,
      cex = 1.12,
      col = text_colour,
      xpd = label_xpd
    )
  }

  user_coordinates <- par("usr")
  strip_bottom <- n_features + 0.82
  strip_top <- n_features + 1.70

  rect(
    xleft = user_coordinates[1],
    ybottom = strip_bottom,
    xright = user_coordinates[2],
    ytop = strip_top,
    col = strip_colour,
    border = "black",
    lwd = 1.0,
    xpd = NA
  )

  text(
    x = user_coordinates[1] + 0.018 * diff(user_coordinates[1:2]),
    y = mean(c(strip_bottom, strip_top)),
    labels = panel_label,
    adj = c(0, 0.5),
    cex = 1.48,
    font = 2,
    col = text_colour,
    xpd = NA
  )

  text(
    x = mean(user_coordinates[1:2]),
    y = mean(c(strip_bottom, strip_top)),
    labels = outcome,
    cex = 1.48,
    font = 2,
    col = text_colour,
    xpd = NA
  )
}

plot_figure15 <- function() {
  old_par <- par(no.readonly = TRUE)
  on.exit(par(old_par), add = TRUE)

  # Layout margins are kept compact so the panels read as one figure.
  layout(
    matrix(1:4, nrow = 2, byrow = TRUE),
    widths = c(1, 1),
    heights = c(1, 1)
  )

  par(
    oma = c(2.0, 0.35, 0.05, 0.05),
    family = "sans",
    fg = text_colour,
    col.axis = text_colour,
    col.lab = text_colour
  )

  for (index in seq_len(nrow(task_information))) {
    task <- task_information$Task[index]
    panel_data <- top_shap[top_shap$Task == task, , drop = FALSE]

    draw_shap_panel(
      panel_data = panel_data,
      panel_label = task_information$Panel[index],
      outcome = task_information$Outcome[index],
      show_x_axis = task_information$Show_x_axis[index]
    )
  }

  mtext(
    "Mean |SHAP|",
    side = 1,
    outer = TRUE,
    line = 0.45,
    cex = 1.45,
    col = text_colour
  )
}

save_figure15 <- function(output_stem, width = 9.0, height = 6.2) {
  grDevices::png(
    filename = paste0(output_stem, ".png"),
    width = width,
    height = height,
    units = "in",
    res = 600,
    bg = "white",
    type = "cairo-png"
  )
  plot_figure15()
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
  plot_figure15()
  grDevices::dev.off()

  grDevices::cairo_pdf(
    filename = paste0(output_stem, ".pdf"),
    width = width,
    height = height,
    family = "sans",
    bg = "white"
  )
  plot_figure15()
  grDevices::dev.off()

  grDevices::svg(
    filename = paste0(output_stem, ".svg"),
    width = width,
    height = height,
    bg = "white"
  )
  plot_figure15()
  grDevices::dev.off()
}

output_stem <- file.path(
  output_directory,
  "Figure15_SHAP_global_importance_refined_R"
)

save_figure15(output_stem)


