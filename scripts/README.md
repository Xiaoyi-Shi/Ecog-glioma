# Scripts

This folder contains ad hoc and reusable scripts for the ECoG glioma workflow.

## Environment

Run scripts from the repository root.

Recommended interpreter:

```powershell
.\.venv\Scripts\python.exe
```

Using the project virtual environment matters because the system `python` may not have `mne`, `mne-bids`, or `openpyxl` installed.

R scripts require a working `Rscript` on `PATH`.

Current reporting scripts expect these R packages:
- `dplyr`
- `readr`
- `tidyr`
- `stringr`
- `purrr`
- `ggplot2`
- `lme4`
- `lmerTest`
- `broom.mixed`
- `splines`

All new analysis outputs for the boundary-gradient workflow are written into
timestamped subdirectories under `results`, for example:

```text
results/20260526_154027/
```

Each run directory contains:
- `00_manifest`
- `01_qc`
- `02_static_network`
- `03_hfo`
- `04_controllability`
- `05_fragility`
- `06_model_tables`
- `07_stats_r`
- `08_figures`
- `09_dynamic_audit`
- `10_coupling_robustness`
- `logs`

## `fif_to_bids.py`

Purpose:
- Convert cleaned `.fif` electrophysiology recordings into a BIDS derivative dataset.
- Filter exported files by spreadsheet session metadata.
- Preserve bad channels and bad-segment annotations.
- Optionally run `bids-validator` after export.

Current default workflow:
- Source directory: `datas/data_01_ECoG_clean_1`
- Output BIDS root: `datas/data_02_BIDS`
- Metadata file: `datas/ele_pos.xlsx`
- Session filter: `before`
- Datatype: `ieeg`
- Channel type override: `ecog`
- Output format: `EDF`

Basic usage:

```powershell
.\.venv\Scripts\python.exe scripts\fif_to_bids.py
```

Preview without writing files:

```powershell
.\.venv\Scripts\python.exe scripts\fif_to_bids.py --dry-run
```

Run export and validate:

```powershell
.\.venv\Scripts\python.exe scripts\fif_to_bids.py --validate --overwrite
```

Common options:
- `--source-dir`: input `.fif` directory
- `--bids-root`: output BIDS dataset root
- `--metadata-xlsx`: spreadsheet with `patient_id`, `Sub-ID`, and `sesion`
- `--session-filter`: only export rows matching this session
- `--datatype`: one of `auto`, `eeg`, `ieeg`, `meg`, `nirs`
- `--channel-type`: one of `preserve`, `eeg`, `ecog`, `seeg`, `dbs`
- `--task`: BIDS task label
- `--format`: one of `auto`, `EDF`, `BrainVision`, `EEGLAB`, `FIF`
- `--validate`: run validator after export
- `--overwrite`: overwrite existing output files
- `--dry-run`: show planned actions only

Example: preserve source channel types and infer datatype automatically:

```powershell
.\.venv\Scripts\python.exe scripts\fif_to_bids.py --datatype auto --channel-type preserve
```

Outputs:
- BIDS dataset under `datas/data_02_BIDS`
- Conversion report: `datas/data_02_BIDS/reports/conversion_report.csv`
- Validation report: `datas/data_02_BIDS/reports/validation_report.json`
- Verification report: `datas/data_02_BIDS/reports/verification_report.json`

Notes:
- Files without a matching spreadsheet row for the selected `sesion` are skipped and listed in the conversion report.
- For the current ECoG workflow, electrode coordinates are still placeholders until manual localization is added later.
- Validator status may be `passed_with_warnings` if the dataset has recommended-field warnings but no hard errors.

## `bids_qc_report.py`

Purpose:
- Read the BIDS dataset under `datas/data_02_BIDS` in read-only mode.
- Generate a simple patient-level QC overview as one HTML file under `results`.
- Summarize bad-channel counts, bad-channel names, bad-segment positions, and PSD overviews.

Important behavior:
- The script does not modify anything inside `datas/data_02_BIDS`.
- The only output is a dated HTML file such as `results/2026-05-25.html`.
- PSD figures are embedded directly into the HTML report; no extra image folder is created.

Basic usage:

```powershell
.\.venv\Scripts\python.exe scripts\bids_qc_report.py
```

Common options:
- `--bids-root`: input BIDS root, default `datas/data_02_BIDS`
- `--output-dir`: report output directory, default `results`
- `--fmin`: PSD lower frequency bound, default `1`
- `--fmax`: PSD upper frequency bound, default `200`

Example:

