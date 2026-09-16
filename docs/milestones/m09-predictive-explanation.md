# M9 — Bounded predictive explanation

**Status:** complete.

## Purpose and scope

Describe which scalar inputs the existing M7 models rely on and where evaluation
features lie outside their training ranges. These are post-hoc explanations for
the portfolio, not new modeling or evidence of physical causes. Follow the
[explanation scope](../spec.md#explanation-dashboard-and-release) and
[M7 results](m07-uncertainty-and-shift.md). M8 remains skipped.

Deliver two small tables: permutation importance and feature-support summaries.
No SHAP, PLS loading study, latent-space visualization, new uncertainty score,
feature selection, model search or dashboard implementation in this milestone.

## Models and evaluation populations

Read the four selected candidate settings from M7's `run.json`; refit each once
using its original M3 fit/tune rows and existing scalar pipeline. Do not rerun
candidate selection. Calibration rows remain unused. Use the saved M7 evaluation
predictions as a unit-keyed reference: refitted predictions must reproduce them
within 1e-10 before reporting explanations. Check the M7 source and membership
identity against the actual inputs; a mismatched run needs regeneration, not a
compatibility path or artifact registry.

Use six evaluation populations: the three primary held-out experiments and the
three experiment subsets of the secondary ID evaluation. ID subsets use the same
ID-fitted model. Sort by unit_id before deterministic permutation. Do not shuffle
across ID experiment boundaries or present a pooled importance that rewards regime
recognition. Record model/settings, counts and unpermuted MAE with each population.

## Permutation importance

For each of the 16 allowed raw scalar columns, use ten repeated permutations
within its evaluation population, seed 42, single-threaded. Use the existing
fitted preprocessing/model pipeline without fitting anything on shuffled inputs.
Importance is `MAE_permuted - MAE_original` in grams: positive means perturbation
increased error. Use scikit-learn's `permutation_importance` with
`scoring="neg_mean_absolute_error"`, `n_repeats=10`, `random_state=42`, `n_jobs=1`.
Retain all mean importance values, population standard deviations across repeats,
and repeat values; do not clip negative importance or turn it into percentages.
The standard deviation describes permutation variability, not a confidence interval.

As the [method documentation](https://scikit-learn.org/stable/modules/permutation_importance.html)
warns, importance describes a particular fitted model on a particular population,
not intrinsic feature value. Correlated heating channels can substitute for each
other; shuffling can create implausible combinations. Low/negative importance for
a poorly transferring model does not establish an unimportant physical variable.
Different primary folds use different fitted models and sometimes different model
families, so differences do not isolate a change in the physical relationship.

## Feature-support diagnostic

For each scalar and those same six populations, use only the corresponding
fit/tune rows to compute training minimum, maximum, mean and population standard
deviation (ddof=0). Save evaluation mean, fraction strictly below/above the training
range, their sum, and signed standardized mean shift:
`(evaluation_mean - training_mean) / training_std`.
Equality to a range endpoint is in range. For zero training standard deviation,
record standardized shift as null plus a constant-training-feature flag; retain
range fractions. No artificial epsilon or invented units.

These marginal observed ranges are not full multivariate support, product limits,
invalid-data thresholds or a new OOD decision rule. Co-occurring shift and error
do not identify the cause of M7's coverage failures. No model changes follow from
the diagnostic in v0.1.

## Delivery and verification

1. Reuse current scalar assembly/model builders with minimal helper exposure if
   needed; keep one short explanation module and reproducible script. No new
   dependency, generic attribution framework or model serialization.
2. Write ignored `artifacts/m09/` permutation/support Parquets and a compact run
   record with M7 reference, source/membership identity, selected settings, seed,
   repeats and population baseline metrics. The tables have 96 rows each; repeat
   values may live in the importance table rather than a separate artifact.
3. Record a few concrete findings and limitations here; update README/roadmap.
   M10 owns presentation charts and the dashboard. M4–M7 results remain unchanged.

Focused synthetic tests: a known predictor with a relevant and irrelevant feature
to check importance sign/value against an independent permutation calculation;
analytic support calculations including boundary equality and zero variance; and
the ordinary runner's unit alignment, population separation and same-model refit.
Evaluation labels may change importance but not fitted predictions or support;
calibration labels must affect neither output. Reuse existing model tests.

Run repository CI checks and the real workflow. Independently recalculate support
statistics and at least one importance result, verify all baseline predictions
against M7, and repeat the local run within 1e-10 numerical tolerance. Preserve
negative/near-zero findings without extra attribution methods. Full real training
stays out of CI. Completion leads to M10, not another model or feature experiment.

## Results

The reproducible run produced six evaluation populations and 96 rows in each
table. All four refitted pipelines reproduced the saved M7 predictions exactly
in the locked environment (maximum absolute difference 0 g). Primary baseline
MAEs remained 0.868994 g for experiment 15, 0.468671 g for experiment 20 and
0.798067 g for experiment 23. The three separate ID experiment MAEs were
0.053945 g, 0.049007 g and 0.053077 g for experiments 15, 20 and 23.

Switchover injection pressure had the largest mean permutation importance in the
ID experiment-15 and experiment-20 populations (0.354698 g and 0.425020 g) and
in primary holdout experiment 20 (0.198389 g). The ID patterns were not uniform:
injection time led experiment 23 at 0.069479 g. Forty of the 96 mean importances
were negative and were retained; the shifted primary models in particular should
not be interpreted from a ranked list alone when their baseline errors are large.

Marginal support differed sharply under experiment shift. Every evaluation row
in primary experiment 15 lay outside the fit/tune range for actual back pressure
and cycle duration. Every row in primary experiment 23 lay outside the training
range for all eight barrel-heating zones, injection time, maximum injection
pressure and switchover injection pressure. Primary experiment 20 also placed
92.8% of actual-back-pressure values outside its training range. In contrast, the
largest ID outside-range fraction was 4.9%. These values describe one-dimensional
observed ranges only; they do not establish multivariate support, invalid operation,
causality or an explanation for M7's interval-coverage failure.

## Verification evidence

The locked real-data workflow completed twice with identical output tables and
run parameters. Independent calculations reproduced the analytic support fields
and a seeded permutation-importance repeat sequence. Focused tests cover range
endpoint equality, zero training variance, unit alignment, six-population
separation, one refit per saved M7 fold, evaluation/calibration label boundaries,
and preservation of negative values. Repository lint, formatting, strict type
checking, tests and the CLI smoke check pass. M4–M7 artifacts were not modified.
