# Manufacturing Process & Quality Intelligence

**Status:** Canonical project specification and implementation plan.

Repository progress is tracked separately in `docs/implementation-roadmap.md`.
Historical plans and investigations under `.archive/` are non-authoritative.

## 1. Project charter

### Project objective

Build a reusable industrial data-science system that uses manufacturing process data to:

1. characterize normal process behavior;
2. predict downstream product quality;
3. quantify prediction uncertainty;
4. detect process drift and abnormal excursions;
5. localize likely process contributors;
6. support inspection or investigation decisions;
7. demonstrate transfer across multiple manufacturing domains.

The core problem is:

\[
\boxed{
\text{materials + equipment + process state}
\rightarrow
\text{product quality}
}
\]

with a second operational loop:

\[
\boxed{
\text{process excursion}
\rightarrow
\text{detection}
\rightarrow
\text{diagnosis}
\rightarrow
\text{action}
}
\]

The project is specifically designed to demonstrate skills transferable to:

- semiconductor manufacturing;
- aerospace and defense manufacturing;
- pharmaceutical and medical-device manufacturing;
- automotive;
- electronics;
- advanced manufacturing;
- industrial equipment;
- other high-value production environments.

---

# 2. Career positioning

The project should position the candidate as:

> **An engineer/data scientist capable of applying modern statistics, ML and production analytics to physical manufacturing systems.**

The target role families are:

- Manufacturing Data Scientist
- Semiconductor Yield / Process Analytics Engineer
- Industrial Data Scientist
- Manufacturing ML Engineer
- Smart Manufacturing Engineer
- Process Analytics Engineer
- Yield Enhancement Engineer
- Quality Data Scientist
- Equipment / Process Analytics Engineer
- Virtual Metrology Engineer
- Process Control / Fault Detection Engineer
- Defense Production Data Scientist
- Manufacturing Intelligence Engineer

The project should emphasize the intersection:

\[
\boxed{
\text{engineering}
+
\text{statistics}
+
\text{machine learning}
+
\text{manufacturing}
}
\]

rather than generic software development.

---

# 3. Project name

Repository name:

```text
manufacturing-process-intelligence
```

Display name:

# Manufacturing Process & Quality Intelligence

Avoid names such as:

- Smart Factory AI
- Industry 4.0 AI Platform
- Autonomous Factory Agent
- Manufacturing Digital Twin

unless the implementation genuinely supports those claims.

---

# 4. Core design principle

Do not make the repository specific to injection molding, machining, semiconductor etching or pharmaceuticals.

Instead define reusable manufacturing abstractions and implement dataset-specific adapters.

Conceptually:

```text
                    Manufacturing Unit
                           │
               ┌───────────┴───────────┐
               │                       │
            Materials               Process
                                       │
                              ┌────────┴────────┐
                              │                 │
                          Equipment         Operations
                              │                 │
                              └────────┬────────┘
                                       │
                                  Measurements
                                       │
                       ┌───────────────┼───────────────┐
                       │               │               │
                    Monitor         Predict         Diagnose
                       │               │               │
                       └───────────────┼───────────────┘
                                       │
                                     Quality
                                       │
                                  Decision
```

This architecture should survive the addition of new manufacturing domains without rewriting the analytical core.

---

# 5. Dataset strategy

## Dataset A — High-resolution injection molding

### Role

**MVP predictive-quality dataset**

This should be the first implementation.

