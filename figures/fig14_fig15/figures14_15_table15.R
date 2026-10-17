# -*- coding: UTF-8 -*-
#
# Journal-ready Figures 14–15 and Table 15
# Muleke et al. manuscript
#
# This script uses base R only. It therefore avoids ggplot2/dplyr/rlang
# dependency conflicts. Save and run the file with UTF-8 encoding.
#
# Required inputs (place beside this script):
#   RA_improved_variance_decomposition.csv
#   RA_process_SHAP_importance.csv
#   RA_process_model_grouped_CV_metrics.csv
#
# Main outputs:
#   Figure14_SOC_variance_decomposition_R.{svg,pdf,png,tiff}
#   Figure15_SHAP_global_importance_R.{svg,pdf,png,tiff}
#   Table15_SOC_variance_decomposition_R.csv
#   Table15_SOC_variance_decomposition_R.html
#   Figure15_predictor_abbreviations_R.csv
#   Figure15_grouped_CV_model_validation_R.csv
#   Figures14_15_Table15_sessionInfo.txt
#
# Statistical note:
# Table 15 is a descriptive factorial decomposition of total sums of squares.
# The omitted Management × Climate × Season term is labelled Residual, but is
# not independently replicated experimental error. F tests and p-values are
# therefore not reported.

rm(list = ls())
options(stringsAsFactors = F)






# =============================================================================
# 1. File paths and graphical settings
# =============================================================================

script_path <- {
  file_arg <- grep(
    "^--file=",
    commandArgs(trailingOnly = FALSE),
    value = TRUE
  )

  if (length(file_arg) > 0L) {
    normalizePath(
      sub("^--file=", "", file_arg[1L]),
      winslash = "/",
      mustWork = FALSE
    )
  } else {
    NA_character_
  }
}

script_directory <- if (!is.na(script_path)) {
  dirname(script_path)
} else {
  getwd()
}

input_path <- function(filename) {
  candidate <- file.path(Sys.getenv("RA_RESULTS_DIR", "outputs/anova_shap_raw"), filename)
  if (!file.exists(candidate)) {
    stop(
      "Required input file not found: ", filename, "\n",
      "Place it in RA_RESULTS_DIR or outputs/anova_shap_raw."
    )
  }
  candidate
}

output_directory <- Sys.getenv("RA_RESULTS_DIR", "outputs/anova_shap_raw")
dir.create(output_directory, recursive = TRUE, showWarnings = FALSE)

variance_file <- input_path("RA_improved_variance_decomposition.csv")
shap_file <- input_path("RA_process_SHAP_importance.csv")
cv_file <- input_path("RA_process_model_grouped_CV_metrics.csv")

text_colour <- "#000000"
grid_colour <- "#D9D9D9"
strip_colour <- "#D9D9D9"

component_colours <- c(
  "Management" = "#7A0177",
  "Climate" = "#F04A24",
  "Management × climate" = "#2C7FB8",
  "Season" = "#41B6C4",
  "Residual" = "#4DAF4A"
)

outcome_colours <- c(
  "SOC" = "#8E2A8B",
  "Wheat" = "#009E73",
  "Barley" = "#E69F00",
  "Rapeseed oil" = "#5975C1"
)

component_order <- names(component_colours)


# =============================================================================
# 2. Device helpers: vector plus 600-dpi publication files
# =============================================================================

open_png <- function(filename, width, height, resolution = 600) {
  arguments <- list(
    filename = filename,
    width = width,
    height = height,
    units = "in",
    res = resolution,
    bg = "white"
  )

  if (capabilities("cairo")) {
    arguments$type <- "cairo"
  }

  do.call(grDevices::png, arguments)
}

open_tiff <- function(filename, width, height, resolution = 600) {
  arguments <- list(
    filename = filename,
    width = width,
    height = height,
    units = "in",
    res = resolution,
    compression = "lzw",
    bg = "white"
  )

  if (capabilities("cairo")) {
    arguments$type <- "cairo"
  }

  do.call(grDevices::tiff, arguments)
}

