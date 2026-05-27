# boundary-analysis-reporting Specification

## Purpose
Define the run-scoped statistical modeling and figure-generation requirements for the boundary analysis workflow, including cohort-partitioned outputs and robustness-aware reporting.

## Requirements
### Requirement: Create a timestamped results layout for each analysis run
The system SHALL create a new timestamped run directory under `results/` for each pipeline execution and organize outputs into stable stage-specific subdirectories.

#### Scenario: New run directory is created
- **WHEN** a user starts a new analysis run
- **THEN** the system creates a unique directory named with a timestamp and initializes stage folders for manifests, QC, feature outputs, model tables, statistics, figures, and logs

### Requirement: Run R-based statistical analyses from exported tables
The system SHALL execute R scripts against Python-exported tables to produce the mixed-effects, spline, spatial-autocorrelation, multiplicity, and summary outputs needed by the research workflow.

#### Scenario: Region and distance models are computed
- **WHEN** the R statistics stage receives model-ready long tables
- **THEN** it writes statistical result tables covering region effects, distance effects, spline fits, and multiplicity-adjusted summaries into the run-specific statistics directory

#### Scenario: Boundary-interface and spatial diagnostics are computed
- **WHEN** the R statistics stage evaluates supported feature sets
- **THEN** it includes `is_boundary_interface` terms where applicable and exports Moran's I diagnostics or equivalent spatial-autocorrelation summaries

### Requirement: Generate khaki-themed figures from run-specific results
The system SHALL generate figures with a khaki-background visual theme and write them into the run-specific figures directory.

#### Scenario: Figure generation uses the project theme
- **WHEN** an R plotting script renders a figure for the analysis run
- **THEN** the figure uses the project khaki-background style and is saved into the active run directory without overwriting figures from previous runs

### Requirement: Preserve run provenance across Python and R stages
The system SHALL persist enough run metadata and logging so a generated figure or statistics table can be traced back to the specific inputs, thresholds, and stage outputs that produced it.

#### Scenario: Run metadata is recorded
- **WHEN** a pipeline run completes any stage
- **THEN** the active run directory contains machine-readable metadata or logs identifying the run timestamp, stage outputs, and key parameter settings used by Python and R

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

### Requirement: Surface robustness status in phenotype reporting
The system SHALL expose robustness-stage conclusions in the run-specific phenotype reporting outputs so the main narrative can distinguish robustness-supported findings from exploratory, artifact-risk, or threshold-sensitive findings.

#### Scenario: Reporting artifacts incorporate robustness classifications
- **WHEN** a run contains completed coupling-robustness outputs
- **THEN** the reporting layer includes the robustness status and source artifact reference for each tracked AC/NF headline finding
- **AND** the primary main-cohort narrative does not present an exploratory or artifact-risk finding as if it were robustness-supported

#### Scenario: Reporting degrades gracefully when robustness outputs are absent
- **WHEN** a user rerenders reporting for a run that does not contain the coupling-robustness stage
- **THEN** the reporting layer records that robustness classification is unavailable
- **AND** the rerender still succeeds without fabricating robustness labels

### Requirement: Keep reporting downstream of audit and robustness computation
The system SHALL consume precomputed audit and robustness artifacts in reporting outputs rather than silently recomputing those exploratory or robustness layers inside the reporting step.

#### Scenario: Reporting references upstream audit and robustness artifacts
- **WHEN** a run contains completed `09_dynamic_audit` or `10_coupling_robustness` outputs
- **THEN** reporting artifacts reference or summarize those upstream outputs
- **AND** the reporting layer preserves the provenance boundary between computed source artifacts and rendered narrative summaries
