# bipolar-boundary-manifest Specification

## Purpose
Define how boundary labels, adjacent bipolar analysis units, and downstream QC inclusion tables are constructed for the boundary-analysis workflow.

## Requirements

### Requirement: Parse interval labels into a standardized manifest
The system SHALL read `datas/ele_pos.xlsx` and export an interval-level manifest for `session = before` that preserves the raw label, resolves `patient_id` and `Sub-ID`, and derives `interval_id`, `distance_mm`, `region`, `is_boundary_interface`, and parse-status fields for every adjacent-contact interval column.

#### Scenario: Tumor-internal label is parsed
- **WHEN** an interval cell contains an `a*` label
- **THEN** the manifest records that interval as valid with `region = 1`, `is_boundary_interface = 0`, and no positive distance requirement

#### Scenario: Boundary-interface label is parsed
- **WHEN** an interval cell contains a `b*[0]` label
- **THEN** the manifest records that interval as valid with `distance_mm = 0`, `region = 2`, and `is_boundary_interface = 1`

#### Scenario: Non-zero tumor-external label is parsed
- **WHEN** an interval cell contains a `b*[distance]` label with a positive numeric distance
- **THEN** the manifest records that interval as valid and assigns `region = 2` for `0 <= distance < 1.5` or `region = 3` for `distance >= 1.5`

#### Scenario: Invalid or unsupported label is encountered
- **WHEN** an interval cell is blank, marked `用不了`, or cannot be parsed into `a*` or `b*[distance]`
- **THEN** the manifest records the interval as excluded from the main analysis with an explicit parse-status reason

### Requirement: Map BIDS recordings onto adjacent bipolar intervals
The system SHALL derive adjacent bipolar analysis units from each eligible BIDS recording so that interval labels such as `1_2` and `23_24` align directly with bipolar signals built from the corresponding single-contact channels.

#### Scenario: Standard 24-contact recording is converted
- **WHEN** a recording contains channels `EEG 1` through `EEG 24`
- **THEN** the system creates bipolar analysis units for `1_2`, `2_3`, ..., `23_24` and preserves the interval ordering needed to join the label manifest

#### Scenario: Bad endpoints affect bipolar interval usability
- **WHEN** either contact endpoint of an interval is marked bad in the BIDS channel metadata
- **THEN** the corresponding bipolar interval is marked unusable for feature extraction and the QC tables record the exclusion reason

### Requirement: Emit QC inclusion tables for downstream analyses
The system SHALL export patient-level and interval-level QC tables that identify usable bipolar intervals, main-vs-sensitivity inclusion status, and the reasons intervals or patients were excluded.

#### Scenario: Patient meets main-analysis threshold
- **WHEN** a patient has at least 16 usable bipolar intervals after label parsing and bad-endpoint propagation
- **THEN** the patient QC table marks that case as included in the main analysis and in the sensitivity analysis

#### Scenario: Patient fails main but meets sensitivity threshold
- **WHEN** a patient has between 12 and 15 usable bipolar intervals after QC
- **THEN** the patient QC table marks that case as excluded from the main analysis but included in the sensitivity analysis
