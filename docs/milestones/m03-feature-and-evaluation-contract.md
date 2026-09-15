# M3 — Feature and evaluation contract

**Status:** complete.

## Outcome and scope

Give M4 one understandable, reproducible input and evaluation contract for Dataset
2 weight prediction. Follow [the spec](../spec.md#validation-and-feature-availability),
[M2 evidence](m02-dataset-audit.md) and the
[source contract](../datasets/injection-molding-source-contract.md).
This is a personal portfolio experiment, not an evaluation platform.

## Implemented feature and cutoff contract

The prediction point is after the complete machine cycle and before consuming that
unit's inspection result. The source establishes complete cycle-keyed scalar and
pressure/flow records, but not controller export latency or inspection timestamps.
This remains a retrospective process-to-quality experiment; early-cycle and live
availability claims are out of scope.

The scalar predictor allowlist is exactly `cycle_duration`,
`maximum_injection_pressure`, `switchover_injection_pressure`,
`actual_back_pressure`, `injection_time`, `melt_cushion`, `dosing_time`,
`barrel_heating_zone_1` through `barrel_heating_zone_8`, and
`mold_heating_circuit_1`.

These 16 native-value fields are selected explicitly rather than by subtracting
known exclusions from the retained schema. The correlated heating zones remain;
later transformations or selection must be fitted inside training data. The
unusual `actual_back_pressure` range (including negative values) is retained as
released, with unresolved unit/reference and no silent repair. Required trajectory
inputs are the native `elapsed_time_seconds`, `injection_pressure` and
`injection_flow` samples, grouped by unit/operation and sample index. No trajectory
features are computed here.

All other retained columns are excluded from default predictors. Experiment and
intervention context remains available only for grouping/evaluation. Quality,
geometry, integral/state fields, identities, source position and optional source
groups cannot enter through the allowlist.

## Implemented membership contract

The generator first sorts each experiment by `cycle_counter`, then applies a
NumPy PCG64 permutation seeded through `SeedSequence([42, protocol_code,
experiment_id])`. The protocol code is 1 for primary and 2 for secondary ID, so
the two benchmarks use separate permutations. The method identifier, seed, source
version and source archive SHA-256 are stored in every artifact row. The recorded
allocation method is `numpy-pcg64-seedsequence`.

For primary folds, the first `ceil(20%)` units in each experiment's primary
permutation are calibration and the remainder are fit/tune whenever that
experiment is in development. The entire held-out experiment is test. The same
per-experiment development membership is reused across applicable outer folds.
Primary tuning uses two leave-one-development-experiment-out folds. For fit/tune
rows, `inner_fold` is the experiment ID: validate on that experiment and train on
the other development experiment, excluding calibration. Average the two inner
validation MAEs equally for model/parameter selection, then refit on all fit/tune
rows. Calibration and evaluation (`role = test`) rows have null inner folds.

The separate secondary ID fold uses its own per-experiment permutation: first
`ceil(20%)` test, next `ceil(20%)` calibration, and the remainder fit/tune with
three inner folds (0, 1, 2), assigned round-robin in permutation order within each
experiment. This targets within-regime interpolation, subject to adjacent-cycle
dependence, not chronology or an ID subset nested inside primary folds.

## Results and verification

The README command generated the ignored
`artifacts/m03/injection_molding_memberships.parquet` artifact from the current
829-cycle prepared bundle without modifying prepared inputs. It contains 3,316
rows: 829 for each of three primary folds and 829 for the secondary ID fold.

Primary development allocations (`fit/tune`, calibration) are 242/61 for
experiment 15, 178/45 for experiment 20, and 242/61 for experiment 23 whenever
represented. Fold totals (`fit/tune`, calibration, test) are 420/106/303 for
holdout 15, 484/122/223 for holdout 20, and 420/106/303 for holdout 23. Secondary
ID experiment allocations (`fit/tune`, calibration, test) are 181/61/61,
133/45/45 and 181/61/61 respectively, totaling 495/167/167. Primary inner validation
counts are 178/242 (holdout 15: experiments 20/23), 242/242 (holdout 20:
experiments 15/23), and 242/178 (holdout 23: experiments 15/20). Secondary inner
counts remain 167/164/164. These totals follow independent
`ceil(20%)` calculations from source group sizes 303/223/303. The primary test
union contains every unit once.

Focused synthetic tests cover disjoint/complete partitions, exact outer
experiment separation, row-order and unrelated-value independence, inner-fold
exclusion/balance, stable reused primary development memberships, and protection
against newly retained predictor columns. An independent reconstruction from the
prepared unit/context tables matched every generated role and inner-fold
assignment.

The pre-M4 correction regenerated memberships with experiment-grouped primary
inner folds. All 3,316 unit/role memberships and the entire secondary ID table
match the previous artifact; only primary fit/tune inner-fold labels changed.
Synthetic checks verify that inner training and validation experiments are disjoint.

`uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, all 54
tests, `uv run mpi --version`, and the documented generator command pass with the
repository-local UV cache. Git ignore inspection resolves the generated artifact
to `artifacts/**`, and documentation links were checked against their local
targets. No models, derived trajectory features or performance claims were
produced.

## Interpretation and next step

This is leave-one-experiment-out grouped cross-validation, not a pristine prospective
holdout: M2 inspected targets and associations in all three experiments. Fold-local
fitting prevents training leakage but does not erase that exploratory exposure.
The `test` role is an evaluation designation, not a claim of never-seen data.
Primary group-aware tuning aligns selection with experiment-shift evaluation, but
only two development groups provide limited evidence. The secondary ID benchmark
may be optimistic because adjacent cycles can be dependent.

Define M5 features and M6 search choices from physical reasoning, existing M2
exploration and fold-local development evidence, not M4 outer residuals or errors.
Record precise candidate definitions before their outer evaluation. Any later
outer-result-driven redesign must be reported as exploratory, not confirmation.
No new dataset, model, feature search or unit-resolution work is required here.
Next: M4 Mean, Ridge and PLS scalar baselines. Model matrices contain only the
16 allowlisted scalars: `select_scalar_predictors()` excludes join identifiers;
callers align rows/targets by identity before selecting predictors.
