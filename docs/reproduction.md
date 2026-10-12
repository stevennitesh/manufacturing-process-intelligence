# Setup and reproduction

The [case study](https://stevennitesh.github.io/manufacturing-process-intelligence/)
and [GitHub front page](../README.md) show the saved results without installation.
This guide owns the local CLI, report generation and full study reproduction.
All commands run from the repository root. Reproduction fits the predefined models;
presentation rendering only reads saved outputs.

## Development setup

Commands below use PowerShell and run from the repository root. First clone the
repository and enter it:

```powershell
git clone https://github.com/stevennitesh/manufacturing-process-intelligence.git
cd manufacturing-process-intelligence
```

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

### Regenerate the HTML presentation

After producing the saved study evidence below, run:

```powershell
uv run python scripts/render_portfolio_report.py
Invoke-Item docs/report/index.html
```

The renderer reads the prepared bundle and saved M4–M7/M9 outputs through the
dashboard's source/membership checks. It writes a self-contained HTML file with inline
styles, aggregate charts and tables, plus `docs/images/scalar-comparison.svg` for the
GitHub preview. Both use the same saved scalar comparisons. It does not train models or download data.
Use `--output <path> --figure-output <svg-path>` to render comparison copies. The template is
`docs/report/template.html`; review its interpretation when the scientific study changes.

A fresh clone can read the committed report and milestone summaries immediately.
Regenerating the report requires local saved artifacts; the full sequence below
reproduces those inputs. The tracked audit notebook has no saved outputs.

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

## Reproduce the full study

From the repository root, acquire and prepare Dataset 2, then run the complete
saved-evidence sequence:

```powershell
uv run mpi data acquire injection_molding
uv run mpi data prepare injection_molding --raw-root data/raw/injection_molding
New-Item -ItemType Directory -Force artifacts/m02 | Out-Null
uv run jupyter nbconvert --to notebook --execute notebooks/m02_injection_molding_audit.ipynb `
  --output m02_injection_molding_audit.executed.ipynb --output-dir artifacts/m02 `
  --ExecutePreprocessor.timeout=300
uv run python scripts/create_injection_molding_memberships.py
uv run python scripts/run_scalar_baselines.py
uv run python scripts/run_trajectory_representations.py
uv run python scripts/run_lightgbm_comparison.py
uv run python scripts/run_uncertainty_shift.py
uv run python scripts/run_predictive_explanation.py
uv run python scripts/render_portfolio_report.py
uv run streamlit run src/mpi/dashboard.py --browser.gatherUsageStats false
```

<details>
<summary>Per-step methodology, outputs and special commands</summary>

The following notes link each step to its detailed methodology and limitations.
Saved files call the represented-condition benchmark `secondary_id` and the
whole-experiment benchmark `primary`; these are implementation labels for the two
evaluation settings described above.

### Exploratory audit

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
[M2 audit summary](milestones/m02-dataset-audit.md) for aggregate findings
and the [M3 contract](milestones/m03-feature-and-evaluation-contract.md) for the
subsequently fixed modeling decisions.

### Fixed evaluation memberships

After preparing Dataset 2 at the default path, generate the ignored membership
artifact shared by the scalar and trajectory experiments:

```powershell
uv run python scripts/create_injection_molding_memberships.py
```

The command writes `artifacts/m03/injection_molding_memberships.parquet`. It records
the source hash, protocol, fold, experiment, role, inner fold, seed and exact unit
identity. Re-running it is deterministic for the locked environment and does not
modify the prepared bundle. The [M3 contract](milestones/m03-feature-and-evaluation-contract.md)
owns the cutoff, predictor allowlist, allocation rules and limitations.

### Scalar baselines

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
[M4 results and limitations](milestones/m04-scalar-baselines.md).

The pooled ID result combines represented regimes; per-experiment ID metrics and
post-hoc signed errors are recorded in `run.json` and the M4 results. To refresh
only these diagnostics from saved predictions, without retraining:

```powershell
uv run python scripts/run_scalar_baselines.py --report-only
```

### Trajectory comparison

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
[M5 results and limitations](milestones/m05-trajectory-representations.md).

### LightGBM comparison

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
[M6 results and limitations](milestones/m06-lightgbm-comparison.md).

### Uncertainty evaluation

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
[M7 results and limitations](milestones/m07-uncertainty-and-shift.md).

### Predictive explanation

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
[M9 results and limitations](milestones/m09-predictive-explanation.md).

### Run the Dataset 2 dashboard

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
Inputs are cached between interactions. After regenerating artifacts, click
**Reload saved evidence** (or restart Streamlit). Loading checks that the milestone
run records share the prepared source and M3 membership identity; it does not
re-hash every Parquet or detect files changed while a cached snapshot is displayed.

</details>
