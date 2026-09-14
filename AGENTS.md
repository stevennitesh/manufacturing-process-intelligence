# Repository guidance

This is a personal manufacturing-data-science portfolio, not a production service.
Prefer a correct, understandable end-to-end result over infrastructure breadth.

## Context and progress

- For milestone planning/status, read [the roadmap](docs/implementation-roadmap.md)
  and only the relevant milestone. For scientific scope, use [the spec](docs/spec.md).
  Source meanings, evidence and limitations live in [dataset contracts](docs/datasets/).
  A routine code change does not require reading the whole plan or every milestone.
- Plan only decisions the next work needs; a small change needs no saved plan.
  Keep progress/evidence in the roadmap or relevant milestone, not here.
  Planning does not authorize implementation. Completion does not restrict later changes.
- This compact file owns engineering and progression guidance. Do not recreate
  separate domain/engineering/tracker guides or an archive directory to satisfy
  skill templates. Git history retains obsolete documents; preserve useful facts
  at their current owner before deletion. This is a deliberate local convention.
- Issues and ADRs are optional, not coding prerequisites. If tracker work is requested,
  use the configured remote's Issues and inspect current labels/relationships.
  Existing GitHub conventions use native sub-issues/dependencies and close implemented
  issues only within the authorized workflow; no remote changes are implied here.

## Implementation

- Keep parsing and source semantics in dataset adapters. Reuse established guarantees
  within a pipeline; do not duplicate the source audit at every helper boundary.
  Prefer transformation tests over runtime assertions of values just constructed.
- Protect source identity, cycle joins, units/nulls, native sampling, target separation
  and leakage-safe evaluation. Keep unknowns explicit; do not invent chronology,
  specification limits or causal claims.
- Add a layer, test or dependency for a concrete correct result, realistic failure
  or materially simpler ordinary workflow—not hypothetical production use.
  Create future directories/configs only when they have a current consumer.
- Local single-user batch processing is sufficient. Preserve existing files on
  failure; no artifact registry, acquisition receipts, concurrent-writer protocol
  or compatibility machinery is required. Source hashes/lineage/limitations matter;
  research history belongs in documentation, not mandatory runtime payloads.
- Keep work within the requested scope and preserve unrelated changes.

## Verification and data

- Follow README setup; runtime/package configuration and dependencies are owned by
  `.python-version`, `pyproject.toml` and `uv.lock`.
- For code changes run the checks in `.github/workflows/ci.yml` plus a focused
  ordinary-path test. Reuse checks for unchanged code/inputs. Transformation changes
  need an independent reference comparison; full training stays out of CI.
  Documentation-only edits need content/link checks. Report verification gaps.
- Keep raw/prepared third-party data, credentials, environments and generated
  outputs out of Git. Record admitted-source provenance/hashes in `data/manifests/`;
  follow DATA_LICENSES.md. Use synthetic fixtures in tests.
- Inspect the staged diff and run `git diff --cached --check` before committing.
