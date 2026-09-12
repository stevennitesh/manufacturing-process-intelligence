# Implementation roadmap

This is the concise status view of the
[greenfield implementation plan](plans/Manufacturing%20Quality%20%26%20Process%20Intelligence%20%E2%80%94%20Greenfield%20Technical%20Specification%20%26%20Implementation%20Plan.md).
The plan remains the authority for scope and acceptance criteria.

**Current position:** Milestone 0 is complete. Milestone 1 is next.

## Status key

- `✓` complete and verified
- `▶` next milestone or subsystem
- `◐` in progress
- `○` planned
- `⚠` blocked

```mermaid
flowchart TB
    F["✓ M0 · Foundation<br/>Platform system: runtime, package, CLI, configuration, logging, tests, CI"]

    MVP["v0.1 · Predictive Quality MVP<br/>▶ M1 Data: SoliDAIR ingestion<br/>○ M2 Evaluation: splits and baselines<br/>○ M3 Modeling: quality model<br/>○ M4 Uncertainty: conformal coverage<br/>○ M5 Decisions: inspection policy<br/>○ M6 Experience: dashboard and release"]

    V1["v0.2 · Process Intelligence<br/>○ M7 Data: CiP-DMD adapter<br/>○ M8 Monitoring: process statistics<br/>○ M9 Detection: physical anomalies<br/>○ M10 Diagnostics: attribution and QC linkage"]

    V15["v0.3 · Productionization<br/>○ M11 Operational platform: tracking, API, batch, Docker, drift, CI"]

    V2["v0.4 · Semiconductor Transfer<br/>○ M12 Data: plasma ingestion and synchronization<br/>○ M13 Modeling: virtual metrology<br/>○ M14 Validation: transfer, drift, and architecture reuse"]

    F --> MVP --> V1 --> V15 --> V2
```

## Milestone drill-downs

- [M0 — Repository foundation](milestones/m00-foundation.md)
- [M1 — SoliDAIR ingestion](milestones/m01-solidair-ingestion.md)

Create a later milestone drill-down only when that milestone is approaching. GitHub
Issues track individual tasks; these diagrams track subsystem readiness and gates.

## Updating status

Update this page and the active milestone diagram together. Change a subsystem to
`✓` only when its named artifact exists and its relevant verification passes. Mark
the milestone complete only when its acceptance gate passes end to end.