open_pdf <- function(filename, width, height) {
  if (capabilities("cairo")) {
    grDevices::cairo_pdf(
      filename = filename,
      width = width,
      height = height,
      family = "sans",
      bg = "white"
    )
  } else {
    grDevices::pdf(
      file = filename,
      width = width,
      height = height,
      family = "sans",
      bg = "white",
      useDingbats = FALSE
    )
  }
}

open_svg <- function(filename, width, height) {
  grDevices::svg(
    filename = filename,
    width = width,
    height = height,
    family = "sans",
    bg = "white",
    pointsize = 12
  )
}

save_publication_figure <- function(plot_function,
                                    output_stem,
                                    width,
                                    height) {
  paths <- c(
    svg = file.path(output_directory, paste0(output_stem, ".svg")),
    pdf = file.path(output_directory, paste0(output_stem, ".pdf")),
    png = file.path(output_directory, paste0(output_stem, ".png")),
    tiff = file.path(output_directory, paste0(output_stem, ".tiff"))
  )

  open_svg(paths[["svg"]], width, height)
  plot_function()
  invisible(grDevices::dev.off())

  open_pdf(paths[["pdf"]], width, height)
  plot_function()
  invisible(grDevices::dev.off())

  open_png(paths[["png"]], width, height, resolution = 600)
  plot_function()
  invisible(grDevices::dev.off())

  open_tiff(paths[["tiff"]], width, height, resolution = 600)
  plot_function()
  invisible(grDevices::dev.off())

  message(
    "Saved ", output_stem,
    " as SVG, PDF, 600-dpi PNG and 600-dpi TIFF."
  )
}


# =============================================================================
# 3. Read and prepare the variance decomposition
# =============================================================================

variance_raw <- read.csv(
  variance_file,
  stringsAsFactors = FALSE,
  check.names = FALSE,
  fileEncoding = "UTF-8"
)

required_variance_columns <- c(
  "Analysis",
  "Term",
  "df",
  "SS",
  "Percent_total_SS"
)

missing_variance_columns <- setdiff(
  required_variance_columns,
  names(variance_raw)
)

if (length(missing_variance_columns) > 0L) {
  stop(
    "Variance input is missing: ",
    paste(missing_variance_columns, collapse = ", ")
  )
}

cumulative_analysis <- paste0(
  "31-year SOC accrual: six complete systems, both periods, ",
  "higher fixed CO2"
)

annual_analysis <- paste0(
  "Annual SOC change: six complete systems, both periods, ",
  "higher fixed CO2"
)

variance <- variance_raw[
  variance_raw$Analysis %in% c(cumulative_analysis, annual_analysis),
  ,
  drop = FALSE
]

source_map <- c(
  "System" = "Management",
  "Period" = "Climate",
  "Climate year" = "Climate",
  "Rotation" = "Season",
  "System × Period" = "Management × climate",
  "System × Climate year" = "Management × climate",
  "System × Rotation" = "Management × season",
  "Period × Rotation" = "Climate × season",
  "Climate year × Rotation" = "Climate × season",
  "Residual (omitted three-way term)" = "Residual"
)

variance$Source <- unname(source_map[variance$Term])

if (anyNA(variance$Source)) {
  unmapped <- unique(variance$Term[is.na(variance$Source)])
  stop(
    "Unmapped variance terms: ",
    paste(unmapped, collapse = ", ")
  )
}

variance$Panel <- ifelse(
  variance$Analysis == cumulative_analysis,
  "A",
  "B"
)

variance$Outcome <- ifelse(
  variance$Panel == "A",
  "Cumulative SOC",
  "Annual SOC change"
)

table_source_order <- c(
  "Management",
  "Climate",
  "Season",
  "Management × climate",
  "Management × season",
  "Climate × season",
  "Residual"
)

variance$Source <- factor(
  variance$Source,
  levels = table_source_order,
  ordered = TRUE
)

