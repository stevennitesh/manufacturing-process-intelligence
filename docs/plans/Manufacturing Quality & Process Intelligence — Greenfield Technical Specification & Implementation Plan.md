# Manufacturing Quality & Process Intelligence

## 1. Project charter

### Objective

Build a production-quality data science system that demonstrates how manufacturing process data can be used to:

1. predict downstream product quality;
2. quantify prediction uncertainty;
3. support inspection decisions;
4. detect developing process excursions;
5. identify likely contributing process conditions;
6. demonstrate transfer across materially different manufacturing environments.

The core abstraction is:

\[
\boxed{\text{manufacturing process} \rightarrow \text{product quality}}
\]

The project should demonstrate manufacturing statistics, modern ML, data engineering, MLOps, explainability, uncertainty quantification, and production-oriented software engineering without pretending to operate a real factory.

---

# 2. Portfolio positioning

The project should communicate:

> Built an end-to-end manufacturing quality intelligence system for predictive quality, process monitoring, uncertainty-aware inspection, and excursion diagnostics; validated across automotive/discrete manufacturing and semiconductor process data.

It should look appropriate for:

- Manufacturing Data Scientist
- Industrial Data Scientist
- Manufacturing ML Engineer
- Yield Data Scientist
- Process Analytics Engineer
- Quality Analytics Engineer
- Industrial AI Engineer
- Semiconductor Data Scientist
- Reliability / Process Data Scientist
- Manufacturing Data Engineer with ML responsibilities

The distinguishing characteristic should be the combination of:

\[
\text{manufacturing statistics}
+
\text{ML}
+
\text{software engineering}
+
\text{operational decisions}
\]

rather than model novelty.

---

# 3. Scope

## In scope

The finished core project covers:

- predictive quality / virtual metrology;
- tabular process ML;
- regression and quality classification where valid;
- uncertainty quantification;
- inspection policy optimization;
- SPC;
- multivariate process monitoring;
- change/excursion detection;
- process/signal feature engineering;
- root-cause candidate analysis;
- model/data drift;
- reproducible training;
- experiment tracking;
- API inference;
- operational visualization;
- transfer to a semiconductor process.

## Explicitly out of scope for the core

Do not add these until the core is complete:

- predictive maintenance;
- computer vision;
- Kubernetes;
- distributed Spark infrastructure;
- Kafka;
- enterprise feature stores;
- LLM agents;
- RAG;
- digital twins;
- reinforcement learning;
- autonomous process control;
- full MES/SCADA emulation.

Those could create more surface area without improving the manufacturing DS story.

---

# 4. Dataset strategy

## Primary dataset — SoliDAIR

Purpose:

\[
\boxed{\text{predictive quality / virtual metrology}}
\]

Use for:

- upstream-process → EoL-quality prediction;
- continuous quality regression;
- potentially pass/fail prediction if authoritative specification limits exist;
- uncertainty estimation;
- inspection policy simulation;
- feature attribution;
- real-versus-simulation experiments later.

This is the MVP dataset.

---

## Secondary dataset — CiP-DMD

Purpose:

\[
\boxed{\text{physical process monitoring and diagnosis}}
\]

Use for:

- physical sensor signals;
- subprocess identification;
- SPC;
- EWMA/CUSUM;
- multivariate process monitoring;
- signal processing;
- known anomaly detection;
- quality traceability;
- root-cause candidate validation.

This becomes V1.

---

## Transfer dataset — Bosch Plasma Etching

Purpose:

\[
\boxed{\text{semiconductor transfer validation}}
\]

Use for:

- multirate process telemetry;
- optical spectra;
- high-dimensional signal compression;
- wafer virtual metrology;
- day/process drift;
- semiconductor-quality prediction.

This becomes V2.

---

## Datasets intentionally excluded from the main project

**SECOM:** useful legacy baseline but superseded by the stronger semiconductor dataset.

**Bosch Production Line Performance:** useful scale benchmark, but its severe anonymization adds less incremental value after SoliDAIR + CiP-DMD.

**C-MAPSS / Bosch CNC:** reserve for a separate Equipment Health / PHM project.

---

# 5. Version roadmap

| Release | Purpose | Data |
|---|---|---|
| **v0.1 MVP** | Uncertainty-aware predictive quality | SoliDAIR |
| **v0.2 V1** | Process monitoring + excursion diagnostics | + CiP-DMD |
| **v0.3 V1.5** | Productionization + MLOps | Same |
| **v0.4 V2** | Semiconductor transfer | + Bosch Plasma |
| **v0.5 V3 optional** | Near-real-time OT replay | Existing data |
| **v0.6 V4 optional** | Hybrid physics / advanced process intelligence | SoliDAIR simulation + real |

**Resume-ready threshold: v0.3.**

Applications should not wait for V2–V4.

---

# 6. Technology stack

## Runtime and package management

**Python 3.12**

Use a conservative, widely supported ML runtime rather than chasing the newest Python minor.

**uv**

Responsibilities:

- virtual environments;
- dependency installation;
- lockfile;
- CLI reproducibility.

Files:

```text
pyproject.toml
uv.lock
```

---

# 7. Core data stack

### Primary dataframe engine

**Polars**

Use for:

- CSV ingestion;
- Parquet;
- lazy scans;
- filtering;
- joins;
- aggregation;
- feature generation.

Use Pandas only where a library requires it.

### Storage

**Parquet**

Canonical processed datasets should be stored as Parquet.

Do not repeatedly train directly against giant CSV files.

### Analytical SQL

**DuckDB**

Use for:

- exploratory queries;
- dataset diagnostics;
- cross-table joins;
- validation reports;
- aggregated production reporting.

