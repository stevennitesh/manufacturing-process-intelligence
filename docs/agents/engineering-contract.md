# Engineering contract

Use this guide for design, implementation and review. The canonical specification
owns project scope: a personal manufacturing-data-science portfolio, not a
production service.

## Choose the smallest useful outcome

Build the current caller's end-to-end path. Prefer existing Python, Polars and
repository facilities over new layers or dependencies. Add an abstraction only
for meaningful current variation, not hypothetical future datasets. A small
dataset-specific module is acceptable; do not build a generic ML framework.

Protect scientific validity: source identity, key-based alignment, units/nulls,
native sampling, target separation and leakage-safe evaluation. Keep unknowns
explicit. These are essential even in a personal project.

Default to local, single-user batch execution. Keep basic input/path safety,
bounded downloads and no unintended overwrite. Do not add service reliability,
concurrent-writer protocols, platform certification, cryptographic authenticity
or deployment machinery without an actual authorized need. Leave working
safeguards alone when removing them would create more work than it saves.

## Keep contracts usable

Validate external inputs and loaded artifacts where they enter the program.
Within one owned pipeline, reuse established guarantees instead of repeating the
same full checks at every helper. Validate changed semantics at their owner.
Keep schema compatibility separate from package versions, documentation wording,
code formatting and historical execution evidence.

Preserve recorded provenance and research context; only machine-relevant
invariants belong in runtime rejection rules. Existing artifacts are evidence,
not an obligation to support every old implementation forever. When changing a
format, state explicitly whether it remains readable or needs regeneration;
never overwrite existing user data as an implicit migration.

## Verify proportionately

For code changes, run the configured CI checks and the nearest tests that can
distinguish a wrong result. Keep one real integration path through affected stages.
Reuse passing evidence for unchanged code/inputs; do not repeat full-source proof
for a prose-only edit or an unrelated helper change. Data transformation changes
need an independent reference comparison, not only self-consistent round trips.

Test failures likely in the supported workflow: malformed input, wrong joins,
lost nulls, incompatible artifacts and interrupted writes. No test-count target,
exhaustive adversarial matrix or separate platform gate is implied. Linux CI and
the user's local environment provide routine coverage; add a platform-specific
probe only when the changed mechanism needs it. Documentation-only changes need
content/link checks, not the full code suite.

Report missing evidence honestly. Do not invent runtime/performance gains; measure
them only when a relevant claim requires it. Full training stays outside CI.

## Work and review efficiently

Investigate only enough to settle the named decision. Keep changes within the
authorized outcome and preserve unrelated work. A focused review should prioritize
wrong scientific conclusions, lost information, broken ordinary workflows and
clear maintenance costs. Ask whether the requirement itself is useful before
demanding another layer to satisfy it.

New review requirements need a concrete supported scenario and consequence.
Potential enterprise use is not sufficient. Keep optional hardening nonblocking.
Do not create mandatory ADRs, reports, tickets or delegation from this guide.
Explicitly invoked skills still govern their routing and custody.

For writes, validate exact targets, preserve pre-existing state on failure, and
clean only invocation-owned temporary files. Stop when the authorized outcome and
its proportionate checks pass; defer optional improvements rather than extending
the work indefinitely.