variance <- variance[
  order(variance$Panel, variance$Source),
  ,
  drop = FALSE
]


# =============================================================================
# 4. Table 15: descriptive total-SS decomposition
# =============================================================================

table15 <- data.frame(
  Panel = variance$Panel,
  Outcome = variance$Outcome,
  Source = as.character(variance$Source),
  df = as.integer(variance$df),
  `Sum of squares` = as.numeric(variance$SS),
  `Share of total SS (%)` = as.numeric(variance$Percent_total_SS),
  check.names = FALSE,
  stringsAsFactors = FALSE
)

table15_csv <- file.path(
  output_directory,
  "Table15_SOC_variance_decomposition_R.csv"
)

write.csv(
  table15,
  table15_csv,
  row.names = FALSE,
  fileEncoding = "UTF-8"
)

html_escape <- function(x) {
  x <- gsub("&", "&amp;", x, fixed = TRUE)
  x <- gsub("<", "&lt;", x, fixed = TRUE)
  x <- gsub(">", "&gt;", x, fixed = TRUE)
  x
}

format_share <- function(x) {
  ifelse(
    x < 0.1,
    sprintf("%.2f", x),
    sprintf("%.1f", x)
  )
}

write_table15_html <- function(data, filename) {
  panel_titles <- c(
    "A" = "A. Cumulative SOC",
    "B" = "B. Annual SOC change"
  )

  html <- c(
    "<!DOCTYPE html>",
    "<html>",
    "<head>",
    "<meta charset=\"UTF-8\">",
    "<style>",
    "body { font-family: Arial, Helvetica, sans-serif; color: #000000; }",
    ".caption { font-weight: bold; font-size: 11pt; margin-bottom: 8px; }",
    "table { border-collapse: collapse; width: 100%; font-size: 10.5pt; }",
    "th { border-top: 1.5pt solid #000; border-bottom: 1pt solid #000;",
    "     padding: 6px 7px; text-align: left; }",
    "td { padding: 5px 7px; vertical-align: top; }",
    "td.num, th.num { text-align: right; }",
    ".panel { background: #E6E6E6; font-weight: bold;",
    "         border-top: 1pt solid #000; border-bottom: 0.75pt solid #000; }",
    ".last { border-bottom: 1.5pt solid #000; }",
    ".note { font-size: 9.5pt; margin-top: 8px; line-height: 1.25; }",
    "</style>",
    "</head>",
    "<body>",
    paste0(
      "<div class=\"caption\">Table 15. Descriptive factorial ",
      "decomposition of variation in cumulative and annual SOC responses ",
      "under regenerative management.</div>"
    ),
    "<table>",
    "<thead>",
    "<tr>",
    "<th>Source</th>",
    "<th class=\"num\">df</th>",
    "<th class=\"num\">Sum of squares</th>",
    "<th class=\"num\">Share of total SS (%)</th>",
    "</tr>",
    "</thead>",
    "<tbody>"
  )

  for (panel in c("A", "B")) {
    subset_data <- data[data$Panel == panel, , drop = FALSE]
    html <- c(
      html,
      paste0(
        "<tr><td class=\"panel\" colspan=\"4\">",
        html_escape(panel_titles[[panel]]),
        "</td></tr>"
      )
    )

    for (row_index in seq_len(nrow(subset_data))) {
      row <- subset_data[row_index, , drop = FALSE]
      last_class <- if (
        panel == "B" && row_index == nrow(subset_data)
      ) {
        " class=\"last\""
      } else {
        ""
      }

      html <- c(
        html,
        "<tr>",
        paste0("<td", last_class, ">", html_escape(row$Source), "</td>"),
        paste0(
          "<td class=\"num",
          if (nzchar(last_class)) " last" else "",
          "\">",
          row$df,
          "</td>"
        ),
        paste0(
          "<td class=\"num",
          if (nzchar(last_class)) " last" else "",
          "\">",
          sprintf("%.3f", row[["Sum of squares"]]),
          "</td>"
        ),
        paste0(
          "<td class=\"num",
          if (nzchar(last_class)) " last" else "",
          "\">",
          format_share(row[["Share of total SS (%)"]]),
          "</td>"
        ),
        "</tr>"
      )
    }
  }

  html <- c(
    html,
    "</tbody>",
    "</table>",
    paste0(
      "<div class=\"note\"><b>Note:</b> Values are a descriptive ",
      "decomposition of total sums of squares. Climate denotes climate ",
      "period for cumulative SOC and climate year for annual SOC change; ",
      "season denotes the winter or spring rotation. Residual is the ",
      "omitted Management × Climate × Season term and does not provide ",
      "independently replicated error. F tests and p-values are therefore ",
      "not reported. Analyses used the six complete management systems, ",
      "both climate periods and the higher fixed CO₂ scenario.</div>"
    ),
    "</body>",
    "</html>"
  )

  writeLines(html, filename, useBytes = TRUE)
}