No PostgreSQL is needed in the MVP.

### Serialization

**PyArrow**

Use underneath Parquet/interoperability.

### Data validation

Use:

**Pandera**

plus explicit application-level checks.

Validate:

- required columns;
- dtypes;
- uniqueness;
- ranges where known;
- target availability;
- missingness constraints;
- split integrity.

---

# 8. Modeling stack

### General

- NumPy
- SciPy
- scikit-learn
- statsmodels

### Primary predictive model

**LightGBM**

Reasons:

- strong tabular performance;
- missing-value handling;
- nonlinear interactions;
- computationally inexpensive;
- widely understood in applied DS.

### Secondary benchmark

**XGBoost**

Do not spend the project proving LightGBM versus XGBoost.

One becomes the production candidate; the other is a robustness comparison.

### Classical manufacturing baselines

Include:

- mean/median predictor;
- Ridge / Elastic Net;
- Partial Least Squares regression;
- logistic regression where classification is valid.

PLS is especially useful for high-dimensional correlated manufacturing measurements.

### Explainability

- permutation importance;
- SHAP;
- ALE/PDP selectively.

### Process monitoring

- scipy/statsmodels;
- custom SPC utilities;
- `ruptures` for change-point experiments.

### Hyperparameter tuning

Use **Optuna only after establishing baselines**.

Keep the search bounded.

Model selection should not become the project.

---

# 9. Uncertainty quantification

Implement simple **split conformal prediction** directly in the project.

Avoid hiding the important logic behind a large library initially.

For regression:

\[
C(x)=
[\hat y(x)-q,\hat y(x)+q]
\]

where \(q\) is calibrated from held-out residuals.

Measure:

\[
\text{coverage}
=
P(Y\in C(X))
\]

and:

\[
\text{mean interval width}
\]

Evaluate coverage across:

- target ranges;
- process regimes;
- batches/days when available;
- high/low predicted values.

A nominal 90% interval whose actual coverage is 74% is not acceptable.

---

# 10. CLI

Use **Typer**.

The entire project should be executable without notebooks.

Example interface:

```text
uv run mqi data pull solidair
uv run mqi data prepare solidair
uv run mqi audit solidair

uv run mqi train quality --dataset solidair
uv run mqi evaluate quality --dataset solidair

uv run mqi train monitoring --dataset cip-dmd

uv run mqi dashboard
uv run mqi api
```

This is substantially more professional than a repository requiring users to execute notebooks manually.

---

# 11. Visualization

Use:

- Plotly;
- Streamlit.

Streamlit is sufficient for this portfolio.

Do not build a React application unless there is a separate frontend objective.

The dashboard is a demonstration surface, not the project itself.

---

# 12. MLOps

Starting V1.5:

**MLflow**

Track:

- parameters;
- split metadata;
- feature-set hash;
- dataset version/hash;
- metrics;
- artifacts;
- models;
- evaluation plots.

Use a local MLflow store for the portfolio.

There is no need to deploy a remote tracking server.

---

# 13. API

Starting V1.5:

**FastAPI + Pydantic**

Expose:

```text
POST /predict/quality
POST /monitor/process
GET  /health
GET  /model/info
```

Responses should include model metadata.

Example:

```json
{
  "prediction": 8.42,
  "prediction_interval": [8.31, 8.55],
  "decision": "inspect",
  "model_version": "quality-solidair-1.2.0"
}
```

---

# 14. Development quality

Use:

- pytest;
- Ruff;
- Pyright;
- pre-commit;
- GitHub Actions;
- Docker.

CI should execute:

```text
dependency install
      ↓
ruff
      ↓
pyright
      ↓
pytest
      ↓
small pipeline smoke test
      ↓
Docker build
```

Never execute full dataset training in CI.

---

# 15. Documentation

Use:

- README.md;
- docs/;
- architecture diagrams;
- dataset cards;
- model cards;
- experiment reports.

MkDocs Material can be added once enough documentation exists to justify it.

Do not create documentation infrastructure before useful documentation exists.

---

# 16. Repository architecture

```text
manufacturing-quality-intelligence/
│
├── pyproject.toml
├── uv.lock
├── README.md
├── LICENSE
├── DATA_LICENSES.md
├── .gitignore
├── .pre-commit-config.yaml
│
├── configs/
│   ├── datasets/
│   │   ├── solidair.yaml
│   │   ├── cip_dmd.yaml
│   │   └── bosch_plasma.yaml
│   ├── models/
│   └── policies/
│
├── data/
│   ├── raw/             # gitignored
│   ├── interim/         # gitignored
│   └── processed/       # gitignored
│
├── src/
│   └── mqi/
│       ├── cli/
│       │
│       ├── core/
│       │   ├── config.py
│       │   ├── types.py
│       │   ├── logging.py
│       │   └── seeds.py
│       │
│       ├── data/
│       │   ├── contracts.py
│       │   ├── manifests.py
│       │   ├── validation.py
│       │   └── splits.py
│       │
│       ├── datasets/
│       │   ├── base.py
│       │   ├── solidair.py
│       │   ├── cip_dmd.py
│       │   └── bosch_plasma.py
│       │
│       ├── features/
│       │   ├── tabular.py
│       │   ├── signals.py
│       │   ├── spectra.py
│       │   └── registry.py
│       │
│       ├── quality/
│       │   ├── baselines.py
│       │   ├── gbdt.py
│       │   ├── conformal.py
│       │   ├── decision_policy.py
│       │   └── evaluation.py
│       │
│       ├── monitoring/
│       │   ├── spc.py
│       │   ├── mspc.py
│       │   ├── anomaly.py
│       │   ├── change_points.py
│       │   └── evaluation.py
│       │
│       ├── diagnostics/
│       │   ├── attribution.py
│       │   ├── grouping.py
│       │   └── event_analysis.py
│       │
│       ├── drift/
│       │
│       ├── tracking/
│       │
│       ├── api/
│       │
│       └── pipelines/
│
├── dashboard/
│
├── notebooks/
│   ├── solidair_eda.ipynb
│   ├── cip_dmd_eda.ipynb
│   └── plasma_eda.ipynb
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contracts/
│   └── fixtures/
│
└── docs/
    ├── architecture.md
    ├── methodology.md
    ├── datasets/
    ├── experiments/
    └── model_cards/
```

