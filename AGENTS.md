# Repository agent instructions

## Work in this repository

- This is a greenfield manufacturing quality and process-intelligence project.
- Python 3.12 and uv own the runtime and environment. Production code lives under `src/mqi/`.
- The implementation roadmap and scope boundaries are owned by the greenfield plan under `docs/plans/`. Work only within the requested milestone; do not pull later infrastructure or modeling forward without a demonstrated need.
- Keep dataset-specific parsing and semantics in dataset adapters. Do not turn the project into a generic ML framework.

## Verify changes

Set up the environment with:

```text
uv sync --locked --group dev
```

Run the required checks:

```text
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest
```

Use `uv run mqi --help` for a CLI smoke test. Keep full dataset training out of CI.

## Protect data and history

- Never commit raw, interim, or processed third-party data unless redistribution is explicitly permitted.
- Keep acquisition provenance and hashes in version-controlled manifests under `data/manifests/`.
- Do not commit credentials, local environments, generated artifacts, model binaries, or experiment stores.
- Preserve unrelated work. Inspect the staged diff and run `git diff --cached --check` before committing.

## Read the owning guidance

- For substantive design, implementation, debugging, refactoring, or review, read `docs/agents/engineering-contract.md`.
- When manufacturing meaning, statistical validity, scope, or an accepted architectural decision matters, read `docs/agents/domain.md` and follow its routes.
- For tracker-backed work, read `docs/agents/issue-tracker.md` and `docs/agents/triage-labels.md`.

Direct coding does not require a GitHub issue. These pointers do not start extra workflows on their own.
