# M2 — Bounded Dataset 2 audit

**Status:** complete.

## Accepted outcome

Understand the weight-prediction problem for the portfolio before M3 decides the
prediction cutoff, feature allowlist and evaluation partitions. Answer whether
weight varies usefully, how experiments differ, which scalar associations merit
investigation, what trajectories contain, and what availability evidence remains
unresolved. Negative findings are valid; this is analysis, not model selection.

Scope follows the [specification](../spec.md).
The [source contract](../datasets/injection-molding-source-contract.md) owns meaning
and limitations; [M1](m01-injection-molding-ingestion.md) owns ingestion evidence.

### Audit coverage

The notebook summarizes prepared-data counts, weight distributions and descriptive
outlier flags, all 31 retained process scalars, their pooled and within-experiment
weight associations, redundancy and experiment dependence. Constant and 95%-modal
near-constant flags are descriptive, not feature-selection rules. No records are
removed and no product tolerances are invented.

Pressure and flow views include seeded cycle examples, means, 10th–90th percentile
envelopes and standard deviations on native elapsed time. Audit means, maxima and
trapezoidal AUC use actual irregular timestamps; they do not define M5's features.
Signal amplitude units remain unknown. Source-order intervention views preserve
experiment 15's paper/release discrepancy and context nulls without inventing days,
physical phase boundaries or causal effects.

The field inventory traces all 40 source scalars and the required pressure/flow
channels through source names, canonical names, meaning, availability evidence,
leakage risk and provisional modeling disposition. Experiment ID, moisture,
mold-temperature context and charge codes remain separate from predictors.
Optional cavity/state groups remain deferred. Complete-cycle availability was a
hypothesis for M3 to assess, not an approved cutoff in this audit.

Pairwise standardized mean differences describe experiment shift. Between- and
within-experiment weight variation and all-data correlations remain exploratory;
they do not measure predictive performance, identify causes or justify selecting
outer folds for favorable outcomes.

## Implementation

One executable notebook uses the existing prepared bundle. Signal rows are joined
to cycle identity and sorted by source cycle position and sample index before
reshaping; physical-phase labels and resampling are not introduced. The tracked
notebook has no outputs; generated figures and tables remain under `artifacts/`.

## Findings

The audit is implemented in
[`notebooks/m02_injection_molding_audit.ipynb`](../../notebooks/m02_injection_molding_audit.ipynb)
and executes against the ignored prepared bundle. It preserves all inputs, uses
source-order cycle identity and native signal time, and leaves the tracked notebook
free of outputs. The aggregate results below are descriptive evidence for M3, not
an accepted feature set or validation design.

### Weight and experiment variation

- The snapshot reproduces 829 labeled cycles (303/223/303 for experiments
  15/20/23), 2,048 pressure and flow samples per cycle, 92 signal-only exclusions,
  and no missing weights.
- Overall weight is 115.160 g mean, 114.905 g median, 0.842 g sample standard
  deviation, 1.575 g IQR, and 113.897–116.690 g range. The same Tukey
  1.5-IQR rule flags no overall records; it flags 0/0/10 within experiments
  15/20/23, and no flagged records are removed.
- Experiment means are 115.956, 115.237 and 114.308 g for 15, 20 and 23;
  respective standard deviations are 0.542, 0.572 and 0.198 g. Pairwise weight
  standardized mean differences are 1.289 (15–20), 4.038 (15–23) and 2.169
  (20–23). Between-experiment sums of squares account descriptively for 70.45%
  of total observed weight variation. This is strong distribution-shift evidence,
  not an estimate of causal effect.

### Scalar and trajectory evidence

- All 31 retained process scalars are complete and vary under the stated
  constant/95%-modal near-constant definitions. Several barrel-temperature fields
  are almost duplicates across the pooled data (`r` above 0.997), and their
  extreme between-experiment standardized differences arise from very small
  within-experiment variation. They are strong experiment proxies, not independent
  evidence of weight mechanism.
