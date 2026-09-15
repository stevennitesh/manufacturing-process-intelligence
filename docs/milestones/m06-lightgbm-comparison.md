# M6 — LightGBM representation comparison

**Status:** complete; fixed search and real-data results verified.

## Purpose and scope

Test whether nonlinear modeling changes the benefit of the fixed trajectory
representations for Dataset 2 weight prediction under experiment shift. This adds
one model family to the personal portfolio experiment, not a modeling framework.
Follow the [spec](../spec.md#representation-and-models), unchanged
[M3 memberships](m03-feature-and-evaluation-contract.md), and exact
[M5 representations](m05-trajectory-representations.md#exact-representations).

Evaluate LightGBM separately on A, B, C-PCA and C-PLS. A is the matched scalar
LightGBM reference. Retain all results, including worse-than-baseline outcomes.
No new features, operating context, normalization choices or M4/M5 retuning.

## Fixed experiment decisions

Use CPU `LGBMRegressor` with squared-error objective (`regression`), `gbdt`,
learning rate 0.05, max depth -1, L1 penalty 0 and L2 penalty 1. Search the Cartesian
product of:

- `num_leaves`: 7, 15;
- `min_child_samples`: 10, 30;
- `n_estimators`: 100, 300.

These eight settings span modest tree complexity and boosting length at the small
development sample size. They are a bounded comparison, not an optimality claim.
No early stopping or extra validation carve-out. Use all rows/features per fit
(`subsample=1`, `subsample_freq=0`, `colsample_bytree=1`), seed 42, one CPU thread,
`deterministic=True`, `force_col_wise=True`; other parameters retain pinned-library
defaults. Record the installed version and effective estimator parameters.
These controls follow the [LightGBM API](https://lightgbm.readthedocs.io/en/stable/pythonapi/lightgbm.LGBMRegressor.html)
and [determinism guidance](https://lightgbm.readthedocs.io/en/stable/Parameters.html#deterministic).
Reproducibility means the same locked local environment, not bitwise equivalence
across operating systems or library versions.

C jointly searches the same M5 component counts 2, 4, 8 with those eight settings
(24 candidates per compressed representation). Retain M5's fold-local trajectory
column scaling, full-SVD PCA / supervised PLS, and combined-matrix scaling for all
representations. Scaling is retained to reuse exactly the existing representation
path, not because trees require it. Do not reuse M5 Ridge-selected component counts
or fitted compressors. Reuse computed training-partition transformations across
tree settings where convenient; no persistent preprocessing cache.

Candidate order is ascending components (A/B have none), then leaves, minimum
child samples and tree count. Select the lowest equal-weight mean inner MAE within
each representation/protocol/outer fold; first exact tie wins. Primary uses two
leave-one-development-experiment-out folds, secondary ID uses M3's three folds.
Fit all learned transformations and LightGBM only on inner training rows during
selection. Refit selected settings on all fit/tune rows, then predict evaluation
rows. Calibration remains unused; outer labels only enter final metrics.

## Results and interpretation

Save ignored unit-keyed predictions, 16 representation/fold metric rows and a run
record under `artifacts/m06/`, following the existing small local output convention.
Include source/membership identity, feature-definition reference, fixed search,
inner candidate scores, selected settings and package versions.

Report primary per-experiment MAE/RMSE/R²/counts, equal-fold mean MAE, and pooled
sample-weighted primary MAE. Show delta MAE = LightGBM A minus augmentation per
primary fold and equal-fold mean. Keep pooled secondary ID and per-experiment ID
metrics separate. Compare with the existing M4 scalar PLS and M5 Ridge results
descriptively, without rerunning or modifying them.

There is no global winner selected by outer performance in M6. Preserve development
scores for subsequent model-selection decisions; the M7 plan must specify its
development-only selection policy before uncertainty evaluation. Better outer
scores may describe evidence, not authorize a deployment choice or another search.

M2 explored all three groups, so this remains grouped cross-validation, not a
pristine prospective holdout. Nonlinear improvement supports usefulness of the
tested features/model combination; lack of improvement cannot uniquely diagnose
concept shift, missing context or representation failure. ID-only improvement is
not proof that features merely encode regime identity. Three experiments and the
small predefined searches limit conclusions. No exploratory feature pass is a gate.

## Delivery and verification

1. Add the LightGBM dependency and locked environment entry. Reuse M5's extraction,
   fold-local preparation and actual shared reporting where this avoids duplication;
   routine helper organization is flexible. No registry, generic configuration
   engine, tuning service, model serialization or new CLI framework.
2. Implement one reproducible runner and bounded selection/evaluation path. Keep
   M4/M5 behavior and saved results unchanged when sharing helpers.
3. Verify and run the fixed real-data experiment; record results/limits here and
   update README/roadmap. Completed records describe the project, not delivery roles.

Focused synthetic evidence must exercise the public runner's wiring, preserve unit
alignment under row shuffling, and show that calibration/evaluation labels cannot
change selection or predictions. Demonstrate train-local compression and supervised
PLS label boundaries using existing valid tests plus focused integration checks.
Independently fit a small direct LightGBM reference from an explicitly constructed
training matrix to verify selected parameters and predictions; recalculate saved
metrics/deltas independently. If numerical transformations change, compare against
M5/reference calculations. Do not duplicate unchanged numerical tests.

Run the repository CI commands plus the real Dataset 2 workflow; compare repeated
local results at numerical tolerance (1e-10 for predictions/metrics). Full real-data
training stays out of CI. Scientific success does not require improved MAE; a
correctly bounded negative result completes M6. Conformal prediction and uncertainty
ranking belong to M7, not this delivery.

## Completed results

The fixed real-data run wrote 3,984 unit-keyed predictions, all 16
representation/fold metric rows and the full candidate record under ignored
`artifacts/m06/`. LightGBM 4.7.0 was installed from the locked environment. Primary
results were:

| Representation | Holdout 15 MAE / RMSE / R² (n=303) | Holdout 20 MAE / RMSE / R² (n=223) | Holdout 23 MAE / RMSE / R² (n=303) | Equal-fold MAE | Pooled MAE | Equal-fold delta vs A |
|---|---:|---:|---:|---:|---:|---:|
| A | 0.868994 / 0.893925 / -1.729803 | 0.468671 / 0.543928 / 0.092882 | 0.566511 / 0.597799 / -8.101153 | 0.634726 | 0.650750 | 0.000000 |
| B | 0.797282 / 0.828049 / -1.342293 | 0.508679 / 0.573876 / -0.009758 | 0.567159 / 0.598928 / -8.135561 | 0.624374 | 0.635538 | +0.010352 |
| C-PCA | 0.870128 / 0.896805 / -1.747420 | 0.418281 / 0.492377 / 0.256681 | 0.625394 / 0.653957 / -9.891399 | 0.637934 | 0.659131 | -0.003209 |
| C-PLS | 0.964066 / 0.984001 / -2.307654 | 0.431139 / 0.486363 / 0.274728 | 0.552575 / 0.587112 / -7.778658 | 0.649260 | 0.670309 | -0.014535 |

The pooled secondary ID MAEs were 0.052297 g for A, 0.047490 g for B,
0.055338 g for C-PCA and 0.052049 g for C-PLS. The run record keeps those pooled
metrics separate from per-experiment ID metrics for experiments 15, 20 and 23.

B produced the only positive equal-fold trajectory delta over LightGBM A, and that
0.010352 g change was heterogeneous: B improved holdout 15 but was worse on
holdouts 20 and 23. Compression did not improve the equal-fold LightGBM result,
although both compressed representations improved on holdout 20 and C-PLS improved
on holdout 23. These are outer evaluation findings, not a global representation
selection.

Relative to the earlier model families, scalar LightGBM A improved on M5 Ridge A
(0.634726 versus 0.918559 g equal-fold MAE), and LightGBM C-PLS improved on M5
Ridge C-PLS (0.649260 versus 0.704219 g). M4 scalar PLS remained lower at
0.502668 g. These are descriptive comparisons on identical M3 evaluation
memberships, not causal attributions; they do not change any M4/M5 results or
select a winner for M7. Primary-versus-ID results remain separate protocols rather
than paired shift estimates.

Focused synthetic tests exercise the public runner, shuffled-row identity
alignment, exclusion of calibration/evaluation labels from selection and
predictions, exact fixed-grid order, and a direct independently constructed
LightGBM reference. Existing M5 tests continue to cover train-local PCA/PLS and
the supervised PLS label boundary. Two complete real-data runs matched exactly
(maximum prediction and metric difference 0.0, within the required 1e-10
tolerance). The locked dependency, all candidate scores, selected settings,
effective estimator parameters, package versions, source/membership identity,
preprocessing and limitations are recorded in `run.json`.

`uv sync --locked --group dev`, `uv run ruff check .`,
`uv run ruff format --check .`, `uv run pyright`, all 69 tests, and
`uv run mpi --version` pass with the repository-local UV cache. Local Markdown
links resolve to tracked targets, and `git diff --check` reports no whitespace
errors.

The findings remain limited by three experiments, prior M2 exploration, a small
fixed grid and large primary fold variation including negative R². Better ID
performance does not diagnose regime encoding, and the experiment does not isolate
concept shift, missing operating context or representation failure. M7 must define
its development-only selection policy before uncertainty evaluation; no M7 model
choice or conformal implementation is made here.
