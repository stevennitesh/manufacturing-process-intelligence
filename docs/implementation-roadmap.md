# Implementation roadmap

This is the concise status view of the
[canonical greenfield implementation plan](plans/Manufacturing%20Process%20%26%20Quality%20Intelligence%20%E2%80%94%20Greenfield%20Specification%20and%20Implementation%20Plan.md).
The plan owns scope and acceptance criteria; this roadmap owns current position.

**Current position:** Milestone 0 is complete. Milestone 1 is in progress: the
injection-molding source contract, reproducible Dataset 2 acquisition, and strict
raw validation are complete. Dataset 2 canonicalization is the next subsystem;
its [detailed plan](milestones/m01-injection-molding-ingestion.md#next-phase--canonicalization)
is saved and awaiting implementation authorization. Persistence remains deferred.

## Status key

- `✓` complete and verified
- `▶` next milestone or subsystem
- `◐` in progress
- `○` planned
- `⚠` blocked

```mermaid
flowchart TB
    F["✓ M0 · Foundation<br/>Runtime, mpi package and CLI, configuration, logging, tests, CI"]

    MVP["v0.1 · Predictive Quality MVP<br/>◐ M1 Source contract + ingestion<br/>○ M2 Data audit<br/>○ M3 Validation strategy<br/>○ M4 Baselines<br/>○ M5 Time-series representation<br/>○ M6 GBDT quality model<br/>○ M7 Uncertainty<br/>○ M8 Selective measurement<br/>○ M9 Explainability<br/>○ M10 Dashboard"]

    PI["v0.2 · Process Intelligence<br/>○ CiP-DMD ingestion, SPC, anomaly detection, diagnosis"]
    PROD["v0.3 · Productionization<br/>○ Tracking, API, batch scoring, Docker, drift, operational CI"]
    SEMI["v0.4 · Semiconductor Transfer<br/>○ BOSCH plasma virtual metrology and transfer validation"]
    PHARMA["v0.5 · Regulated Transfer<br/>○ Pharmaceutical batch quality and genealogy"]
    ADV["v0.6 · Optional Advanced Manufacturing<br/>○ Additional transfer case only if earlier gates justify it"]

    F --> MVP --> PI --> PROD --> SEMI --> PHARMA --> ADV
```

## Milestone drill-downs

- [M0 — Repository foundation](milestones/m00-foundation.md)
- [M1 — Injection-molding source contract and ingestion](milestones/m01-injection-molding-ingestion.md)

The [planning and progression guide](agents/planning-and-progression.md) defines
when to expand milestone plans, how to track subsystem progress, and what evidence
is required to close a gate. These diagrams summarize readiness; linked milestone
documents hold execution details and evidence.