```powershell
.\.venv\Scripts\python.exe scripts\bids_qc_report.py --fmin 1 --fmax 150
```

## Boundary Analysis Pipeline

The Version 2 research workflow from `docs/科研路径提纲版本2.md` is implemented
as a read-only BIDS analysis pipeline.

Method summary:
- Read input from `datas/data_02_BIDS`
- Parse interval labels from `datas/ele_pos.xlsx`
- Convert monopolar contacts into adjacent bipolar intervals
- Compute static network, HFO, controllability, and fragility features
- Export model-ready tables
- Run R statistics and khaki-themed figure generation from an existing timestamped result directory

The pipeline does not modify `datas/data_02_BIDS`.

### `build_label_manifest.py`

Purpose:
- Build the interval label manifest and QC tables
- Create or reuse a timestamped run directory under `results`

Run:

```powershell
.\.venv\Scripts\python.exe scripts\build_label_manifest.py
```

### `run_static_network.py`

Purpose:
- Compute dwPLI connectivity per band
- Export node-level and multilayer static-network summaries

Run:

```powershell
.\.venv\Scripts\python.exe scripts\run_static_network.py --run-dir results\20260526_154027
```

### `run_hfo.py`

Purpose:
- Detect ripple and fast-ripple events
- Export event-level and interval-level HFO summaries

Run:

```powershell
.\.venv\Scripts\python.exe scripts\run_hfo.py --run-dir results\20260526_154027
```

### `run_controllability.py`

Purpose:
- Estimate sliding-window state matrices
- Export average and modal controllability summaries

Run:

```powershell
.\.venv\Scripts\python.exe scripts\run_controllability.py --run-dir results\20260526_154027
```

### `run_fragility.py`

Purpose:
- Compute neural fragility from saved state matrices
- Export window-level and interval-level fragility summaries

Run:

```powershell
.\.venv\Scripts\python.exe scripts\run_fragility.py --run-dir results\20260526_154027
```

### `export_model_tables.py`

Purpose:
- Merge Python stage outputs into R-ready long tables

Run:

```powershell
.\.venv\Scripts\python.exe scripts\export_model_tables.py --run-dir results\20260526_154027
```

### `run_pipeline_v2.py`

Purpose:
- Run the Python stages of the Version 2 boundary-gradient pipeline
- Create or reuse a timestamped run directory under `results`
- Generate all Python-side outputs up to `06_model_tables`

Recommended first step:

```powershell
.\.venv\Scripts\python.exe scripts\run_pipeline_v2.py
```

Optional combined run:

```powershell
.\.venv\Scripts\python.exe scripts\run_pipeline_v2.py --with-r
```

Main outputs from a completed Python run:
- `00_manifest/label_manifest.csv`
- `01_qc/patient_qc_summary.csv`
- `02_static_network/node_features_static.csv`
- `03_hfo/hfo_channel_summary.csv`
- `04_controllability/channel_level_ac_mc_summary.csv`
- `05_fragility/channel_level_fragility_summary.csv`
- `06_model_tables/model_band_metric_long.csv`
- `06_model_tables/model_joint_long.csv`

Console output includes the generated run directory, for example:

```text
Python pipeline complete: F:\uv_env\Ecog-glioma\results\20260526_161122
```

### `run_r_reporting.py`

Purpose:
- Run R statistical modeling and figure generation for an existing timestamped run directory
- Reuse the Python outputs already generated in `00_manifest` to `06_model_tables`
- Avoid re-running the full Python feature extraction when only statistics or plots need refresh

Run:

```powershell
.\.venv\Scripts\python.exe scripts\run_r_reporting.py --run-dir results\20260526_161122
```

Outputs written by the R stage:
- `07_stats_r/<cohort>/*.csv`
- `07_stats_r/<cohort>/run_boundary_models.html`
- `08_figures/<cohort>/*.png`
- `08_figures/<cohort>/run_boundary_figures.html`
- `09_dynamic_audit/*.csv`
- `09_dynamic_audit/dynamic_audit_summary.md`
- `10_coupling_robustness/*.csv`
- `10_coupling_robustness/coupling_robustness_summary.md`

Where `<cohort>` is one of `main`, `sensitivity`, or `full_modelable`.

