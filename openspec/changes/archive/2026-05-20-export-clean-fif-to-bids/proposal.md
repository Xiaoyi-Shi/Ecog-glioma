## Why

The project currently stores manually cleaned electrophysiology recordings as standalone `.fif` files, which makes downstream reuse, sharing, and validation difficult. A repeatable BIDS export flow is needed now so the existing `before` ECoG recordings can be organized as a derivative dataset while keeping the export script reusable for future `.fif`-based modalities.

## What Changes

- Add a reusable conversion script under `scripts/` that exports `.fif` recordings to a BIDS dataset rooted at `datas/data_02_BIDS`.
- Support filtering the export by session metadata so the current workflow can export only `before` recordings from `datas/data_01_ECoG_clean_1`.
- Write cleaned recordings as BIDS derivative data with EDF payload files and preserve bad channels and bad-segment annotations during export.
- Build subject/session/run metadata from the existing filename pattern and `datas/ele_pos.xlsx`, and emit a conversion report for skipped or unmapped files.
- Add optional `bids-validator` execution so the export can produce a validation result alongside the dataset.
- Keep the script parameterized so later `.fif` workflows can export other electrophysiology datatypes and channel-type mappings without rewriting the core logic.

## Capabilities

### New Capabilities
- `fif-to-bids-export`: Export cleaned `.fif` electrophysiology recordings into a BIDS-compatible dataset using configurable datatype, metadata mapping, output format, and validation behavior.

### Modified Capabilities
- None.

## Impact

- Affected code: new export script in `scripts/`, supporting utilities if needed, and project dependency metadata for `mne-bids` and validator tooling.
- Affected data flow: `datas/data_01_ECoG_clean_1`, `datas/ele_pos.xlsx`, and generated output in `datas/data_02_BIDS`.
- External dependencies: `mne-bids` for BIDS writing and a supported `bids-validator` CLI for dataset validation.
