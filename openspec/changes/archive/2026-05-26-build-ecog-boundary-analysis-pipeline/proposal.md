## Why

The current repository can export cleaned FIF recordings into a read-only BIDS derivative and generate basic QC, but it cannot yet execute the Version 2 research plan from `docs/科研路径提纲版本2.md`. The next step is to add a reproducible analysis pipeline that aligns `ele_pos.xlsx` interval labels with bipolar ECoG signals, computes the agreed feature families, and writes run-scoped outputs that can be re-generated and audited across repeated studies.

## What Changes

- Add a standardized interval-level manifest that parses `datas/ele_pos.xlsx`, converts adjacent contacts into bipolar analysis units, and records region, distance, boundary-interface, and QC inclusion flags.
- Add Python analysis scripts and reusable modules that read `datas/data_02_BIDS` without modifying it, derive adjacent bipolar signals, and compute:
  - static multi-band connectivity and multilayer features
  - HFO event summaries
  - dynamic controllability features
  - neural fragility features
- Add model-ready long-table exports with patient-level z-scored features and main-vs-sensitivity QC flags for downstream statistics.
- Add an R-based reporting layer for mixed-effects models, spline distance analyses, Moran's I diagnostics, multiple-comparison correction summaries, and publication-oriented figures.
- Standardize all pipeline outputs under `results/<timestamp>/...` using numbered stage folders so multiple runs remain isolated and traceable.

## Capabilities

### New Capabilities
- `bipolar-boundary-manifest`: Standardize interval label parsing, bipolar interval mapping, and QC inclusion tables for `before` ECoG analyses.
- `ecog-boundary-feature-extraction`: Compute static, HFO, controllability, and fragility features from read-only BIDS inputs and export model-ready data tables.
- `boundary-analysis-reporting`: Run R-based statistics and khaki-themed figures from exported tables into timestamped result directories.

### Modified Capabilities
- None.

## Impact

- Affected code: new Python modules under `src/ecog_glioma/`, new CLI scripts under `scripts/`, new R scripts under `scripts_r/`, and script documentation updates.
- Affected data flow: `datas/data_02_BIDS` and `datas/ele_pos.xlsx` become the canonical read-only inputs for the analysis pipeline.
- Affected outputs: all derived research outputs move to `results/<timestamp>/` rather than mixing files at the repository root.
- Dependencies: likely Python additions for connectivity/network math and table export, plus documented R package requirements for modeling and plotting.
