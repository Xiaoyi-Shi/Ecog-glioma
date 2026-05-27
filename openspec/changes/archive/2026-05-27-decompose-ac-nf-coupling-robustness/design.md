## Context

The current pipeline now separates `main`, `sensitivity`, and `full_modelable` reporting cohorts and writes an exploratory dynamic audit under `09_dynamic_audit/`. On the 2026-05-27 run, observed AC-NF coupling is consistently very negative across cohorts and scales, but the structural baseline audit also shows that stable state-matrix structure alone can induce substantial negative coupling. The main scientific risk is therefore over-interpreting pooled anticorrelation as a biological compensation mechanism before decomposing where the signal comes from and how sensitive it is to threshold choices.

Constraints:
- Upstream BIDS inputs remain read-only.
- Existing feature extraction stages are already validated and should not be recomputed unnecessarily.
- The primary cohort is small (`9` patients), so patient-level pseudo-replication must be handled explicitly.
- The next change should work from completed `results/<timestamp>/` runs whenever possible.

## Goals / Non-Goals

**Goals:**
- Decompose AC-NF coupling into pooled, between-patient, within-patient, within-region, and within-band views that are interpretable with the current nested data structure.
- Compare observed coupling against null references that address both metric-construction effects and threshold/sampling effects.
- Quantify whether the headline findings are stable across inclusion thresholds and region-2 distance-threshold choices.
- Expose a machine-readable robustness status that downstream reports can use to separate primary conclusions from exploratory observations.

**Non-Goals:**
- Replacing current AC or fragility estimators.
- Adding new HFO detectors, clustering, or supervised classification in this change.
- Claiming causal or clinical conclusions from the robustness outputs.
- Rebuilding the full upstream feature-extraction pipeline for every sensitivity configuration when the exported run tables already contain the needed provenance.

## Decisions

### Decision: Reuse completed run outputs instead of rerunning upstream feature extraction
The robustness workflow will consume existing `06_model_tables/` outputs plus the exploratory `09_dynamic_audit/` artifacts from a completed run directory.

Rationale:
- The open question is interpretive robustness, not feature generation correctness.
- Reusing completed runs keeps iteration fast and avoids changing validated upstream outputs.

Alternatives considered:
- Full pipeline reruns for every threshold configuration: rejected as too slow and unnecessary for a first-pass robustness audit.

### Decision: Add a dedicated post-audit stage for robustness outputs
The pipeline will add a new run-scoped stage after `09_dynamic_audit/` for decomposition tables, threshold scans, null comparisons, and a compact summary report.

Rationale:
- Robustness outputs are not primary inferential model tables.
- Keeping them in a dedicated stage avoids polluting `07_stats_r/` while preserving provenance.

Alternatives considered:
- Fold robustness tables into `09_dynamic_audit/`: rejected because `09` already serves exploratory data assembly and basic coupling summaries; the new stage adds interpretive classification and threshold scans.

### Decision: Use decomposition tables rather than a single new omnibus model
The workflow will compute separate summaries for pooled rows, patient means, patient-centered rows, region-stratified rows, and band-stratified rows, with explicit insufficient-data statuses when a view is too sparse.

Rationale:
- This directly answers whether the negative coupling is mostly between patients, within patients, or only in certain strata.
- Decomposition tables are easier to audit and explain than a more opaque covariance-partition model.

Alternatives considered:
- A single multilevel covariance model: rejected for the first iteration because it is harder to validate and less transparent for report readers.

### Decision: Calibrate robustness with two null families
The new stage will compare observed coupling against:
1. the existing stable-matrix structural baseline, and
2. label-preserving or stratum-preserving permutation summaries that break the observed pairing while keeping cohort and grouping sizes fixed.

Rationale:
- The structural baseline addresses metric-construction coupling.
- Permutations address whether the observed effect could arise from the current sampling structure alone.

Alternatives considered:
- Structural baseline only: rejected because it does not address threshold- or grouping-dependent sampling artifacts.

### Decision: Restrict threshold sensitivity to a small predefined grid
The first implementation will scan a compact grid of inclusion thresholds and region-2 distance thresholds and summarize stability for the main headline findings: region-2 AC elevation, region-2 fragility reduction, and AC-NF coupling direction/magnitude.

Rationale:
- A compact grid is enough to reveal whether conclusions are brittle.
- This keeps runtime and output size bounded.

Alternatives considered:
- Exhaustive continuous threshold optimization: rejected because it would encourage p-hacking and produce a harder-to-defend narrative.

### Decision: Emit explicit robustness labels for reporting
Each headline finding will receive a machine-readable status such as `supported`, `exploratory`, `artifact_risk`, `threshold_sensitive`, or `insufficient`.

Rationale:
- The reporting layer needs a compact, non-hand-wavy way to describe what survived the checks.
- Explicit labels also force the classification logic to be reviewable.

Alternatives considered:
- Free-text interpretation only: rejected because it is harder to test and easier to overstate.

## Risks / Trade-offs

- [Distance-threshold relabeling may not perfectly match the original region semantics] -> Record the relabeling rule explicitly, limit scans to rows with valid numeric distances, and mark missing-distance rows as excluded.
- [Within-patient or within-region decompositions may be sparse in the main cohort] -> Emit explicit insufficient-data statuses rather than unstable summary values.
- [Permutation scans may increase runtime or produce large artifacts] -> Persist only summary tables and seed/provenance metadata, not every replicate-level row.
- [Robustness labels could look arbitrary] -> Define the decision rules in code and write the supporting evidence columns used for each label.
- [A dedicated robustness stage adds one more reporting layer] -> Keep the outputs compact and make the main report link to one summary file rather than duplicating every table.

## Migration Plan

1. Add the new robustness stage directory to run metadata and reporting documentation.
2. Implement the stage so it can run on an existing completed run directory after `09_dynamic_audit/`.
3. Update reporting templates to consume robustness summary outputs when present and to fall back gracefully when absent.
4. Re-run the reporting workflow on the 2026-05-27 results directory and confirm that upstream feature stages remain untouched.

## Open Questions

- What exact inclusion-threshold grid is best for the current patient distribution: `8/10/12/14/16/18`, or a smaller subset?
- Which structural covariates already exposed in exported tables are sufficient for the first confound summary?
- Should region-1 rows participate in distance-threshold sensitivity, or should that scan be limited to boundary-vs-remote reassignment outside the tumor core?
