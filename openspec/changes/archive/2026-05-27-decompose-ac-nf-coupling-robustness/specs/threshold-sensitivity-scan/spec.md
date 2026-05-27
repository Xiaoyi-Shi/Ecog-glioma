## ADDED Requirements

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
