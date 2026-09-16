# Manufacturing Process & Quality Intelligence

A greenfield manufacturing data-science project starting with a focused question:
does high-resolution machine telemetry improve part-weight prediction beyond
scalar measurements, and does it generalize under controlled process changes?

This is a personal résumé/portfolio project: rigorous analysis, reproducible local
commands and an understandable demo, not a production-grade factory service.

The MVP uses **scatimdata Dataset 2 only**: 829 labeled cycles, pressure/flow
trajectories and weight in grams. Its three experimental production groups
represent controlled process-condition changes, not verified calendar days.
Leave-one-experiment-out evaluation and uncertainty are required. Selective physical
measurement follows only if a simple uncertainty score supports error ranking.
Geometry is retained as deferred evidence; AUTO-PREDICT / MEASURE
does not mean PASS/FAIL or product conformance.

**Milestone 0: repository foundation** and **Milestone 1: injection-molding source
contract and ingestion** are complete. Dataset 2 can be acquired, strictly
validated, canonicalized, saved as Parquet plus JSON source metadata,
and independently reloaded without the raw source.
The scalar baselines, trajectory comparisons and bounded uncertainty evaluation
are now implemented; their grouped and separate within-experiment results are
reported with their limitations below.

See the [implementation roadmap](docs/implementation-roadmap.md) for the current
milestone, subsystem status, and acceptance gates. The
[project specification](docs/spec.md)
is the canonical scope authority.

## Development setup

Prerequisites:

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- Git

```powershell
uv sync --locked --group dev
uv run mpi --version
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run pyright
```

Install the Git hooks after syncing:

```powershell
uv run pre-commit install
```

## Command line interface

```powershell
uv run mpi --help
uv run mpi data acquire injection_molding
uv run mpi data validate injection_molding
uv run mpi data prepare injection_molding --raw-root data/raw/injection_molding
```

The acquisition command downloads only the manifest-admitted Dataset 2 archive to
`data/raw/injection_molding/` and verifies its exact size and SHA-256 before saving.
Use `--raw-root <directory>` for an isolated destination. A matching
archive is verified and reused without network access. A mismatched archive is
preserved and reported; move or remove it manually only after investigating its
identity. Acquisition does not extract, parse, validate, or prepare the dataset.

The validation command is local-only. It rechecks the acquired bytes before safely
reading the single pinned HDF5 member, validates the complete scalar, pressure, and
flow source contract, and reports labeled and signal-only membership plus accepted
limitations. It does not canonicalize, resample, impute, or prepare data.

The preparation command is offline. For a new output it validates the pinned raw
source, canonicalizes it, and writes six Parquet tables plus `metadata.json`.
Metadata retains source identity, license, field lineage, transformations,
exclusions and limitations; the source contract owns research evidence.
The source manifest is the sole source identity; edits to its descriptive notes do
not invalidate prepared data. The default output is `data/processed/injection_molding/dataset2`.

An existing output is loaded after schema and manifest-pinned source checks, without
reprocessing raw data or writing files. Reuse is not a code-freshness check: after
changing transformations, explicitly remove the generated output or choose a new
`--output` directory. Existing files are never overwritten. An interrupted write
may leave an incomplete directory; inspect/remove it or choose another output.
Only the current schema is supported; there are no artifact manifests or compatibility readers.
Both raw and prepared data remain outside Git.

## Reproduce the M2 audit

After preparing Dataset 2 at the default path, execute the bounded audit headlessly:

```powershell
New-Item -ItemType Directory -Force artifacts/m02 | Out-Null
uv run jupyter nbconvert --to notebook --execute notebooks/m02_injection_molding_audit.ipynb `
  --output m02_injection_molding_audit.executed.ipynb --output-dir artifacts/m02 `
  --ExecutePreprocessor.timeout=300
```

The executed copy is generated under ignored `artifacts/`; the tracked notebook
has no outputs. The audit is descriptive and does not approve a prediction cutoff,
feature allowlist, split, model, or trajectory representation. See the
[M2 audit summary](docs/milestones/m02-dataset-audit.md) for aggregate findings
and unresolved M3 decisions.

## Reproduce the M3 memberships

After preparing Dataset 2 at the default path, generate the ignored membership
artifact used by future scalar and trajectory experiments:

```powershell
uv run python scripts/create_injection_molding_memberships.py
```

The command writes `artifacts/m03/injection_molding_memberships.parquet`. It records
the source hash, protocol, fold, experiment, role, inner fold, seed and exact unit
identity. Re-running it is deterministic for the locked environment and does not
modify the prepared bundle. The [M3 contract](docs/milestones/m03-feature-and-evaluation-contract.md)
owns the cutoff, predictor allowlist, allocation rules and limitations.

## Reproduce the M4 scalar baselines

After preparing Dataset 2 and generating the M3 memberships, run:

```powershell
uv run python scripts/run_scalar_baselines.py
```

The command evaluates Mean, Ridge and PLS on all three grouped primary folds and
the separate secondary ID fold. It writes ignored predictions, metrics and a run
record under `artifacts/m04/`. Primary equal-fold mean MAEs are 1.041300 g for
Mean, 0.918559 g for Ridge and 0.502668 g for PLS; pooled sample-weighted MAEs are
1.090584 g, 0.966475 g and 0.523299 g, respectively. Performance varies strongly
by held-out experiment and includes negative R² values. The much lower separate ID
errors are descriptive, not a paired estimate of shift. See the
[M4 results and limitations](docs/milestones/m04-scalar-baselines.md).