table15_html <- file.path(
  output_directory,
  "Table15_SOC_variance_decomposition_R.html"
)

write_table15_html(table15, table15_html)


# =============================================================================
# 5. Figure 14: compact SOC variance-decomposition donuts
# =============================================================================

aggregate_donut_components <- function(data, panel) {
  panel_data <- data[data$Panel == panel, , drop = FALSE]
  component <- as.character(panel_data$Source)
  component[
    component %in% c(
      "Season",
      "Management × season",
      "Climate × season"
    )
  ] <- "Season"

  totals <- tapply(
    panel_data$Percent_total_SS,
    component,
    sum
  )

  result <- setNames(
    rep(0, length(component_order)),
    component_order
  )

  result[names(totals)] <- totals
  result
}

cumulative_donut <- aggregate_donut_components(variance, "A")
annual_donut <- aggregate_donut_components(variance, "B")

format_percentage <- function(value) {
  if (value < 0.1) {
    sprintf("%.2f%%", value)
  } else {
    sprintf("%.1f%%", value)
  }
}

draw_annular_sector <- function(start_angle,
                                end_angle,
                                outer_radius = 1.07,
                                inner_radius = 0.68,
                                fill_colour,
                                border_colour = "white",
                                border_width = 1.5) {
  n_points <- max(
    30L,
    ceiling(abs(end_angle - start_angle) / (2 * pi) * 720)
  )

  angle <- seq(
    start_angle,
    end_angle,
    length.out = n_points
  )

  polygon(
    x = c(
      outer_radius * cos(angle),
      inner_radius * cos(rev(angle))
    ),
    y = c(
      outer_radius * sin(angle),
      inner_radius * sin(rev(angle))
    ),
    col = fill_colour,
    border = border_colour,
    lwd = border_width
  )
}

draw_donut_callout <- function(label,
                               x_start,
                               y_start,
                               x_text,
                               y_text,
                               border_colour) {
  segments(
    x_start,
    y_start,
    x_text,
    y_text,
    col = "#555555",
    lwd = 1.0,
    xpd = NA
  )

  text_width <- strwidth(label, cex = 1.28, font = 2)
  text_height <- strheight(label, cex = 1.28, font = 2)
  horizontal_padding <- 0.035
  vertical_padding <- 0.022
  left_aligned <- x_text >= 0

  if (left_aligned) {
    x_left <- x_text - horizontal_padding
    x_right <- x_text + text_width + horizontal_padding
  } else {
    x_left <- x_text - text_width - horizontal_padding
    x_right <- x_text + horizontal_padding
  }

  rect(
    xleft = x_left,
    ybottom = y_text - text_height / 2 - vertical_padding,
    xright = x_right,
    ytop = y_text + text_height / 2 + vertical_padding,
    col = "white",
    border = border_colour,
    lwd = 1.1,
    xpd = NA
  )

  text(
    x_text,
    y_text,
    labels = label,
    adj = if (left_aligned) c(0, 0.5) else c(1, 0.5),
    cex = 1.28,
    font = 2,
    col = text_colour,
    xpd = NA
  )
}

