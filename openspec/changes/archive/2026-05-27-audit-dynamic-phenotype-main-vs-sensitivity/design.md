## Context

The repository already exports dynamic feature summaries, model tables, and R-based statistics for the boundary-analysis workflow. The current reporting path, however, treats all modelable rows as one default cohort, even though the upstream tables already carry `patient_main_included` and `patient_sensitivity_included` flags. At the same time, the strongest scientific discussion now centers on the observed average-controllability versus fragility dissociation, but the current coupling summary is built from a narrow role table that averages patient-level z-scores across bands and does not explicitly separate raw-value behavior, cohort membership, or potential metric-coupling artifacts.

This change therefore sits across the Python-to-R boundary: existing feature extraction is largely sufficient, but the reporting contract and run outputs need to make cohort selection explicit and add a bounded dynamic-phenotype audit layer before the current AC-vs-fragility interpretation is promoted into the main narrative.

## Goals / Non-Goals

**Goals:**
- Make `main`, `sensitivity`, and `full_modelable` cohorts first-class reporting units instead of implicit post hoc summaries.
- Add a reproducible dynamic-phenotype audit that tests whether the AC-vs-fragility pattern persists across cohort definitions, raw-vs-standardized scales, and aggregation levels already supported by the pipeline outputs.
- Add provenance-rich audit outputs that distinguish inferential model results from exploratory audit summaries within the same run directory.
- Reuse existing dynamic stage outputs and model tables whenever possible so the audit measures interpretation robustness rather than changing the underlying signal-processing pipeline.

**Non-Goals:**
- Replacing the current controllability or fragility algorithms in this change.
- Adding new biological modalities such as transfer entropy, outcome prediction, or `after`-session analyses.
- Building a large parameter-sweep framework across every threshold, band definition, and model family.
- Elevating exploratory audit outputs into final biological conclusions automatically.

## Decisions

### 1. Define cohort partitions in the reporting layer and propagate them as explicit output metadata

The reporting workflow will construct three named cohorts from existing inclusion flags:
- `main`: rows from patients with `patient_main_included = TRUE`
- `sensitivity`: rows from patients with `patient_sensitivity_included = TRUE`
- `full_modelable`: all rows that reach the model tables

All inferential model outputs and audit summaries will carry a cohort label, row counts, and patient counts.

Alternatives considered:
- Filter only in prose or summary markdown. Rejected because the CSV outputs would remain ambiguous and non-reproducible.
- Rebuild model tables separately for each cohort in Python. Rejected because the existing tables already carry sufficient flags, and duplicating tables would create avoidable maintenance cost.

### 2. Add a dedicated run stage for exploratory dynamic audits

The run directory will gain a dedicated top-level stage for dynamic phenotype auditing so exploratory checks remain separate from the main inferential outputs in `07_stats_r` and figure outputs in `08_figures`.

The new stage will hold cohort manifests, coupling summaries, artifact-baseline summaries, and an audit-oriented report or summary document.

Alternatives considered:
- Write audit files into `07_stats_r`. Rejected because it would blur the line between main inferential outputs and robustness checks.
- Write audit plots into `08_figures` only. Rejected because the audit needs machine-readable tables and provenance in addition to figures.

### 3. Build the audit from exported tables and saved dynamic summaries rather than recomputing signals

The audit will consume existing run outputs such as:
- `06_model_tables/model_joint_long.csv`
- `06_model_tables/model_band_metric_long.csv`
- `04_controllability/window_level_ac_mc.csv`
- `04_controllability/channel_level_ac_mc_summary.csv`
- `05_fragility/window_level_fragility.csv`
- `05_fragility/channel_level_fragility_summary.csv`

This keeps the audit focused on interpretation robustness and cohort semantics, not on re-running feature extraction from BIDS input.

Alternatives considered:
- Re-read BIDS recordings and recompute dynamic features inside the audit stage. Rejected because it would duplicate the dynamic pipeline and create a second source of truth.
- Restrict the audit to final `feature_z` values only. Rejected because it would not answer whether the observed dissociation depends on scaling choices.

### 4. Use a bounded audit matrix instead of an open-ended sensitivity framework

The dynamic audit will evaluate AC-vs-fragility behavior across a fixed grid:
- cohorts: `main`, `sensitivity`, `full_modelable`
- scales: raw feature values, existing patient-level `feature_z`, and `feature_z_within_band` where available
- aggregation levels: window-level, interval-summary level, and band-aggregated interval level
- grouping views: overall, by patient, by region, and by band

This yields a finite set of outputs that can be reviewed and compared without turning the change into a general-purpose sensitivity platform.

Alternatives considered:
- Add all threshold, band-definition, and modeling sensitivities now. Rejected because it would dilute the immediate goal of validating the central dynamic finding.
- Audit only the strongest published summary statistics. Rejected because the main concern is whether the pattern survives different legitimate views of the same data.

### 5. Include a structural baseline for metric-coupling artifact checks

The audit will include a baseline summary that compares observed AC-vs-fragility coupling against values produced from simulated stable state matrices using matched node counts and bounded spectral radii. This baseline is not a proof of artifact or biology, but it provides necessary context for deciding whether the observed negative coupling is exceptional under the current metric definitions.

Alternatives considered:
- No artifact baseline. Rejected because it would leave the most important interpretive objection unanswered.
- Full surrogate generation from raw signals. Rejected because it is materially more complex and not required for the first audit pass.

### 6. Keep the main biological narrative conservative until the audit passes

This change will formalize the audit outputs and cohort partitioning, but it will not automatically rename the dynamic pattern as a compensatory mechanism. Main summaries should treat the AC-vs-fragility result as a robustness-tested phenotype claim whose mechanistic interpretation remains downstream.

Alternatives considered:
- Encode the compensatory interpretation directly into the reporting layer. Rejected because the software contract should remain descriptive and testable.

## Risks / Trade-offs

- [Risk] The simulated artifact baseline may be criticized as an imperfect proxy for the real dynamic pipeline. → Mitigation: report it as a contextual baseline, preserve its assumptions in metadata, and keep observed-data summaries primary.
- [Risk] Cohort splitting reduces sample size and may make some previously visible effects unstable. → Mitigation: record cohort-specific counts, effect sizes, and model fallback status so instability is explicit rather than hidden.
- [Risk] Additional audit outputs can confuse downstream interpretation if they look equivalent to main inferential results. → Mitigation: place them in a dedicated stage and label them as audit/exploratory artifacts in filenames and metadata.
- [Risk] Window-level audits can increase output volume. → Mitigation: reuse existing window tables, write compact summary CSVs, and avoid duplicating heavyweight intermediates.

## Migration Plan

1. Extend run-context metadata and stage layout to include a dedicated dynamic-audit stage.
2. Refactor the R reporting entry point so cohort definitions are created once and reused consistently across region models, interaction models, summaries, and figures.
3. Emit cohort-labeled inferential outputs for `main`, `sensitivity`, and `full_modelable` cohorts without changing the upstream feature-extraction contract.
4. Add the dynamic audit tables and summary report using the existing model tables and window-level dynamic outputs.
5. Update documentation and result-summary conventions so users know which files are main inferential outputs versus audit outputs.

Rollback is straightforward because the change is additive: the audit stage and cohort-partitioned reports can be disabled without affecting BIDS inputs or previously generated feature outputs.

## Open Questions

- Should the audit summary be rendered as an R Markdown HTML report, a markdown file, or CSV-only plus figures?
- How tightly should the structural baseline match observed state-matrix spectra in the first implementation pass?
- Should `full_modelable` outputs be presented alongside main and sensitivity results by default, or only as explicitly exploratory tables?
