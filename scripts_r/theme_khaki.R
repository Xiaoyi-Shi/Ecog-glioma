khaki_palette <- list(
  plot_bg = "#F3EBD7",
  panel_bg = "#E8DFC8",
  grid = "#D6C7A8",
  text = "#3E3528",
  accent = "#6E7F4D",
  accent2 = "#A65E2E",
  accent3 = "#7B3F3F",
  border = "#BDAF90"
)

theme_boundary_khaki <- function(base_size = 12) {
  ggplot2::theme_minimal(base_size = base_size) +
    ggplot2::theme(
      plot.background = ggplot2::element_rect(fill = khaki_palette$plot_bg, color = NA),
      panel.background = ggplot2::element_rect(fill = khaki_palette$panel_bg, color = NA),
      panel.grid.major = ggplot2::element_line(color = khaki_palette$grid, linewidth = 0.35),
      panel.grid.minor = ggplot2::element_blank(),
      axis.text = ggplot2::element_text(color = khaki_palette$text),
      axis.title = ggplot2::element_text(color = khaki_palette$text),
      plot.title = ggplot2::element_text(color = khaki_palette$text, face = "bold"),
      plot.subtitle = ggplot2::element_text(color = khaki_palette$text),
      strip.background = ggplot2::element_rect(fill = khaki_palette$border, color = NA),
      strip.text = ggplot2::element_text(color = khaki_palette$text, face = "bold"),
      legend.background = ggplot2::element_rect(fill = khaki_palette$plot_bg, color = NA),
      legend.key = ggplot2::element_rect(fill = khaki_palette$plot_bg, color = NA)
    )
}
