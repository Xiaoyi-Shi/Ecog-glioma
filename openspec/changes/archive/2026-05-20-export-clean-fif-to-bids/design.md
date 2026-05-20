## Context

The repository currently has manually curated ECoG recordings stored as cropped and filtered `.fif` files in `datas/data_01_ECoG_clean_1`. These files are not raw acquisitions: they already contain preprocessing decisions, bad-channel markings, and in some cases bad-segment annotations. The immediate requirement is to export only the `before` session recordings into `datas/data_02_BIDS`, while preserving enough flexibility to reuse the same script for other `.fif` electrophysiology data later.

The local metadata source is `datas/ele_pos.xlsx`, which maps `patient_id` values to `Sub-ID` and `sesion`. The cleaned file names currently follow `YYYYMMDD_patientid_run.fif`. Not every cleaned file has a matching `before` row in the spreadsheet, so the exporter must report skipped inputs instead of failing silently. The current `.fif` files also lack electrode coordinates, so the export must tolerate a staged workflow where the BIDS dataset is created first and electrode location files are added later.

## Goals / Non-Goals

**Goals:**
- Provide a single CLI script in `scripts/` that converts `.fif` recordings into a BIDS dataset.
- Support the current ECoG workflow by filtering spreadsheet metadata to `sesion=before`.
- Emit a derivative dataset in `datas/data_02_BIDS` with EDF data files.
- Preserve bad-channel and bad-segment information during export.
- Make datatype, channel-type, task, session filter, validation, and metadata source configurable for future reuse.
- Produce explicit reporting for converted and skipped files.

**Non-Goals:**
- Creating electrode coordinate files from surgical photographs in this change.
- Backfilling missing spreadsheet metadata for unmapped files.
- Reconstructing raw, pre-cleaning datasets from the cleaned `.fif` inputs.
- Building a full package API; the first delivery is a robust script entry point.

## Decisions

### Treat the output as a BIDS derivative dataset
The cleaned `.fif` files have already been filtered, cropped, and annotated, so they should not be written as a raw BIDS dataset. The exporter will create a derivative dataset rooted at `datas/data_02_BIDS` and use `desc-clean` in file naming to make the preprocessing state explicit.

Alternative considered:
- Write directly as raw BIDS. Rejected because it misrepresents the provenance of the files and makes downstream interpretation ambiguous.

### Use a parameterized CLI with current-project defaults
The script will accept arguments for source directory, BIDS root, metadata spreadsheet, session filter, datatype, channel-type override, task label, output format, line frequency, reference text, validation behavior, and dry-run/overwrite control. Defaults will target the current workflow (`data_01_ECoG_clean_1`, `data_02_BIDS`, `before`, `ieeg`, `ecog`, `EDF`), but the CLI will not hardcode those assumptions into the conversion logic.

Alternative considered:
- Write a project-specific one-off script. Rejected because the user explicitly wants to reuse the same tool for future `.fif` electrophysiology exports.

### Build subject and session metadata from both filename parsing and Excel mapping
Filename parsing alone is insufficient because BIDS subject labels come from `Sub-ID` and the export must filter to `before` rows only. The exporter will parse `patient_id` and run from the filename, then join against `datas/ele_pos.xlsx` to resolve `subject` and confirm session inclusion. Inputs without a matching row will be skipped and listed in a report.

Alternative considered:
- Use only filenames. Rejected because it would lose the existing `Sub-ID` assignment and session metadata contract.

### Preserve bad channels and bad segments through MNE-BIDS export
The exporter will read each `.fif` into MNE, optionally override channel types for the selected modality, and write through `mne-bids` with EDF output. This keeps `raw.info["bads"]` and `raw.annotations` attached to the exported BIDS sidecars instead of reimplementing channel and event file generation manually.

Alternative considered:
- Export EDF manually and generate TSV/JSON files separately. Rejected because it duplicates BIDS-writing logic and increases the risk of metadata drift.

### Do not fabricate electrode positions in this change
The exporter will not invent placeholder coordinates. If the ECoG dataset cannot fully satisfy all iEEG validator expectations until coordinates are created from surgical images, the script will still emit the dataset and run validation as an explicit reporting step. This keeps the pipeline honest about current metadata completeness.

Alternative considered:
- Generate fake or zeroed coordinates to satisfy file presence checks. Rejected because it would create misleading metadata that must later be corrected.

### Include validator execution as an optional post-export step
The script will optionally invoke an installed `bids-validator` command after export and surface the result in the terminal and reporting artifacts. Validation must be optional because not every environment will have the validator CLI installed yet.

Alternative considered:
- Omit validation from the script and require manual validation. Rejected because validation is part of the requested workflow and should be automatable.

## Risks / Trade-offs

- [Missing electrode coordinates for ECoG/iEEG] -> Export the dataset without fabricating positions, document the staged workflow, and surface validator findings clearly so coordinate completion can happen in a follow-up step.
- [Spreadsheet coverage gaps for some cleaned files] -> Skip unmapped inputs, log them to a machine-readable report, and avoid partial subject labels guessed from filenames.
- [Datatype/channel-type mismatch in existing FIF files] -> Allow an explicit channel-type override so current ECoG recordings can be exported as `ecog` even if the source files still carry `eeg` channel types.
- [EDF export or BIDS writing may constrain metadata fidelity] -> Add a post-export verification task that checks a sample export for duration, sampling rate, channel count, bad channels, and bad-segment propagation.
- [Validator CLI differences across environments] -> Make the validator command configurable and degrade gracefully when the tool is absent.

## Migration Plan

There is no runtime deployment requirement for this repository. Migration consists of:
1. Add the required export dependencies.
2. Implement the exporter script and dataset/report generation.
3. Run the script against `datas/data_01_ECoG_clean_1` with `before` filtering.
4. Inspect conversion and validation reports.
5. Add electrode coordinate files in a later change and re-run validation if needed.

Rollback is simple: remove the generated `datas/data_02_BIDS` output and revert the script/dependency changes.

## Open Questions

- What task label should be used for the current recordings if they are not all rest data?
- Should channel names remain as `EEG 1..24` for now, or should a future change rename them to surgical contact labels before coordinate files are introduced?
- Which validator installation path should be the default target in this environment: `bids-validator-deno`, `deno run ...`, or another local wrapper?