The pooled ID result combines represented regimes; per-experiment ID metrics and
post-hoc signed errors are recorded in `run.json` and the M4 results. To refresh
only these diagnostics from saved predictions, without retraining:

```powershell
uv run python scripts/run_scalar_baselines.py --report-only
```

## Reproduce the M5 trajectory comparison

After preparing Dataset 2 and generating the M3 memberships, run:

```powershell
uv run python scripts/run_trajectory_representations.py
```

The command evaluates the pre-specified A scalar, B engineered-summary, C-PCA and
C-PLS representations with fold-local transformations and Ridge. It writes ignored
predictions, metrics and a run record under `artifacts/m05/`. Primary equal-fold
mean MAEs are 0.918559 g for A, 1.457393 g for B, 1.046989 g for C-PCA and
0.704219 g for C-PLS. The result is heterogeneous: each augmented representation
is worse than A on at least one held-out experiment, and no representation is
selected from its outer score. See the
[M5 results and limitations](docs/milestones/m05-trajectory-representations.md).

## Reproduce the M6 LightGBM comparison

After preparing Dataset 2 and generating the M3 memberships, run:

```powershell
uv run python scripts/run_lightgbm_comparison.py
```

The command evaluates the same A, B, C-PCA and C-PLS representations with the
pre-specified bounded LightGBM search. It writes ignored predictions, all 16
fold/representation metric rows and the full run record under `artifacts/m06/`.
Primary equal-fold mean MAEs are 0.634726 g for A, 0.624374 g for B, 0.637934 g
for C-PCA and 0.649260 g for C-PLS. B's small aggregate improvement is not
consistent across held-out experiments, compression does not improve the aggregate
LightGBM result, and no global winner is selected from outer performance. See the
[M6 results and limitations](docs/milestones/m06-lightgbm-comparison.md).

## Reproduce the M7 uncertainty evaluation

After preparing Dataset 2 and generating the M3 memberships, run:

```powershell
uv run python scripts/run_uncertainty_shift.py
```

The command performs fixed development-only scalar PLS/LightGBM selection, 90%
split-conformal calibration and the five-neighbor distance screen. Under primary
experiment shift, pooled coverage is only 0.052 versus 0.862 for the separate ID
protocol. The distance screen fails its pre-specified every-fold gate because one
primary fold improves development MAE by only 4.31%; M8 is therefore skipped, with
no additional score search. See the
[M7 results and limitations](docs/milestones/m07-uncertainty-and-shift.md).

## Reproduce the M9 predictive explanation

After reproducing M7, run:

```powershell
uv run python scripts/run_predictive_explanation.py
```

The command reads M7's four selected scalar-model settings, refits each model once
on its original fit/tune rows, and verifies its unit-aligned predictions against
the saved M7 evaluation predictions. It writes ignored 96-row permutation-importance
and marginal feature-support tables plus a compact run record under `artifacts/m09/`.
The six populations keep each primary holdout and each secondary ID experiment
separate. These diagnostics describe fitted-model associations and observed marginal
support, not physical causes or product limits. See the
[M9 results and limitations](docs/milestones/m09-predictive-explanation.md).

## Run the Dataset 2 dashboard

After preparing Dataset 2 and reproducing M4-M7 and M9 at their default artifact
paths, launch the offline portfolio dashboard from the repository root:

```powershell
uv run streamlit run src/mpi/dashboard.py --browser.gatherUsageStats false
```

The three tabs present the saved data/process, prediction/generalization, and
reliability-under-shift evidence. Dashboard use does not fit models, download data,
write artifacts or call remote services; the documented command also disables
Streamlit usage telemetry. If a required input is absent, the page
lists the missing paths and the existing reproduction commands. Weight is shown in
grams; pressure and flow amplitudes remain in unresolved source-native units.

## Data policy

Raw, interim, and processed third-party data are local-only and ignored by Git.
Version-controlled manifests in `data/manifests/` record admitted-source provenance
and hashes. See [DATA_LICENSES.md](DATA_LICENSES.md) before acquiring or redistributing
any dataset.

## Scope

The project follows this progression:

```text
predict -> test generalization -> quantify uncertainty -> selectively measure if supported
        -> detect abnormalities -> diagnose supported contributors -> transfer
```

After the MVP: audit PyScrew versus CiP-DMD and the cross-process-chain candidate
for process/assembly intelligence (v0.2), prioritize Bosch Plasma semiconductor
transfer (v0.3), then an optional role-specific engineering demo (v0.4). Pharma (v0.5) and advanced
manufacturing (v0.6) are optional later extensions. These are planned capabilities,
not implemented results; SPC and physical RCA are not Dataset 2 MVP requirements.

The core excludes predictive maintenance, computer vision, distributed
infrastructure, agentic AI, and autonomous process control until the defined
quality-intelligence milestones are complete.

## Status

See the [roadmap](docs/implementation-roadmap.md) for the next action and the
[M1 summary](docs/milestones/m01-injection-molding-ingestion.md) for completion
evidence. M2 and M3 are complete: the audit, retrospective cutoff, explicit feature
allowlist and evaluation memberships are reviewed. M4 scalar baselines, M5's fixed
trajectory comparison, M6's bounded LightGBM comparison, M7's conformal/shift
evaluation, M9's bounded predictive explanation, and M10's three-tab offline
dashboard are complete. M7's simple distance score failed the pre-specified gate,
so M8 remains skipped; the dashboard does not invent a selective-measurement policy.
The current data contract has no legacy readers or migration paths. Version labels
are not bumped for routine edits; historical versions become useful when there are
data or results worth retaining across changes.
