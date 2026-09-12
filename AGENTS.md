# Repository agent instructions

## Work in this repository

- This is a manufacturing process and quality-intelligence project developed from a greenfield specification.
- Use the runtime declared in `.python-version` and `pyproject.toml`, with dependencies resolved by `uv.lock`. Follow `README.md` for setup and `pyproject.toml` for package layout and entry points.
- Work within the user's authorized scope. Milestone order and technical scope come from the specification routed by `docs/agents/domain.md`; current progress comes from `docs/implementation-roadmap.md` and its linked milestone documents.
- Keep dataset-specific parsing and semantics in dataset adapters. Do not turn the project into a generic ML framework.

## Plan and progress

- Before planning, implementing, resuming, or reporting milestone work, read `docs/agents/planning-and-progression.md`, the roadmap, and the relevant milestone document.
- Plan the overall milestone first; detail each subsystem when approaching its implementation. Progress through dependencies and verify subsystem outputs before claiming completion. A milestone closes only when its acceptance gate passes.
- Keep status, next actions, blockers, and completion evidence in the roadmap and milestone documents, not in this file. Creating a plan does not authorize its implementation or advance its implementation status.

## Verify changes

Run the required checks declared in `.github/workflows/ci.yml`, using the tool
configuration in `pyproject.toml`, plus verification required by the affected
behavior and milestone gate. Use the configured CLI's help for an additional CLI
smoke test. Keep full dataset training out of CI. Report checks that could not run
and the resulting verification gap.

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

Update this file when repository-wide policy or an owning document's location
changes, not when milestones advance, commands are added, or dependency versions
change. Update those facts at their owners and keep affected links consistent.