draw_donut_panel <- function(values,
                             panel_label,
                             centre_label,
                             label_positions,
                             leader_categories = character()) {
  par(
    mar = c(0.1, 0.1, 0.1, 0.1),
    family = "sans",
    fg = text_colour,
    col.axis = text_colour,
    col.lab = text_colour,
    xpd = NA
  )

  plot.new()
  plot.window(
    xlim = c(-1.30, 1.60),
    ylim = c(-1.30, 1.30),
    asp = 1
  )

  proportions <- values / sum(values)
  start_angles <- numeric(length(values))
  end_angles <- numeric(length(values))
  current_angle <- pi / 2

  for (index in seq_along(values)) {
    start_angles[index] <- current_angle
    end_angles[index] <- current_angle + 2 * pi * proportions[index]

    draw_annular_sector(
      start_angle = start_angles[index],
      end_angle = end_angles[index],
      fill_colour = unname(component_colours[names(values)[index]])
    )

    current_angle <- end_angles[index]
  }

  midpoint_angles <- (start_angles + end_angles) / 2

  for (index in seq_along(values)) {
    component <- names(values)[index]
    value <- values[index]
    angle <- midpoint_angles[index]
    label <- format_percentage(value)

    if (value >= 5) {
      position <- label_positions[[component]]
      text(
        x = position[1],
        y = position[2],
        labels = label,
        cex = 1.36,
        font = 2,
        col = text_colour,
        xpd = NA
      )
    } else {
      end <- label_positions[[component]]

      if (component %in% leader_categories) {
        draw_donut_callout(
          label = label,
          x_start = 1.075 * cos(angle),
          y_start = 1.075 * sin(angle),
          x_text = end[1],
          y_text = end[2],
          border_colour = unname(component_colours[component])
        )
      } else {
        text(
          x = end[1],
          y = end[2],
          labels = label,
          cex = 1.36,
          font = 2,
          col = text_colour,
          xpd = NA
        )
      }
    }
  }

  text(
    0,
    0,
    labels = centre_label,
    cex = 1.62,
    font = 2,
    col = text_colour
  )

  text(
    -1.18,
    1.15,
    labels = panel_label,
    adj = c(0, 1),
    cex = 1.86,
    font = 2,
    col = text_colour,
    xpd = NA
  )
}

draw_variance_legend <- function() {
  par(
    mar = c(0, 0, 0, 0),
    family = "sans",
    fg = text_colour,
    xpd = NA
  )

  plot.new()

  legend(
    "center",
    legend = component_order,
    fill = unname(component_colours[component_order]),
    border = "black",
    bty = "n",
    ncol = 3,
    cex = 1.12,
    text.col = text_colour,
    x.intersp = 0.55,
    y.intersp = 1.0
  )
}

plot_figure14 <- function() {
  layout(
    matrix(c(1, 2, 3, 3), nrow = 2, byrow = TRUE),
    heights = c(4.8, 1.0)
  )

  draw_donut_panel(
    values = cumulative_donut,
    panel_label = "A",
    centre_label = "Long-term",
    label_positions = list(
      "Management" = c(0.02, -1.21),
      "Climate" = c(-0.22, 1.21),
      "Management × climate" = c(1.48, 0.16),
      "Season" = c(1.39, -0.17),
      "Residual" = c(1.18, -0.50)
    ),
    leader_categories = c(
      "Management × climate",
      "Season",
      "Residual"
    )
  )

  draw_donut_panel(
    values = annual_donut,
    panel_label = "B",
    centre_label = "Annual",
    label_positions = list(
      "Management" = c(0.22, 1.16),
      "Climate" = c(1.18, 0.12),
      "Management × climate" = c(-0.92, -0.88),
      "Season" = c(1.18, 0.67),
      "Residual" = c(-0.40, 1.14)
    ),
    leader_categories = "Season"
  )

  draw_variance_legend()
}

