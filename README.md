## Ecog Glioma

This repository contains an intraoperative ECoG workflow for:
- manual EDF cleaning into `.fif`
- cleaned FIF export into a read-only BIDS derivative
- patient-level BIDS QC reporting
- boundary-gradient research analysis from BIDS plus `ele_pos.xlsx`

Primary analysis outputs are written under timestamped subdirectories in
`results/`.

Key entry points:
- `scripts/fif_to_bids.py`
- `scripts/bids_qc_report.py`
- `scripts/run_pipeline_v2.py`
