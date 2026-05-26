args <- commandArgs(trailingOnly = TRUE)

`%||%` <- function(x, y) {
  if (is.null(x) || !nzchar(x)) y else x
}

get_option_value <- function(flag) {
  index <- match(flag, args)
  if (is.na(index) || index == length(args)) {
    return("")
  }
  args[[index + 1]]
}

run_dir_arg <- get_option_value("--run-dir")
if (!nzchar(run_dir_arg)) {
  stop("Missing required argument: --run-dir results/<timestamp>", call. = FALSE)
}

run_dir <- normalizePath(run_dir_arg, winslash = "/", mustWork = TRUE)
script_arg <- grep("^--file=", commandArgs(FALSE), value = TRUE)
script_path <- if (length(script_arg) > 0) {
  sub("^--file=", "", script_arg[[1]])
} else {
  commandArgs(FALSE)[[1]]
}
script_dir <- normalizePath(dirname(script_path), winslash = "/", mustWork = TRUE)

render_report <- function(input_name, output_dir_name, output_file) {
  output_dir <- file.path(run_dir, output_dir_name)
  dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
  rmarkdown::render(
    input = file.path(script_dir, input_name),
    output_file = output_file,
    output_dir = output_dir,
    params = list(
      run_dir = run_dir,
      script_dir = script_dir
    ),
    envir = new.env(parent = globalenv())
  )
}

suppressPackageStartupMessages({
  library(rmarkdown)
})

render_report("run_boundary_models.Rmd", "07_stats_r", "run_boundary_models.html")
render_report("run_boundary_figures.Rmd", "08_figures", "run_boundary_figures.html")

message("R reporting complete: ", run_dir)