save_publication_figure(
  plot_function = plot_figure14,
  output_stem = "Figure14_SOC_variance_decomposition_R",
  width = 7.4,
  height = 3.75
)


# =============================================================================
# 6. Figure 15: global SHAP importance
# =============================================================================

shap <- read.csv(
  shap_file,
  stringsAsFactors = FALSE,
  check.names = FALSE,
  fileEncoding = "UTF-8"
)

required_shap_columns <- c(
  "Task",
  "Feature_label",
  "Mean_abs_Shapley",
  "Rank"
)

missing_shap_columns <- setdiff(
  required_shap_columns,
  names(shap)
)

if (length(missing_shap_columns) > 0L) {
  stop(
    "SHAP input is missing: ",
    paste(missing_shap_columns, collapse = ", ")
  )
}

short_labels <- c(
  "Annual soil evaporation" = "Soil evap.",
  "Mean surface residue C" = "Residue C",
  "Starting SOC" = "Initial SOC",
  "Minimum soil water" = "Min. soil water",
  "Change in surface residue C" = "Δ residue C",
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
    "Annual SOC change — six complete systems, both periods",
    "Wheat yield — six complete systems, both periods",
    "Barley yield — six complete systems, both periods",
    "Rapeseed oil yield — six complete systems, both periods"
  ),
  Panel = c("A", "B", "C", "D"),
  Outcome = c("SOC", "Wheat", "Barley", "Rapeseed oil"),
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
    result$Panel <- task_information$Panel[index]
    result$Outcome <- task_information$Outcome[index]
    result$Abbreviation <- unname(short_labels[result$Feature_label])

    if (anyNA(result$Abbreviation)) {
      missing <- unique(result$Feature_label[is.na(result$Abbreviation)])
      stop(
        "Missing SHAP abbreviations: ",
        paste(missing, collapse = ", ")
      )
    }

    result
  })
)

abbreviation_table <- unique(
  top_shap[
    ,
    c("Panel", "Outcome", "Abbreviation", "Feature_label"),
    drop = FALSE
  ]
)

names(abbreviation_table)[4] <- "Full predictor"

write.csv(
  abbreviation_table,
  file.path(
    output_directory,
    "Figure15_predictor_abbreviations_R.csv"
  ),
  row.names = FALSE,
  fileEncoding = "UTF-8"
)

draw_shap_panel <- function(panel_data, panel_label, outcome) {
  panel_data <- panel_data[order(panel_data$Rank), , drop = FALSE]
  n_features <- nrow(panel_data)
  y_positions <- rev(seq_len(n_features))
  values <- panel_data$Mean_abs_Shapley
  maximum_x <- max(values) * 1.18
  tick_values <- pretty(c(0, maximum_x), n = 4)
  tick_values <- tick_values[
    tick_values >= 0 & tick_values <= maximum_x
  ]

  par(
    mar = c(3.1, 8.0, 3.4, 0.9),
    family = "sans",
    fg = text_colour,
    col.axis = text_colour,
    col.lab = text_colour,
    xpd = FALSE
  )

  plot.new()
  plot.window(
    xlim = c(0, maximum_x),
    ylim = c(0.35, n_features + 0.65),
    xaxs = "i",
    yaxs = "i"
  )

  abline(
    v = tick_values,
    col = grid_colour,
    lwd = 0.9
  )

  rect(
    xleft = 0,
    ybottom = y_positions - 0.35,
    xright = values,
    ytop = y_positions + 0.35,
    col = unname(outcome_colours[outcome]),
    border = "black",
    lwd = 1.0
  )

  axis(
    1,
    at = tick_values,
    labels = format(tick_values, trim = TRUE),
    cex.axis = 1.10,
    col.axis = text_colour,
    col = text_colour,
    lwd = 1.1,
    lwd.ticks = 1.1
  )

  axis(
    2,
    at = y_positions,
    labels = panel_data$Abbreviation,
    las = 1,
    tick = FALSE,
    cex.axis = 1.08,
    col.axis = text_colour
  )

  segments(
    x0 = 0,
    y0 = 0.35,
    x1 = maximum_x,
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

  text(
    x = values + maximum_x * 0.018,
    y = y_positions,
    labels = sprintf("%.2f", values),
    adj = c(0, 0.5),
    cex = 1.02,
    col = text_colour
  )

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
    x = user_coordinates[1] + 0.02 * diff(user_coordinates[1:2]),
    y = mean(c(strip_bottom, strip_top)),
    labels = panel_label,
    adj = c(0, 0.5),
    cex = 1.28,
    font = 2,
    col = text_colour,
    xpd = NA
  )

  text(
    x = mean(user_coordinates[1:2]),
    y = mean(c(strip_bottom, strip_top)),
    labels = outcome,
    cex = 1.28,
    font = 2,
    col = text_colour,
    xpd = NA
  )
}

