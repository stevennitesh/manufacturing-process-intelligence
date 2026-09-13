# Manufacturing Process & Quality Intelligence

**Status:** Canonical project specification and implementation plan.

Repository progress is tracked separately in `docs/implementation-roadmap.md`.
Historical plans and investigations under `.archive/` are non-authoritative.

**Accepted scope reconciliation (2026-09-12):** v0.1 is a Dataset 2 part-weight
experiment under process shift, not a factory monitoring or conformance system.
The architecture remains multi-domain; later capabilities must pass their own
source gates. Section 11 owns release order; numbered sections are stable topic
references, not a requirement to implement productionization before semiconductor
transfer. Planning revisions do not advance implementation status.

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

**MVP predictive-quality dataset: scatimdata Dataset 2 only**

This should be the first implementation.

Freeze the required MVP population to 829 labeled cycles with one-to-one process
and part linkage, scalar process measurements, injection pressure, injection flow,
and **part weight in grams**. Explicitly exclude the 92 signal-only cycles from
labeled units. Do not pool Datasets 1–3. Keep geometry in raw/canonical evidence
with unresolved units and experimental/deferred status; it is not a required
modeling target or a dependency of the weight-only release gate.

The central question is: **Does high-resolution machine-cycle telemetry improve
part-weight prediction beyond scalar measurements under changed process
conditions?** Test this question; do not promise that the answer will be positive.
The decision policy is AUTO-PREDICT / MEASURE, not PASS / INSPECT / HOLD. No
specification-based failure rate, quality escapes, classical SPC, longitudinal
factory chronology or physical root-cause analysis is required in v0.1.

