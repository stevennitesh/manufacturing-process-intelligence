# M3 — Feature and evaluation contract

**Status:** complete; M3-final review passed.

## Outcome and scope

Give M4 one understandable, reproducible input and evaluation contract for Dataset
2 weight prediction. Follow [the spec](../spec.md#validation-and-feature-availability),
[M2 evidence](m02-dataset-audit.md) and the
[source contract](../datasets/injection-molding-source-contract.md).
This is a personal portfolio experiment, not an evaluation platform.

### Decisions for delivery

- Predict weight in grams from completed machine-cycle process measurements and
  the released pressure/flow trajectories, without access to that part's quality
  measurements. This is a retrospective process-to-quality experiment, not an
  early-cycle or verified live deployment claim. Document the source evidence for
  measurement availability separately from the assumption that a consumer can
  obtain the completed process record before consuming inspection results. Do not
  invent a verified wall-clock ordering or controller export latency. If source
  evidence cannot support an ordinary field's completion, exclude it and raise any
  material change to the intended cutoff with the lead.
- Use an explicit allowlist of ordinary process measurements supported at that
  cutoff, expected to be the 16 non-integral process scalars. Include near-duplicate
  temperature measurements initially: M2 correlation alone is not a selection
  rule. Native units remain unchanged. Explain the anomalous back-pressure values
  without silently repairing them or assigning physical units.
- Required trajectory channels are injection pressure and injection flow, with
  native elapsed time and all samples kept with their unit. M3 does not extract
  features or fit a representation. No geometry, quality-derived fields, integral
  fields, cavity/state channels, identifiers, source order or experimental context
  enters the default predictor list. Context stays available for evaluation.
- Primary evaluation holds out each complete experiment (15, 20, 23) once. For
  each remaining experiment, sort units by cycle identity then apply a deterministic
  seeded permutation; allocate ceil(20% of its units) to calibration and the rest
  to fit/tune. Use seed 42, with a documented stable per-experiment allocation reused
  wherever that experiment is in primary development. Membership selection must
  not inspect weight or feature values.
- Within each primary fit/tune set, provide three deterministic inner validation
  fold assignments balanced within each experiment. A tuning fold is validated
  using only that fold; its complement is fitted. It is not an extra permanent
  holdout. Calibration and outer test never receive inner-fold assignments.
- Secondary ID benchmark: a separate seeded cycle-level shuffle within each
  experiment, ceil(20%) test, ceil(20%) calibration and the remainder fit/tune;
  provide the same three-fold inner assignment rule. This deliberately measures
  interpolation within represented experiments, not chronology or independent
  production runs. Adjacent-cycle dependence may make it optimistic. It is not
  another ID subset inside every primary fold, and comparisons with primary
  results are descriptive comparisons of different fitted pipelines.
- Preserve exact unit memberships, protocol/fold, experiment, role and inner-fold
  assignments in one simple local artifact. Document seed/allocation rules and
  source identity through existing owners. Generated memberships remain ignored.
  Future models/representations reuse these memberships. All fitting, scaling,
  transformations, feature selection and tuning stay inside the applicable training
  subset; calibration stays outside selection. Final models refit on fit/tune only.
- No model training, correlations/interaction search, transformations, feature
  selection, conformal implementation or performance claims in M3. M4 establishes
  scalar baselines; M5 plans bounded feature experiments on development data.

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
Fit/tune units receive inner folds 0, 1 and 2 round-robin in permutation order;
calibration and test rows have null inner folds.

The separate secondary ID fold uses its own per-experiment permutation: first
`ceil(20%)` test, next `ceil(20%)` calibration, and the remainder fit/tune with
the same balanced inner-fold rule. It is an interpolation benchmark subject to
adjacent-cycle dependence, not a chronology test or an ID subset nested inside
primary folds.

## Delivery approach

Start from `6e8baec8da220ffc69eab8442100c5bb7b820121` on `main`, clean before this
plan. This file is the only lead-created pre-existing change.

Prefer one small reusable dataset-specific module for the feature list and split
construction, a thin runnable script if needed for reproduction, and focused
synthetic tests. Do not introduce a framework, configuration layer, artifact
registry, new bundle schema, compatibility logic, version bump or dependencies
unless an actual current operation requires one. Keep source/prepared files intact.
Routine function/file design belongs to the implementer.

Update this document with actual allowlist, counts, command/evidence and limitations;
README owns the reproduction command, roadmap owns progress. Reconcile active
spec/source wording only where necessary, using links rather than copying this
protocol throughout older milestone records. M2 findings remain historical evidence.

### Final gate: M3-final

One integrated final review is sufficient; at most two correction rounds. Acceptance:

- The documented command generates usable memberships on the current 829-cycle
  bundle without changing raw/prepared inputs or using targets to select rows.
- Each protocol/fold partitions every eligible unit exactly once into disjoint
  fit/tune, calibration and test roles. Primary tests contain precisely the held-out
  experiment; their union contains each unit once. Inner folds cover fit/tune only.
- Explicit predictor selection cannot accidentally include context/targets or newly
  retained columns. Feature membership and cutoff rationale are understandable.
- Synthetic tests prove split disjointness/coverage, outer-experiment separation,
  deterministic row-order-independent membership, inner-fold exclusion and explicit
  allowlisting. Avoid tests that merely repeat implementation constants.
- Independently check real role/group counts and selected memberships against the
  stated allocation rule. Run CI lint/format/type/tests and CLI smoke check; inspect
  documentation links and verify generated outputs stay outside Git. No training
  is necessary to pass M3.

Delivery uses one Sol Medium implementer with worker-only Ponytail guidance. Return
with writers stopped and custody released for review. No commit/push is authorized.

## Delivery evidence for final review

The README command generated the ignored
`artifacts/m03/injection_molding_memberships.parquet` artifact from the current
829-cycle prepared bundle without modifying prepared inputs. It contains 3,316
rows: 829 for each of three primary folds and 829 for the secondary ID fold.

Primary development allocations (`fit/tune`, calibration) are 242/61 for
experiment 15, 178/45 for experiment 20, and 242/61 for experiment 23 whenever
represented. Fold totals (`fit/tune`, calibration, test) are 420/106/303 for
holdout 15, 484/122/223 for holdout 20, and 420/106/303 for holdout 23. Secondary
ID experiment allocations (`fit/tune`, calibration, test) are 181/61/61,
133/45/45 and 181/61/61 respectively, totaling 495/167/167. Primary inner-fold
counts are 141/140/139 (holdout 15), 162/162/160 (holdout 20), and 141/140/139
(holdout 23); secondary counts are 167/164/164. These totals follow independent
`ceil(20%)` calculations from source group sizes 303/223/303. The primary test
union contains every unit once.

Focused synthetic tests cover disjoint/complete partitions, exact outer
experiment separation, row-order and unrelated-value independence, inner-fold
exclusion/balance, stable reused primary development memberships, and protection
against newly retained predictor columns. An independent reconstruction from the
prepared unit/context tables matched every generated role and inner-fold
assignment.

`uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, all 54
tests, `uv run mpi --version`, and the documented generator command pass with the
repository-local UV cache. Git ignore inspection resolves the generated artifact
to `artifacts/**`, and documentation links were checked against their local
targets. No models, derived trajectory features or performance claims were
produced.

M3-final passed after one simplification correction removed redundant prepared-schema
checks and row-construction plumbing without changing any memberships. Lead review
independently checked real partition counts, coverage and experiment separation.
The retrospective cutoff and ID-dependence limitations remain explicit. Next:
plan M4's scalar Mean, Ridge and PLS baselines using this contract.