Rule:

> **Notebooks explore; production modules implement.**

Nothing required to reproduce the final results should live only inside a notebook.

---

# 17. Canonical data abstraction

Do not force every manufacturing dataset into one giant normalized SQL schema.

Manufacturing datasets have very different shapes.

Instead define a `DatasetBundle`.

Conceptually:

```text
DatasetBundle

units
├── unit_id
├── batch_id?
├── product_type?
└── timestamps?

process_features
├── unit_id
└── static / aggregated process features

quality
├── unit_id
├── characteristic
├── value
├── lower_spec?
└── upper_spec?

operations (optional)
├── unit_id
├── operation_id
├── machine_id?
├── operation_type
├── start_time
└── end_time

signals (optional)
├── unit_id
├── operation_id
├── timestamp
└── sensor channels

metadata
├── feature semantics
├── sampling rates
├── units
└── provenance
```

This accommodates:

**SoliDAIR**

```text
units
process_features
quality
```

**CiP-DMD**

```text
units
operations
signals
quality
```

**Bosch Plasma**

```text
units/wafers
operations
signals
spectra
quality
```

Do not convert thousands of spectral channels into an enormous long table unnecessarily.

---

# 18. Dataset adapter contract

Each dataset adapter should own:

```text
download metadata
      ↓
raw validation
      ↓
dataset-specific parsing
      ↓
canonical DatasetBundle
      ↓
split metadata
```

Core modeling code should not contain statements such as:

```python
if dataset == "solidair":
```

Dataset-specific behavior belongs in the adapter.

That is one of the main architectural tests of V2.

---

# 19. Dataset provenance

Each processed dataset should generate a manifest containing:

```text
dataset_name
dataset_version
source
download_date
raw_file_hash
processed_file_hash
adapter_version
row counts
column counts
split strategy
```

Never commit raw third-party datasets unless their license explicitly permits redistribution.

Commit download instructions and metadata instead.

---

# 20. MVP — v0.1

## Objective

Answer:

> Can upstream manufacturing process parameters predict downstream quality accurately enough to support uncertainty-aware inspection decisions?

Dataset:

**SoliDAIR only.**

The MVP should already be resume-worthy.

---

# 21. MVP Stage A — data audit

Produce a reproducible audit containing:

- dimensions;
- feature types;
- target definitions;
- missingness;
- constant/near-constant features;
- duplicate observations;
- feature distributions;
- target distributions;
- high correlations;
- potential target leakage;
- suspicious identifiers;
- simulation versus production distinction;
- available grouping/time variables.

Generate:

```text
artifacts/audit/solidair_report.html
```

or an equivalent reproducible report.

---

# 22. MVP Stage B — splitting strategy

This is a critical validity issue.

Prefer, in order:

1. chronological split if production time exists;
2. batch/lot/group split if meaningful production grouping exists;
3. grouped split based on correlated process runs;
4. random split only if no stronger dependency information exists.

Default conceptual division:

```text
training
validation/calibration
test
```

The untouched test set is used once for final evaluation.

Conformal calibration must not use test labels.

Add automated assertions:

```text
train ∩ validation = ∅
train ∩ test = ∅
validation ∩ test = ∅
```

for all relevant group identifiers.

---

# 23. MVP Stage C — baseline models

For each EoL output:

### Baseline 0

Mean predictor.

### Baseline 1

Ridge regression.

### Baseline 2

Partial Least Squares.

### Candidate

LightGBM.

Optional robustness comparison:

XGBoost.

Do not tune anything until the baseline table exists.

Example report:

| Model | MAE | RMSE | R² |
|---|---:|---:|---:|
| Mean | | | |
| Ridge | | | |
| PLS | | | |
| LightGBM | | | |
| XGBoost | | | |

---

# 24. MVP Stage D — hyperparameter optimization

Only tune the strongest tree model.

Use validation data / CV within training.

Search a conservative space:

- learning rate;
- number of leaves / tree depth;
- minimum samples per leaf;
- feature subsampling;
- row subsampling;
- regularization.

Primary metric:

appropriate regression error, typically MAE or RMSE based on downstream cost.

Use early stopping.

Do not run hundreds of meaningless optimization trials.

---

# 25. MVP Stage E — uncertainty

Wrap the selected model using split conformal prediction.

For every output:

```text
prediction
lower bound
upper bound
interval width
```

Evaluate:

- nominal coverage;
- observed coverage;
- interval width;
- conditional coverage.

Example:

```text
Target coverage:     90.0%
Observed coverage:   90.7%
Mean interval width: 0.41
```

---

# 26. MVP Stage F — inspection policy

There are two valid modes.

## Mode A — specification limits exist

If legitimate LSL/USL values exist:

### Auto-pass

Prediction interval entirely within specification with required safety margin.

### Inspect

Prediction interval overlaps a specification boundary.

### Hold

Prediction interval is confidently outside specification.

Conceptually:

