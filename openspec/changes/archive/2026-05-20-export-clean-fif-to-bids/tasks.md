## 1. Export Foundations

- [x] 1.1 Add the BIDS export dependency set needed for `mne-bids` export and validator integration.
- [x] 1.2 Define the CLI contract for the exporter, including current defaults for `before`, `ieeg`, `ecog`, `EDF`, and derivative output.
- [x] 1.3 Implement metadata loading from `datas/ele_pos.xlsx` and filename parsing for patient ID and run extraction.

## 2. BIDS Conversion Workflow

- [x] 2.1 Implement the core conversion flow that reads `.fif` files, filters them by session mapping, and skips unmapped inputs with explicit reporting.
- [x] 2.2 Implement configurable datatype and channel-type handling, including the current ECoG override path for source files still marked as EEG.
- [x] 2.3 Implement BIDS derivative writing to `datas/data_02_BIDS` with EDF output and preservation of bad channels and annotations.

## 3. Validation And Verification

- [x] 3.1 Add optional `bids-validator` execution with configurable command resolution and clear failure reporting when the tool is unavailable.
- [x] 3.2 Generate conversion and validation reports that distinguish exported files, skipped files, and validation outcomes.
- [x] 3.3 Verify the exporter against the current `before` dataset with a sample round-trip check for duration, sampling rate, channel count, and preserved quality markers.
