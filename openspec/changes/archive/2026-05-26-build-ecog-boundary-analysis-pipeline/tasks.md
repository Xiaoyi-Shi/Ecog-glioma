## 1. Run Context And Manifest

- [x] 1.1 Add shared run-context utilities that create `results/<timestamp>/` and the stage-specific subdirectories used by Python and R.
- [x] 1.2 Implement `ele_pos.xlsx` interval parsing into a standardized `before`-session label manifest with `region`, `distance_mm`, `is_boundary_interface`, and parse-status fields.
- [x] 1.3 Implement adjacent bipolar interval mapping from BIDS channels and export interval-level and patient-level QC inclusion tables.

## 2. Static Network And HFO Features

- [x] 2.1 Implement bipolar signal derivation with bad-endpoint propagation and reusable clean-segment selection helpers.
- [x] 2.2 Implement dwPLI-based static connectivity across the agreed frequency bands and export node-level `strength`, `EC`, and `clustering` summaries.
- [x] 2.3 Implement multilayer summaries (`mEC`, `MPC`, `interlayer_similarity`) with recorded coupling parameters and sensitivity-ready metadata.
- [x] 2.4 Implement ripple and fast-ripple detection plus event-level and interval-level HFO summary exports.

## 3. Dynamic Features

- [x] 3.1 Implement shared sliding-window and state-matrix estimation utilities with bad-annotation window exclusion and stage logging.
- [x] 3.2 Implement average and modal controllability exports from the shared dynamic-state workflow.
- [x] 3.3 Implement neural fragility exports from the same dynamic-state workflow and summarize interval-level fragility statistics.

## 4. Model Tables And R Reporting

- [x] 4.1 Export long-form model tables that join labels, QC flags, raw feature values, and patient-level z-scored feature values.
- [x] 4.2 Add R scripts for region models, distance/spline models, Moran's I diagnostics, and multiple-comparison summaries against the exported tables.
- [x] 4.3 Add a shared khaki plotting theme and figure scripts that write publication-style outputs into the run-specific figures directory.
- [x] 4.4 Add run metadata and logging outputs that tie Python and R stages back to a single timestamped analysis run.

## 5. Orchestration And Verification

- [x] 5.1 Add CLI entry points or documented stage runners for manifest, feature, statistics, and figure generation.
- [x] 5.2 Update repository documentation for dependencies, execution order, and the `results/<timestamp>/` output layout.
- [x] 5.3 Verify the pipeline on the current `before` dataset and confirm that all outputs remain outside `datas/data_02_BIDS`.
