# Manufacturing Process & Quality Intelligence

Canonical scope and acceptance criteria. The [roadmap](implementation-roadmap.md)
owns progress, [README](../README.md) owns commands, and [AGENTS.md](../AGENTS.md)
owns engineering guidance. This replaces the long greenfield plan; its full text
remains in Git history at commit `60e3c25`.

## Purpose and boundaries

Build a personal manufacturing-data-science portfolio demonstrating how process
telemetry predicts physical product quality, how predictions behave under process
changes, and when measurement is preferable. Later studies add monitoring,
supported diagnostics and semiconductor transfer. Optimize for credible results,
clear code and a reproducible local demo, not production operations.

The first question is: **Does high-resolution telemetry improve part-weight
prediction beyond scalar measurements, especially under changed conditions?**
A negative result is valid. Do not promise improvement or measurement savings.

Required progression: predict → evaluate generalization → quantify uncertainty →
selectively measure; then source-supported monitoring/diagnostics and transfer.
No MVP SPC, physical RCA, PASS/FAIL, quality escapes or fabricated factory chronology.
No distributed systems, feature store, agentic AI, autonomous control, predictive
maintenance or computer-vision scope. Deep learning requires a later justified
experiment, not a résumé keyword. MLflow, APIs and containers are optional later.

## Sources and admission

| Release | Dataset and purpose |
| --- | --- |
| v0.1 | scatimdata Dataset 2 only: weight prediction under experiment shift |
| v0.2 | Choose PyScrew or CiP-DMD after audit: process/assembly intelligence |
| v0.3 | Bosch Plasma after audit: semiconductor virtual metrology |
| v0.4 optional | One role-relevant engineering demonstration |
| v0.5 optional | Pharmaceutical batch-quality transfer |
| v0.6 optional | NIST additive/advanced manufacturing if useful for target roles |

Before adding a source, establish publisher/version, license and redistribution,
physical row/unit meaning, IDs/joins, chronology, units, targets, interventions,
limits and leakage-safe evaluation. It must support the scientific claim, a valid
split and legally shareable portfolio evidence. An interesting landing page does
not admit a dataset. Preserve discrepancies; do not repair data to fit a paper.

Dataset 2's [source contract](datasets/injection-molding-source-contract.md) and
[manifest](../data/manifests/injection-molding-source.json) own exact evidence.
Keep 829 labeled cycles with matched pressure/flow, zero labeled-only cycles and
92 excluded signal-only identities. Preserve all 40 scalar fields and the native
2,048-point grid, 0–12.276 seconds, mostly 6 ms with three 4 ms increments.
No padding, fabricated sample 2,049, resampling or inferred physical units at ingestion.
Weight is in grams; geometry remains native, unknown-unit, deferred evidence.
Experiment IDs 20/23/15 have 223/303/303 units. They are controlled experiment
boundaries, not authoritative calendar days. Spec limits remain unknown.
Equipment accuracy is not a product tolerance. Do not pool Datasets 1–3.
SoliDAIR is outside the core; its abandoned work is recoverable from Git history.

## Implementation shape

Python runtime and dependencies are declared in `pyproject.toml`, `.python-version`
and `uv.lock`. Use Polars and Parquet; NumPy for numeric work. Add scientific
libraries when a current experiment needs them. Pydantic/Typer support config/CLI;
Streamlit and Plotly are the planned dashboard stack. No React or database service
is required. Notebooks may investigate; reusable computation belongs in `src/mpi`
and reproduction must work outside Jupyter.

Dataset adapters own parsing and source semantics. Current canonical tables are
`units`, `operations`, `process_features`, `signals`, `quality` and `context`,
with source identity, licensing, lineage, transformations and limitations in
metadata. Keep this existing shape, but let actual later sources test its value.
Do not invent hierarchy or force high-dimensional spectra into a giant long table.
No generic adapter framework or future directory/config scaffold is required.

Raw hashes identify the source; derived tables use ordinary save/load and schema
checks. No acquisition receipts, processed-file hash registry, producer Git-state
gate or automatic freshness machinery is required. Research interpretation belongs
in documentation. Experiment outputs must identify their data, exact split,
feature definitions, model/configuration and seed so results can be reproduced;
simple local records suffice.

## MVP milestones

| Milestone | Deliverable and distinguishing outcome |
| --- | --- |
| M0 | Runnable package/CLI, locked environment, configuration, logging, tests and CI |
| M1 | Reproducible acquisition, validated source, canonicalization and Parquet/JSON reload preserving the Dataset 2 facts above |
| M2 | Reproducible audit: counts/groups, weight distribution, missingness, scalar distributions/correlations, trajectory shapes, interventions, variation and leakage risks |
| M3 | Prediction cutoff, explicit process-feature allowlist and exact leakage-safe fit/tuning/calibration/policy/test memberships |
| M4 | Scalar Mean, Ridge and PLS baselines; MAE, RMSE and R²; no tuning campaign |
| M5 | Matched scalar, engineered-trajectory and compressed-trajectory comparisons |
| M6 | LightGBM on the same representations/splits, with bounded inner tuning |
| M7 | Conformal baseline, per-cycle uncertainty score and ID-versus-shift evaluation |
| M8 | Selective measurement risk-coverage experiment with baseline rankings |
| M9 | Bounded predictive explanation, not physical root-cause claims |
| M10 | Five-page offline dashboard and reproducible résumé-ready release |

