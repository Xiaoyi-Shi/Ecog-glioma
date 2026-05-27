## Why

The strongest current finding is the near-perfect negative coupling between average controllability and neural fragility, but the existing audit already shows that part of this anticorrelation can arise from stable-matrix structure alone. Before building a "compensation mechanism" narrative, the project needs a focused robustness pass that separates biological signal from metric construction, sampling, and threshold-choice artifacts.

## What Changes

- Add a dedicated robustness workflow that decomposes AC-NF coupling across between-patient, within-patient, within-region, and within-band views rather than reporting only pooled correlations.
- Add null and sensitivity summaries that compare observed coupling against structural baselines, inclusion-threshold choices, and region-2 distance-threshold choices.
- Add compact QC/confound summaries for interval counts, patient contribution imbalance, and simple structural covariates that could mechanically drive AC-NF coupling.
- Produce a single interpretation-facing report that labels which coupling results are primary, which are exploratory, and which fail robustness checks.

## Capabilities

### New Capabilities
- `coupling-robustness-analysis`: Generate decomposition tables, null comparisons, and robustness summaries for AC-NF coupling across cohorts, patient structure, regions, bands, and threshold choices.
- `threshold-sensitivity-scan`: Scan inclusion and boundary-distance thresholds and summarize whether the primary AC/NF findings remain directionally and statistically stable.

### Modified Capabilities
- `boundary-analysis-reporting`: Extend reporting outputs so the main report can explicitly distinguish robustness-supported findings from exploratory or threshold-dependent findings.

## Impact

- Affected code: Python stage orchestration, dynamic audit/reporting helpers, model-table exports, and R reporting templates that summarize phenotype findings.
- Affected outputs: new robustness tables and reports will be added under each run directory, and reporting metadata will record threshold definitions and robustness status.
- Affected interpretation: the next paper narrative will be allowed to promote AC-NF coupling only if it survives decomposition and sensitivity checks; otherwise it will be reframed as a metric-coupling or sampling-sensitive observation.