The dataset provides physical process measurements linked directly to manufactured parts, including scalar machine parameters and high-resolution injection-pressure and flow trajectories. The paper describes 2,049 samples at 6 ms resolution; inspection of the pinned release found 2,048 elapsed-time rows with a predominantly 6 ms grid and three 4 ms transitions. The released structure and its validation boundary are recorded in the [source contract](../datasets/injection-molding-source-contract.md). Manufactured parts have physical quality measurements such as weight and dimensions. The experiments include deliberate changes in process settings, startup states, pauses and multiple production days. See the [peer-reviewed data description](https://doi.org/10.3390/polym15040978) and [publisher dataset repository](https://github.com/sc4t1m/scatimdata).

The publisher dataset repository states a [CC BY 4.0 license](https://github.com/sc4t1m/scatimdata#license). M1 must verify the exact admitted files and terms before acquisition.

### Source-evidence boundary

The three injection-molding archives are distinct experiments/products, not an
automatically pooled training population. Candidate-specific materials, chronology,
target discrepancies and admission decisions belong to the
[source contract](../datasets/injection-molding-source-contract.md#candidate-selection-and-exclusions).
Further source research must reconcile that contract and the affected milestone
plan before changing ingestion scope. Dataset 2's explicit experiment groups
support experiment-held-out evaluation; cross-day claims require a confirmed day
mapping. Published ordinal tables, machine counters and released row indices are
not interchangeable. Do not repair data to fit paper summaries, infer physical
units from translation, or treat measurement-equipment accuracy as part tolerances.

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
- descriptive experiment/process-condition comparisons;
- uncertainty quantification;
- selective measurement/inspection;
- uncertainty degradation under controlled experiment shift;
- experiment-held-out generalization, not confirmed calendar-day generalization.

---

# 6. Dataset B — Process / assembly intelligence candidates

### Role

**v0.2 source-contract selection: PyScrew versus CiP-DMD**

Neither candidate is admitted by this specification. Before choosing, audit exact
files/version, license, units, label provenance, repeated parts, chronological
structure, leakage-safe splits and links to downstream quality. Prefer PyScrew
when verified assembly/degradation/anomaly evidence better serves the robotics
and automation story; prefer CiP-DMD for verified multi-stage machining/QC and
operation hierarchy. Career relevance is a selection criterion, not source proof.

Primary PyScrew leads: the [author repository](https://github.com/nikolaiwest/pyscrew),
[descriptor](https://arxiv.org/abs/2505.11925), and
[dataset collection](https://doi.org/10.5281/zenodo.14729547).
Treat station OK/NOK outcomes, induced condition labels and final physical QC as
different quantities until audited. Do not equate nominal labels with defects.

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

### Cross-process-chain decision gate

Before committing to v0.2 dataset scope, perform a bounded audit of the 2025
[Cross-process-chain dataset archive](https://zenodo.org/records/17240390).
Verify upstream molding to downstream screw-driving lineage, component/assembly
IDs, join cardinalities, final-quality meaning, repeated-workpiece leakage,
license and usable sample counts. Check overlap with PyScrew: linked or duplicated
parts must not appear on both sides of a split or masquerade as independent
transfer evidence. Record accept/defer/reject and rationale. A passed audit may
justify a revised transfer scope; it does not automatically authorize a third
adapter. If it fails or remains unresolved, proceed with the defensible audited
candidate without blocking the MVP or semiconductor work. No admission is claimed
from the landing page alone.

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

This is an optional later test of transfer to regulated manufacturing, not an
achieved result. It is not required during the initial three-month job-search
cycle and follows semiconductor relevance and essential production polish.

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
| **v0.1 MVP** | Predictive quality under process shift; uncertainty and selective measurement | scatimdata Dataset 2, weight only |
| **v0.2** | Process / assembly monitoring and diagnostics | PyScrew or CiP-DMD after audit; cross-process-chain decision gate |
| **v0.3** | Semiconductor transfer | Bosch Plasma after source admission |
| **v0.4** | Productionization / MLOps | Admitted sources |
| **v0.5 optional** | Regulated manufacturing transfer | Pharma after initial job-search priorities |
| **v0.6 optional** | Advanced manufacturing transfer | + NIST AMMT |

The recommended application checkpoint is:

\[
\boxed{\text{credible v0.1, then strengthen with v0.2 and v0.3}}
\]

Do not wait for all datasets before applying.
An interview-driven semiconductor case study may be pulled forward once its
technical prerequisites and source gate pass; unfinished release gates stay
unfinished. SoliDAIR is outside the required core and 12-week schedule. Revisit
only under a separately authorized large-N tabular stress-testing need.

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

SPC/MSPC, anomaly monitoring and capability analysis below are later-domain
capabilities, not Dataset 2 MVP requirements. The MVP uses PLS/PCA, prediction,
experiment-shift evaluation, uncertainty and selective measurement.

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

Optional later robustness benchmark (not a v0.1 gate):

**XGBoost**

Baselines:

- mean;
- Ridge;
- PLS.

Median, ordinary linear regression and Elastic Net are optional extensions, not
additional required MVP comparisons.

Do not make model comparison the primary purpose.

The required MVP comparison is:

\[
\text{scalar only}
\quad\text{vs.}\quad
\text{scalar + engineered trajectories}
\quad\text{vs.}\quad
\text{scalar + compressed trajectories}
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
For Dataset 2, unresolved signal units remain unresolved through derived features;
do not label a pressure/flow integral as physical energy or volume without unit
and signal-definition evidence. Frequency-domain methods require an explicitly
appropriate sampling treatment, not an assumption of a perfectly uniform grid.

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
- coverage by experiment (calendar day only for later sources that establish it);
- coverage by target range.

Example report:

```text
Nominal coverage:       90.0%
Observed coverage:      90.6%
Median interval width:  ...
```

Do not call this a production guarantee.
Use held-out calibration residuals and the finite-sample conformal quantile, with
training, calibration and evaluation membership recorded separately. Standard
split-conformal coverage relies on exchangeability, which experiment shift can
violate; report observed coverage under shift rather than claiming a guarantee.
See the [conformal methods reference](https://arxiv.org/abs/2107.07511).

The simple absolute-residual construction has one q per fitted model/calibration
fold and therefore constant interval width within that fold. It cannot by itself
rank cycles or automatically widen on unfamiliar inputs. M7 must additionally
validate a per-cycle uncertainty score for M8 (for example a train-only fitted
positive residual-scale model and normalized conformal intervals). That extension
has its own assumptions; compare it with the constant-width baseline and measure
whether it actually identifies higher-error held-out cycles.

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
For accepted set A, compute selective MAE as the mean absolute error on A;
measurement rate is 1 minus auto-predict coverage. Report coverage 100%, 90%, 75%
and 50% with accepted counts, measurement rate and accepted MAE in grams. At zero
accepted units risk is undefined, not zero. Distinguish auto-predict coverage
from prediction-interval coverage. Rank without test labels; specify deterministic
tie handling. A test-set coverage sweep is descriptive, while an operational
threshold must be selected on development/policy-validation data and frozen
before the outer test. Never tune it using held-out error or claim quality escapes.

---

# 21. Quality-decision policy

If a later dataset provides defensible specification limits:

This section is excluded from the Dataset 2 MVP, including its UI and API claims.

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

Starting in v0.2 after the chosen source establishes applicable ordering and
reference-process assumptions; not part of the Dataset 2 MVP:

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
│       │   ├── process_assembly.py  # candidate-owned adapter after source gate
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
│   ├── process_assembly_eda.ipynb
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
├── experiment_id?
├── production_day?
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

Illustrative future commands, not the current CLI contract (see README/help):

```text
uv run mpi dataset audit injection-molding
uv run mpi dataset prepare injection-molding

uv run mpi train quality \
    --dataset injection-molding \
    --target weight

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
  name: weight

split:
  strategy: leave_one_experiment_out
  group_field: experiment_id
  groups: [15, 20, 23]

features:
  allowlist: process_only  # explicit cutoff-reviewed names, not all retained columns
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
Docker build (starting in v0.4, after the image exists)
```

Do not train full models in CI.

---

# 34. Experiment tracking

Do not start with MLflow on day one.

Use local structured experiment artifacts during the MVP.

Starting v0.4, add:

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

MVP pages are dataset/experiment explorer, predictive quality, generalization,
uncertainty, and selective prediction (section 47). No fabricated timeline,
PASS/FAIL status, SPC chart or physical RCA in this release. Monitoring and
diagnostics pages begin in v0.2 with source-supported chronology/labels;
semiconductor transfer views begin in v0.3 and pharma views are optional later.

---

# 36. MVP v0.1 — Predictive Quality Under Process Shift

## Dataset

scatimdata Dataset 2 only; required target `weight` in grams. Preserve geometry
as deferred evidence, not additional required modeling. The three experimental
production groups represent controlled process-condition changes, not established
calendar days or a broad factory timeline.

## Business question

> Does high-resolution machine-cycle telemetry improve part-weight prediction
> beyond standard scalar measurements, especially under changed process conditions,
> and can uncertainty identify when physical measurement is preferable?

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
- explicit experiment IDs and unavailable calendar-day labels;
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

one CLI command reproducibly builds the prepared dataset. Assert 829 labeled
units, all matched to pressure/flow, zero labeled-only units, 92 signal-only
exclusions, and all 2,048 native timestamps from 0 to 12.276 seconds including
the three 4-ms transitions. Regression tests must reject padding/resampling or
fabricated sample 2,049. Keep source/canonical names traceable, geometry units and
spec limits null, and experiment IDs 15/20/23 distinct from production days.
The existing acquisition/raw-validation evidence remains valid; M1 completion
still requires canonicalization and persistence, not modeling or source repair.

---

# 39. MVP M2 — Data audit

Generate a reproducible report containing:

- number of units;
- experiment groups 15/20/23 and counts 303/223/303;
- target distributions;
- missingness;
- scalar-variable distributions;
- trajectory shapes;
- interventions;
- source-declared intervention context, with inferred startup/day labels separate;
- correlations;
- quality variation;
- leakage audit.

Key goal:

understand the **experimental process structure before modeling**.
Weight is the required target. Geometry and source discrepancies are audit
appendices, not additional training targets. Keep moisture, mold-temperature
context, charge codes and experiment IDs separate from process predictors.
Exploratory access does not authorize outcome-guided selection of the outer test
folds; freeze the evaluation/feature-selection protocol before model comparison.

---

# 40. MVP M3 — Validation strategy

Primary benchmark: leave one **experiment** out, using all three outer folds:

| Development experiment IDs | Outer test experiment ID | Test units |
| --- | --- | ---: |
| 20, 23 | 15 | 303 |
| 15, 23 | 20 | 223 |
| 15, 20 | 23 | 303 |

Each cycle and all of its samples stay together. Do not split signal rows. Save
exact IDs for fit, inner validation, calibration, optional policy validation and
outer test; fit preprocessing, imputation, scaling, feature selection, PCA and
PLS only on the appropriate training partition. PLS is supervised and must never
see calibration/test targets. Tune models and uncertainty scores only inside the
two development experiments. Freeze choices before evaluating the outer group.

M3's detailed plan must define a feasible, disjoint inner tuning/calibration
protocol given only two development groups, minimum partition sizes and any
within-experiment blocking/gap policy. It must not assume three independent
groups remain inside each outer fold or calibrate on the held-out experiment.

Secondary benchmark: separately specified within-distribution cycle-level
random/grouped or blocked evaluation, with its dependence limitations reported.
For paired ID-versus-shift comparisons, reserve an ID evaluation subset inside
the development groups before fitting, keeping it out of tuning, calibration and
policy fitting. Evaluate the same frozen pipeline on that ID subset and the
outer experiment. Do not compare training errors against outer-test errors.

Headline: equal-weight mean of the three outer-fold MAEs in grams, accompanied
by each fold's MAE/RMSE/R² and sample count. Also report pooled out-of-fold MAE
explicitly as sample-weighted; do not conceal a failing experiment in an average.
Report secondary ID results separately and record split identity on every metric.
Three experiments do not establish broad factory generalization or reliable
population-level significance; report fold variability and avoid overstated tests.

### Prediction-time feature contract

Before M4, specify the prediction cutoff (initial candidate: after complete
cycle telemetry is available but without using that cycle's quality measurement).
Validate availability of each retained predictor by that cutoff; early-cycle
prediction is a separately scoped extension. Unknown availability means excluded,
not assumed available. The 31 retained process columns are not an allowlist.

Required benchmarks are process-only. Exclude weight, all geometry and anything
derived from outcomes; IDs and row indices are bookkeeping, not predictors.
`experiment_id`, moisture, mold-temperature context and source charge remain
context-only. An optional process-plus-known-context ablation must justify
inference-time availability and remain separate from the headline experiment.
Source integrals are process summaries, **not established quality-derived fields**;
their state/cutoff semantics are unresolved, so exclude them by default. Cavity
pressure, state matrices and source integrals are optional extensions only after
clearance. M1 retention and English translation do not grant modeling eligibility.

---

# 41. MVP M4 — Baselines

For Dataset 2 weight only, under the frozen M3 splits and process allowlist:

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

Compare three required representation families on the same cycles and splits:

- A: the cutoff-reviewed scalar process allowlist.
- B: A plus engineered pressure/flow features: AUC, mean/std, peaks and their
  elapsed timing, quantiles, rise/fall slopes and defined segment integrals.
- C: A plus compressed pressure/flow representations. PCA is the minimum
  compressed baseline; evaluate supervised PLS representation as a bounded
  alternative. Functional PCA is optional, not another mandatory dependency.

Use actual elapsed timestamps for integration, slopes and peak timing. Segments
are elapsed-time windows unless physical phases are source-supported. Any
regularized representation must be explicit, justified and confined to feature
engineering; never change the canonical 2,048-point grid. Fit every learned
transform inside the training fold, including choosing component counts.

Report paired `delta_error = MAE_scalar - MAE_augmented` for each outer fold and
representation, using a common downstream estimator to isolate representation
benefit. A negative or zero delta is a valid finding, not a failed integrity gate.

The key scientific question:

> Does high-resolution process shape contain useful quality information beyond machine summary variables?

---

# 43. MVP M6 — GBDT model

Train LightGBM on A, B and C using identical outer splits. Compare against Mean,
Ridge and PLS, retaining scalar LightGBM as the model-matched reference. Bounded
inner selection may choose a representation; never choose the "strongest" one
from outer-test results and then present those results as untouched validation.

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

Implement the split-conformal baseline and a validated per-cycle uncertainty
score for selective measurement as specified in section 19. Calibrate only on
the M3 development calibration partition, never on the outer experiment.

Report nominal and empirical coverage, mean/median interval width in grams and
sample counts for each held-out experiment and for the reserved ID subsets.
Measure `MAE_shift - MAE_ID` and `interval_coverage_shift - interval_coverage_ID`
using the same frozen pipeline. Test whether the uncertainty score tracks higher
error under shift; do not assume widening. Constant-width baseline intervals
cannot widen per input. Report coverage degradation honestly; nominal coverage
under nonexchangeable shift is not a release guarantee. Do not use inferred day
or startup labels as ground-truth strata. This controlled experiment does not
establish robustness to arbitrary lots, suppliers, machines or chambers.

---

# 45. MVP M8 — Selective measurement policy

Rank units using the M7 per-cycle score without observing test outcomes. Compare
against measure-none/auto-predict-all and a seeded random-ranking reference;
record ties and realized accepted counts. Follow section 20's separation of a
descriptive coverage sweep and a deployable threshold fixed on development data.

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

Do not overclaim causation. This is bounded predictive explanation, not physical
RCA or a required factory diagnosis subsystem. Prefer one grouped importance
view plus illustrative predictions; no exhaustive explainability model zoo.

---

# 47. MVP M10 — Dashboard

Create:

1. Dataset / experiment explorer: groups, condition context, weight distributions
   and native pressure/flow examples; no fabricated production-day timeline.
2. Predictive quality: actual versus predicted, residuals, Mean/Ridge/PLS/LightGBM
   and scalar/engineered/compressed comparisons, with optional unit explanations.
3. Generalization: all held-out experiments and separately labeled ID results.
4. Uncertainty: intervals, nominal/empirical coverage and width by experiment.
5. Selective prediction: risk-coverage, physical measurement rate and accepted MAE.

Use AUTO-PREDICT / MEASURE only. These are offline measurement-policy experiments,
not a deployed station or evidence of reduced defective-part escapes.

This is enough for a recruiter demo.

---

# 48. MVP release gate

v0.1 is complete when:

- reproducible Dataset 2 acquisition/preparation preserves exactly 829 labeled
  units, all required joins, 92 explicit signal-only exclusions and the native grid;
- weight in grams is the sole required target; geometry remains deferred evidence;
- process-only allowlist/cutoff and leakage-safe fit/tuning/calibration/test
  membership are recorded; leave-one-experiment-out is the primary benchmark;
- Mean, Ridge, PLS and LightGBM results exist, alongside A/B/C representation
  comparisons, per-experiment metrics and explicit scalar-to-trajectory deltas;
- conformal coverage and width, ID-versus-shift differences and a validated
  per-cycle uncertainty score are reported without claiming a shift guarantee;
- risk-coverage/measurement-rate/accepted-error results exist at the specified
  coverages, with baseline comparisons and no test-label-informed policy tuning;
- the five-page dashboard, package, CLI, locked environment and tests/CI work;
- README/model evidence explains unknowns, statistical limitations and negative
  results; no PASS/FAIL, quality-escape, fabricated chronology or physical RCA claim.

Completion means a rigorous, reproducible answer, not guaranteed improvement,
nominal coverage on every shifted group or a promised measurement saving. SPC,
anomaly monitoring, geometry models, additional datasets, MLflow, API and Docker
are not requirements for this gate.

Tag:

```text
v0.1.0
```

At this point, add the project to the resume and begin applying.

---

# 49. v0.2 — Manufacturing Process / Assembly Intelligence

## Dataset

Choose PyScrew or CiP-DMD after the section 6 source-contract comparison and
cross-process-chain decision gate. Do not implement both by default.

## Objective

> Detect abnormal manufacturing behavior and identify which machine/process stage is most likely responsible.

---

# 50. v0.2 M1 — Source selection and admitted adapter

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

Preserve source-supported traceability only. The audit must establish the
selected source's signals, repeated-part identity, label meaning and evaluation
groups before mapping. No fake hierarchy to make assembly resemble machining.

Acceptance:

the admitted adapter passes source and bundle gates; reuse existing core
interfaces where valid and document any necessary justified changes.

---

# 51. v0.2 M2 — Signal feature extraction

For the chosen source's machine/vibration or torque/angle signals, select
physically meaningful features from:

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

Then apply only where the selected source supports ordered process streams and
an appropriate in-control reference. Unsupported time semantics prohibit
per-hour/delay claims; report per-run results or explicitly narrow the gate.

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

Compare attribution against source-verified induced anomalies where available.
Use only the hierarchy the selected source establishes; missing physical-cause
ground truth is a limitation, not permission to equate attribution with RCA.

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

- the source comparison and cross-process-chain audit decisions are recorded;
- the selected PyScrew or CiP-DMD adapter works;
- SPC is tested;
- anomaly detection has operational metrics;
- anomalies are localized to the resolution supported by verified labels;
- process events connect to verified QC/assembly outcomes without conflating
  station OK/NOK, induced anomaly classes and measured physical defects;
- dashboard has process-monitoring page.

Tag:

```text
v0.2.0
```

This is a strong resume checkpoint.

---

# 58. v0.4 — Productionization

After the priority semiconductor case study, improve software maturity. Basic
reproducibility remains mandatory earlier; MLflow, API and containers do not gate
v0.1 or v0.3. Topic section numbering is retained for stable references.

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

# 64. v0.4 release gate

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
v0.4.0
```

This is the production-polish release, not a prerequisite for applications.

---

# 65. v0.3 — Semiconductor Transfer

## Dataset

Bosch Plasma Etching, subject to its source admission gate. This is the highest
priority domain-transfer study and precedes full productionization and pharma.

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

The key software metric for v0.3:

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
reporting
local experiment lineage
```

Reuse tracking/API contracts if already implemented, but do not require v0.4
infrastructure for this study. Record core changes and why they were needed;
architecture transfer does not mean direct transfer of a fitted molding model.

---

# 72. v0.3 release gate

Produce a semiconductor-specific case study:

> OES + equipment telemetry → wafer metrology.

Acceptance requires an admitted versioned source, verified wafer/run joins and
multirate handling, at least one supported physical metrology target, statistical
baselines and spectral/process representation comparisons on a justified held-out
condition split, plus reproducible commands, checks, limitations and a record of
reused versus changed core components. Exact scope is detailed at its milestone;
do not require every listed wafer target or any v0.4 deployment service.

Tag:

```text
v0.3.0
```

This version should be highlighted when applying to TI, semiconductor equipment vendors, fabs and suppliers.

---

# 73. v0.5 optional — Regulated Manufacturing Transfer

## Dataset

Pharmaceutical manufacturing; optional during the first three months, after
the semiconductor/job-search checkpoint. Do not delay applications for it.

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

Process/assembly (chosen admitted source):
operation → component QC or verified assembly outcome

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

This is a relative delivery target, not elapsed calendar progress or permission
to skip gates. Do not restart completed foundation work. M3's split/allowlist
protocol must precede M4 fitting even though week 5 emphasizes final evaluation.

| Weeks | Deliverable |
| --- | --- |
| 1–2 | Dataset 2 ingestion, canonicalization, persistence and audit |
| 3 | Freeze validation/cutoff/allowlist; scalar Mean, Ridge and PLS |
| 4 | Engineered and compressed trajectories; bounded LightGBM comparisons |
| 5 | Complete all experiment-held-out evaluations and separate ID comparisons |
| 6 | Conformal/shift evaluation, selective measurement, bounded explanations and dashboard; release v0.1 if its gate passes, then apply |
| 7 | PyScrew versus CiP-DMD source audit, cross-process-chain decision and selected adapter |
| 8 | Source-supported SPC/MSPC, anomaly and process/assembly diagnostics; v0.2 gate |
| 9–10 | Focused Bosch Plasma source audit and semiconductor case study; v0.3 gate |
| 11 | Productionization essentials; v0.4 only when its full gate passes |
| 12 | Resume/demo/interview polish; pharma only if ahead and useful |

An imminent semiconductor interview may pull the focused Bosch study forward
once prerequisites pass. Do not require MLflow/API/Docker first. Missing source
evidence may defer a dataset, not justify invented lineage or quality semantics.
Pharma is optional in this window; SoliDAIR consumes none of it.

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

### By credible v0.1 (target week 6), or earlier with presentable evidence

Start applications.

### v0.1

Add project to resume.

### v0.2

Update bullets to emphasize manufacturing analytics.

### v0.3

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
- per-experiment performance and macro/pooled outer-fold summaries;
- scalar versus engineered/compressed trajectory deltas on matched splits.

## Uncertainty

Report:

- empirical coverage;
- interval width;
- empirical subgroup coverage (not guaranteed conditional coverage);
- held-out-experiment versus reserved ID coverage and error deltas.

## Selective prediction

Report:

- coverage;
- selective MAE/RMSE;
- physical measurement/abstention rate;
- accepted sample counts and random-ranking reference.

## Process monitoring

v0.2 onward, only with source-supported labels and ordering.

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
ADR-005 Why the audited process/assembly source was selected
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

Initial study:
• Dataset 2 part-weight prediction under experiment shift
• Scalar versus high-resolution trajectory comparison
• Uncertainty and selective physical measurement

Add process/assembly, semiconductor and optional pharma claims only after
their case studies have actually passed their gates.
```

Then immediately show one high-value result.

---

# 90. Required portfolio figures

Do not generate dozens of plots.

Produce the first three for v0.1, then source-supported later-stage figures.
The MVP also needs the representation and held-out-experiment comparisons
specified in its dashboard gate; SPC and diagnostics figures do not block it.

### Figure 1

Process → quality architecture.

### Figure 2

Predicted versus measured quality.

### Figure 3

Risk-coverage / selective prediction.

### Figure 4

SPC excursion with detection point (v0.2).

### Figure 5

Source-supported process/assembly diagnostic (v0.2).

### Figure 6

Cross-domain transfer summary.

Priority semiconductor figure (v0.3):

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

> “I started by testing whether high-resolution machine telemetry improves
> part-weight prediction beyond scalar measurements and whether that model
> generalizes across controlled process experiments. I then evaluated uncertainty
> and selective measurement. Later case studies test process/assembly anomalies
> and transfer the same abstractions to semiconductor fabrication.”

Use past tense only for completed, verified work. Do not imply a fixed machining
choice, positive trajectory benefit, factory-wide generalization or causal RCA.

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
Semiconductor transfer
        ↓
Production polish
```

Pharma and additive manufacturing are valuable extensions, but they should not delay applications.

---

# 97. Final architecture

```text
                         DATA SOURCES

        Dataset 2      PyScrew OR      Plasma       Pharma
        weight         CiP-DMD                      optional
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