M2 keeps geometry and unresolved source details in audit appendices, not new
modeling targets. Separate experimental context from predictors. Exploratory
target access does not permit choosing outer folds based on favorable outcomes.
M3's protocol precedes model comparisons.

### Validation and feature availability

Primary: all three leave-one-experiment-out folds, holding out 15, 20 and 23 in
turn. Keep each cycle and all samples together; never split signal rows.
Inside each outer fold only two development experiments remain. M3 must specify
a feasible disjoint inner tuning/calibration protocol, minimum partition sizes
and any within-experiment blocking/gaps; it cannot assume three inner groups.
Save exact unit IDs for fitting, inner validation, calibration, optional policy
validation and outer test. Never calibrate or tune on the outer experiment.

Fit imputation, scaling, selection, PCA/PLS and component counts only in appropriate
training partitions. PLS is supervised: calibration/test targets must not enter it.
Keep an independently reserved ID evaluation subset from the development groups
out of fitting, tuning, calibration and policy selection. Evaluate the same fitted
pipeline on that subset and the outer experiment for paired shift comparisons.
Separately report the secondary cycle-level random/grouped/blocked ID benchmark
and its dependence limitations; training error is not ID evaluation.

Headline: equal-weight mean of the three outer-fold MAEs in grams. Also report
per-fold MAE/RMSE/R² and counts, plus pooled out-of-fold MAE labeled sample-weighted.
Record split identity with metrics. Three groups do not establish factory-wide
generalization or strong population-level significance; show fold variability.

Before M4, define a prediction cutoff; the initial candidate is complete cycle
telemetry, before that cycle's quality measurement. Unknown availability means
excluded. Early-cycle prediction is separate scope. The 31 retained process fields
are not a training allowlist. Exclude quality and quality-derived data, geometry,
IDs and row indices. Keep experiment ID, moisture, mold-temperature context and
charge codes context-only. Optional process-plus-known-context ablations require
availability justification and separate reporting.
Source integrals are not established quality-derived fields, but their state/cutoff
meaning is unresolved: exclude by default. Cavity pressure and state matrices are
optional only after clearance. English translation does not grant eligibility.

### Representation and models

Compare A: allowed scalars; B: A plus engineered pressure/flow features; C: A plus
compressed pressure/flow. B includes AUC, mean/std, peaks/timing, quantiles,
rise/fall slopes and defined segment integrals. Use actual elapsed times.
Windows are time intervals unless physical phases are verified. Preserve units
as unknown where unresolved; an integral is not automatically energy or volume.
Any regularization belongs in feature engineering and must be explicit/justified;
frequency features require appropriate sampling treatment.

PCA is the minimum compressed baseline; evaluate PLS representation as a bounded
alternative. Functional PCA, XGBoost and generic feature generators are not gates.
Compare representations using a common downstream estimator to isolate their
benefit; report per-fold MAE_scalar minus MAE_augmented. LightGBM compares A/B/C
on identical outer splits with scalar LightGBM as its matched reference.
Choose/tune inside development data, not by selecting the best outer-test result.

### Uncertainty and measurement policy

Implement split-conformal absolute-residual intervals using held-out calibration
and the finite-sample quantile. Report nominal/empirical coverage, mean/median
width in grams and counts by held-out experiment, reserved ID subset and useful
target/process strata. Exchangeability may fail under shift: no coverage guarantee.
Report MAE_shift minus MAE_ID and interval_coverage_shift minus interval_coverage_ID.

The baseline has constant width within each fitted fold and cannot rank units or
automatically widen on unfamiliar inputs. M7 also evaluates a per-cycle score
(for example train-only residual-scale modeling with normalized conformal
intervals) against that baseline. Test whether it identifies higher-error cycles;
do not assume widening, conditional coverage or robustness to arbitrary factories.
Inferred day/startup labels are not ground-truth strata.

M8 ranks without test labels and compares with auto-predict-all and seeded random
ranking. Define deterministic ties and realized accepted counts. Report
auto-predict coverage 100%, 90%, 75%, 50%; measurement rate = 1 minus coverage;
selective MAE = mean absolute error among accepted predictions. Zero accepted
units means undefined risk, not zero. Distinguish this coverage from interval
coverage. A test coverage sweep is descriptive; an operational threshold must
be fixed using development/policy-validation data before the outer test.
Use AUTO-PREDICT / MEASURE, never PASS/HOLD or quality-escape claims here.

