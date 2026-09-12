# Domain guidance

**Configured layout:** single-context.

## Route

The project charter, manufacturing terminology, scope boundaries, dataset strategy,
statistical validity requirements, architecture, and milestone roadmap are owned by:

`docs/plans/Manufacturing Quality & Process Intelligence — Greenfield Technical Specification & Implementation Plan.md`

Read the relevant sections of that plan whenever domain meaning or scope affects a
task. Accepted architectural decisions belong under `docs/adr/`; distinguish those
records from proposals and observed implementation.

There is no separate root `CONTEXT.md` yet. Add one only when stable cross-cutting
domain context needs a concise owner beyond the plan. Missing context or ADR records
are not setup blockers; resolve the required meaning from the plan, another owning
source, or the user, and capture new domain decisions only within the authorized task.

Do not manufacture specification limits, causal claims, production provenance, or
dataset semantics. Keep dataset-specific meanings in their adapters and documentation.
