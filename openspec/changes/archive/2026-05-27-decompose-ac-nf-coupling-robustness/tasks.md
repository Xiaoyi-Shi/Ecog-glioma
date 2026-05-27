## 1. Robustness Stage Scaffolding

- [x] 1.1 Add a dedicated run-scoped robustness stage and metadata entry so completed runs have a stable home for coupling decomposition and threshold-scan outputs.
- [x] 1.2 Implement run-directory loaders that reuse existing model tables and dynamic-audit artifacts without recomputing upstream feature stages.
- [x] 1.3 Define the tracked headline findings and machine-readable robustness-status schema used across tables and reports.

## 2. Coupling Decomposition And Null Calibration

- [x] 2.1 Implement pooled, between-patient, within-patient, within-region, and within-band AC-NF decomposition summaries with explicit insufficient-data handling.
- [x] 2.2 Add structural-baseline comparisons and stratum-preserving permutation summaries for each supported coupling view.
- [x] 2.3 Write a robustness summary artifact that assigns `supported`, `exploratory`, `artifact_risk`, `threshold_sensitive`, or `insufficient` labels with supporting evidence columns.

## 3. Threshold Sensitivity And Reporting

- [x] 3.1 Implement the predefined inclusion-threshold scan and persist patient counts, interval counts, and headline AC/NF summaries for each threshold.
- [x] 3.2 Implement the predefined region-2 distance-threshold scan using rows with valid distance metadata and record explicit exclusion/insufficient statuses.
- [x] 3.3 Generate a compact stability matrix that merges inclusion-threshold and distance-threshold results for downstream reporting.
- [x] 3.4 Update reporting outputs so the main narrative surfaces robustness status when available and degrades gracefully when the robustness stage is absent.

## 4. Verification And Documentation

- [x] 4.1 Add or update automated tests for decomposition outputs, null-comparison provenance, threshold-scan summaries, and reporting fallback behavior.
- [x] 4.2 Run the robustness workflow on `results/20260527_135055` and verify that the new stage writes the expected artifacts without modifying upstream feature outputs.
- [x] 4.3 Update repository documentation and result-summary conventions to describe robustness labels, threshold scans, and interpretation boundaries.
