## ADDED Requirements

### Requirement: Run inferential reporting separately for named analysis cohorts
The system SHALL execute supported inferential reporting workflows separately for `main`, `sensitivity`, and `full_modelable` cohorts rather than silently treating all modelable rows as one default cohort.

#### Scenario: Cohort-specific model outputs are written
- **WHEN** a user runs the R reporting stage on a completed analysis run
- **THEN** the system writes cohort-labeled outputs for supported region, distance, and region-by-band reporting workflows
- **AND** each cohort-specific output records the patient and row counts used for that result set

#### Scenario: Insufficient cohorts are skipped explicitly
- **WHEN** a requested cohort does not contain enough data for a supported reporting workflow
- **THEN** the system records that the cohort was skipped or marked insufficient for that workflow
- **AND** eligible cohorts still produce their own outputs

### Requirement: Preserve main-versus-exploratory reporting roles
The system SHALL distinguish the primary main-analysis outputs from sensitivity and full-cohort exploratory outputs in run metadata, summaries, and report artifacts.

#### Scenario: Reporting artifacts identify their analysis role
- **WHEN** summary tables, rendered reports, or figures are produced
- **THEN** each artifact identifies whether it represents `main`, `sensitivity`, or `full_modelable` reporting
- **AND** exploratory outputs are not merged into the primary main-analysis summary without explicit labeling
