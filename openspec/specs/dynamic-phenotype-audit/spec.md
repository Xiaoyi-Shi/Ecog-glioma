# dynamic-phenotype-audit Specification

## Purpose
Define the exploratory audit layer that assembles AC-versus-fragility paired datasets, descriptive coupling summaries, and structural baseline context outside the primary inferential reporting outputs.

## Requirements
### Requirement: Produce cohort-partitioned dynamic phenotype audit datasets
The system SHALL assemble dynamic phenotype audit datasets for `main`, `sensitivity`, and `full_modelable` cohorts from an existing run directory using previously exported dynamic stage outputs and model tables.

#### Scenario: Audit datasets are created from a completed run
- **WHEN** a user runs the dynamic phenotype audit against a completed `results/<timestamp>/` directory
- **THEN** the system writes machine-readable audit tables for `main`, `sensitivity`, and `full_modelable` cohorts when eligible rows exist
- **AND** each audit table records the source run, cohort name, patient count, and interval count used for that dataset

### Requirement: Summarize AC-versus-fragility coupling across multiple scales and aggregation levels
The system SHALL compute AC-versus-fragility coupling summaries across raw-value and standardized-value representations and across window-level, interval-summary, and band-aggregated views.

#### Scenario: Coupling summaries cover multiple valid views of the same dynamic data
- **WHEN** the audit processes a completed run
- **THEN** it emits coupling summaries that identify the value scale, aggregation level, and grouping view used for each result
- **AND** the summaries include overall, patient-level, region-level, or band-level coupling views wherever the required data are available

### Requirement: Provide structural baseline context for metric-coupling interpretation
The system SHALL emit a structural baseline summary that estimates expected AC-versus-fragility coupling under simulated stable state matrices matched to the observed node-count structure and records the baseline assumptions.

#### Scenario: Structural baseline is written with audit provenance
- **WHEN** the audit computes observed AC-versus-fragility coupling summaries
- **THEN** it also writes a baseline summary derived from simulated stable state matrices
- **AND** the baseline output records the simulation assumptions needed to interpret the comparison

### Requirement: Keep audit outputs explicitly exploratory and traceable
The system SHALL write dynamic phenotype audit outputs into a dedicated run-scoped location with metadata that distinguishes exploratory audit artifacts from the main inferential reporting outputs.

#### Scenario: Audit artifacts are separated from primary statistics
- **WHEN** the audit stage completes
- **THEN** its tables, summaries, and metadata are written outside the primary inferential result files
- **AND** downstream users can identify those artifacts as audit/exploratory outputs from filenames or recorded metadata
