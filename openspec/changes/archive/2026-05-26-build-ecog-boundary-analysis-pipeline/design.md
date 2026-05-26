## Context

The repository already supports a cleaned-FIF-to-BIDS derivative export and an HTML QC report, but the research workflow described in `docs/科研路径提纲版本2.md` requires a broader analysis stack. The key methodological constraint is that `datas/ele_pos.xlsx` stores labels for adjacent contact intervals such as `1_2`, `2_3`, and `23_24`, while the BIDS recordings store single-contact channels such as `EEG 1` through `EEG 24`. A direct channel-level analysis would therefore misalign the signal unit with the spatial label unit.

The user has fixed four implementation constraints for this change:

- Main analyses SHALL use adjacent bipolar derivations before feature extraction.
- `b*[0]` SHALL be encoded as `region = 2` and `is_boundary_interface = 1`.
- Statistical modeling and figure generation SHALL run in R.
- Every pipeline run SHALL write all outputs under `results/<timestamp>/` while treating `datas/data_02_BIDS` as read-only input.

## Goals / Non-Goals

**Goals:**
- Align analysis units with `ele_pos.xlsx` by converting single-contact BIDS channels into adjacent bipolar intervals.
- Build a reusable Python feature-extraction pipeline for static connectivity, HFO, controllability, and fragility analyses.
- Export model-ready long tables that R can consume without additional restructuring.
- Build an R reporting layer for LME, spline, spatial-autocorrelation, multiplicity summaries, and khaki-themed figures.
- Ensure each run is reproducible and isolated via a timestamped `results/<timestamp>/` directory tree.

**Non-Goals:**
- Modifying or rewriting files inside `datas/data_02_BIDS`.
- Adding `after` analyses in this change.
- Building outcome-prediction, machine-learning, or GNN workflows.
- Adding coordinate-based 3D anatomy integration before surgical-image localization is available.
- Finalizing every supplementary method from Version 2 if a stable first-pass implementation can stage them incrementally.

## Decisions

### 1. Use adjacent bipolar derivations as the primary analysis unit

The pipeline will derive `EEG1-EEG2`, `EEG2-EEG3`, ..., `EEG23-EEG24` for each recording before feature extraction. This keeps each signal unit identical to the interval label unit in `ele_pos.xlsx`.

Alternatives considered:
- Map interval labels onto single contacts by midpoint assignment. Rejected because one interval label would be forced onto multiple incompatible single-contact interpretations.
- Keep monopolar channels for all analyses and join interval labels later. Rejected because the spatial label and feature unit would remain mismatched.

### 2. Use a stage-oriented run directory under `results/<timestamp>/`

Each run will create a deterministic directory layout such as `00_manifest`, `01_qc`, `02_static_network`, ..., `08_figures`, plus `logs`. Python and R scripts will receive the same run directory and only write inside it.

Alternatives considered:
- Write outputs directly into `results/` without subfolders. Rejected because repeated runs would overwrite or mix artifacts.
- Write some outputs beside the source data. Rejected because it weakens provenance and risks accidental input mutation.

### 3. Split responsibilities by language boundary

Python will own input parsing, bipolar derivation, QC filtering, feature extraction, and table export. R will own mixed-effects modeling, spline fits, Moran's I diagnostics, multiplicity summaries, and figure generation.

Alternatives considered:
- Keep all computation and statistics in Python. Rejected because the requested LME and reporting workflow is better supported and more maintainable in R for this project.
- Use R for signal processing as well. Rejected because the repository already uses MNE-oriented Python tooling and BIDS access patterns.

### 4. Encode `b*[0]` as a dual representation

Boundary-interface labels will remain in Region 2 for the four-region model and simultaneously set `is_boundary_interface = 1` so the interface effect can be tested independently in the R models.

Alternatives considered:
- Exclude `b*[0]` from the main model. Rejected because the user explicitly wants it retained and modeled.
- Create a fifth region. Rejected because it complicates the main four-region narrative and reduces power with the current sample size.

### 5. Reuse a shared sliding-window state-matrix workflow for controllability and fragility

Dynamic controllability and neural fragility will share the same window extraction, bad-window exclusion, and state-matrix estimation path. AC, MC, and NF will then be derived from that common representation.

Alternatives considered:
- Compute controllability from static undirected connectivity matrices. Rejected because it weakens the linear dynamical systems interpretation described in the research plan.
- Implement fragility as an unrelated standalone pipeline. Rejected because it duplicates windowing logic and makes AC-vs-NF comparisons less coherent.

### 6. Keep BIDS inputs read-only and emit model-ready tables as the integration boundary

The pipeline will not write derivatives back into the BIDS tree. Instead, Python will export normalized long tables that become the formal contract consumed by R.

Alternatives considered:
- Store intermediate derivative files inside BIDS `derivatives/`. Rejected for this change because the user asked for `datas/data_02_BIDS` to remain untouched.
- Pass Python objects in-memory into R. Rejected because run-to-run traceability would become fragile.

## Risks / Trade-offs

- [Risk] Adjacent bipolar intervals share contacts, so some interval-pair dependencies may be inflated. → Mitigation: expose shared-endpoint metadata and plan sensitivity analyses that compare shared-endpoint vs non-shared-endpoint edges.
- [Risk] Bad-contact propagation can reduce the number of usable intervals below the target threshold in lower-quality cases. → Mitigation: emit both main (`>= 16`) and sensitivity (`>= 12`) QC inclusion flags per patient.
- [Risk] HFO detection may be sensitive to artifacts and threshold choice. → Mitigation: save event-level outputs, artifact flags, detector settings, and cross-detector agreement summaries.
- [Risk] Dynamic state estimation can be numerically unstable in short windows. → Mitigation: centralize stability checks, log failed windows, and keep the agreed 2 s / 4 s / 6 s sensitivity settings.
- [Risk] Cross-language orchestration can make failures harder to trace. → Mitigation: create a single run context, persist per-stage logs, and write explicit handoff tables between Python and R.

## Migration Plan

1. Add run-context utilities that create `results/<timestamp>/` and pass the resolved run directory to every stage.
2. Implement the interval manifest and QC outputs first so later stages share one source of truth.
3. Layer static/HFO and then dynamic features on top of the manifest contract.
4. Export R-ready long tables and build R statistics/figure scripts against those stable schemas.
5. Keep existing BIDS export and QC scripts untouched, but update script documentation so the new analysis pipeline is discoverable.

Rollback is simple because the pipeline is additive: disabling the new scripts or deleting a single run directory leaves the existing BIDS workflow unchanged.

## Open Questions

- Which concrete Python libraries should be preferred for multilayer metrics and directed connectivity if the first implementation phase postpones TE/source-sink support?
- Whether the first implementation milestone should include the shared-endpoint sensitivity analysis in code or only reserve the metadata needed for it.
- Whether the pipeline runner should orchestrate R through `Rscript` directly or leave Python and R stages as separately invokable commands plus a documented order.
