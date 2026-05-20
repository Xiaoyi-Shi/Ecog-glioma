# Scripts

This folder contains ad hoc and reusable scripts for the ECoG glioma workflow.

## Environment

Run scripts from the repository root.

Recommended interpreter:

```powershell
.\.venv\Scripts\python.exe
```

Using the project virtual environment matters because the system `python` may not have `mne`, `mne-bids`, or `openpyxl` installed.

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
