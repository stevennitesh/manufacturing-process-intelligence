# Manufacturing Process & Quality Intelligence

A greenfield manufacturing data-science project starting with a focused question:
does high-resolution machine telemetry improve part-weight prediction beyond
scalar measurements, and does it generalize under controlled process changes?

This is a personal résumé/portfolio project: rigorous analysis, reproducible local
commands and an understandable demo, not a production-grade factory service.

The MVP uses **scatimdata Dataset 2 only**: 829 labeled cycles, pressure/flow
trajectories and weight in grams. Its three experimental production groups
represent controlled process-condition changes, not verified calendar days.
Leave-one-experiment-out evaluation, uncertainty and selective physical measurement
are required. Geometry is retained as deferred evidence; AUTO-PREDICT / MEASURE
does not mean PASS/FAIL or product conformance.

**Milestone 0: repository foundation** and **Milestone 1: injection-molding source
contract and ingestion** are complete. Dataset 2 can be acquired, strictly
validated, canonicalized, safely published as typed Parquet plus JSON provenance,
and independently reloaded without the raw source.
The repository intentionally contains no modeling or performance claims yet.

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
uv run mpi config validate configs/datasets/injection_molding.yaml
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
exclusions and limitations; the research dossier lives in dataset documentation.
The default output is `data/processed/injection_molding/dataset2`.

An existing output is loaded after schema and configured-source checks, without
reprocessing raw data or writing files. Reuse is not a code-freshness check: after
changing transformations, explicitly remove the generated output or choose a new
`--output` directory. Existing files are never overwritten. An interrupted write
may leave an incomplete directory; inspect/remove it or choose another output.
There are no artifact manifests, schema versions or compatibility readers.
Both raw and prepared data remain outside Git.

Training, evaluation, dashboard, and API commands will be added only in their
owning milestones.

## Data policy

Raw, interim, and processed third-party data are local-only and ignored by Git.
Version-controlled manifests in `data/manifests/` record admitted-source provenance
and hashes. See [DATA_LICENSES.md](DATA_LICENSES.md) before acquiring or redistributing
any dataset.

## Scope

The project follows this progression:

```text
predict -> test generalization -> quantify uncertainty -> selectively measure
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
evidence. The bounded M1 simplification is complete; M2 audit planning is next.
The current unversioned data contract has no legacy readers or migration paths.