The dataset provides physical process measurements linked directly to manufactured parts, including scalar machine parameters and high-resolution injection-pressure and flow trajectories. The paper describes 2,049 samples at 6 ms resolution; inspection of the pinned release found 2,048 elapsed-time rows with a predominantly 6 ms grid and three 4 ms transitions. The released structure and its validation boundary are recorded in the [source contract](../datasets/injection-molding-source-contract.md). Manufactured parts have physical quality measurements such as weight and dimensions. The experiments include deliberate changes in process settings, startup states, pauses and multiple production days. See the [peer-reviewed data description](https://doi.org/10.3390/polym15040978) and [publisher dataset repository](https://github.com/sc4t1m/scatimdata).

The publisher dataset repository states a [CC BY 4.0 license](https://github.com/sc4t1m/scatimdata#license). M1 must verify the exact admitted files and terms before acquisition.

### Why it is first

It cleanly supports:

\[
\text{process telemetry}
\rightarrow
\text{physical product quality}
\]

without the provenance problems encountered with SoliDAIR.

### Primary tasks

- predictive quality;
- virtual metrology;
- time-series feature extraction;
- process-state characterization;
- uncertainty quantification;
- selective measurement/inspection;
- process drift;
- cross-day generalization.

---

# 6. Dataset B — CiP-DMD

### Role

**Process-monitoring and diagnosis dataset**

CiP-DMD contains 847 pneumatic cylinders across a multi-stage manufacturing chain, with 697 normal and 150 anomalous units. It preserves part identifiers, manufacturing timestamps, machine/process data and QC results through a traceability scheme. See the [dataset paper and release record](https://zenodo.org/records/8420132).

### Why it complements injection molding

Injection molding answers:

> Can process telemetry predict product quality?

CiP-DMD answers:

> Can abnormal manufacturing behavior be detected and localized to a process stage?

### Primary tasks

- SPC;
- EWMA;
- CUSUM;
- multivariate SPC;
- signal processing;
- vibration analysis;
- anomaly detection;
- process-stage localization;
- known-anomaly validation;
- quality-traceability analysis.

---

# 7. Dataset C — Bosch Plasma Etching

### Role

**Semiconductor domain-transfer dataset**

The dataset includes:

- 3,648-channel OES spectra at 25 Hz;
- 31 process parameters at 5 Hz;
- pre/post wafer measurements;
- wafer measurements at 9 and 89 spatial positions;
- etch-depth, selectivity and uniformity information.


The experiment also includes systematic chamber-conditioning variation intended to study process state and drift. See the [versioned Zenodo dataset](https://doi.org/10.5281/zenodo.17122442).

### Primary tasks

- virtual metrology;
- semiconductor process prediction;
- spectral dimensionality reduction;
- process drift;
- multirate sensor synchronization;
- day/condition holdouts;
- PLS/PCA;
- domain transfer.

This dataset should be prominent when presenting the project to semiconductor employers.

---

# 8. Dataset D — Pharmaceutical manufacturing

### Role

**Regulated-manufacturing transfer dataset**

The pharmaceutical dataset contains 1,005 actual manufacturing batches collected from 2018–2021. It links raw-material laboratory data, intermediate measurements, tablet-compression process time series and final-product quality. Process trajectories were collected every 10 seconds. See the [Scientific Data descriptor](https://doi.org/10.1038/s41597-022-01203-x).

The laboratory data includes critical quality attributes and product genealogy and is distributed under CC BY 4.0 through the [versioned Figshare collection](https://doi.org/10.6084/m9.figshare.c.5645578.v3).

### Primary tasks

- batch genealogy;
- raw-material effects;
- process-to-quality modeling;
- batch-level prediction;
- multivariate process monitoring;
- product-family effects;
- PLS;
- regulated-quality concepts.

This proves that the architecture transfers from discrete engineering manufacturing to regulated health manufacturing.

---

# 9. Optional Dataset E — NIST additive manufacturing

### Role

**Defense/aerospace advanced-manufacturing extension**

Use only after the core project is complete.

Potential tasks:

- in-situ additive monitoring;
- melt-pool/process analysis;
- layer monitoring;
- process-to-defect relationships;
- post-build inspection.

Do not make this required for the first job-search release.

---

# 10. Dataset admission gate

No dataset enters the core project merely because it looks interesting.

Before implementation, create a source contract answering:

```text
source
version
publisher
license
physical entity represented by a row/sample
process chronology
identifiers
targets
known leakage paths
quality limits
sampling frequency
known anomalies/interventions
redistribution constraints
```

A dataset must pass three gates:

### Scientific suitability

Can the desired claim actually be supported?

### Validation suitability

Can the data be split without obvious leakage?

### Portfolio suitability

Can derived artifacts safely be shown publicly?

This source-contract stage should remain a permanent project feature.

---

# 11. Version roadmap

| Version | Purpose | Dataset |
|---|---|---|
| **v0.1 MVP** | Predictive quality + uncertainty | Injection molding |
| **v0.2** | Process monitoring + diagnostics | + CiP-DMD |
| **v0.3** | Productionization / MLOps | Same |
| **v0.4** | Semiconductor transfer | + Bosch Plasma |
| **v0.5** | Regulated manufacturing transfer | + Pharma |
| **v0.6 optional** | Advanced manufacturing transfer | + NIST AMMT |

The recommended application checkpoint is:

\[
\boxed{\text{v0.2 to v0.3}}
\]

Do not wait for all datasets before applying.

---

# 12. Technology stack

## Language

**Python 3.12**

Conservative enough for broad scientific/ML compatibility.

---

## Package/environment management

**uv**

Use:

```text
pyproject.toml
uv.lock
```

Goals:

- deterministic dependencies;
- simple local setup;
- reproducible CI.

---

# 13. Data stack

### Polars

Primary dataframe engine.

Use for:

- CSV parsing;
- Parquet processing;
- joins;
- aggregations;
- lazy pipelines.

### PyArrow / Parquet

Canonical processed-data format.

### DuckDB

Use for:

- analytical queries;
- batch diagnostics;
- QA reports;
- cross-table analysis.

Do not deploy PostgreSQL in the MVP.

### Pandas

Allowed only where library compatibility makes it useful.

---

# 14. Data validation

Use:

- Pandera or equivalent dataframe contracts;
- explicit application assertions.

Check:

- expected columns;
- dtypes;
- non-null constraints;
- uniqueness;
- valid identifiers;
- legal ranges;
- timestamp consistency;
- process-order consistency;
- target separation.

Dataset contracts should fail loudly.

---

# 15. Statistical stack

Use:

- NumPy
- SciPy
- statsmodels
- scikit-learn

Implement manufacturing statistics explicitly where reasonable.

Core techniques:

- I/MR control charts;
- EWMA;
- CUSUM;
- PCA;
- Hotelling \(T^2\);
- SPE/Q;
- PLS;
- process capability where valid;
- statistical hypothesis tests where justified.

Do not calculate Cp/Cpk merely because the formula is available.

Capability metrics require:

- meaningful specification limits;
- reasonably stable process;
- documented assumptions.

---

# 16. ML stack

Primary:

**LightGBM**

Secondary robustness benchmark:

**XGBoost**

Baselines:

- mean/median;
- linear regression;
- Ridge;
- Elastic Net where useful;
- PLS.

Do not make model comparison the primary purpose.

The important comparison is:

\[
\text{simple statistical model}
\rightarrow
\text{modern tabular model}
\]

and whether additional complexity materially improves the manufacturing decision.

---

# 17. Time-series feature stack

Implement manufacturing-relevant features directly.

### Time domain

- mean;
- standard deviation;
- minimum/maximum;
- RMS;
- peak-to-peak;
- skewness;
- kurtosis;
- crest factor;
- area under curve;
- slope;
- rise/fall characteristics.

### Frequency domain where physically appropriate

- dominant frequency;
- spectral centroid;
- band energy;
- spectral entropy;
- frequency-band RMS.

Do not generate hundreds of generic TSFresh-style features unless justified.

Feature lineage must be preserved.

---

# 18. Feature lineage

Every derived feature should retain:

```text
dataset
source_signal
machine
operation
transformation
window
physical_unit
```

Example:

```text
cip_dmd.milling.face_milling.accel_y.band_600_900hz_energy
```

This enables engineering-level diagnostics instead of anonymous feature rankings.

---

# 19. Uncertainty quantification

Include uncertainty in the MVP.

Implement **split conformal regression**.

For predictor:

\[
\hat y = f(x)
\]

return:

\[
C(x)=
[\hat y-q,\hat y+q]
\]

for calibrated residual quantile \(q\).

Evaluate:

- empirical coverage;
- interval width;
- coverage by process state;
- coverage by day;
- coverage by target range.

Example report:

```text
Nominal coverage:       90.0%
Observed coverage:      90.6%
Median interval width:  ...
```

Do not call this a production guarantee.

---

# 20. Selective prediction

When specifications are unavailable, do not invent PASS/FAIL thresholds.

Instead implement:

```text
                Prediction
                    │
             uncertainty
                    │
            ┌───────┴────────┐
            │                │
        confident        uncertain
            │                │
      AUTO-PREDICT         MEASURE
```

Evaluate:

\[
\text{coverage}
=
\frac{\text{automatically predicted units}}
{\text{total units}}
\]

against selective risk:

\[
R=
E[L(y,\hat y)\mid\text{accepted}]
\]

This produces a risk-coverage curve.

---

# 21. Quality-decision policy

If a later dataset provides defensible specification limits:

```text
prediction interval entirely within tolerance
               ↓
           low risk

prediction interval intersects tolerance limit
               ↓
            inspect

prediction confidently outside tolerance
               ↓
          hold/investigate
```

Only use PASS/HOLD language when supported by actual specification semantics.

---

# 22. Explainability and diagnostics

Use:

- grouped permutation importance;
- SHAP;
- SHAP interaction values selectively;
- ALE/PDP selectively;
- process-state comparison;
- event attribution.

Terminology:

**Allowed**

- predictive driver
- contributing feature
- root-cause candidate
- associated process stage

**Avoid without causal evidence**

- root cause
- feature X caused failure

---

# 23. Process monitoring

Starting in v0.2:

## Univariate SPC

Implement:

- I/MR;
- EWMA;
- CUSUM.

## Multivariate monitoring

Implement:

- PCA;
- Hotelling \(T^2\);
- SPE/Q.

## Change-point detection

Use:

- `ruptures` for offline experiments;
- manufacturing SPC methods for operational monitoring.

Compare anomaly techniques against simpler SPC baselines.

---

# 24. Anomaly detection

Baseline methods:

1. Mahalanobis distance;
2. PCA reconstruction error;
3. Isolation Forest.

Neural autoencoders are not required.

Only add them if:

\[
\text{measured improvement}
>
\text{complexity cost}
\]

Evaluation:

- event recall;
- false alerts per run/hour;
- detection delay;
- subsystem localization.

Do not lead with ROC-AUC alone.

---

# 25. Root-cause candidate hierarchy

For CiP-DMD and similar datasets, aggregate attribution:

```text
Factory
  ↓
Process stage
  ↓
Machine
  ↓
Operation
  ↓
Sensor family
  ↓
Derived feature
```

Example:

```text
Detected excursion

CNC milling                     72%
 └─ Face milling               61%
     └─ Accelerometer Y        48%
         └─ High-band energy   27%
```

This is substantially more useful than presenting 200 SHAP bars.

---

# 26. Project software architecture

```text
manufacturing-process-intelligence/
│
├── pyproject.toml
├── uv.lock
├── README.md
├── LICENSE
├── DATA_LICENSES.md
│
├── configs/
│   ├── datasets/
│   ├── models/
│   └── policies/
│
├── data/
│   ├── raw/                 # gitignored
│   ├── interim/             # gitignored
│   ├── processed/           # gitignored
│   └── manifests/
│
├── src/
│   └── mpi/
│       ├── cli/
│       │
│       ├── core/
│       │   ├── config.py
│       │   ├── types.py
│       │   ├── logging.py
│       │   └── provenance.py
│       │
│       ├── data/
│       │   ├── contracts.py
│       │   ├── validation.py
│       │   ├── manifests.py
│       │   └── splits.py
│       │
│       ├── datasets/
│       │   ├── base.py
│       │   ├── injection_molding.py
│       │   ├── cip_dmd.py
│       │   ├── plasma_etch.py
│       │   └── pharma.py
│       │
│       ├── features/
│       │   ├── tabular.py
│       │   ├── time_domain.py
│       │   ├── frequency_domain.py
│       │   ├── spectra.py
│       │   └── lineage.py
│       │
│       ├── quality/
│       │   ├── baselines.py
│       │   ├── gbdt.py
│       │   ├── pls.py
│       │   ├── conformal.py
│       │   ├── selective.py
│       │   └── evaluation.py
│       │
│       ├── monitoring/
│       │   ├── spc.py
│       │   ├── mspc.py
│       │   ├── change_points.py
│       │   ├── anomaly.py
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
│   ├── injection_molding_eda.ipynb
│   ├── cip_dmd_eda.ipynb
│   ├── plasma_etch_eda.ipynb
│   └── pharma_eda.ipynb
│
├── tests/
│   ├── unit/
│   ├── contracts/
│   ├── integration/
│   └── fixtures/
│
└── docs/
    ├── architecture.md
    ├── methodology.md
    ├── datasets/
    ├── experiments/
    ├── model_cards/
    └── adr/
```

Rule:

> Notebooks investigate. `src/` implements.

No production logic should exist only inside notebooks.

---

# 27. Canonical manufacturing data model

Do not force every dataset into a relational schema it cannot naturally support.

Use a flexible `ManufacturingBundle`.

Conceptually:

```text
ManufacturingBundle

units
├── unit_id
├── batch_id?
├── product_family?
├── material?
└── production_time?

operations
├── unit_id
├── operation_id
├── machine_id?
├── process_stage
├── start_time
└── end_time

process_features
├── unit_id
├── operation_id?
└── scalar process variables

signals
├── unit_id
├── operation_id?
├── timestamp
└── signal channels

quality
├── unit_id
├── characteristic
├── measured_value
├── lower_spec?
└── upper_spec?

context
├── recipe
├── material_batch
├── product_family
├── production_day
└── operating_state

metadata
├── units
├── source descriptions
├── sampling rates
└── provenance
```

Dataset adapters populate only supported sections.

---

# 28. Dataset adapter interface

Conceptual interface:

```python
class DatasetAdapter:
    def source_contract(...)
    def download(...)
    def validate_raw(...)
    def prepare(...)
    def load_bundle(...)
    def split_strategy(...)
```

Core analytics should never contain:

```python
if dataset == "cip_dmd":
```

Dataset-specific behavior belongs in adapters/configuration.

---

# 29. Provenance manifest

Every processed dataset should generate:

```text
dataset
source_version
download_timestamp
source_url
raw hashes
processed hashes
adapter version
git commit
row/unit counts
feature counts
target definition
split definition
license
```

A trained model should always be traceable back to:

\[
\text{code}
+
\text{dataset}
+
\text{split}
+
\text{features}
+
\text{configuration}
\]

---

# 30. CLI

Use **Typer**.

Examples:

```text
uv run mpi dataset audit injection-molding
uv run mpi dataset prepare injection-molding

uv run mpi train quality \
    --dataset injection-molding \
    --target part_weight

uv run mpi evaluate quality \
    --run <run-id>

uv run mpi monitor \
    --dataset cip-dmd

uv run mpi dashboard
```

Everything needed for reproduction must work outside Jupyter.

---

# 31. Configuration

Use YAML/TOML validated by Pydantic.

Example:

```yaml
dataset: injection_molding

target:
  name: part_weight

split:
  strategy: production_day
  test_groups: [4]

features:
  scalar: true
  time_domain: true
  frequency_domain: false

model:
  type: lightgbm

uncertainty:
  method: split_conformal
  alpha: 0.10
```

Avoid Hydra unless configuration complexity actually demands it.

---

# 32. Testing stack

Use:

- pytest;
- Ruff;
- Pyright;
- pre-commit;
- GitHub Actions.

Tests should cover:

### Statistical functions

Known synthetic signals for:

- EWMA;
- CUSUM;
- control limits;
- conformal quantiles.

### Data contracts

Known-good and malformed fixtures.

### Leakage

Explicit assertions against target leakage and group overlap.

### Dataset adapters

Tiny representative synthetic fixtures.

### End-to-end integration

```text
fixture
  ↓
adapter
  ↓
feature extraction
  ↓
model
  ↓
prediction
  ↓
evaluation
```

---

# 33. CI pipeline

Pull-request checks:

```text
uv sync
   ↓
ruff
   ↓
pyright
   ↓
pytest
   ↓
small integration smoke test
```

Main branch additionally:

```text
Docker build (starting in v0.3, after the image exists)
```

Do not train full models in CI.

---

# 34. Experiment tracking

Do not start with MLflow on day one.

Use local structured experiment artifacts during the MVP.

Starting v0.3, add:

**MLflow**

Track:

```text
dataset hash
split hash
feature-set hash
git commit
parameters
metrics
plots
model
runtime
```

This keeps MVP scope contained.

---

# 35. Dashboard

Use:

**Streamlit + Plotly**

No React frontend.

Primary pages:

### Process overview

- production units;
- process states;
- target distributions;
- current model.

### Predictive quality

- actual vs predicted;
- residuals;
- uncertainty;
- accepted/abstained samples.

### Process monitoring

- SPC charts;
- multivariate scores;
- alerts;
- process stage.

### Diagnostics

- event timeline;
- affected operations;
- grouped attribution;
- quality effects.

### Transfer studies

- semiconductor;
- pharma;
- performance comparison.

---

# 36. MVP v0.1 — Predictive Quality

## Dataset

High-resolution injection molding.

## Business question

> Can process telemetry predict physical product quality sufficiently well to reduce the number of physical measurements required while identifying uncertain cases?

This is the smallest complete project.

---

# 37. MVP milestone M0 — Repository foundation

Deliver:

- Python project;
- uv;
- CLI shell;
- Ruff;
- Pyright;
- pytest;
- GitHub Actions;
- logging;
- configuration;
- repository structure.

Acceptance:

```text
uv run ruff check .
uv run pyright
uv run pytest
```

all succeed.

No ML yet.

---

# 38. MVP M1 — Source contract and ingestion

Produce:

```text
docs/datasets/injection-molding-source-contract.md
```

Document:

- dataset origin;
- license;
- experiment structure;
- machine-cycle ID;
- process variables;
- quality measurements;
- production days;
- process interventions.

Create:

```text
raw
  ↓
validated raw
  ↓
canonical bundle
  ↓
Parquet
```

Acceptance:

one CLI command reproducibly builds the prepared dataset.

---

# 39. MVP M2 — Data audit

Generate a reproducible report containing:

- number of units;
- production days;
- target distributions;
- missingness;
- scalar-variable distributions;
- trajectory shapes;
- interventions;
- startup/running state;
- correlations;
- quality variation;
- leakage audit.

Key goal:

understand the **experimental process structure before modeling**.

---

# 40. MVP M3 — Validation strategy

Use production structure instead of random splitting wherever possible.

Prefer:

\[
\text{train days/conditions}
\rightarrow
\text{held-out day/condition}
\]

Run both:

### Within-domain benchmark

Random/grouped split.

### Generalization benchmark

Held-out production day or intervention group.

This distinction is important.

Report:

\[
\text{interpolation performance}
\]

separately from:

\[
\text{process-state generalization}
\]

---

# 41. MVP M4 — Baselines

For each quality target:

### Baseline 0

Mean prediction.

### Baseline 1

Ridge.

### Baseline 2

PLS.

Start with scalar machine features.

Report:

| Model | MAE | RMSE | R² |
|---|---:|---:|---:|
| Mean | | | |
| Ridge | | | |
| PLS | | | |

No tuning yet.

---

# 42. MVP M5 — Time-series representation

Extract interpretable features from pressure/flow trajectories.

Compare:

### Scalar process values only

versus:

### Scalar + trajectory features

Examples:

```text
peak pressure
AUC
pressure rise slope
switch-over behavior
flow AUC
flow variance
trajectory duration
```

Potential PCA/functional representation later.

The key scientific question:

> Does high-resolution process shape contain useful quality information beyond machine summary variables?

---

# 43. MVP M6 — GBDT model

Train LightGBM using the strongest feature set.

Perform only bounded tuning.

Compare:

```text
Ridge
PLS
LightGBM
```

Optional XGBoost robustness check.

Do not spend weeks hyperparameter searching.

---

# 44. MVP M7 — Uncertainty

Implement conformal intervals.

Evaluate:

- marginal coverage;
- interval width;
- coverage by production day;
- startup vs running;
- process-intervention groups.

Example:

```text
Prediction:              58.94 g
90% conformal interval:  [58.88, 59.01]
```

---

# 45. MVP M8 — Selective measurement policy

Rank units using uncertainty.

Evaluate:

```text
Coverage        Units measured       MAE on auto-predicted
100%                  0%                     ...
90%                  10%                     ...
75%                  25%                     ...
50%                  50%                     ...
```

Produce:

\[
\boxed{\text{risk-coverage curve}}
\]

This becomes one of the project's headline charts.

---

# 46. MVP M9 — Explainability

Produce:

- global permutation importance;
- grouped SHAP;
- individual predictions;
- process-trajectory feature interpretation.

Question:

> Which aspects of the molding process most strongly influence the model's quality predictions?

Do not overclaim causation.

---

# 47. MVP M10 — Dashboard

Create:

### Overview

Process/target summary.

### Quality prediction

Model performance.

### Unit explorer

Prediction, uncertainty and feature attribution.

### Inspection tradeoff

Risk-coverage curve.

This is enough for a recruiter demo.

---

# 48. MVP release gate

v0.1 is complete when:

- data acquisition is reproducible;
- validation strategy is defensible;
- statistical baseline exists;
- ML candidate is evaluated;
- uncertainty is calibrated;
- selective prediction is demonstrated;
- dashboard works;
- tests/CI pass;
- README explains limitations.

Tag:

```text
v0.1.0
```

At this point, add the project to the resume and begin applying.

---

# 49. v0.2 — Process Intelligence

## Dataset

CiP-DMD.

## Objective

> Detect abnormal manufacturing behavior and identify which machine/process stage is most likely responsible.

---

# 50. v0.2 M1 — CiP-DMD adapter

Map:

```text
part
process
machine
operation
signal
quality
anomaly
```

into the canonical bundle.

Preserve full traceability.

Acceptance:

the existing core interfaces work without modification.

---

# 51. v0.2 M2 — Signal feature extraction

For machine/vibration signals implement:

- RMS;
- standard deviation;
- peak-to-peak;
- skewness;
- kurtosis;
- crest factor;
- band energy;
- spectral centroid where useful.

Every feature maintains process lineage.

---

# 52. v0.2 M3 — SPC

Implement and test:

- I/MR;
- EWMA;
- CUSUM.

Validate algorithms first on synthetic known-shift signals.

Then apply to real process streams.

---

# 53. v0.2 M4 — Multivariate monitoring

Implement:

\[
T^2
\]

and:

\[
SPE/Q
\]

from an in-control PCA reference model.

Analyze known normal/anomalous units.

---

# 54. v0.2 M5 — Anomaly benchmark

Compare:

- SPC;
- Mahalanobis;
- PCA/SPE;
- Isolation Forest.

Metrics:

- event recall;
- false-alert rate;
- detection timing;
- process-stage identification.

Avoid generic classification accuracy.

---

# 55. v0.2 M6 — Process diagnostics

For detected events produce:

```text
event
 ↓
process stage
 ↓
machine
 ↓
sub-operation
 ↓
signal family
 ↓
derived feature
```

Compare attribution against known induced anomalies.

This is your strongest root-cause-candidate validation.

---

# 56. v0.2 M7 — Quality linkage

Link process abnormalities to:

- dimensional QC;
- physical quality measurements;
- assembly outcomes.

Ask:

> Does the detected process excursion correspond to measurable downstream quality degradation?

This connects monitoring with business value.

---

# 57. v0.2 release gate

Complete when:

- CiP-DMD adapter works;
- SPC is tested;
- anomaly detection has operational metrics;
- known anomalies are localized;
- process events connect to QC outcomes;
- dashboard has process-monitoring page.

Tag:

```text
v0.2.0
```

This is a strong resume checkpoint.

---

# 58. v0.3 — Productionization

Now improve software maturity rather than adding another dataset.

---

# 59. MLflow

Add experiment tracking.

Record:

```text
dataset
dataset version/hash
split
feature set
git commit
seed
model
parameters
metrics
artifacts
```

---

# 60. Batch inference

Manufacturing systems are often batch-oriented.

Support:

```text
uv run mpi predict batch \
    --model quality-v1 \
    --input incoming.parquet \
    --output predictions.parquet
```

This is more realistic than REST-only deployment.

---

# 61. FastAPI

Expose:

```text
POST /v1/quality/predict
POST /v1/process/score
GET  /v1/models
GET  /health
```

Responses include:

```text
prediction
uncertainty
model version
feature version
decision state
```

---

# 62. Docker

One reproducible application image.

Docker Compose only if needed for:

- application;
- MLflow.

No Kubernetes.

---

# 63. Drift monitoring

Implement:

### Input drift

- missingness;
- PSI where appropriate;
- KS;
- Wasserstein;
- distribution plots.

### Performance drift

When quality labels arrive:

- MAE/RMSE;
- conformal coverage;
- selective risk;
- anomaly false-alert rate.

Keep:

\[
P(X)
\]

drift conceptually separate from:

\[
P(Y|X)
\]

performance degradation.

---

# 64. v0.3 release gate

Complete when:

- reproducible model lineage exists;
- batch inference works;
- API works;
- Docker works;
- drift reporting exists;
- CI includes container build;
- README contains deployment architecture.

Tag:

```text
v0.3.0
```

This is the recommended full resume-ready release.

---

# 65. v0.4 — Semiconductor Transfer

## Dataset

Bosch Plasma Etching.

## Objective

> Demonstrate that the same manufacturing-quality architecture generalizes to a high-dimensional semiconductor process.

---

# 66. Semiconductor ingestion

Support:

- NetCDF;
- wafer identifiers;
- 25-Hz OES;
- 5-Hz machine telemetry;
- wafer metrology.

Do not convert everything to a giant long dataframe.

Keep efficient array structures where appropriate.

---

# 67. Multirate alignment

Explicitly document:

- synchronization;
- resampling;
- process-cycle segmentation;
- missing intervals;
- wafer/run aggregation.

This is valuable data-engineering evidence by itself.

---

# 68. Spectral representation

Start simple:

### PCA

\[
3648D \rightarrow kD
\]

### PLS

Supervised dimensionality reduction.

### Engineered spectral bands

Where physically meaningful.

Only later consider neural embeddings.

---

# 69. Semiconductor virtual metrology

Predict:

- etch depth;
- uniformity;
- selectivity.

Compare:

```text
PLS
PCA + Ridge
PCA + LightGBM
spectral engineered + LightGBM
```

No neural network requirement.

---

# 70. Semiconductor drift

Use chamber-conditioning or experiment-day structure.

Evaluate:

```text
within-condition validation
```

versus:

```text
held-out condition/day validation
```

This demonstrates a real deployment issue:

\[
\text{process-state shift}
\]

---

# 71. Architecture-transfer test

The key software metric for v0.4:

> How much core code had to change?

Expected new components:

```text
plasma dataset adapter
spectral feature extractor
semiconductor config
```

Expected reused components:

```text
model interfaces
evaluation
uncertainty
drift
tracking
reporting
API contracts
```

If the entire system needs rewriting, the abstraction failed.

---

# 72. v0.4 release gate

Produce a semiconductor-specific case study:

> OES + equipment telemetry → wafer metrology.

Tag:

```text
v0.4.0
```

This version should be highlighted when applying to TI, semiconductor equipment vendors, fabs and suppliers.

---

# 73. v0.5 — Regulated Manufacturing Transfer

## Dataset

Pharmaceutical manufacturing.

## Objective

> Demonstrate process-quality analytics in a regulated batch-manufacturing environment.

---

# 74. Batch genealogy

Model:

```text
raw-material lots
       ↓
product batch
       ↓
compression process
       ↓
intermediate quality
       ↓
final quality
```

This is the major new conceptual capability.

---

# 75. Pharma statistical methods

Emphasize:

- PLS;
- PCA/MSPC;
- batch trajectory features;
- process capability where documented;
- raw-material variation;
- product-family effects.

Do not over-emphasize GBDT.

This case study should show that you understand **industrial statistics**, not merely ML.

---

# 76. Pharma validation

Use:

- chronological holdout where practical;
- product-family-aware splits;
- batch-level grouping.

No row-level random split across a single batch's time-series observations.

---

# 77. Pharma transfer report

Produce a concise report comparing:

```text
Injection molding:
cycle → part quality

Machining:
operation → component quality

Semiconductor:
plasma run → wafer quality

Pharma:
batch process → final product quality
```

This becomes the evidence that the architecture is genuinely broad.

Tag:

```text
v0.5.0
```

---

# 78. v0.6 optional — Advanced Manufacturing

Only if job targets justify it.

Potential NIST additive-manufacturing study:

```text
process command
       ↓
in-situ signal / image
       ↓
melt/layer behavior
       ↓
post-build defect/geometry
```

Useful for:

- Lockheed;
- RTX;
- aerospace;
- defense;
- advanced materials.

Do not delay job applications for this version.

---

# 79. 12-week implementation plan

## Weeks 1–2

### Foundation + source contract

Deliver:

- repository;
- testing/tooling;
- injection-molding source contract;
- adapter;
- clean processed dataset;
- EDA/audit.

End-state:

**data pipeline works.**

---

## Weeks 3–4

### Predictive-quality MVP

Deliver:

- split strategy;
- baselines;
- PLS;
- LightGBM;
- trajectory features;
- evaluation.

End-state:

**quality prediction works.**

Begin applying near end of week 4 if results are presentable.

---

## Week 5

### Uncertainty + selective prediction

Deliver:

- conformal intervals;
- risk-coverage analysis;
- uncertainty dashboard.

End-state:

**MVP becomes differentiated.**

Release v0.1.

---

## Weeks 6–7

### CiP-DMD process monitoring

Deliver:

- adapter;
- signal features;
- SPC;
- MSPC;
- anomaly benchmark.

---

## Week 8

### Diagnostics

Deliver:

- process-stage attribution;
- known-anomaly validation;
- quality linkage.

Release v0.2.

At this point the project should be prominent on the resume.

---

## Week 9

### Productionization

Deliver:

- MLflow;
- batch inference;
- FastAPI;
- Docker;
- drift report.

Release v0.3.

---

## Weeks 10–11

### Semiconductor transfer

Do one focused study.

Do not implement every possible semiconductor task.

Target:

\[
OES + process
\rightarrow
etch-quality prediction
\]

with a held-out process-state/day experiment.

Release v0.4.

---

## Week 12

### Job-search polish

Choose between:

- pharma transfer;
- recruiter-facing documentation;
- interview preparation;
- targeted semiconductor feature work.

For a strict three-month job goal, **presentation and applications are higher ROI than rushing another dataset**.

Pharma can continue afterward.

---

# 80. Application cadence

Do not sequence:

```text
finish project
    ↓
start job search
```

Use:

```text
MVP reaches credible state
        ↓
start applying
        ↓
continue improving project
        ↓
use new versions in interviews
```

Recommended:

### Weeks 1–3

Prepare resume and target-company list.

### Week 4+

Start applications.

### v0.1

Add project to resume.

### v0.2

Update bullets to emphasize manufacturing analytics.

### v0.4

Create semiconductor-specific resume version.

---

# 81. Target-company presentation

## Semiconductor resume

Lead with:

- virtual metrology;
- SPC/MSPC;
- process drift;
- OES/process data;
- yield-quality prediction;
- DOE/process-state validation.

---

## Defense/aerospace resume

Lead with:

- physical process signals;
- anomaly detection;
- precision manufacturing;
- traceability;
- root-cause candidates;
- quality monitoring;
- production analytics.

---

## Healthcare/pharma resume

Lead with:

- regulated process quality;
- batch genealogy;
- process capability;
- multivariate process monitoring;
- uncertainty;
- traceability.

Same project.

Different emphasis.

---

# 82. Evaluation matrix

## Predictive quality

Report:

- MAE;
- RMSE;
- \(R^2\);
- performance by process state.

## Uncertainty

Report:

- empirical coverage;
- interval width;
- conditional coverage.

## Selective prediction

Report:

- coverage;
- selective MAE/RMSE;
- abstention rate.

## Process monitoring

Report:

- event detection rate;
- false alerts;
- detection delay.

## Diagnosis

When ground truth exists:

- correct process stage;
- machine/subsystem rank;
- anomaly-class localization.

## Drift

Report:

- feature drift;
- performance degradation;
- uncertainty degradation.

---

# 83. Experiment discipline

Every experiment follows:

```text
question
   ↓
baseline
   ↓
one meaningful change
   ↓
validation
   ↓
keep / reject
```

Example:

> Does the pressure trajectory add useful quality information beyond scalar machine values?

Baseline:

scalar features.

Change:

trajectory features.

Decision:

retain only if held-out performance or robustness materially improves.

This prevents model zoo behavior.

---

# 84. Things explicitly not to add

Until there is a demonstrated requirement:

- Kafka
- Kubernetes
- Spark
- feature store
- vector DB
- LLM agent
- RAG
- ROS
- digital twin
- reinforcement learning
- graph database
- distributed training

A professional project is not defined by technology count.

---

# 85. When deep learning is justified

Do not use PyTorch merely to put it on the resume.

Potential valid later use:

### Injection pressure/flow trajectories

1-D CNN if engineered representations plateau.

### Semiconductor spectra

1-D spectral CNN if PCA/PLS baselines leave substantial performance.

### Additive manufacturing imagery

Vision models if NIST extension is implemented.

A neural model should answer:

> Does end-to-end representation learning outperform engineered/statistical representations?

If not:

remove it.

---

# 86. Documentation

Required:

```text
README.md
docs/architecture.md
docs/methodology.md
docs/datasets/
docs/experiments/
docs/model_cards/
DATA_LICENSES.md
```

Optional:

MkDocs later.

Do not spend the first week building a documentation website.

---

# 87. Architecture decision records

Keep short ADRs for meaningful choices.

Examples:

```text
ADR-001 Why injection molding replaced SoliDAIR as MVP
ADR-002 Why Polars + Parquet
ADR-003 Why no feature store
ADR-004 Why conformal prediction
ADR-005 Why CiP-DMD is the process-monitoring benchmark
ADR-006 Why predictive maintenance remains separate
```

These demonstrate engineering judgment.

---

# 88. README structure

The README should begin with the manufacturing problem, not installation instructions.

Recommended structure:

```text
Manufacturing Process & Quality Intelligence

1. Problem
2. Key result
3. Demo
4. Manufacturing use cases
5. Architecture
6. Dataset transfer
7. Validation methodology
8. Results
9. Reproduction
10. Limitations
```

---

# 89. README hero section

Once results exist:

```text
Manufacturing Process & Quality Intelligence

Predict downstream product quality, detect process excursions,
and identify likely process contributors from manufacturing telemetry.

Validated across:
• Injection molding
• Discrete machining
• Semiconductor plasma etching
• Pharmaceutical production
```

Then immediately show one high-value result.

---

# 90. Required portfolio figures

Do not generate dozens of plots.

Produce six excellent ones.

### Figure 1

Process → quality architecture.

### Figure 2

Predicted versus measured quality.

### Figure 3

Risk-coverage / selective prediction.

### Figure 4

SPC excursion with detection point.

### Figure 5

Hierarchical process diagnostic.

### Figure 6

Cross-domain transfer summary.

Optional semiconductor:

OES/spectral representation → wafer quality.

---

# 91. Resume bullets after v0.2

Use actual measurements when available.

Example structure:

> Developed an end-to-end manufacturing process intelligence system combining statistical process control, machine learning and uncertainty quantification to predict downstream product quality and detect manufacturing excursions from multivariate process telemetry.

> Built reusable process-data adapters and feature pipelines for cyclic and multi-stage manufacturing, including high-resolution machine signals, process traceability, multivariate SPC and operation-level anomaly diagnostics.

> Evaluated uncertainty-aware selective prediction to quantify the tradeoff between automated quality estimation and physical measurement requirements under process-state changes.

---

# 92. Resume bullet after semiconductor extension

> Extended the platform to semiconductor plasma etching, integrating 3,648-channel optical-emission spectra with equipment telemetry for virtual-metrology and process-drift experiments across chamber conditions.

Use exact measured results once available.

---

# 93. Interview story

The project should support this explanation:

> “I wanted a manufacturing ML project that wasn't just a Kaggle classifier. I modeled the common structure across factories: equipment and process measurements produce a physical product whose quality is measured later. I started with injection molding because it gives traceable process-to-quality data, then added a multi-stage machining dataset to test SPC and anomaly diagnosis, and finally tested whether the architecture transferred to semiconductor plasma processing.”

Then:

> “The models are only one layer. I also included uncertainty because a factory needs to know when not to trust an ML prediction, and I separated statistical attribution from causal root-cause claims.”

That is a strong mid-level applied-DS answer.

---

# 94. Success criteria

The project succeeds if it demonstrates:

### Manufacturing knowledge

- SPC;
- process variation;
- quality;
- traceability;
- DOE-aware validation.

### Statistical maturity

- baselines;
- PLS/PCA;
- uncertainty;
- appropriate splits.

### ML competence

- GBDT;
- feature engineering;
- evaluation;
- explainability.

### MLE competence

- reusable adapters;
- data contracts;
- lineage;
- testing;
- batch inference;
- API;
- Docker;
- experiment tracking.

### Domain transfer

At least:

\[
\text{general manufacturing}
+
\text{semiconductor}
\]

with pharma as the next extension.

---

# 95. Failure conditions

Stop or simplify a subsystem if:

- there is no measurable benefit;
- it cannot be validated;
- it exists solely to name a technology;
- the dataset does not support the claim;
- its complexity cannot be explained clearly in an interview.

Prefer:

\[
\boxed{\text{credible simplicity}}
\]

over:

\[
\boxed{\text{unvalidated sophistication}}
\]

---

# 96. Recommended stopping point

For the current hiring objective:

\[
\boxed{
v0.1
\rightarrow
v0.2
\rightarrow
v0.3
\rightarrow
v0.4
}
\]

is the optimal core.

That gives:

```text
Predictive quality
        ↓
Process monitoring
        ↓
Diagnostics
        ↓
Productionization
        ↓
Semiconductor transfer
```

Pharma and additive manufacturing are valuable extensions, but they should not delay applications.

---

# 97. Final architecture

```text
                         DATA SOURCES

        Injection        CiP-DMD       Plasma       Pharma
        Molding
            │               │             │            │
            └──────────── dataset adapters ────────────┘
                                │
                                ▼
                     MANUFACTURING CONTRACTS
                                │
             ┌──────────────────┼───────────────────┐
             │                  │                   │
             ▼                  ▼                   ▼
        PROCESS DATA        SIGNAL DATA         QUALITY DATA
             │                  │                   │
             └──────────────────┼───────────────────┘
                                ▼
                      FEATURE / STATE LAYER
                                │
            ┌───────────────────┼────────────────────┐
            │                   │                    │
            ▼                   ▼                    ▼
         QUALITY             PROCESS             ANOMALY
        PREDICTION          MONITORING           DETECTION
            │                   │                    │
            └───────────────────┼────────────────────┘
                                ▼
                         UNCERTAINTY
                                │
                                ▼
                          DIAGNOSTICS
                                │
                                ▼
                       DECISION SUPPORT
                      /                \
                 Dashboard             API
```

The project should demonstrate one idea exceptionally well:

\[
\boxed{
\text{measure}
\rightarrow
\text{understand}
\rightarrow
\text{predict}
\rightarrow
\text{detect}
\rightarrow
\text{diagnose}
\rightarrow
\text{decide}
}
\]

across physical manufacturing systems.
