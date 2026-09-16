# M10 — Offline portfolio dashboard

**Status:** complete.

## Purpose and accepted scope

Give a portfolio reviewer a clear, runnable account of Dataset 2: strong prediction
within represented regimes did not translate into reliable unseen-regime results.
Present existing evidence, not another modeling experiment. The
[specification](../spec.md#explanation-dashboard-and-release) owns release scope;
[M7](m07-uncertainty-and-shift.md) and [M9](m09-predictive-explanation.md) own
uncertainty and explanation interpretation.

One local Streamlit application with Plotly figures, reading the prepared bundle
and saved M4–M7/M9 artifacts. No training, downloads, artifact writes or remote
services during dashboard use. Missing inputs show actionable reproduction commands,
not a fabricated demo or automatic pipeline run. Existing README commands remain
the reproduction workflow. No authentication, database, configurable dashboard
framework, new analytics, deployment, model persistence or compatibility layer.

## Three tabs

1. **Data & process:** explain machine telemetry → part weight; show experiment
   counts and weight distributions, plus selectable pressure/flow cycle examples
   against their native elapsed-time grid. Identify weight in grams and unknown
   signal amplitudes as native units. Experiments are not calendar days.
2. **Prediction & generalization:** lead with primary equal-fold MAE versus
   separately labeled pooled ID MAE. Show scalar baselines and matched Ridge/
   LightGBM representation comparisons without selecting a universal winner.
   Allow per-experiment metrics and actual-versus-predicted inspection. Keep ID
   per-experiment results available, not just its pooled R². Include a small
   selectable M9 population-specific importance view, retaining negative values
   and warning that correlated inputs and poor transfer complicate interpretation.
3. **Reliability under shift:** show 90% nominal and empirical coverage by
   population, widths and illustrative saved intervals. Put M9 outside-training-
   range fractions in a feature-by-experiment heatmap nearby, with ID subsets
   available for contrast. Explain the failed development distance gate and M8
   skip; do not invent selective-measurement curves or a support-based policy.

## Scientific presentation

- Derive displayed values from saved data, including any presentation-only grouping;
  do not maintain a second hand-entered results table. Preserve unit joins and
  distinguish model/representation/protocol/population selectors.
- Primary headline is equal-fold MAE; any pooled primary value is sample-weighted
  and explicitly labeled. ID-versus-primary compares different fitted pipelines,
  not a paired estimate of the effect of shift. M2 inspected all experiments.
- Show small nonzero coverage accurately (experiment 23 is approximately 0.3%,
  not 0%). Distinguish pooled ID coverage from per-experiment coverage.
- Observed marginal range departures are neither full distributional support nor
  causal explanations or product limits. If a maximum range fraction is summarized,
  name the features/populations over which that maximum was taken.
- Feature shift co-occurs with errors; it has not been established as their dominant
  cause. No physical RCA, PASS/FAIL, manufacturing specification or deployment claim.
- Negative results are legitimate findings. No new features, scores or model search.

## Delivery approach

Build the smallest application and a few direct presentation helpers where they
make data selection/aggregation independently testable. Add Streamlit/Plotly to
the locked environment; keep raw data and generated artifacts ignored. Reuse
existing metric functions where practical, without changing the modeling code.
Update README launch/prerequisite instructions and the roadmap. Keep package
versions and Git tags unchanged; release publication is a separate user action.

One final integrated review covers the runnable dashboard and documented workflow;
there is no costly intermediate interface requiring a separate checkpoint.

## Acceptance and evidence

- Local launch renders all three tabs from existing real artifacts without model
  fitting or source mutation. Exercise selectors and inspect representative charts
  at desktop size for readable labels, legends and units.
- Focused synthetic tests distinguish equal-fold from pooled aggregation, preserve
  protocol/experiment identity and small nonzero coverage, and cover the ordinary
  app path plus useful missing-input guidance. Prefer Streamlit's app testing to
  a separate browser automation dependency. No full training in CI.
- Independently reconcile representative displayed metrics with saved predictions
  or artifact rows, including per-experiment ID results and the support heatmap.
- Run existing CI checks and a real-data application smoke test. Record any actual
  visual-verification gap rather than treating a server-health response as proof
  that the dashboard renders correctly.
- Finish this record with implementation, verification, limitations and next step.

## Implementation

`src/mpi/dashboard.py` provides the single offline Streamlit entry point. It loads
the prepared Dataset 2 bundle and saved M4-M7/M9 Parquet/JSON outputs directly,
then renders the three accepted tabs with Plotly. Small presentation helpers own
the independently tested equal-fold versus pooled MAE, per-experiment metrics,
coverage labels, weight/context join and feature-support heatmap shaping.

The data tab shows the 303/223/303 experiment counts, weight distributions in
grams, and selectable pressure/flow cycles on the native elapsed-time grid. The
prediction tab separates primary equal-fold, primary pooled sample-weighted and
separately fitted pooled ID MAE; compares the same A/B/C representations for Ridge
and LightGBM; exposes primary and ID per-experiment predictions; and retains signed
population-specific permutation importance. The reliability tab keeps nominal,
primary and pooled/per-experiment ID coverage distinct, shows saved intervals and
the feature-by-experiment marginal range-departure heatmap, and records the failed
distance gate and M8 skip without proposing a policy.

The locked runtime now includes Streamlit and Plotly. The README owns the launch
command, prerequisites and launch-time disabling of Streamlit usage telemetry.
Missing inputs name every absent path and show the existing bounded reproduction
commands; the dashboard does not run them or write artifacts.

## Verification

- `uv sync --locked --group dev` completed against the 122-package lock.
- CI-equivalent checks passed: `ruff check .`, `ruff format --check .`, `pyright`,
  all 83 tests, and `mpi --version` (`0.0.1`).
- Five focused dashboard tests cover synthetic equal-fold versus pooled aggregation,
  protocol/experiment preservation, experiment 23-style small nonzero coverage,
  analytic MAE/RMSE/R² including null R² for a constant target, support populations,
  actionable missing-input guidance, all three tabs and a selector rerun through
  Streamlit's application test harness.
- The real-data application test rendered all three tabs from the existing prepared
  bundle and M4-M7/M9 artifacts, then reran secondary-ID prediction and support
  selectors without exceptions. Direct reconciliation recovered PLS MAE of
  0.502667583 g (primary equal-fold), 0.523299419 g (primary pooled) and
  0.113668893 g (separately fitted pooled ID), three per-experiment ID Ridge rows,
  including experiment 23's 0.087060831 g MAE, 0.106434371 g RMSE and 0.539380043
  R², and all 48 primary feature-support cells with a maximum fraction of 1.0.
- Desktop browser inspection at 1280 × 720 confirmed readable tabs, headings,
  legends, axes and units for representative data, prediction, coverage, interval
  and support views. Changing support from primary to secondary ID visibly updated
  the heatmap. The temporary browser tab and local Streamlit server were closed.

## Limitations and next step

The dashboard is a local view of the current artifact schema, not a compatibility
reader or deployed service. It presents observed associations and marginal range
departures; neither establishes causal process drivers, complete distributional
support, product limits or conformance. Primary and ID values come from different
fitted pipelines. Coverage under shift remains poor, the development distance gate
failed, and M8 remains skipped. There is no selective-measurement curve or policy.

The bounded Dataset 2 MVP is ready for the separate release decision. No Git tag or
publication is part of this milestone; the roadmap's next decision is the post-MVP
source audit gate.
