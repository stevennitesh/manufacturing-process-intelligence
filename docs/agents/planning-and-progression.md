# Planning and progression

Read this guide when planning, implementing, resuming, or reporting milestone
work. It defines the planning method; the linked project documents supply the
current scope and state.

## Document ownership

| Owner | What belongs there |
| --- | --- |
| Specification routed by [domain guidance](domain.md) | Project scope, milestone sequence, technical requirements, and acceptance criteria. |
| [Implementation roadmap](../implementation-roadmap.md) | Current cross-milestone position, status vocabulary, concise master diagram, and links to milestone plans. |
| Active document under `docs/milestones/` | Overall milestone plan, subsystem diagram, dependencies, detailed steps for approaching work, blockers, next action, and completion evidence. |
| `docs/adr/` | Accepted architectural decisions and their rationale, when a decision warrants a durable record. |
| GitHub Issues, when used | Individual work items and dependencies, governed by [tracker guidance](issue-tracker.md); link to the milestone plan rather than copying it. |

Treat a specification as intended behavior and implementation evidence as observed
behavior. If they disagree, record the discrepancy and resolve it within the
authorized scope. Do not silently weaken a gate or treat a diagram as proof.
Record accepted scope changes in the owning plan and reconcile affected milestone
documents and decisions.

## Plan at two levels

1. **Establish the milestone outline.** Read its specification sections and
   prerequisite evidence. Create or extend its milestone document with objective,
   scope and exclusions, subsystem responsibilities, dependencies, expected
   interfaces/artifacts, material unknowns, execution order, and an observable
   acceptance gate. Keep a brief subsystem diagram near the top.
2. **Detail the next subsystem when needed.** Before implementing it, inspect the
   actual code, inputs, and completed prerequisites. Add a bounded set of steps,
   relevant contracts, failure behavior, and verification criteria to the milestone
   document. Resolve assumptions that could change dependent work with a focused
   discovery step or experiment, then revise that work's plan from the evidence.
3. **Keep later detail deferred.** Outline dependencies now, but detail later
   subsystems and milestones as they approach. Split out a subsystem document only
   when complexity makes the milestone document hard to use; link it from the
   milestone plan and give each detail one owner.

Planning should be sufficient to execute and verify the next authorized work.
Routine fixes or small changes within an existing plan do not require a new plan,
issue, ADR, or approval cycle. A request to plan ends with the reviewable plan;
an implementation request continues through the authorized outcome.

## Execute and resume from evidence

1. Read the user's requested scope, the roadmap, and the relevant milestone plan.
   Check the actual checkout and cited evidence before relying on recorded status.
2. Select work whose prerequisites are satisfied. Follow the milestone's dependency
   order; completing one subsystem permits dependent work within the existing
   authorization without asking again. A request for one subsystem does not
   authorize the rest of the milestone or later milestones.
3. Implement and verify the selected work according to the
   [engineering contract](engineering-contract.md). Test the consuming handoff
   where subsystem outputs feed the next stage. Resolve failures and update
   affected plans when discoveries change assumptions.
4. Record progress with the implementation change. Keep a concise next action and
   any blocker in the milestone document so another session can resume without
   reconstructing the conversation. Do not duplicate the work log in `AGENTS.md`.
5. Continue while safe work remains within the authorized outcome. When a required
   dependency or scope decision prevents further progress, record the specific
   missing evidence or decision and report it. Do not invent source semantics,
   silently substitute scope, or mark unfinished work complete.

## Track progress and close gates

Use the status key in the roadmap. A planned document is not implementation
progress. Mark a subsystem in progress when execution begins, and complete only
when its promised artifact exists and relevant verification passes. If a completed
subsystem's evidence becomes invalid after a change, revise its status and record
what needs re-verification.

Keep the milestone's diagram, checklist, and evidence consistent. Update the
roadmap whenever cross-milestone status or its summary changes; it need not repeat
every subsystem step. If another maintained summary repeats the changed status,
reconcile it or replace the duplicate with a link to its owner.

Completion evidence should identify the output or code reference, relevant
commands/checks and results, material input/configuration identity where applicable,
and remaining limitations. Use existing test results and artifacts when sufficient;
do not create a separate report merely to restate them. Keep generated or restricted
artifacts outside Git and record safe references or hashes as appropriate.

Close a milestone only after its end-to-end acceptance gate and required repository
checks pass. Record gate evidence and the next milestone's prerequisite handoff,
then update the roadmap. Passing unit tests, committing code, closing an issue, or
finishing a discovery experiment alone does not establish milestone completion.
Continue into the next milestone only when it is within the user's authorization.
