# M5 — Trajectory representations

**Status:** complete; definitions below were fixed before M5 outer evaluation.

## Purpose and contract

Test whether pressure/flow trajectories improve part-weight prediction beyond the
16 scalars under experiment shift. This is a bounded portfolio experiment, not a
feature platform. Follow [M3](m03-feature-and-evaluation-contract.md) unchanged and
the [representation scope](../spec.md#representation-and-models).

Compare A (scalars), B (scalars plus engineered summaries), C-PCA and C-PLS
(scalars plus compressed trajectories). All use Ridge downstream, with M4's alpha
grid 0.1, 1, 10, 100, 1000. Ridge provides a simple common comparator; choosing it
does not claim it beat M4 PLS. Retain M4 results unchanged and reproduce its Ridge
reference. Do not select a representation by its outer score.

### Exact representations

Align trajectories by unit identity and sample index before converting to arrays.
Keep all 2,048 native samples and actual elapsed times; no resampling or padding.
For each of pressure and flow, B adds these 13 summaries (26 total):

- Arithmetic sample mean and population standard deviation (ddof=0).
- Maximum and elapsed time of its first occurrence.
- Sample quantiles 0.10, 0.50, 0.90, using linear interpolation.
- Full-record trapezoidal AUC using actual elapsed times.
- Maximum and minimum adjacent difference divided by elapsed-time difference:
  signed steepest rise/fall summaries, not verified physical-phase slopes.
- Three trapezoidal segment integrals on [0, 4.092], [4.092, 8.184],
  [8.184, 12.276] seconds. Include endpoints, linearly interpolating at a boundary
  if absent. These fixed equal-duration windows are not named molding phases.

Mean/std/quantiles are sample-weighted, not time-weighted. Amplitudes retain native
unknown units; integrals are native amplitude-seconds, not claimed volume/energy.

C concatenates pressure then flow samples into 4,096 predictors. Standardize each
sample-position column using training rows only, then fit joint PCA or supervised
PLS on that trajectory block. Candidate component counts are 2, 4, 8 for each.
PCA uses deterministic full SVD; PLS disables its own scaling after the scaler.
PLS uses only training weight labels and returns X scores at prediction time.
Concatenate scores with the 16 scalars, then training-standardize this combined
matrix before Ridge. A/B likewise standardize their full matrix before Ridge.
No whitening, time weighting, channel/feature selection or extra compression grid.

This compares these specific representations, not every possible trajectory model.
Column scaling balances native signal units but can emphasize low-variance samples;
retain that limitation rather than adding another scaling search.

### Selection and evaluation

Reuse exact M3 memberships, including two experiment-aware primary inner folds and
three secondary ID inner folds. Select alpha (and C component count jointly) by
equal-weight mean inner MAE. Candidate order is ascending components then ascending
alpha; first exact tie wins. Fit scalers and compression separately inside each
inner training partition, then refit the selected pipeline on all fit/tune rows.
Calibration remains unused. Never fit preprocessing/compression on all units.

Report each representation's primary per-experiment MAE/RMSE/R² and equal-fold
mean MAE, plus per-fold and equal-fold delta MAE = A minus augmented. Keep pooled
secondary ID and per-experiment ID metrics distinct from primary results. Preserve
all candidates' inner scores and selected settings; a negative result is complete.
M2 explored all groups, so this is grouped cross-validation, not an untouched
prospective test. No features/offsets/grid expansions derived from M4 experiment-23
errors or M5 outer results. No causal or factory-wide generalization claim.

## Delivery approach and evidence

1. Implement bounded feature extraction and fold-local representations, reusing
   M4's actual shared evaluation behavior where useful. Keep routine internal
   organization flexible; no generic model registry/configuration framework.
2. Add one reproducible runner and ignored M5 predictions, metrics and run record
   with definitions, selections, source/membership identity and comparisons.
3. Verify, run the fixed experiment, and record its results and limitations here;
   update README and roadmap. No new dependency is expected.

Focused evidence must include shuffled signal/scalar row invariance; independently
calculated irregular-grid AUC, segment boundaries and slope/quantile summaries;
training-only scaling and PCA/PLS (including supervised label isolation); unchanged
selection/predictions when calibration or outer labels are perturbed; and matched
scalar Ridge predictions against M4. Use synthetic checks for CI, with independent
small reference calculations for numerical transformations. Run CI commands and
the real Dataset 2 workflow locally; retain full training outside CI.

LightGBM is M6. Conformal/selective prediction, plots/dashboard expansion, new
source-unit research, model serialization and further M4 tuning are outside M5.

## Implemented results

The fixed experiment writes ignored unit-keyed predictions, fold metrics and a
run record under `artifacts/m05/`. Positive delta means the augmented representation
reduced MAE relative to A in that fold. Metrics are grams except R².

| Protocol / evaluation fold | Representation | Components | Alpha | MAE | RMSE | R² | Delta MAE vs A |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Primary / experiment 15 | A | — | 0.1 | 1.133925 | 1.158351 | -3.583633 | 0.000000 |
| Primary / experiment 15 | B | — | 1000 | 3.859171 | 3.888092 | -50.641919 | -2.725246 |
| Primary / experiment 15 | C-PCA | 8 | 10 | 0.337317 | 0.397513 | 0.460202 | 0.796608 |
| Primary / experiment 15 | C-PLS | 8 | 10 | 0.444272 | 0.513074 | 0.100732 | 0.689653 |
| Primary / experiment 20 | A | — | 0.1 | 0.422031 | 0.485721 | 0.276642 | 0.000000 |
| Primary / experiment 20 | B | — | 0.1 | 0.183668 | 0.213344 | 0.860446 | 0.238364 |
| Primary / experiment 20 | C-PCA | 8 | 10 | 0.989944 | 1.029983 | -2.252677 | -0.567913 |
| Primary / experiment 20 | C-PLS | 8 | 0.1 | 0.370924 | 0.404580 | 0.498133 | 0.051107 |
| Primary / experiment 23 | A | — | 0.1 | 1.199722 | 1.217764 | -36.766963 | 0.000000 |
| Primary / experiment 23 | B | — | 0.1 | 0.329340 | 0.365853 | -2.408786 | 0.870381 |
| Primary / experiment 23 | C-PCA | 4 | 0.1 | 1.813708 | 1.823162 | -83.651739 | -0.613986 |
| Primary / experiment 23 | C-PLS | 2 | 0.1 | 1.297462 | 1.308689 | -42.617244 | -0.097740 |
| Pooled secondary ID | A | — | 0.1 | 0.112408 | 0.150032 | 0.967622 | 0.000000 |
| Pooled secondary ID | B | — | 0.1 | 0.079283 | 0.103198 | 0.984681 | 0.033125 |
| Pooled secondary ID | C-PCA | 8 | 0.1 | 0.084815 | 0.114263 | 0.981220 | 0.027593 |
| Pooled secondary ID | C-PLS | 8 | 0.1 | 0.057142 | 0.071187 | 0.992711 | 0.055266 |

| Representation | Primary equal-fold mean MAE | Equal-fold delta vs A |
| --- | ---: | ---: |
| A | 0.918559 | 0.000000 |
| B | 1.457393 | -0.538834 |
| C-PCA | 1.046989 | -0.128430 |
| C-PLS | 0.704219 | 0.214340 |

C-PLS has the lowest aggregate primary MAE among these representations, but that
is outer evaluation evidence rather than a representation selection: its experiment-23
MAE is worse than A and its R² is strongly negative. B improves experiments 20 and
23 but fails badly on experiment 15; C-PCA improves only experiment 15 and worsens
experiments 20 and 23. C-PLS's 0.704219 g aggregate does not beat M4 scalar PLS's
0.502668 g; the matched Ridge comparison isolates the tested augmentation rather
than establishing superiority to the strongest prior scalar baseline. The pooled
secondary ID metrics are lower for every augmentation, but remain a distinct
within-regime interpolation benchmark. Per-experiment secondary metrics are retained
in `run.json`; C-PLS ID MAE is 0.046289, 0.062931 and 0.063723 g for experiments
15, 20 and 23, while corresponding R² is 0.988362, 0.979714 and 0.758298.

## Verification and limitations

The real run retained 16 metric rows and 3,316 primary prediction rows (829 units
per representation), plus 668 secondary prediction rows. A reproduced M4 Ridge's
selected alpha and predictions. Focused synthetic tests independently calculate
irregular-grid AUC, linearly interpolated segment integrals, slopes and quantiles;
verify shuffled signal/scalar row invariance; and match an independently assembled
training-local PLS/scaling/Ridge calculation. Perturbing calibration and outer
labels leaves supervised selection unchanged. An independent NumPy SVD plus
closed-form Ridge reconstruction matched C-PCA predictions on a synthetic fixture
within `4.44e-15`.
Repository CI checks and the real command pass in the locked environment.

The comparison is confined to the pre-specified summaries, scaling, component
counts and Ridge grid. Scaling 4,096 sample-position columns can emphasize low-variance
positions. Three explored experiments and two primary inner groups provide limited
shift evidence; none of the representations establishes prospective, causal or
factory-wide generalization. M6 may compare its pre-specified model scope, but these
outer results do not authorize new feature or grid tuning.
