## Why

The current boundary-analysis pipeline produces interesting dynamic findings, but the strongest interpretation is not yet defensible. The reporting layer still mixes modelable patients instead of cleanly separating main and sensitivity cohorts, and the headline AC-vs-fragility pattern needs an explicit audit before it can support a mechanism-level narrative.

## What Changes

- Add an audit workflow for the dynamic phenotype that re-expresses average controllability and neural fragility across cohort definitions, raw-vs-standardized scales, and aggregation levels so the observed dissociation can be checked for robustness and possible metric-coupling artifacts.
- Update the reporting workflow so main-analysis, sensitivity-analysis, and full modelable-cohort results are emitted separately rather than being summarized from a single mixed cohort by default.
- Add audit-oriented result tables and summaries that make it clear which cohort, feature scale, and comparison basis produced each dynamic phenotype finding.
- Tighten run metadata and reporting provenance so downstream summaries can distinguish exploratory audit outputs from main inferential outputs.

## Capabilities

### New Capabilities
- `dynamic-phenotype-audit`: Produce audit-ready dynamic phenotype tables and summaries that test whether the AC-vs-fragility pattern is stable across cohorts, scales, and aggregation choices.

### Modified Capabilities
- `boundary-analysis-reporting`: Change reporting requirements so region, interaction, and summary outputs are partitioned into main, sensitivity, and full modelable cohorts with explicit cohort labeling and provenance.

## Impact

- Affected code: `scripts_r/run_boundary_models.Rmd`, `scripts_r/run_boundary_figures.Rmd`, and supporting Python orchestration/report metadata code that defines run outputs.
- Affected outputs: run directories will gain explicit cohort-partitioned statistics plus dynamic phenotype audit tables/reports in addition to the existing stage outputs.
- Affected interpretation: the pipeline will treat AC-vs-fragility as a claim that must be audited before being promoted to the main biological narrative.