\[
L < \hat y_{low}
\quad\land\quad
\hat y_{high}<U
\]

may permit automated acceptance.

---

## Mode B — specifications unavailable

Do **not** manufacture arbitrary quality limits.

Use:

```text
AUTO-PREDICT / LOW RISK
```

versus:

```text
INSPECT / UNCERTAIN
```

based on:

- conformal interval width;
- prediction uncertainty;
- optionally distance from training distribution later.

Do not call observations PASS/FAIL without actual engineering limits.

---

# 27. MVP Stage G — operational economics

Create a configurable cost model.

Where applicable:

\[
C =
C_{escape}N_{escape}
+
C_{inspection}N_{inspect}
+
C_{hold}N_{hold}
\]

Plot:

\[
\text{inspection rate}
\]

versus:

\[
\text{quality risk / expected cost}
\]

The central business graphic should resemble:

```text
inspection reduction
        ↑
        │
        │             ● operating point
        │
        │
        └────────────────────────→ quality risk
```

This is more useful than showing ROC-AUC by itself.

---

# 28. MVP Stage H — explainability

Produce:

- global permutation importance;
- global SHAP summary;
- local prediction decomposition;
- important feature interactions where meaningful.

Use language such as:

**quality drivers**

or:

**root-cause candidates**

Never:

**root cause**

unless intervention/experimental evidence exists.

---

# 29. MVP dashboard

Provide four surfaces.

## Overview

Show:

- dataset/model version;
- sample count;
- prediction quality;
- interval coverage;
- inspection policy result.

## Quality model

Show:

- predicted vs actual;
- residuals;
- error distributions;
- feature importance.

## Decision tradeoff

Show:

- inspection rate;
- quality-risk proxy;
- expected cost;
- selected threshold/policy.

## Unit explorer

For an individual observation:

```text
Prediction
Prediction interval
Inspection decision
Top contributing features
Model version
```

---

# 30. MVP acceptance criteria

The MVP is complete only when all are true.

### Data

- reproducible ingestion;
- deterministic preparation;
- documented dataset version;
- no obvious leakage;
- split methodology justified.

### Modeling

- simple statistical baseline exists;
- candidate ML model is benchmarked against it;
- untouched test evaluation exists.

### Uncertainty

- coverage is measured;
- interval width is reported;
- uncertainty is used in the operational decision.

### Decision value

At least one explicit tradeoff between:

\[
\text{inspection burden}
\]

and:

\[
\text{quality risk}
\]

is quantified.

### Engineering

- packaged Python code;
- CLI;
- tests;
- CI;
- Ruff;
- Pyright;
- reproducible environment.

### Presentation

- README;
- architecture diagram;
- methodology;
- results table;
- dashboard;
- limitations section.

This is the first resume-ready release.

Tag:

```text
v0.1.0
```

---

# 31. V1 — v0.2 Process Intelligence

Dataset:

**CiP-DMD**

Objective:

> Detect abnormal process behavior early and trace quality degradation to plausible process stages and signal families.

This version adds manufacturing-engineering depth rather than more predictive models.

---

# 32. V1 Stage A — adapter validation

Implement the CiP-DMD adapter.

It should produce:

```text
units
operations
signals
quality
metadata
```

without changes to the existing quality-model interfaces.

Add contract tests proving both SoliDAIR and CiP-DMD satisfy their declared portions of `DatasetBundle`.

---

# 33. V1 Stage B — process feature extraction

For physical sensor signals, extract interpretable features.

Time domain:

- mean;
- standard deviation;
- RMS;
- peak;
- peak-to-peak;
- skewness;
- kurtosis;
- crest factor.

Frequency domain:

- dominant frequency;
- spectral centroid;
- band energy;
- spectral entropy;
- selected frequency-band RMS.

Features must retain provenance:

```text
machine
operation
sensor
feature
window
```

Example:

```text
milling.face_milling.accel_y.band_600_900hz_energy
```

This makes later diagnostic aggregation possible.

---

# 34. V1 Stage C — classical SPC

Implement:

### Individuals / Moving Range

For process variables without rational subgroups.

### EWMA

\[
z_t = \lambda x_t +(1-\lambda)z_{t-1}
\]

for small persistent shifts.

### CUSUM

for mean-shift detection.

Calculate process capability only where legitimate.

Do **not** report Cp/Cpk unless:

- valid specification limits exist;
- the process is reasonably stable;
- the assumptions are documented.

---

# 35. V1 Stage D — multivariate SPC

Add:

### PCA-based monitoring

Compute:

\[
T^2
\]

and:

\[
Q/SPE
\]

Use training/in-control samples to establish reference distributions.

Evaluate whether induced process deviations appear as:

```text
normal
   ↓
warning
   ↓
excursion
```

---

# 36. V1 Stage E — anomaly detection

Compare:

- robust Mahalanobis distance;
- PCA reconstruction/SPE;
- Isolation Forest.

Do not use autoencoders unless simpler approaches demonstrably fail.

Evaluation should be event-oriented:

- anomaly event recall;
- false alerts/hour or process run;
- detection delay;
- average run length where meaningful.

Generic accuracy should not be the main metric.

---

# 37. V1 Stage F — excursion diagnostics

For an abnormal event:

```text
process excursion
       ↓
affected machine/operation
       ↓
affected sensor family
       ↓
abnormal derived features
       ↓
associated quality measurement
```

Implement hierarchical attribution.

Example:

```text
Event 42

Likely contributors

Milling                 72%
 └─ Face milling        61%
     └─ Accelerometer Y 53%
        └─ 600–900 Hz   31%

Fixture/clamping        19%
Other                    9%
```

This is much more useful than hundreds of individual SHAP values.