### Explanation, dashboard and release

M9 uses global permutation importance, grouped SHAP and illustrative predictions/
trajectory interpretation; favor a compact grouped view over a method catalog.
Attribution identifies predictive associations, not causal root causes.
M10 pages: dataset/experiment explorer; predictive quality/model/representation
comparisons; held-out generalization versus ID; intervals/coverage/width; selective
measurement risk-coverage. No fabricated timeline or implied deployed station.

v0.1 is complete when the data invariants, cutoff/allowlist/splits, Mean/Ridge/PLS/
LightGBM and A/B/C results, per-experiment metrics/deltas, uncertainty and selective
measurement comparisons, bounded explanation, dashboard, package/CLI, locked
environment and CI are reproducible. Document limitations and negative results.
Keep figures focused: process-to-quality architecture, prediction versus measured
weight, representation/experiment comparisons and risk-coverage.
Completion does not require positive trajectory benefit, nominal shifted coverage
or measurement savings. Tag v0.1.0 when ready and use actual results on the résumé.

## Later releases

**v0.2:** Audit [PyScrew](https://github.com/nikolaiwest/pyscrew)
([descriptor](https://arxiv.org/abs/2505.11925),
[collection](https://doi.org/10.5281/zenodo.14729547)) versus
[CiP-DMD](https://zenodo.org/records/8420132). Choose one, not both by default.
Prefer verified assembly/degradation evidence for automation roles or multi-stage
machining/QC evidence for precision manufacturing. Distinguish station OK/NOK,
induced anomalies and final physical QC. Audit the
[cross-process-chain candidate](https://zenodo.org/records/17240390) for upstream/
downstream lineage, IDs, quality, license, usable counts and PyScrew overlap.
Record accept/defer/reject; a passed audit does not automatically add an adapter.
Unresolved evidence must not block independent MVP/semiconductor work.

For the selected source, implement meaningful signal features, I/MR/EWMA/CUSUM
(tested on known synthetic shifts), PCA T² and SPE/Q from an in-control reference,
and compare SPC, Mahalanobis, PCA/SPE and Isolation Forest. Evaluate event recall,
false alerts and timing only at the source-supported run/time resolution.
Localize to supported stages/sensors and compare with verified anomaly labels;
connect events to QC/assembly outcomes without equating attribution with causes.
The release requires the admitted adapter, comparison decisions, tested monitoring,
operational metrics, supported localization/quality linkage and monitoring view.

**v0.3:** [Bosch Plasma](https://doi.org/10.5281/zenodo.17122442) is the priority
semiconductor transfer after source admission. Verify wafer/run joins, NetCDF/
array layout, OES versus equipment sampling, synchronization/segmentation,
missing intervals and aggregation. Start with PCA/PLS and physically justified
spectral bands; compare statistical baselines and spectral/process representations
on a justified condition/day holdout. Require at least one supported physical
metrology target, reproducible commands/checks, limits and a record of reused
versus changed core components. Do not require every etch target, neural models,
API/container infrastructure or direct transfer of a fitted molding model.

**v0.4 optional:** Choose a role-relevant batch-inference, tracking, API, container
or drift-report demonstration. Require a clear purpose, ordinary-path test, local
invocation, model/data lineage and documented limits—not production readiness.
Input-distribution drift and labeled performance degradation are different.
Unselected capabilities do not gate release; container CI only if an image exists.

**v0.5 optional:** [Pharma descriptor](https://doi.org/10.1038/s41597-022-01203-x)
and [versioned collection](https://doi.org/10.6084/m9.figshare.c.5645578.v3) are
source leads. Study raw-material lots → batch → compression/intermediate → final
quality, PLS/PCA/MSPC, batch trajectories and product-family/material effects.
Use batch-level grouping and justified chronological/product-family splits;
never random-split rows from one batch trajectory. Capability metrics need
documented specs and a stable process. Produce a concise domain-transfer report.
**v0.6 optional:** NIST additive manufacturing only when target roles justify it.
Neither is required in the initial job-search cycle.

## Delivery priorities

The relative 12-week target is not calendar progress or permission to skip evidence:
weeks 1–2 ingestion/audit; week 3 cutoff/splits/scalar baselines; week 4 trajectories/
LightGBM; week 5 held-out comparisons; week 6 uncertainty/measurement/explanation/
dashboard and credible v0.1; weeks 7–8 process/assembly source selection and study;
weeks 9–10 semiconductor; weeks 11–12 demo/résumé polish and only useful optional
work. Do not restart completed foundation work.

Apply at credible v0.1 or earlier with presentable evidence; continue improving.
An imminent semiconductor interview may bring Bosch forward once prerequisites
pass, without waiting for engineering extras or pharma. Use past tense only for
verified results and never invent performance figures.
