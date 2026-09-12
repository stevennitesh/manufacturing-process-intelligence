# M1 — SoliDAIR ingestion

**Status:** `▶ Next`

**Objective:** reproducibly acquire, validate, transform, and audit the authoritative
SoliDAIR distribution without committing third-party data.

```mermaid
flowchart LR
    S["▶ Source contract<br/>authority, version, license, access"]
    A["○ Acquisition<br/>download instructions and metadata"]
    R["○ Raw evidence<br/>immutable files, checksums, manifest"]
    D["○ Dataset adapter<br/>SoliDAIR parsing and DatasetBundle"]
    V["○ Validation<br/>schema, identity, targets, missingness"]
    P["○ Processed data<br/>deterministic Parquet outputs"]
    U["○ Data audit<br/>leakage, groups, time, distributions"]
    G{"○ M1 gate<br/>one command reproduces validated processed data"}

    S --> A --> R --> D --> V --> P --> U --> G
```

## Tracked outputs

- source and download documentation;
- raw-data provenance manifest and checksums;
- SoliDAIR dataset adapter;
- validation rules and contract tests;
- deterministic processed Parquet layout;
- reproducible data-audit artifact.

## Gate

From an empty local data directory, the documented acquisition and preparation
commands produce validated processed data and a provenance manifest. A repeat run
with identical source inputs produces identical processed hashes.

Source identity, licensing, unit and target meaning, production versus simulation
status, and available grouping or time fields must be established from evidence.
Do not invent missing semantics or specification limits.

The [implementation roadmap](../implementation-roadmap.md) owns the current
cross-milestone status.
