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

render_report <- function(input_name, output_dir_name, output_file, current_cohort) {
  cohort_dir <- file.path(run_dir, output_dir_name, current_cohort$name)
  dir.create(cohort_dir, recursive = TRUE, showWarnings = FALSE)
  dynamic_audit_dir <- file.path(run_dir, "09_dynamic_audit")
  dir.create(dynamic_audit_dir, recursive = TRUE, showWarnings = FALSE)
  coupling_robustness_dir <- file.path(run_dir, "10_coupling_robustness")
  dir.create(coupling_robustness_dir, recursive = TRUE, showWarnings = FALSE)
  rmarkdown::render(
    input = file.path(script_dir, input_name),
    output_file = output_file,
    output_dir = cohort_dir,
    params = list(
      run_dir = run_dir,
      script_dir = script_dir,
      report_dir = cohort_dir,
      dynamic_audit_dir = dynamic_audit_dir,
      coupling_robustness_dir = coupling_robustness_dir,
      cohort_name = current_cohort$name,
      analysis_role = current_cohort$analysis_role
    ),
    envir = new.env(parent = globalenv())
  )
}

cohorts <- list(
  list(name = "main", analysis_role = "primary"),
  list(name = "sensitivity", analysis_role = "exploratory"),
  list(name = "full_modelable", analysis_role = "exploratory")
)

render_for_cohort <- function(current_cohort) {
  output_dir <- file.path(run_dir, "07_stats_r", current_cohort$name)
  dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
  render_report("run_boundary_models.Rmd", "07_stats_r", "run_boundary_models.html", current_cohort)
  render_report("run_boundary_figures.Rmd", "08_figures", "run_boundary_figures.html", current_cohort)
}

suppressPackageStartupMessages({
  library(rmarkdown)
})

for (current_cohort in cohorts) {
  render_for_cohort(current_cohort)
}

message("R reporting complete: ", run_dir)