- Several ordinary process measurements retain sizable within-experiment weight
  associations: injection time correlations are -0.924/-0.960/-0.614,
  switchover-pressure correlations are -0.985/-0.985/-0.671, and maximum-pressure
  correlations are -0.982/-0.975/-0.359 for experiments 15/20/23. Conversely,
  the roughly 0.77 pooled correlations for barrel zones 2–8 shrink substantially
  within experiments. These exploratory associations justify investigation, not
  feature selection or performance claims. State-integral associations remain
  deferred because their timing and meanings are unresolved.
- Native-grid trajectory summaries differ visibly. Pressure means are
  487.118/488.859/507.608 and trapezoidal AUC means are
  5,982.921/6,004.145/6,234.537 native-amplitude-seconds for experiments
  15/20/23. Flow means are 9.878/5.834/5.623 and AUC means are
  121.375/71.757/69.169. Experiment 20 has materially broader cycle-to-cycle
  pressure and flow-summary spreads than experiment 23. Flow maximum is exactly
  109.576 for every experiment-23 cycle, illustrating why a maximum alone can be
  uninformative. These six audit summaries do not define M5 features.

### Intervention and availability evidence

- Source-order context runs are reproduced without day labels: experiment 15
  moisture 89/98/116 rows at raw 0.050/0.100/0.150; experiment 20 moisture
  76/86/61 rows at 0.086/0.180/0.046; and experiment 23 mold temperature
  99/103/101 rows at 80/90/70. Segment mean weights change from
  115.246 to 115.946 to 116.509 g in experiment 15, are
  114.686/115.849/115.061 g in experiment 20, and are
  114.133/114.299/114.488 g in experiment 23. Process-measurement plots move
  alongside some boundaries, but chronology and co-varying conditions prevent a
  causal claim. Experiment 15's paper/release moisture discrepancy remains open.
- The inventory traces every one of the 40 source scalars plus pressure and flow.
  Identity and all four quality fields are excluded; experiment/moisture/
  mold-temperature/charge fields remain context-only; ordinary measured process
  scalars and required trajectories are provisional candidates; integral fields
  and optional cavity/state groups remain unresolved/deferred. M3 must decide the
  cutoff and confirm measurement completion before admitting any candidate.

### Decisions reserved for M3

The audit left the prediction cutoff, availability at that cutoff, scalar and
trajectory allowlists, and leakage-safe tuning/calibration within
leave-one-experiment-out evaluation to M3. Handling near-duplicate experiment
proxies also required a decision before consulting eventual holdout results.
Moisture, mold temperature, charge and experiment ID remain context, not default
predictors. No split, model, tolerance, geometry role, integral-state decoding or
complete-cycle policy is accepted by M2.

### Verification

The documented `jupyter nbconvert --execute` command completed the full notebook
from the clean tracked source and wrote only the ignored executed copy. Rendered
weight, selected-scalar, trajectory, variability and intervention figures were
inspected for readable labels, correct experiment grouping and explicit units or
unit limitations. Scoped full-table rendering exposes all scalar-distribution
rows and every inventory field with untruncated availability and leakage text;
the main scalar overview remains compact. Independent calculations reproduced
grouped sample counts,
weight means and sample standard deviations. For one cycle, `numpy.trapezoid`
and an explicit adjacent-trapezoid sum both gave 6,124.330682938099; the checked
time axis contained 3 intervals of 0.004 seconds and 2,044 of 0.006 seconds.

The original audit passed lint, formatting, type checking, 49 tests and the CLI
smoke check. The admitted raw ZIP matched
manifest SHA-256 `69294087889a52791c296734051d6b21b30847c2859613e4178074182150c491`.
Only the source manifest is tracked under `data/`; notebook outputs and all raw,
prepared and row-level data remain ignored.

The pre-M4 identity-ordering correction was checked against shuffled real signal
rows: both reconstructed channel matrices, elapsed times and every cycle's AUC
were identical to the original ordered-bundle results. The full notebook executed
again successfully; the tracked copy remains output-free.

The audit's all-experiment exploration is descriptive, not an untouched holdout.
The completed [M3 contract](m03-feature-and-evaluation-contract.md) defines the
cutoff, feature eligibility and evaluation memberships used by the
[M4 scalar baselines](m04-scalar-baselines.md).
