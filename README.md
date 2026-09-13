# Manufacturing Process & Quality Intelligence

A greenfield, production-oriented data science system for predictive quality,
uncertainty-aware inspection, process monitoring, and excursion diagnostics across
manufacturing domains.

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
measure -> predict -> quantify uncertainty -> decide
        -> detect change -> diagnose -> deploy -> prove transfer
```

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