plot_figure15 <- function() {
  old_par <- par(no.readonly = TRUE)
  on.exit(par(old_par), add = TRUE)

  layout(matrix(1:4, nrow = 2, byrow = TRUE))
  par(
    oma = c(2.3, 0, 0, 0),
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
      outcome = task_information$Outcome[index]
    )
  }

  mtext(
    "Mean |SHAP|",
    side = 1,
    outer = TRUE,
    line = 0.55,
    cex = 1.32,
    col = text_colour
  )
}

save_publication_figure(
  plot_function = plot_figure15,
  output_stem = "Figure15_SHAP_global_importance_R",
  width = 7.4,
  height = 6.15
)


# =============================================================================
# 7. Grouped cross-validation summary supporting Figure 15
# =============================================================================

cv <- read.csv(
  cv_file,
  stringsAsFactors = FALSE,
  check.names = FALSE,
  fileEncoding = "UTF-8"
)

required_cv_columns <- c(
  "Task",
  "Model",
  "n",
  "n_groups",
  "Grouped_CV_R2",
  "Grouped_CV_RMSE",
  "Grouped_CV_MAE",
  "Selected"
)

missing_cv_columns <- setdiff(
  required_cv_columns,
  names(cv)
)

if (length(missing_cv_columns) > 0L) {
  stop(
    "CV input is missing: ",
    paste(missing_cv_columns, collapse = ", ")
  )
}

selected_cv <- cv[
  as.logical(cv$Selected) &
    cv$Task %in% task_information$Task,
  c(
    "Task",
    "Model",
    "n",
    "n_groups",
    "Grouped_CV_R2",
    "Grouped_CV_RMSE",
    "Grouped_CV_MAE"
  ),
  drop = FALSE
]

selected_cv$Outcome <- task_information$Outcome[
  match(selected_cv$Task, task_information$Task)
]

selected_cv <- selected_cv[
  match(task_information$Task, selected_cv$Task),
  c(
    "Outcome",
    "Model",
    "n",
    "n_groups",
    "Grouped_CV_R2",
    "Grouped_CV_RMSE",
    "Grouped_CV_MAE"
  ),
  drop = FALSE
]

write.csv(
  selected_cv,
  file.path(
    output_directory,
    "Figure15_grouped_CV_model_validation_R.csv"
  ),
  row.names = FALSE,
  fileEncoding = "UTF-8"
)


# =============================================================================
# 8. Reproducibility record
# =============================================================================

session_information_file <- file.path(
  output_directory,
  "Figures14_15_Table15_sessionInfo.txt"
)

capture.output(
  sessionInfo(),
  file = session_information_file
)

message("Saved Table 15 CSV: ", table15_csv)
message("Saved Table 15 HTML: ", table15_html)
message("Saved SHAP abbreviation and grouped-CV tables.")
message("Saved R session information.")
message("All journal-ready outputs were generated successfully.")
