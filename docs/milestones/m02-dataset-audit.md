# M2 — Bounded Dataset 2 audit

**Status:** complete; M2-final review passed.

## Accepted outcome

Understand the weight-prediction problem for the portfolio before M3 decides the
prediction cutoff, feature allowlist and evaluation partitions. Answer whether
weight varies usefully, how experiments differ, which scalar associations merit
investigation, what trajectories contain, and what availability evidence remains
unresolved. Negative findings are valid; this is analysis, not model selection.

Scope comes from the user's M2 audit brief and [specification](../spec.md).
The [source contract](../datasets/injection-molding-source-contract.md) owns meaning
and limitations; [M1](m01-injection-molding-ingestion.md) owns ingestion evidence.

### Required audit

1. Load the existing prepared bundle. Show 829 labeled cycles, experiment counts
   15/20/23 = 303/223/303, 2,048 pressure/flow samples per cycle, 92 exclusions and
   zero missing weights. This is a reader-facing snapshot, not another raw audit.
2. Summarize weight in grams overall and per experiment: count, mean, median,
   standard deviation, IQR, min/max, histogram and boxplot. Quantify outlier flags
   descriptively with a stated rule; do not remove records or invent tolerances.
3. Inventory all 31 retained process scalars: missingness, unique counts,
   mean/std/range, per-experiment distributions, weight associations overall and
   within experiments, redundancy and experiment dependence. Flag constants and
   near-constants using an explicit descriptive definition, not a feature filter.
   Keep the overview readable; full compact tables may accompany selected plots.
4. Keep experiment ID, moisture, mold-temperature context and charge codes separate
   from predictors. Compare between-experiment and within-experiment weight
   variation descriptively; do not present explained variation as a causal effect.
5. For each pressure/flow channel and experiment, show seeded cycle examples,
   mean, 10th–90th percentile envelope and standard deviation over native elapsed
   time. Derive only audit means, maxima and trapezoidal AUC per cycle and compare
   their distributions by experiment. AUC uses actual irregular timestamps; these
   summaries are not the M5 feature contract. Signal amplitude units stay unknown.
6. Examine weight and a small number of process measurements across the observed
   moisture/temperature intervention segments in source order. Preserve experiment
   15's paper/release discrepancy and context nulls. No fabricated calendar days,
   repaired values, inferred physical phase boundaries or causal claims.
7. Produce an exhaustive field inventory covering all 40 source scalars and the
   required pressure/flow channels, with source/canonical name, meaning, availability
   evidence, leakage risk and provisional M3 disposition. Families may share reasons,
   but individual fields must remain traceable. Distinguish candidate process,
   context-only, outcome/identity exclusion and unresolved/deferred fields.
   Record optional cavity/state groups as deferred rather than decoding them.
   Complete-cycle availability is a hypothesis for M3, not an approved cutoff.
8. Quantify experiment shift with a small interpretable effect-size summary:
   pairwise standardized mean differences suffice. Define denominator and handling
   of zero variance/missing values. No hypothesis-test battery is required.
9. Summarize evidence-backed answers and unresolved questions for M3 in this file.
   Correlations across all data are exploratory, not predictive performance or
   permission to choose outer folds based on their eventual results.

## Delivery approach

- Start from `8b2cd3f71529b718b545ca0a8d8e10c16fd2cc72` on `main`; checkout was
  clean before this plan. This plan is the only lead-created pre-existing change.
- Implement primarily in `notebooks/m02_injection_molding_audit.ipynb`. Make the
  full audit executable top-to-bottom from a documented command without manual
  notebook interaction. Add only needed notebook/plotting dependencies to the
  locked environment. Keep generated row-level outputs local/ignored; a clean
  notebook and concise attributed aggregate findings are sufficient in Git.
- Promote calculations into a small module only if actual reuse/testability
  warrants it. No EDA framework, report generator, config system, new adapter,
  persistence refactor, model training, feature selection or version bump.
- Preserve raw/prepared inputs. Use existing `load_bundle`; joins and trajectory
  reshaping must align by cycle/sample identity rather than incidental row order.
- Use readable selected plots rather than a huge heatmap or plot catalog. Keep
  conclusions tied to observed numeric evidence and cite the existing source.
- Update README reproduction instructions and roadmap status/links. Do not rewrite
  unrelated plans or create historical report/version directories.

### Final gate: M2-final

One integrated review covers the entire change against the starting commit plus
this plan. No intermediate checkpoint is needed: the work has one local analytical
consumer and no new persistent interface for downstream code.

Required evidence: documented command successfully executes the full audit on the
prepared Dataset 2 bundle; tables/figures inspected for readable labels and valid
units/grouping; selected numerical calculations checked independently, including
irregular-grid AUC and grouped statistics; focused synthetic tests where reusable
calculation code is introduced; configured lint/format/type/test checks pass.
Show no source mutation and no tracked raw/row-level dataset payload. Normal CI
must remain independent of local third-party data. Notebook outputs may be cleared
after execution; retain reproducible commands and concise result evidence here.

Cost-aware delivery uses one Sol Medium implementer with the selected Ponytail
guidance. Final review has at most two correction rounds. The implementer returns
with writers stopped and checkout custody released; the lead records acceptance.
No commits, pushes, issue changes or M3 implementation are authorized by this plan.

## Findings and handoff

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

### M3 questions left open

M3 must choose the prediction cutoff, verify availability at that cutoff, freeze
the scalar and trajectory allowlists, and define leakage-safe tuning/calibration
within leave-one-experiment-out evaluation. It must also decide how to handle
near-duplicate experiment proxies without consulting eventual holdout results.
Moisture, mold temperature, charge and experiment ID remain context, not default
predictors. No split, model, tolerance, geometry role, integral-state decoding or
complete-cycle policy is accepted by M2.

### Execution evidence for final review

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

`uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, all 49
tests, and the CLI version smoke test pass. The admitted raw ZIP still matches
manifest SHA-256 `69294087889a52791c296734051d6b21b30847c2859613e4178074182150c491`.
Only the source manifest is tracked under `data/`; notebook outputs and all raw,
prepared and row-level data remain ignored.

M2-final review passed against the starting commit and the full uncommitted
delivery. One presentation correction made exhaustive tables readable without
row/column/text truncation; re-execution passed. Numerical and source-boundary
checks remain valid. No modeling, feature approval or version changes were made.
Next: plan M3's cutoff, feature contract and evaluation memberships.
