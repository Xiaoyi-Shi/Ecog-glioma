## ADDED Requirements

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