---

# 38. V1 validation

CiP-DMD has known induced abnormalities.

Use them as a partial validation mechanism.

Ask:

> Does the diagnostic system recover the subsystem associated with the known injected abnormality?

This is considerably stronger than merely showing attractive anomaly plots.

---

# 39. V1 dashboard extension

Add a Process Monitoring page:

```text
Process state        NORMAL / WARNING / EXCURSION

Recent alerts
SPC chart
EWMA/CUSUM
Multivariate score
Affected operation
Likely contributing signals
Associated QC outcomes
```

---

# 40. V1 acceptance criteria

V1 is complete when:

- both dataset adapters work;
- signal feature extraction is reproducible;
- SPC implementations have unit tests;
- known process anomalies can be evaluated;
- false-alert metrics exist;
- event diagnostics produce hierarchical candidate causes;
- quality associations can be traced back to an operation/signal;
- the dashboard exposes process state and diagnostics.

Tag:

```text
v0.2.0
```

---

# 41. V1.5 — v0.3 Productionization

This is the strongest stopping point for active job applications.

The analytics already work.

Now make the project look deployable.

---

# 42. MLflow integration

Every training run logs:

```text
dataset hash
split hash
feature-set hash
git commit
random seed
model configuration
validation metrics
test metrics
plots
model artifact
```

Model naming:

```text
solidair-quality-output1
cipdmd-process-monitor
```

No manual model-file copying.

---

# 43. FastAPI inference

Implement:

```text
POST /v1/quality/predict
POST /v1/process/score
GET /v1/models
GET /health
```

Pydantic validates payloads.

Return explicit errors for:

- missing fields;
- wrong feature version;
- incompatible schema.

---

# 44. Batch inference

Manufacturing analytics is frequently batch-oriented.

Support:

```text
uv run mqi predict batch \
  --dataset solidair \
  --input incoming.parquet \
  --output predictions.parquet
```

Batch inference matters at least as much as REST inference.

---

# 45. Model/data drift

## Data drift

Track:

- missingness;
- distribution shift;
- categorical frequency shift;
- KS statistics;
- Wasserstein distance;
- PSI where appropriate.

## Performance drift

When labels arrive:

- MAE/RMSE;
- conformal coverage;
- interval width;
- escape rate where applicable;
- inspection rate;
- cost.

Distinguish:

\[
P(X)\text{ drift}
\]

from:

\[
P(Y|X)\text{ degradation}
\]

in the documentation.

---

# 46. Docker

Create one application container.

Potential optional Docker Compose later:

```text
application
mlflow
```

Do not add Kubernetes.

---

# 47. CI/CD

GitHub Actions should enforce:

### Pull request

```text
lint
types
unit tests
contract tests
small integration test
```

### Main branch

Additionally:

```text
Docker build
```

A release can publish container artifacts if desired, but this is optional.

---

# 48. Testing strategy

## Unit

Test:

- SPC calculations;
- conformal quantile calculation;
- decision rules;
- feature transformations;
- metric functions.

## Data-contract

Verify:

- expected columns;
- types;
- uniqueness;
- legal missingness;
- target availability.

## Leakage

Explicit tests for:

- target column in feature matrices;
- group overlap;
- future data in training windows.

## Integration

Tiny fixture:

```text
raw data
   ↓
adapter
   ↓
features
   ↓
train
   ↓
predict
   ↓
evaluate
```

## API

Test:

- valid request;
- missing field;
- unknown model;
- incompatible schema.

---

# 49. V1.5 documentation

README structure:

```text
Problem
Business decision
Architecture
Datasets
Methodology
Validation
Results
Manufacturing interpretation
Demo
Reproduce locally
Limitations
Future work
```

Create explicit:

```text
MODEL_CARD.md
DATA_CARD_SOLIDAIR.md
DATA_CARD_CIP_DMD.md
```

Tag:

```text
v0.3.0
```

At this stage, stop and apply for jobs.

---

# 50. V2 — v0.4 Semiconductor Transfer

Dataset:

**Bosch Plasma Etching**

Objective:

> Demonstrate that the architecture generalizes from automotive/discrete manufacturing to a high-dimensional semiconductor process.

This version should be framed as a **transfer study**, not another platform rewrite.

---

# 51. V2 Stage A — data engineering

Support:

- high-dimensional spectra;
- process parameter streams;
- different sampling frequencies;
- wafer/run identifiers;
- pre/post metrology.

Raw data should be converted to an efficient processed representation.

Use:

- Parquet;
- lazy Polars scans;
- chunked processing.

Never load the complete 7+ GB dataset into memory unless necessary.

---

# 52. V2 Stage B — synchronization

Create a processing pipeline for:

```text
optical spectrum @ high rate
            +
equipment/process telemetry @ lower rate
            ↓
aligned wafer/process-run representation
```

Document:

- timestamp alignment;
- interpolation policy;
- missing intervals;
- aggregation windows.

This is an important applied data-engineering task.

---

# 53. V2 Stage C — spectral dimensionality reduction

Start with interpretable/simple methods:

### PCA

\[
X_{3648} \rightarrow Z_k
\]

### PLS

Especially useful because it is supervised toward quality/metrology.

### Spectral aggregation

Energy/bands where meaningful.

Compare:

```text
raw/selected spectrum
PCA representation
PLS representation
engineered spectral features
```

---

# 54. V2 Stage D — virtual metrology

Predict relevant wafer outcomes such as:

- etch depth;
- uniformity;
- selectivity;
- other provided metrology targets.

Benchmark:

- PLS;
- Ridge;
- LightGBM on compressed features.

Only consider a neural model after these baselines.

