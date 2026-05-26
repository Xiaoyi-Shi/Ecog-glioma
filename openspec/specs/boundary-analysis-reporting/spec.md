## ADDED Requirements

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
