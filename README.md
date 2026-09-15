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
The first scalar-only benchmarks are now implemented; their grouped and separate
within-experiment results are reported with their limitations below.

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

Trajectory training, uncertainty and dashboard commands are added only in their
owning milestones.

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
allowlist and evaluation memberships are reviewed. M4 scalar baselines are
complete and reviewed. M5 trajectory-representation planning is next.
The current data contract has no legacy readers or migration paths. Version labels
are not bumped for routine edits; historical versions become useful when there are
data or results worth retaining across changes.