A 1-D CNN may be an optional experiment if the data volume genuinely supports it.

It is not a requirement.

---

# 55. V2 Stage E — drift/generalization

If data spans multiple production days or process campaigns:

Train on earlier groups.

Test on held-out day/group.

Measure:

\[
\text{within-domain performance}
\]

versus:

\[
\text{cross-day/process performance}
\]

This is much closer to a real semiconductor deployment problem than random cross-validation.

---

# 56. V2 architecture test

The most important software question is:

> Did adding semiconductor data require rewriting the core?

The desired answer:

**No.**

Only these should materially change:

```text
dataset adapter
signal/spectral feature extraction
dataset-specific configuration
```

These should remain reusable:

```text
evaluation
uncertainty
model interfaces
tracking
API
drift framework
reporting
```

That proves the architecture is useful rather than theoretical.

---

# 57. V2 project story

The final repository now demonstrates:

```text
AUTOMOTIVE / HIGH-VOLUME
SoliDAIR
process parameters
      ↓
EOL quality


DISCRETE MANUFACTURING
CiP-DMD
machine/process signals
      ↓
dimensional quality + anomalies


SEMICONDUCTOR
Bosch Plasma
plasma spectra + machine state
      ↓
wafer metrology
```

Same fundamental problem:

\[
\boxed{\text{process state} \rightarrow \text{quality}}
\]

Tag:

```text
v0.4.0
```

This is the strongest logical final version of the main project.

---

# 58. V3 — optional near-real-time OT replay

Only build this if industrial-AI/MLE roles justify it.

The purpose is **not** to pretend historical datasets are live factories.

Clearly label it:

> historical OT replay simulator.

Architecture:

```text
historical event stream
         ↓
replay service
         ↓
MQTT broker
         ↓
consumer
         ↓
online feature state
         ↓
process/quality model
         ↓
alert/API/dashboard
```

Stack:

- Eclipse Mosquitto;
- MQTT Python client;
- optional `asyncua` OPC UA simulation;
- Docker Compose.

---

# 59. V3 event model

Emit events such as:

```json
{
  "machine_id": "M14",
  "operation": "face_milling",
  "timestamp": "...",
  "signals": {
    "accel_y": 0.41,
    "current": 7.2
  }
}
```

Consumer computes:

```text
rolling statistics
SPC state
anomaly score
quality-risk updates
```

---

# 60. V3 operational dashboard

Example:

```text
LINE STATUS

M12    NORMAL
M13    NORMAL
M14    WARNING
M15    NORMAL


M14 — WARNING

EWMA shift detected
Operation: Face milling
Started: 14:32

Primary signals:
Accel Y
Spindle current

Units since warning: 17

Predicted quality risk:
baseline 2.3%
current 11.9%
```

Measure:

- processing latency;
- alert latency;
- event throughput;
- duplicates/idempotency;
- dropped events.

Do not add Kafka unless MQTT becomes an actual technical limitation.

---

# 61. V4 — optional advanced manufacturing research

Choose **one** advanced direction.

Do not build all of them.

The strongest option is likely hybrid physics + ML.

---

# 62. V4A — hybrid physics/data-driven model

Use SoliDAIR's simulation dataset.

Compare:

### Pure data model

\[
\hat y_{ML}=f(X)
\]

### Simulation model

\[
\hat y_{sim}=g(X)
\]

### Residual model

\[
r=y-\hat y_{sim}
\]

Train:

\[
\hat r=f_{ML}(X)
\]

Final prediction:

\[
\hat y=
\hat y_{sim}+\hat r
\]

Evaluate whether the hybrid:

- improves accuracy;
- improves extrapolation;
- reduces required training data;
- behaves more robustly under distribution shift.

Do not call this a digital twin unless it actually satisfies digital-twin requirements.

Call it:

**hybrid physics-informed quality model**

or:

**simulation-assisted surrogate model**.

---

# 63. V4B — DOE/process optimization alternative

If targeting process-engineering roles, this may be even stronger.

Implement:

- factorial DOE;
- interactions;
- ANOVA;
- response-surface methodology;
- constrained optimization.

Move from:

> Which variables predict quality?

toward:

> Which controllable settings improve expected quality?

This is where causal language can become more defensible if the data-generating experiment supports it.

---

# 64. V4C — industrial copilot alternative

Only after trusted analytics exist.

The LLM should query validated system outputs:

```text
user question
     ↓
structured tool calls
     ↓
SPC events
quality predictions
model explanations
maintenance/process metadata
     ↓
LLM synthesis
```

The LLM must not invent manufacturing diagnoses directly from raw data.

Example:

> Why did quality deteriorate yesterday?

The system answers from existing deterministic analyses.

This should be a thin interface, not a second project.

---

# 65. Experiment discipline

Every experiment answers a predefined question.

Example:

**Question**

Does PLS retain enough information to outperform Ridge while reducing dimensionality?

**Baseline**

Ridge on standardized variables.

**Change**

PLS components selected on validation.

**Metrics**

RMSE, MAE, stability across splits.

**Decision**

Keep or discard.

Avoid experiment sprawl.

---

# 66. Evaluation philosophy

## Predictive quality

Primary:

- MAE;
- RMSE;
- \(R^2\) as descriptive context.

If binary QC labels legitimately exist:

- PR-AUC;
- Brier score;
- log loss;
- recall at operational precision/FPR;
- escape rate.

---

## Uncertainty

- empirical coverage;
- mean/median interval width;
- coverage by operating regime.

---

## Inspection policy

- inspection rate;
- escapes;
- false holds/rejects;
- expected cost.

---

## Process monitoring

