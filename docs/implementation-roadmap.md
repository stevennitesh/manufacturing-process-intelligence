# Implementation roadmap

This is the concise status view of the
[canonical greenfield implementation plan](plans/Manufacturing%20Process%20%26%20Quality%20Intelligence%20%E2%80%94%20Greenfield%20Specification%20and%20Implementation%20Plan.md).
The plan owns scope and acceptance criteria; this roadmap owns current position.

**Current position:** Milestones 0 and 1 are complete. The injection-molding source
contract, reproducible Dataset 2 acquisition, strict raw validation, protected
canonicalization, exact Parquet/JSON persistence, safe publication/reuse and the
offline preparation command are verified. The durable loader needs only the named
artifact and returns the same protected bundle contract. The
[portfolio-sized data contract](milestones/m01-contract-simplification.md) uses one
unversioned artifact layout, without legacy readers or compatibility machinery.
Reuse writes nothing and preparation resolves its inputs and receipt once.
M2 audit planning is next; M2 implementation has not begun.
The adapter retains all admitted source evidence
while enforcing the weight-only MVP policy boundary.
The [all-candidate source refresh](datasets/injection-molding-source-contract.md#all-candidate-evidence-refresh--2026-09-12)
has been incorporated into that plan; Dataset 1/3 remain inspected, not admitted.

**Accepted scope:** v0.1 tests Dataset 2 part-weight prediction under experiment
shift: scalar versus engineered/compressed trajectories, conformal uncertainty
and AUTO-PREDICT / MEASURE. Geometry is retained but deferred, and SPC/physical
diagnostics are outside this MVP. This revision changes plans, not completion
status. Leave-one-experiment-out is the primary benchmark; M3 must freeze its
cutoff, feature allowlist and leakage-safe calibration/tuning protocol before M4.

## Status key

- `✓` complete and verified
- `▶` next milestone or subsystem
- `◐` in progress
- `○` planned
- `⚠` blocked

```mermaid
flowchart TB
    F["✓ M0 · Foundation<br/>Runtime, mpi package and CLI, configuration, logging, tests, CI"]

    MVP["v0.1 · Weight Prediction Under Process Shift<br/>✓ M1 Dataset 2 ingestion<br/>✓ Bounded simplification<br/>▶ M2 Audit planning<br/>○ M3 Experiment holdouts + feature contract<br/>○ M4 Mean, Ridge, PLS<br/>○ M5 Engineered + compressed trajectories<br/>○ M6 LightGBM + representation comparison<br/>○ M7 Conformal + shift evaluation<br/>○ M8 Selective measurement<br/>○ M9 Bounded predictive explanation<br/>○ M10 Five-page dashboard"]

    AUDIT{"○ Source decision gate<br/>PyScrew vs CiP-DMD<br/>Cross-process-chain audit"}
    PI["v0.2 · Process / Assembly Intelligence<br/>○ Selected adapter, SPC/MSPC, anomalies, supported diagnostics"]
    SEMI["v0.3 · Semiconductor Transfer<br/>○ Bosch Plasma source gate, virtual metrology and shift study"]
    PROD["v0.4 · Optional Engineering Demo<br/>○ Select a role-relevant capability, not a production platform"]
    PHARMA["v0.5 · Optional Regulated Transfer<br/>○ Pharmaceutical batch quality and genealogy"]
    ADV["v0.6 · Optional Advanced Manufacturing<br/>○ Additional transfer case only if earlier gates justify it"]

    F --> MVP --> AUDIT --> PI --> SEMI --> PROD --> PHARMA --> ADV
```

Apply at a credible v0.1 (target week 6); later source audits and the semiconductor
case study strengthen the story. Semiconductor work can be prioritized for an
interview once prerequisites pass, without requiring productionization first.
Pharma/advanced manufacturing are optional in the first three months. The
canonical plan's section 79 owns the relative 12-week schedule. SoliDAIR is retired
from the required core. No new source is admitted by this roadmap.

## Milestone drill-downs

- [M0 — Repository foundation](milestones/m00-foundation.md)
- [M1 — Injection-molding source contract and ingestion](milestones/m01-injection-molding-ingestion.md)
- [M1 — Portfolio-sized data contract](milestones/m01-contract-simplification.md)

The [planning and progression guide](agents/planning-and-progression.md) defines
when to expand milestone plans, how to track subsystem progress, and what evidence
is required to close a gate. These diagrams summarize readiness; linked milestone
documents hold execution details and evidence.