R reporting implementation notes:
- Statistical modeling is rendered from `scripts_r/run_boundary_models.Rmd`
- Figure reporting is rendered from `scripts_r/run_boundary_figures.Rmd`
- The Python entry point now renders `main`, `sensitivity`, and `full_modelable` cohorts into separate subdirectories under `07_stats_r/` and `08_figures/`
- `main` is the primary analysis cohort; `sensitivity` and `full_modelable` outputs are exploratory and labeled as such in metadata and report content
- The Python entry point also writes a dedicated `09_dynamic_audit/` stage with cohort manifests, AC-vs-fragility audit tables, and the structural baseline summary
- The Python entry point also writes a dedicated `10_coupling_robustness/` stage with decomposition summaries, null-comparison summaries, threshold scans, a stability matrix, and machine-readable robustness labels
- Figure generation now writes the current paper-facing figure set:
  - `Figure1_cohort_definition_and_coverage.png`
  - `Figure2_fragility_region_contrasts.png`
  - `Figure3_ac_nf_inverse_coupling.png`
  - `Figure4_cross_cohort_robustness_heatmap.png`
  - `Figure5_inclusion_threshold_stability_scan.png`
  - `SupplementaryFigure1_region2_ac_vs_fragility.png`
  - `SupplementaryFigure2_hfo_network_consistency.png`
- Additional statistical exports include cohort summaries, workflow-status tables, HFO-network consistency summaries, and region-by-band models
- AC-vs-fragility coupling outputs now live under `09_dynamic_audit/` instead of being mixed into the primary inferential result directory
- The figure narrative is intentionally conservative: AC-NF inverse coupling is treated as the most stable result, regional fragility contrasts are secondary, and HFO / continuous-distance outputs are supplementary rather than central
- Robustness-supported versus exploratory AC/NF conclusions are surfaced back into `07_stats_r/<cohort>/coupling_robustness_summary.csv`, `08_figures/<cohort>/Figure4_cross_cohort_robustness_heatmap.png`, and `08_figures/<cohort>/Figure5_inclusion_threshold_stability_scan.png`

Cohort semantics:
- `main`: patients meeting the main threshold (`>= 16` usable intervals); primary reporting cohort
- `sensitivity`: patients meeting the sensitivity threshold (`>= 12` usable intervals); exploratory robustness cohort
- `full_modelable`: all model-table rows that reach the reporting layer; exploratory reference cohort

Direct R entry point:

```powershell
Rscript scripts_r\run_boundary_reporting.R --run-dir results\20260526_161122
```

Direct R entry-point note:
- It re-renders the cohort-partitioned `07_stats_r/` and `08_figures/` outputs.
- The full `09_dynamic_audit/` and `10_coupling_robustness/` stages are produced by `scripts\run_r_reporting.py`, so prefer the Python entry point when regenerating the complete reporting package.

Recommended execution order:
1. Run `scripts\run_pipeline_v2.py` once to generate a new timestamped results directory.
2. Keep the printed `results\<timestamp>` path.
3. Run `.\.venv\Scripts\python.exe scripts\run_r_reporting.py --run-dir results\<timestamp>` whenever you need to regenerate the full cohort-partitioned reporting package, including `09_dynamic_audit` and `10_coupling_robustness`.
4. Use `Rscript scripts_r\run_boundary_reporting.R --run-dir results\<timestamp>` only if you specifically want to rerender the cohort-partitioned R reports without rebuilding the Python audit/robustness stages.

Robustness-stage outputs:
- `decomposition_summary.csv`: pooled, between-patient, within-patient, within-region, and within-band AC/NF coupling summaries with insufficient-data status fields
- `null_comparison_summary.csv`: observed coupling matched to structural-baseline and permutation null summaries
- `inclusion_threshold_scan.csv`: headline findings scanned across predefined patient-inclusion thresholds
- `distance_threshold_scan.csv`: boundary-versus-remote headline findings scanned across predefined distance thresholds
- `stability_matrix.csv`: compact summary of direction reversals, significance losses, and insufficient cases
- `robustness_summary.csv`: machine-readable headline labels such as `supported`, `exploratory`, `artifact_risk`, `threshold_sensitive`, and `insufficient`

## `eeg_prop_manual.py`

Purpose:
- Manual exploratory script for opening raw EDF data in MNE.
- Applies filtering, interactive plotting, manual cropping, and saves a cleaned `.fif`.

Run:

```powershell
.\.venv\Scripts\python.exe scripts\eeg_prop_manual.py
```

Current behavior:
- Reads from `datas/ele_pos.xlsx`
- Opens raw EDF files from `datas/data_00_rawECoG`
- Filters the recording
- Displays interactive plots
- Crops a selected time window
- Saves the cropped recording into `datas/data_01_ECoG_clean_1`

Notes:
- This is a manual workflow script, not a reusable CLI.
- It currently contains hard-coded paths and crop settings.
- Review and edit the file before running it on new data.
