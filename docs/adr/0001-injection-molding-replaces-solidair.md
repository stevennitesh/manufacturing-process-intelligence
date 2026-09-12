# ADR-0001: Injection molding replaces SoliDAIR as the MVP

- **Status:** Accepted
- **Date:** 2026-09-12

## Context

The original MVP depended on SoliDAIR. Source discovery showed that the released
production data did not provide the stable, documented process-to-physical-quality
relationship required by the project. Continuing would have forced the architecture
and claims around a dataset that could not support the intended predictive-quality
demonstration.

The replacement high-resolution injection-molding source provides cycle-linked scalar
process measurements, injection-pressure and injection-flow trajectories, and measured
part weight and geometry. Source admission, exact file roles, joins, release identity,
and licensing still must be verified in M1 before acquisition or implementation.

## Decision

Use injection molding as the v0.1 predictive-quality MVP. Use
`Manufacturing Process & Quality Intelligence` as the display name,
`manufacturing-process-intelligence` as the project and repository name, `mpi` as the
Python package and CLI name, and the replacement greenfield plan as the sole active
scope authority.

Archive the former plan and SoliDAIR investigation. Archived material remains evidence,
not an active compatibility contract. Reuse only generic M0 foundation components that
remain valid under the replacement plan.

## Consequences

- M0 remains complete after the naming and guidance migration passes its quality gate.
- M1 restarts at source-contract verification; no SoliDAIR ingestion status carries over.
- No dataset-specific code is implemented until source identity, terms, schema, joins,
  and hashes are frozen.
- Downstream milestone numbering and progress follow the replacement canonical plan.
- SoliDAIR raw bytes may remain local and ignored, but they are not an admitted project
  source and must not influence active tests, commands, or documentation.

## References

- Canonical plan: `docs/plans/Manufacturing Process & Quality Intelligence — Greenfield Specification and Implementation Plan.md`
- Historical evidence: `.archive/docs/plans/SoliDAIR Discovery Findings — Original Plan Review.md`