- event recall;
- detection delay;
- false alerts per unit/hour/run;
- ARL where appropriate.

---

## Diagnostics

For known anomalies:

- subsystem identification;
- operation identification;
- signal-family ranking.

Do not invent a numerical root-cause metric where no ground truth exists.

---

# 67. Statistical validity requirements

The project should explicitly defend against:

### Leakage

Particularly:

- downstream inspection variables used to predict upstream quality;
- timestamps leaking future states;
- duplicate process runs crossing splits.

### Random split optimism

Use temporal/group splitting whenever possible.

### Multiple comparisons

Avoid treating every sensor correlation as meaningful.

### Unstable processes

Do not interpret Cpk as meaningful before assessing process stability.

### Explainability overclaiming

SHAP explains model behavior, not causality.

### Synthetic/experimental generalization

Document exactly which data is:

- production;
- experimental;
- simulated.

---

# 68. Reproducibility

A new machine should require approximately:

```text
git clone
uv sync
dataset download command/instructions
uv run mqi data prepare ...
uv run mqi train ...
uv run mqi evaluate ...
```

No:

```text
"open notebook 7 and manually change cell 38"
```

---

# 69. Data directory policy

```text
data/raw/
data/interim/
data/processed/
```

all gitignored.

Maintain:

```text
data/manifests/
```

in version control.

A manifest should be enough to determine exactly which data produced a model.

---

# 70. Configuration policy

Configuration belongs in YAML/TOML rather than scattered constants.

Example:

```yaml
dataset: solidair

target:
  name: Output_1

split:
  strategy: group
  test_fraction: 0.20

model:
  type: lightgbm
  objective: regression

uncertainty:
  method: split_conformal
  alpha: 0.10
```

Validate configuration with Pydantic.

---

# 71. Logging

Use Python structured logging.

Every training run records:

```text
run_id
dataset
dataset_hash
split
feature_set
model
seed
duration
result path
```

Do not scatter `print()` throughout production modules.

---

# 72. Feature lineage

Maintain metadata such as:

```text
feature_name
source_signal
operation
transformation
window
unit
```

This becomes especially important for CiP-DMD and semiconductor data.

It enables:

```text
individual feature
       ↓
sensor
       ↓
operation
       ↓
process stage
```

for diagnostics.

---

# 73. Model interfaces

Avoid model-specific code throughout the system.

Conceptual interface:

```python
fit(X, y)
predict(X)
save(...)
load(...)
metadata()
```

Uncertainty should wrap the predictor instead of being embedded in every model implementation.

---

# 74. Do not build a generic ML framework

This is important.

The repository should support:

**these manufacturing tasks well**

rather than attempting to become:

> a universal ML platform.

Abstractions should emerge from the three datasets.

Do not create plugin systems or elaborate dependency injection unless actual duplication proves they are needed.

---

# 75. Greenfield implementation order

## Milestone 0 — repository foundation

Deliver:

```text
pyproject
uv
src package
pytest
ruff
pyright
CI
CLI shell
logging
configs
```

No modeling.

Gate:

```text
uv run pytest
uv run ruff check .
uv run pyright
```

all pass.

---

## Milestone 1 — SoliDAIR ingestion

Deliver:

- source/download documentation;
- raw manifest;
- adapter;
- validation;
- processed Parquet;
- data audit.

Gate:

one command reproduces processed data.

---

## Milestone 2 — split + baselines

Deliver:

- split implementation;
- leakage assertions;
- mean;
- Ridge;
- PLS;
- benchmark report.

Gate:

baseline benchmark is reproducible.

---

## Milestone 3 — quality model

Deliver:

- LightGBM;
- bounded tuning;
- holdout evaluation;
- SHAP/permutation diagnostics.

Gate:

candidate is objectively compared with baselines.

---

## Milestone 4 — uncertainty

Deliver:

- conformal prediction;
- coverage testing;
- interval-width analysis.

Gate:

nominal versus actual coverage is documented.

---

## Milestone 5 — decision policy

Deliver:

- inspection policy;
- configurable costs;
- tradeoff curve.

Gate:

system produces an operational decision supported by measured tradeoffs.

---

## Milestone 6 — MVP presentation

Deliver:

- dashboard;
- README;
- architecture;
- model card;
- demo screenshots;
- release tag.

**MVP complete.**

---

## Milestone 7 — CiP-DMD adapter

Deliver:

- operations;
- signals;
- quality;
- traceability.

Gate:

canonical contracts pass.

---

## Milestone 8 — process statistics

Deliver:

- I/MR;
- EWMA;
- CUSUM;
- PCA \(T^2\);
- SPE.

Gate:

functions validated on synthetic test signals with known shifts.

---

## Milestone 9 — physical anomaly analysis

Deliver:

- time/frequency features;
- anomaly baselines;
- event metrics.

Gate:

known CiP-DMD anomalies can be evaluated.

---

## Milestone 10 — diagnostics

Deliver:

- hierarchical feature grouping;
- event attribution;
- QC linkage.

Gate:

known anomalies produce sensible subsystem/process rankings.

**V1 complete.**

---

## Milestone 11 — productionization

Deliver:

- MLflow;
- API;
- batch inference;
- Docker;
- drift reports;
- extended CI.

**V1.5 complete.**

This is the recommended resume/application checkpoint.

---

## Milestone 12 — Bosch Plasma ingestion

Deliver:

- efficient data adapter;
- synchronization;
- processed representation.

---

## Milestone 13 — semiconductor baseline

Deliver:

- PLS;
- PCA + Ridge/GBDT;
- virtual-metrology benchmark.

---

## Milestone 14 — transfer/generalization

Deliver:

