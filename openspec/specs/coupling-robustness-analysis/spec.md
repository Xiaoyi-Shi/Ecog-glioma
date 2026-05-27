# coupling-robustness-analysis Specification

## Purpose
Define the robustness-analysis layer that tests whether headline AC/NF findings remain interpretable under decomposition, null calibration, and threshold-sensitivity scans.

## Requirements
### Requirement: Decompose AC-NF coupling into interpretable nested-data views
The system SHALL generate machine-readable AC-NF decomposition summaries for each supported cohort that distinguish pooled, between-patient, within-patient, within-region, and within-band coupling views and record insufficient-data states when a view cannot be estimated reliably.

#### Scenario: Decomposition tables are written for a completed run
- **WHEN** a user runs the coupling robustness workflow on a completed `results/<timestamp>/` directory
- **THEN** the system writes decomposition tables that identify the cohort, analysis role, value scale, aggregation level, decomposition view, grouping stratum, patient count, and interval count for each coupling summary
- **AND** each row records either the observed coupling statistic or an explicit insufficient-data status

### Requirement: Compare observed AC-NF coupling against null references
The system SHALL compare observed AC-NF coupling against both structural-baseline and permutation-based null summaries so metric-construction and sampling artifacts can be inspected separately.

#### Scenario: Null comparison summaries are emitted
- **WHEN** observed AC-NF coupling summaries are available for a completed run
- **THEN** the system writes null-comparison outputs that include the observed statistic, the relevant structural-baseline summary, the relevant permutation summary, and the provenance fields needed to reproduce the comparison
- **AND** the null-comparison outputs keep the structural-baseline and permutation evidence distinguishable rather than collapsing them into one score

### Requirement: Classify robustness status for headline findings
The system SHALL assign a machine-readable robustness status to each headline AC/NF finding so downstream reports can distinguish robustness-supported results from exploratory or artifact-risk observations.

#### Scenario: Robustness labels are recorded with supporting evidence
- **WHEN** decomposition and null-comparison summaries complete successfully
- **THEN** the system writes a robustness summary that labels each headline finding as `supported`, `exploratory`, `artifact_risk`, `threshold_sensitive`, or `insufficient`
- **AND** each label is accompanied by the evidence fields used to determine that status

### Requirement: Scan cohort inclusion thresholds for primary phenotype stability
The system SHALL evaluate a predefined set of patient-inclusion thresholds and summarize whether the primary AC/NF findings remain directionally and statistically stable across those thresholds.

#### Scenario: Inclusion-threshold stability is summarized
- **WHEN** a completed run contains enough provenance to identify modelable rows for multiple inclusion thresholds
- **THEN** the system writes a threshold-sensitivity table that records the threshold value, eligible patient count, eligible interval count, and the resulting AC/NF headline summaries for that threshold
- **AND** thresholds that cannot support a required summary are marked explicitly as insufficient rather than omitted silently

### Requirement: Scan boundary-distance thresholds for region-2 sensitivity
The system SHALL evaluate a predefined set of region-2 distance thresholds using interval rows with valid numeric distance metadata and summarize how the primary region-2 AC/NF findings change across those thresholds.

#### Scenario: Distance-threshold sensitivity is summarized
- **WHEN** the coupling robustness workflow processes a completed run with valid interval distance metadata
- **THEN** it writes distance-threshold sensitivity outputs that record the threshold value, included row counts, and the resulting region-2 AC/NF headline summaries
- **AND** rows lacking usable distance metadata are excluded with an explicit recorded status

### Requirement: Emit a compact stability matrix for reporting
The system SHALL consolidate inclusion-threshold and distance-threshold scan results into a compact stability summary that identifies which headline findings are stable, unstable, or insufficiently supported.

#### Scenario: Stability matrix is written for downstream reports
- **WHEN** threshold scans finish
- **THEN** the system writes a machine-readable stability matrix or equivalent summary artifact for the tracked headline findings
- **AND** the summary distinguishes direction reversals, significance losses, and insufficient-data cases
