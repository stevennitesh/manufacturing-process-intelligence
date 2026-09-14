# Planning and progression

Use this guide for milestone planning, implementation and status. Keep the
project's personal-portfolio scale active; the specification owns scientific
scope and the [engineering contract](engineering-contract.md) owns coding rigor.

## One owner per decision

| Owner | Content |
| --- | --- |
| Specification routed by [domain guidance](domain.md) | Scientific scope, release priorities and project scale. |
| [Roadmap](../implementation-roadmap.md) | Current position and links, not a duplicate work log. |
| Active milestone document | Outcome, current contract, next action and concise completion evidence. |
| Dataset source contract | Source facts, unresolved semantics and citations. |
| ADR, only when useful | A consequential tradeoff not adequately captured at its existing owner. |
| GitHub issue, only when used | Delivery coordination linked to the local plan. |

README owns usage and a short scope introduction; link to the roadmap for detailed
status. Completed investigations belong in clearly historical records, not standing
instructions. Archive superseded detail under repository-root `.archive/` and
repair links; keep still-needed scientific contracts at their active owners.

## Plan enough to execute

Plan the milestone outcome and dependencies first. Detail only the approaching
work whose decisions are not already settled. One coherent slice can span adjacent
subsystems; subsystem labels do not require separate plans, agents, approvals,
tickets or reports. A conversation is enough for a small unambiguous change.

A useful saved plan states the outcome, boundaries, changed behavior, a few
distinguishing acceptance scenarios and material unknowns. Link existing contracts
rather than copying them. Do not impose word quotas or expand a plan to enumerate
every edge case. Split a document only when the detail has a different reader or
loading time.

Before adding a dependency, hardening requirement or extra gate, identify the
current caller or scientific/demo benefit it serves. Prefer leaving a capability
out when no current need exists. Do not reopen settled choices without evidence.
A request to plan authorizes local planning/context work, not implementation;
an implementation request continues through the authorized outcome.

## Execute and close

Read the roadmap and active milestone, then inspect only the relevant contract and
code. Historical logs need not be loaded unless a decision depends on them.
Respect explicit skill custody; otherwise no delegation workflow is implied.

Implement dependent work within the existing authorization. Ask only for a missing
consequential decision or new authority. Preserve scientific constraints, source
limitations and unrelated edits. Verification follows the engineering contract,
not a growing list of historical check commands.

A milestone closes when its promised ordinary workflow and scoped gate pass.
Keep a compact record of the output, decisive checks/input identity, limitations
and next action. Do not copy every attempt or repair round into active context.
Planning alone does not advance status. A maintenance simplification does not
erase a completed milestone or inherit every former implementation requirement;
record its own pending acceptance and retain unaffected evidence.

Update the milestone when its evidence changes; update the roadmap only when the
current position changes. Use references elsewhere instead of synchronizing several
detailed summaries. Stop after the authorized outcome; do not start the next
milestone or optional hardening without scope.
