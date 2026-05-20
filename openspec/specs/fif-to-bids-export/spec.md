# fif-to-bids-export Specification

## Purpose
TBD - created by archiving change export-clean-fif-to-bids. Update Purpose after archive.
## Requirements
### Requirement: Export cleaned FIF recordings into a BIDS derivative dataset
The system SHALL provide a script that converts cleaned `.fif` electrophysiology recordings into a BIDS derivative dataset rooted at a user-specified output directory.

#### Scenario: Export a configured source directory
- **WHEN** a user runs the export script with a valid source directory and BIDS root
- **THEN** the script creates or updates a BIDS dataset at the requested output location
- **AND** the dataset is marked as derivative data rather than raw acquisition data

### Requirement: Filter inputs using session-aware metadata mapping
The system SHALL support selecting inputs by session metadata using a spreadsheet mapping that resolves filename patient identifiers to BIDS subject labels.

#### Scenario: Export only before-session recordings
- **WHEN** a user runs the script with a session filter of `before`
- **THEN** the script exports only recordings whose metadata row matches that session
- **AND** the script uses the mapped `Sub-ID` value as the BIDS subject label

#### Scenario: Skip unmapped or excluded inputs
- **WHEN** a cleaned `.fif` file has no matching metadata row for the requested session
- **THEN** the script does not export that file
- **AND** the script records the skipped file and the reason in a conversion report

### Requirement: Support configurable datatype and channel-type export behavior
The system SHALL allow the caller to control the target BIDS datatype and channel-type mapping so the same script can be reused for different `.fif` electrophysiology workflows.

#### Scenario: Export ECoG recordings from source FIF files marked as EEG
- **WHEN** a user specifies `ieeg` datatype with an `ecog` channel-type override
- **THEN** the script applies the requested channel-type mapping before BIDS export
- **AND** the exported dataset is organized under the `ieeg` modality branch

#### Scenario: Reuse the script for another FIF modality
- **WHEN** a user provides a different supported datatype or chooses to preserve the source channel types
- **THEN** the script uses the requested export configuration without requiring code changes

### Requirement: Preserve curated quality annotations during export
The system SHALL preserve curated bad-channel markings and bad-segment annotations from the source `.fif` recordings in the exported BIDS dataset.

#### Scenario: Export bad channels
- **WHEN** a source `.fif` file contains entries in `raw.info["bads"]`
- **THEN** the exported BIDS dataset records those channels as bad in the appropriate channel metadata

#### Scenario: Export bad segments
- **WHEN** a source `.fif` file contains `raw.annotations`
- **THEN** the exported BIDS dataset includes corresponding event metadata for those annotations

### Requirement: Emit EDF payload files for the current workflow
The system SHALL support writing exported recordings in EDF format for workflows that require EDF payload files inside the BIDS dataset.

#### Scenario: Force EDF output
- **WHEN** a user requests EDF output
- **THEN** the script writes each exported recording with an EDF data file
- **AND** the accompanying BIDS sidecars remain consistent with the exported file

### Requirement: Provide validation and reporting after export
The system SHALL provide machine-readable reporting for conversion outcomes and optional validation results.

#### Scenario: Report conversion outcomes
- **WHEN** the script finishes an export run
- **THEN** it writes a report that identifies converted files, skipped files, and skip reasons

#### Scenario: Run bids-validator when requested
- **WHEN** the user enables validation and a validator command is available
- **THEN** the script runs validation against the generated BIDS root
- **AND** it surfaces the validation result to the user as part of the export outcome

#### Scenario: Handle missing validator tooling
- **WHEN** validation is requested but the configured validator command is unavailable
- **THEN** the script reports that validation could not be run
- **AND** it does not silently mark the dataset as validated

