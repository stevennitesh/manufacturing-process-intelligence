# M4 — Scalar weight-prediction baselines

**Status:** complete.

## Outcome and scope

Mean, Ridge and PLS now provide reproducible scalar-only weight benchmarks before
trajectory features are introduced. The experiment follows the
[M3 feature and evaluation contract](m03-feature-and-evaluation-contract.md) and
[scientific scope](../spec.md#validation-and-feature-availability). It retains all
model/fold results, including poor shifted-regime performance.

The model matrix contains exactly M3's 16 native-value scalar predictors. Features,
weight targets and memberships are joined by unit identity before numeric selection;
row order, identifiers and context cannot enter training. Calibration rows are unused.
Outer labels only produce final metrics. No imputation, outlier removal, feature
selection, trajectory feature, conformal interval or serialized model is part of M4.

## Implemented experiment

Mean predicts the fit/tune target mean. Ridge evaluates alpha 0.1, 1, 10, 100 and
1000; PLS evaluates 1, 2, 4 and 8 components. Candidate selection is separate for
each protocol/fold using equal-weight mean inner-validation MAE, with the first
candidate winning an exact tie. Each selected model is refit on all fit/tune rows.

Ridge and PLS use a training-pipeline `StandardScaler`. Ridge fits an intercept;
PLS disables its own X scaling while retaining its standard internal centering.
All four folds selected Ridge alpha 0.1 and 8 PLS components. Candidate grids were
fixed before outer evaluation and were not expanded in response to these results.

The ignored `artifacts/m04/` output contains unit-keyed evaluation predictions,
per-fold metrics, and `run.json`. The run record retains source identity, the M3
membership reference, exact feature and candidate definitions, fold-specific
inner scores and selected parameters, summaries, and package versions.

## Results

Metrics are in grams except R². The primary folds are leave-one-experiment-out;
the secondary row is the separate within-experiment interpolation benchmark.

| Protocol / evaluation fold | Model | n | MAE | RMSE | R² |
| --- | --- | ---: | ---: | ---: | ---: |
| Primary / experiment 15 | Mean | 303 | 1.247356 | 1.359643 | -5.315083 |
| Primary / experiment 15 | Ridge | 303 | 1.133925 | 1.158351 | -3.583633 |
| Primary / experiment 15 | PLS | 303 | 0.421065 | 0.489175 | 0.182556 |
| Primary / experiment 20 | Mean | 223 | 0.530590 | 0.580595 | -0.033538 |
| Primary / experiment 20 | Ridge | 223 | 0.422031 | 0.485721 | 0.276642 |
| Primary / experiment 20 | PLS | 223 | 0.288870 | 0.351443 | 0.621305 |
| Primary / experiment 23 | Mean | 303 | 1.345954 | 1.360462 | -46.136632 |
| Primary / experiment 23 | Ridge | 303 | 1.199722 | 1.217764 | -36.766963 |
| Primary / experiment 23 | PLS | 303 | 0.798067 | 0.811999 | -15.791786 |
| Secondary ID | Mean | 167 | 0.739535 | 0.833803 | -0.000010 |
| Secondary ID | Ridge | 167 | 0.112408 | 0.150032 | 0.967622 |
| Secondary ID | PLS | 167 | 0.113669 | 0.151713 | 0.966893 |

| Model | Primary equal-fold mean MAE | Primary pooled sample-weighted MAE |
| --- | ---: | ---: |
| Mean | 1.041300 | 1.090584 |
| Ridge | 0.918559 | 0.966475 |
| PLS | 0.502668 | 0.523299 |

PLS has the lowest primary aggregate errors, but this is retained benchmark
evidence rather than an outer-selected deployment choice. Results vary sharply by
held-out experiment. In particular, every model has negative R² for experiment 23,
so even the lower PLS absolute error does not explain that fold's limited within-fold
weight variation well. The much lower secondary ID errors describe a different
fitted interpolation protocol and do not isolate or quantify a causal shift effect.

M2 inspected all experiment targets and associations, so these grouped folds are
not pristine prospective holdouts. Three experiments do not establish factory-wide
generalization. M4 residuals and outer errors do not authorize M5 feature invention
or M6 search changes; those choices remain pre-specified development decisions.

## Verification

The real command produced 12 model/fold metric rows. Primary predictions cover each
of 829 cycles exactly once per model; secondary predictions cover 167 cycles per
model. Repeated M4 runs reproduced selections and byte-identical numeric artifacts.

Focused synthetic tests exercise the actual training path and verify exact feature
selection, identity-aligned shuffled inputs, grouped primary inner validation,
calibration and evaluation exclusion, evaluation-feature isolation from fitting and
selection, training-local scaling, mean predictions, MAE/RMSE/R², and equal-fold
versus pooled aggregation. The locked dependency is scikit-learn 1.9.1 for the
recorded run. Repository lint, formatting, type checking, full tests, CLI smoke and
the real command pass (58 tests). A focused regression check rejects stale M3
mixed-experiment primary inner folds with an instruction to regenerate memberships.
Independent calculations reproduced all saved metrics, mean predictions and
population counts; this check did not change the candidate grids or results.

## Next step

Plan M5's bounded trajectory representations from the specified feature families
and development evidence, not from these outer-evaluation residuals.
