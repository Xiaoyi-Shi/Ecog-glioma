## 1. Cohort Plumbing And Run Layout

- [x] 1.1 Add a dedicated dynamic-audit stage to the run context and stage-directory metadata so audit outputs have a stable run-scoped home.
- [x] 1.2 Implement shared cohort-partition helpers that derive `main`, `sensitivity`, and `full_modelable` datasets from existing model-table inclusion flags.
- [x] 1.3 Persist cohort counts and analysis-role metadata so downstream reports can identify primary versus exploratory outputs.

## 2. Cohort-Partitioned Reporting

- [x] 2.1 Refactor the R reporting pipeline to run supported region, distance, and region-by-band workflows separately for each named cohort.
- [x] 2.2 Update reporting outputs to record cohort labels, patient counts, row counts, and explicit skipped/insufficient-data status where a cohort cannot support a workflow.
- [x] 2.3 Update rendered summaries and figures so `main` outputs remain primary while `sensitivity` and `full_modelable` outputs are clearly labeled as secondary or exploratory.

## 3. Dynamic Phenotype Audit

- [x] 3.1 Add audit data assembly that reads existing model tables plus window-level controllability and fragility outputs from a completed run directory.
- [x] 3.2 Compute AC-versus-fragility coupling summaries across raw, `feature_z`, and `feature_z_within_band` scales and across window-level, interval-summary, and band-aggregated views.
- [x] 3.3 Add patient-, region-, and band-resolved coupling summaries with machine-readable provenance fields for cohort, scale, and aggregation level.
- [x] 3.4 Implement the simulated stable-matrix baseline summary used to contextualize possible metric-coupling artifacts in the observed AC-versus-fragility pattern.
- [x] 3.5 Emit an audit summary artifact that separates exploratory dynamic-audit findings from the main inferential reporting outputs.

## 4. Verification And Documentation

- [x] 4.1 Add or update automated tests for cohort partitioning, cohort-labeled reporting outputs, and dynamic-audit summary assembly.
- [x] 4.2 Run the updated reporting workflow on an existing `results/<timestamp>/` directory and verify that `main`, `sensitivity`, and `full_modelable` outputs are separated and counted correctly.
- [x] 4.3 Verify that the dynamic-audit stage writes the expected tables, baseline summaries, and provenance metadata without changing upstream feature outputs.
- [x] 4.4 Update repository documentation and result-summary conventions to describe the new cohort semantics, audit stage, and interpretation boundaries.
