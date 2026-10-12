# Manufacturing Process Intelligence

Can injection-molding telemetry estimate completed-part weight—and remain reliable
when process conditions change?

**Steven Bangdiwala · Independent data-science portfolio study**

**[Read the case study →](https://stevennitesh.github.io/manufacturing-process-intelligence/)**

The report opens directly in a browser and includes the contribution, results,
methods and supporting evidence. The committed [HTML copy](docs/report/index.html)
also opens offline after downloading or cloning; GitHub displays HTML as source.

## What I built

I built a Python workflow that joins each machine cycle to its measured part,
preserves native pressure/flow signals, and compares predictions under two fixed
evaluation designs. It includes:

- Pinned-source acquisition, validation and cycle-safe canonical tables with Polars.
- Scalar PLS/Ridge, engineered signal summaries, PCA/PLS compression and LightGBM,
  with scaling and model selection confined to development partitions.
- Split-conformal prediction intervals and a development-only distance screen.
- Predictive explanations, synthetic regression tests, a local Streamlit dashboard
  and a self-contained analytical report.

The source measurements come from **Bogedale et al., scatimdata Dataset 2**.
Scikit-learn and LightGBM provide the model implementations. This project adds
the data preparation, whole-experiment evaluation and interpretation.

## Main finding

Prediction error was low within represented conditions, but the fitted models did
not transfer reliably to an omitted experiment. More detailed signals and nonlinear
models did not consistently solve the transfer problem.

![Scalar model mean absolute error: represented-condition and whole-experiment results use separate fits, pooled cycle weighting and zero-based bars. PLS error is 0.114 g across 167 represented-condition cycles and 0.523 g across 829 cycles in three whole-experiment holdouts.](docs/images/scalar-comparison.svg)

| Saved evidence | Represented conditions | Whole experiment held out |
| --- | ---: | ---: |
| Scalar PLS mean absolute error, pooled by cycle | 0.114 g | 0.523 g |
| Separate uncertainty study: coverage of nominal 90% intervals | 86.2% | 5.2% |
| Separate uncertainty study: pooled mean interval width | 0.194 g | 0.342 g |
| Evaluated cycles per comparison | 167 | 829 across three holdouts |

Mean absolute error (MAE) is the average absolute difference from measured weight;
lower is better. The predefined equal-experiment PLS MAE is **0.503 g**. Pooled MAE
instead gives every evaluated cycle equal weight. The uncertainty study selects
scalar PLS or LightGBM separately using development data and reserves calibration rows.

These are separately fitted retrospective benchmarks, rather than a paired causal
estimate or an untouched prospective test. The source contains three controlled
experiments and no authoritative product-weight tolerance. Low prediction error
therefore does not establish product conformance. The distance screen failed its
predefined criterion, so the selective-measurement study was skipped.

## Inspect the evidence

The study uses **829 labeled molded parts**, 16 completed-cycle scalar measurements
and 2,048 native-time samples per pressure/flow channel. Ninety-two signal-only cycles
have no supported weight target and remain outside the prediction study. Weight and
experiment context stay out of the predictors.

- [Case study](https://stevennitesh.github.io/manufacturing-process-intelligence/):
  results, readable charts, aggregate tables and decision implications.
- [Scalar results](docs/milestones/m04-scalar-baselines.md),
  [signal representations](docs/milestones/m05-trajectory-representations.md), and
  [LightGBM comparisons](docs/milestones/m06-lightgbm-comparison.md):
  evaluation boundaries and per-experiment results.
- [Uncertainty and distance screen](docs/milestones/m07-uncertainty-and-shift.md) and
  [predictive explanations](docs/milestones/m09-predictive-explanation.md):
  interval widths, coverage and model associations.
- [Dataset contract](docs/datasets/injection-molding-source-contract.md),
  [Python implementation](src/mpi/) and [synthetic tests](tests/unit/):
  source meanings, engineering and regression coverage.

The Dataset 2 study is complete. The [roadmap](docs/implementation-roadmap.md)
and [specification](docs/spec.md) describe later studies and scientific scope.

## Run locally

Use Python 3.12 and [uv](https://docs.astral.sh/uv/) from the repository root:

```powershell
uv sync --locked --group dev
uv run mpi --version
uv run pytest
```

A fresh clone can inspect the committed report immediately. The
[setup and reproduction guide](docs/reproduction.md) contains the CLI, full data
and analysis sequence, dashboard command, and all CI checks. Rendering the report
from saved local artifacts does not fit models or download data.

## Source and license

The charts and report are this project's derived summaries of
[scatimdata Dataset 2](https://github.com/sc4t1m/scatimdata/tree/7bd35941d75c97a3f276439377dc430ab47402be),
collected by Bogedale et al. and licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
I joined the data into English-named canonical tables and analyzed them here;
these are not publisher figures. Source data and numeric experiment artifacts
remain local and outside Git. See [DATA_LICENSES.md](DATA_LICENSES.md).

Project code and prose use the [MIT License](LICENSE).
