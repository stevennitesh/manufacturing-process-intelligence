# Manufacturing Quality & Process Intelligence

A greenfield, production-oriented data science system for predictive quality, uncertainty-aware inspection, process monitoring, and excursion diagnostics across manufacturing domains.

**Milestone 0: repository foundation** is complete, and **Milestone 1: SoliDAIR
ingestion** is next. The repository intentionally contains no modeling or
performance claims yet.

See the [implementation roadmap](docs/implementation-roadmap.md) for the current
milestone, subsystem status, and acceptance gates.

## Development setup

Prerequisites:

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- Git

```powershell
uv sync --locked --group dev
uv run mqi --version
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
uv run mqi --help
uv run mqi config validate configs/datasets/solidair.yaml
```

Dataset ingestion, training, evaluation, dashboard, and API commands will be added in the milestones defined by the [greenfield implementation plan](docs/plans/Manufacturing%20Quality%20%26%20Process%20Intelligence%20%E2%80%94%20Greenfield%20Technical%20Specification%20%26%20Implementation%20Plan.md).

## Data policy

Raw, interim, and processed third-party data are local-only and ignored by Git. Version-controlled manifests in `data/manifests/` will record provenance and hashes. See [DATA_LICENSES.md](DATA_LICENSES.md) before acquiring or redistributing any dataset.

## Scope

The project follows this progression:

```text
measure -> predict -> quantify uncertainty -> decide
        -> detect change -> diagnose -> deploy -> prove transfer
```

The core excludes predictive maintenance, computer vision, distributed infrastructure, agentic AI, and autonomous process control until the defined quality-intelligence milestones are complete.

## Status

Milestone 0 provides the package, CLI shell, configuration validation, structured logging, deterministic seed utility, tests, static checks, pre-commit hooks, and GitHub Actions workflow.
