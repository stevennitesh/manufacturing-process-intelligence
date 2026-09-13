# Manufacturing Process & Quality Intelligence

A greenfield manufacturing data-science project starting with a focused question:
does high-resolution machine telemetry improve part-weight prediction beyond
scalar measurements, and does it generalize under controlled process changes?

The MVP uses **scatimdata Dataset 2 only**: 829 labeled cycles, pressure/flow
trajectories and weight in grams. Its three experimental production groups
represent controlled process-condition changes, not verified calendar days.
Leave-one-experiment-out evaluation, uncertainty and selective physical measurement
are required. Geometry is retained as deferred evidence; AUTO-PREDICT / MEASURE
does not mean PASS/FAIL or product conformance.

**Milestone 0: repository foundation** is complete. **Milestone 1: injection-molding
source contract and ingestion** is in progress: the source contract is accepted
with limitations, reproducible acquisition and raw validation are complete, and
Dataset 2 canonicalization is next.
The repository intentionally contains no modeling or performance claims yet.

See the [implementation roadmap](docs/implementation-roadmap.md) for the current
milestone, subsystem status, and acceptance gates. The
[greenfield specification and implementation plan](docs/plans/Manufacturing%20Process%20%26%20Quality%20Intelligence%20%E2%80%94%20Greenfield%20Specification%20and%20Implementation%20Plan.md)
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
```

The acquisition command downloads only the manifest-admitted Dataset 2 archive to
`data/raw/injection_molding/`, verifies its exact size and SHA-256, and writes a
local receipt. Use `--raw-root <directory>` for an isolated destination. A matching
archive is verified and reused without network access. A mismatched archive is
preserved and reported; move or remove it manually only after investigating its
identity. Acquisition does not extract, parse, validate, or prepare the dataset,
and the dataset configuration remains disabled for preparation.

The validation command is local-only. It rechecks the acquired bytes before safely
reading the single pinned HDF5 member, validates the complete scalar, pressure, and
flow source contract, and reports labeled and signal-only membership plus accepted
limitations. It does not canonicalize, resample, impute, or prepare data.

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
transfer (v0.3), then production polish (v0.4). Pharma (v0.5) and advanced
manufacturing (v0.6) are optional later extensions. These are planned capabilities,
not implemented results; SPC and physical RCA are not Dataset 2 MVP requirements.

The core excludes predictive maintenance, computer vision, distributed
infrastructure, agentic AI, and autonomous process control until the defined
quality-intelligence milestones are complete.

## Status

Milestone 0 provides the `mpi` package and CLI shell, configuration validation,
structured logging, deterministic seed utility, tests, static checks, pre-commit
hooks, and GitHub Actions workflow. M1 has frozen and verified the
high-resolution injection-molding source contract and now provides verified,
idempotent acquisition of its pinned Dataset 2 archive. Raw validation now produces
a typed source-native handoff with exact schema, grid, join, missingness, and
experiment checks. Canonicalization remains unimplemented.