- group/day holdout;
- drift analysis;
- architecture reuse report.

**V2 complete.**

---

# 76. Architecture decision records

Keep a short:

```text
docs/adr/
```

Examples:

```text
ADR-001 Why Polars + DuckDB
ADR-002 Why no feature store
ADR-003 Why conformal prediction
ADR-004 Why MQTT instead of Kafka
ADR-005 Why predictive maintenance is separate
```

These demonstrate engineering judgment.

Keep each ADR short.

---

# 77. Git workflow

`main` should always be usable.

Use feature branches and pull requests, even if working alone.

Tag major portfolio states:

```text
v0.1.0  predictive quality MVP
v0.2.0  process intelligence
v0.3.0  productionized
v0.4.0  semiconductor transfer
```

GitHub Issues/Milestones can mirror the implementation milestones.

This makes repository history itself evidence of engineering process.

---

# 78. README results section

Do not lead with architecture.

Lead with the manufacturing problem and evidence.

Example layout:

```text
Problem
↓

Key result
"Reduced simulated inspection load by X%
while maintaining Y% empirical quality-risk bound"

↓

Dashboard screenshot

↓

How it works

↓

Validation

↓

Architecture
```

Recruiters should understand the point before reading implementation details.

---

# 79. Demonstration artifacts

The repository should eventually contain:

### One architecture diagram

Process/data/model flow.

### One predictive-quality figure

Actual versus predicted.

### One uncertainty figure

Prediction interval coverage.

### One decision curve

Inspection rate versus risk/cost.

### One SPC/excursion figure

Normal → developing drift → detected excursion.

### One root-cause candidate figure

Process-stage/signal attribution.

### One semiconductor transfer figure

Plasma/spectrum → wafer metrology.

Six good figures are worth more than 50 generic charts.

---

# 80. Resume bullets after V1.5

Use actual measured values once available.

A final version could resemble:

> Built an end-to-end manufacturing quality intelligence system using Python, LightGBM, statistical process control, and conformal prediction to forecast downstream quality and optimize uncertainty-aware inspection decisions across industrial process data.

> Developed reusable data contracts and manufacturing-process adapters supporting predictive quality, SPC, multivariate anomaly detection, and hierarchical excursion diagnostics; validated against physically induced process anomalies.

> Productionized training and inference with MLflow, FastAPI, Docker, automated data/model validation, and CI testing, including drift monitoring and reproducible dataset/model lineage.

Do not insert fake performance numbers.

---

# 81. Resume bullets after V2

Potential additional bullet:

> Extended the platform to semiconductor plasma-etch data, engineering multirate spectral/process pipelines and virtual-metrology models while preserving the common quality-prediction and monitoring architecture.

Again, use actual results when available.

---

# 82. What makes this project professional

The strongest signals are not the number of models.

They are:

### Correct problem framing

Quality and manufacturing decisions rather than Kaggle metrics.

### Statistical grounding

SPC, PLS, uncertainty and controlled validation.

### Operational evaluation

Inspection burden, escapes, cost, alert frequency and detection delay.

### Software discipline

Package structure, tests, CLI, CI and containers.

### Honest uncertainty

No fabricated quality limits or causal claims.

### Transferability

Automotive/discrete manufacturing → semiconductor.

### Scope discipline

No unnecessary distributed systems or AI-agent layer.

---

# 83. What should trigger deletion rather than expansion

Remove or avoid a component if:

- it does not improve an operational metric;
- it exists only to add a fashionable technology;
- a simpler method performs equivalently;
- it duplicates functionality;
- its result cannot be validated;
- it cannot be clearly explained during an interview.

Examples:

If Isolation Forest performs no better than PCA SPE:

**keep PCA SPE.**

If XGBoost and LightGBM are equivalent:

**keep one production model.**

If a neural model adds complexity without material improvement:

**remove it.**

If Kafka solves no observed throughput problem:

**do not add Kafka.**

---

# 84. Recommended stopping point

For job-search ROI, the optimal sequence is:

\[
\boxed{
MVP
\rightarrow
V1
\rightarrow
V1.5
}
\]

then begin aggressive job applications.

Continue to V2 in parallel as the major enhancement.

V3 and V4 should only be built when they align with target postings.

The project does **not** need to become a complete smart-factory platform to demonstrate mid-level DS/MLE capability.

---

# 85. Final product architecture

The mature but still reasonable system is:

```text
                  DATASETS

       SoliDAIR      CiP-DMD      Plasma
           │             │            │
           └─────── adapters ─────────┘
                         │
                         ▼
                CANONICAL CONTRACTS
                         │
              ┌──────────┼──────────┐
              │          │          │
              ▼          ▼          ▼
           Quality    Process     Signal/
           models    monitoring   spectral
              │          │          │
              └──────────┼──────────┘
                         │
                         ▼
                  DIAGNOSTICS
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
         uncertainty    drift     attribution
              │          │          │
              └──────────┼──────────┘
                         │
                         ▼
                DECISION POLICY
                         │
             ┌───────────┴───────────┐
             ▼                       ▼
         Dashboard                  API
```

This is enough architecture to show serious engineering without turning the repository into an infrastructure project.

---

# 86. Final project principle

Every added capability should move the project through this progression:

\[
\boxed{
\text{measure}
\rightarrow
\text{predict}
\rightarrow
\text{quantify uncertainty}
\rightarrow
\text{decide}
\rightarrow
\text{detect change}
\rightarrow
\text{diagnose}
\rightarrow
\text{deploy}
\rightarrow
\text{prove transfer}
}
\]

That is the project.

Not:

\[
\text{collect as many ML technologies as possible}.
\]