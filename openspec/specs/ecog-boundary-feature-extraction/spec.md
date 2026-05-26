## ADDED Requirements

### Requirement: Read BIDS inputs without modifying the dataset
The system SHALL treat `datas/data_02_BIDS` as read-only input and write all derived research outputs under a run-scoped directory in `results/<timestamp>/`.

#### Scenario: Feature extraction starts from an existing BIDS dataset
- **WHEN** a pipeline stage reads recordings, channels, or events from `datas/data_02_BIDS`
- **THEN** it does not create, update, or delete any file inside the BIDS tree and only writes outputs to the active run directory

### Requirement: Compute static multi-band connectivity and multilayer features
The system SHALL compute static connectivity from QC-passing bipolar intervals across the agreed frequency bands and export node-level and multilayer summary features for each patient.

#### Scenario: Static connectivity is computed for a patient
- **WHEN** a patient passes QC for static analysis
- **THEN** the system computes dwPLI-based connectivity for delta, theta, alpha, beta, low-gamma, and high-gamma bands and exports node-level `strength`, `EC`, and `clustering` summaries

#### Scenario: Multilayer summaries are exported
- **WHEN** band-wise connectivity matrices have been computed for a patient
- **THEN** the system exports `mEC`, `MPC`, and `interlayer_similarity` summaries and records the layer-coupling parameter used for each result set

### Requirement: Compute HFO event and rate summaries
The system SHALL detect ripple and fast-ripple events from QC-passing bipolar intervals and export both event-level detections and interval-level rate summaries.

#### Scenario: HFO detections are exported
- **WHEN** the HFO stage completes for a patient
- **THEN** the run directory contains event-level outputs with event timing, HFO subtype, and artifact-related metadata plus interval-level rate summaries in events-per-minute units

### Requirement: Compute dynamic controllability features from sliding windows
The system SHALL estimate dynamic state representations from QC-passing bipolar intervals using sliding windows and export interval-level summaries for average and modal controllability.

#### Scenario: Bad windows are excluded from controllability estimates
- **WHEN** a sliding window overlaps a bad annotation segment
- **THEN** that window is excluded from controllability estimation and the exclusion is logged in the dynamic-stage outputs

#### Scenario: Controllability summaries are exported
- **WHEN** window-level controllability values have been computed for an interval
- **THEN** the system exports interval-level summaries including at least mean, standard deviation, and upper-quantile controllability statistics

### Requirement: Compute neural fragility from the shared dynamic-state workflow
The system SHALL compute neural fragility from the same windowing and state-matrix estimation workflow used for controllability and export interval-level fragility summaries.

#### Scenario: Fragility shares dynamic preprocessing
- **WHEN** the fragility stage runs on a patient
- **THEN** it uses the same bad-window handling, window definitions, and state-matrix estimation pathway configured for controllability

### Requirement: Export model-ready long tables
The system SHALL export normalized long-form tables that join feature values to interval labels, QC flags, and patient identifiers for direct consumption by downstream R statistics scripts.

#### Scenario: Feature tables are prepared for R
- **WHEN** Python feature extraction has completed for a run
- **THEN** the system exports long-form tables that include `patient`, `subject`, `interval_id`, `region`, `distance_mm`, `is_boundary_interface`, feature identifiers, raw values, patient-level z-scored values, and main-vs-sensitivity inclusion flags
