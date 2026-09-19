# M7 — Uncertainty under experiment shift

**Status:** complete; choices below preceded M7 calibration and evaluation.

## Purpose and boundaries

Quantify how well nominal prediction intervals cover part weight in represented
versus held-out experiments, and test whether one simple process-distance score
is useful enough for the optional selective-measurement study. Follow the
[uncertainty contract](../spec.md#uncertainty-and-measurement-policy) and unchanged
[M3 memberships](m03-feature-and-evaluation-contract.md).

Use only the 16 allowed scalars. Scalar PLS and scalar LightGBM give two contrasting
model families with existing code and small searches. This scope choice is made
after M4–M6 exploration for simplicity; it is not a retrospectively pristine model
shortlist. No new model family, trajectory feature, context ablation, normalized
conformal method, uncertainty ensemble or additional data partition is required.

## Fixed model-selection policy

Within each primary outer fold and the separate secondary ID protocol, jointly
choose among M4 scalar PLS components 1, 2, 4, 8 and M6 scalar LightGBM's eight
unchanged settings. Use equal-weight mean inner-validation MAE: two development
experiment folds for primary, three existing inner folds for ID. Candidate order
is PLS ascending components, then LightGBM in M6 grid order; first exact tie wins.
All scaling/model fitting is inner-training-only. Reuse existing estimator settings,
not previous outer scores or serialized results, for this selection.

Retain the selected candidate's out-of-fold development predictions and candidate
inner scores. Refit that candidate once on all fit/tune rows; use the same fitted
pipeline for calibration and evaluation predictions. Neither calibration nor
evaluation labels/features affect candidate selection or fitting. Calibration labels
are used only for the interval radius below. No global outer-selected winner.

## Split-conformal baseline

Fix nominal coverage at 90% (alpha=0.10); do not search coverage levels. From the
selected fitted model's calibration absolute errors, take order statistic
`k = ceil((n_cal + 1) * 0.90)` (one-based) and `q = sorted_errors[k - 1]`.
Use this exact order statistic, not an interpolated percentile. The bounded runner
requires k <= n_cal (at least nine calibration rows); otherwise report insufficient
calibration for a finite interval rather than clipping k. Actual M3 folds satisfy it.
Predict `[prediction - q, prediction + q]`, with inclusive endpoints, in grams.

Report nominal/empirical coverage, mean/median width, evaluation count and point
MAE/RMSE/R² for each primary fold and pooled secondary ID, plus per-experiment ID
metrics. Include primary equal-fold and pooled sample-weighted summaries, clearly
labeled. No calibration-set coverage is presented as evaluation performance.
Radius and width are constant within a fitted fold: these intervals cannot rank
cycles or automatically widen for unusual inputs.

The [split-conformal reference](https://arxiv.org/html/2107.07511v6) describes
finite-sample marginal coverage under exchangeability. Experimental shift and
adjacent-cycle dependence mean this project must measure coverage, not promise it.
ID and primary results use different fitted pipelines/populations: their comparison
is descriptive, not a paired causal effect of shift or conditional coverage claim.

## One fixed error-ranking screen

Score each query by mean Euclidean distance to its five nearest training cycles
in the 16-scalar space. Fit StandardScaler on the applicable training partition;
use the same transformation on queries and no targets in the distance calculation.
Require at least five training rows. Keep constant-column behavior from StandardScaler.
No distance normalization search, feature reweighting, PCA or Mahalanobis inverse.
Correlated temperature channels can dominate this metric; record that limitation.

During development, each inner validation cycle is scored against only its inner
training rows and paired with the selected candidate's corresponding out-of-fold
absolute error. There are no self-neighbors. Within each inner validation block,
retain `ceil(0.75 * n)` lowest-distance cycles, breaking distance ties by unit_id.
Record full MAE, retained MAE/count and relative reduction
`1 - retained_MAE / full_MAE`. A zero full MAE has no improvable risk and fails the
screen. Average reductions equally across inner blocks within an outer fold.

The M8 gate passes only if every one of the three primary outer folds has at least
10% mean development reduction. Report ID's analogous screen separately; it cannot
rescue a primary failure. This conservative practical screen is not a significance
test or an operational threshold. Model selection reuses these validation labels,
so the selected candidate's development diagnostic is selection-affected and may
be optimistic. Overlapping development folds are not independent replications.
It is a limited go/no-go screen, not evidence of deployed measurement savings.

Compute all development screens and the gate before calibration/outer evaluation.
For evaluation cycles, save distances against the full fit/tune population with
its training-only scaler, regardless of gate result. Do not use calibration errors,
outer errors, or interval width to alter the distance or gate. M8's outer risk-
coverage curves/random benchmark are not implemented here. If the gate fails,
document that this score is unsupported for the intended study, skip M8 and move
toward M9/M10; do not try additional scores to obtain a pass. A pass only makes M8
eligible for subsequent planning, not automatically implemented or validated.

## Delivery and evidence

1. Implement a small scalar selection/conformal/distance workflow using current
   model builders and row joins. No generic uncertainty framework or new dependency.
2. Add one reproducible script and ignored `artifacts/m07/` outputs: evaluation
   predictions/intervals/distances, selected-candidate development predictions and
   distances, metrics and a compact run record. Include selected settings, all
   inner scores, calibration counts/radii, screen decisions and source/membership
   identity. No fitted-model serialization or new artifact registry.
3. Run the fixed experiment, record findings/limits here and update README/roadmap
   with the conditional next step. Preserve M4–M6 data, outputs and scientific rules.

Focused synthetic checks must distinguish real failures: independent order-statistic
interval/coverage calculations (including ties and insufficient calibration), direct
distance/scaling comparison, identity alignment under shuffling, and the actual
selection/refit path with nonconstant predictors. Verify that calibration-label
changes can change q but not the selected model, point predictions, distance or
development gate; evaluation-label changes can affect only evaluation metrics.
Changing held-out features cannot change selection or training transformations.
Test both passing/failing ranking screens and deterministic retained counts/ties.
Use existing estimator tests for unchanged fitting behavior, not duplicated suites.

Run CI commands and one repeatable real workflow. Independently recalculate saved
coverage/width, order-statistic radii and screen decisions; compare repeated numeric
results within 1e-10. Real training stays outside CI. Poor empirical coverage or a
failed ranking screen is a valid completed result, not permission for more tuning.

## Implemented result

The fixed workflow selected scalar LightGBM with 15 leaves, minimum child size 10
and 100 trees for primary holdouts 15 and 20; it selected eight-component scalar
PLS for holdout 23. The separate ID protocol selected scalar LightGBM with 15
leaves, minimum child size 10 and 300 trees. These are fold-local development
choices, not an outer-selected global winner.

| Evaluation population | n | Radius (g) | Coverage | Mean/median width (g) | MAE (g) | RMSE (g) | R² |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Primary holdout experiment 15 | 303 | 0.093914 | 0.000 | 0.187828 | 0.868994 | 0.893925 | -1.729803 |
| Primary holdout experiment 20 | 223 | 0.134603 | 0.188 | 0.269206 | 0.468671 | 0.543928 | 0.092882 |
| Primary holdout experiment 23 | 303 | 0.275215 | 0.003 | 0.550430 | 0.798067 | 0.811999 | -15.791786 |
| Secondary ID pooled | 167 | 0.097238 | 0.862 | 0.194476 | 0.052297 | 0.081571 | 0.990429 |
| ID experiment 15 | 61 | 0.097238 | 0.902 | 0.194476 | 0.053945 | 0.090544 | 0.972116 |
| ID experiment 20 | 45 | 0.097238 | 0.844 | 0.194476 | 0.049007 | 0.083047 | 0.977102 |
| ID experiment 23 | 61 | 0.097238 | 0.836 | 0.194476 | 0.053077 | 0.070214 | 0.799538 |

Primary equal-fold mean coverage is 0.064 and pooled sample-weighted coverage is
0.052. Equal-fold mean width is 0.335822 g; pooled mean width is 0.342250 g.
Equal-fold mean MAE is 0.711911 g and pooled MAE is 0.735384 g. The nominal 90%
intervals therefore fail badly under held-out-experiment shift, while pooled ID
coverage is closer to nominal but still below it. This is measured performance
under different protocols, not a paired causal estimate or conditional coverage.

## Development screen and next step

Mean development error reductions after retaining the lowest-distance 75% were
19.66% for primary holdout 15, 4.31% for holdout 20 and 16.31% for holdout 23.
Because every primary fold had to reach 10%, the gate failed. The analogous ID
screen reduced mean development error by 5.68% and also failed; it could not rescue
the primary result. The selected-candidate validation labels were reused in this
screen, so these already insufficient values are optimistic screening evidence,
not independent proof.

The fixed five-neighbor standardized Euclidean distance is unsupported for the
intended selective-measurement study. M8 is skipped, with no search for another
uncertainty score. Continue to bounded predictive explanation and the dashboard in
M9/M10 while presenting interval failures and the negative gate result directly.
This is failure of the pre-specified conservative criterion, not proof that the
distance score has no utility in every population or use case.
The final cross-milestone interpretation and proposed path to broader operating-
condition coverage are consolidated in [M10](m10-dashboard.md#consolidated-interpretation).

## Reproduction and verification

`uv run python scripts/run_uncertainty_shift.py` writes ignored evaluation,
development and calibration predictions, metrics and a compact run record under
`artifacts/m07/`. Calibration absolute errors are retained so every finite order-
statistic radius can be checked without serialized models. A repeated real run
matched every saved numeric value exactly. An independent calculation reproduced
the four radii, interval coverage/width, point metrics and all screen decisions.

Focused synthetic checks cover order-statistic ties and insufficient calibration,
direct standardized five-neighbor distances, deterministic retained counts and
identity tie-breaking, passing/failing/zero-error screens, shuffled identity
alignment, nonconstant predictors and the actual selection/refit path. Calibration-
label changes alter the radius but not selection, point predictions, distance or
the gate; evaluation labels affect only evaluation results; held-out features do
not change selection or training transformations. Repository CI commands and the
CLI smoke test pass in the locked environment.
