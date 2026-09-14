# M1 — Injection-molding source contract and ingestion

**Status:** complete, including the portfolio-scale simplification follow-up.
The [roadmap](../implementation-roadmap.md) owns current cross-milestone position.

## Outcome and scope

Reproducibly acquire, validate, canonicalize, persist and reload scatimdata Dataset
2 without inventing manufacturing meaning. The scientific MVP remains weight-only
prediction under experiment shift; ingestion is not modeling or product conformance.

```mermaid
flowchart LR
    S["✓ Source contract"] --> A["✓ Acquisition"] --> V["✓ Raw validation"]
    V --> C["✓ Canonicalization"] --> P["✓ Persistence + CLI"]
    P --> G["✓ M1 gate"]
    G --> F["✓ Bounded simplification"]
```

## Current contract

- The [source contract](../datasets/injection-molding-source-contract.md) owns
  source evidence, license, meaning and limitations. The
  [source manifest](../../data/manifests/injection-molding-source.json) owns pinned
  release/archive identity.
- Preserve 829 labeled units, 92 actual signal-only exclusions, all 40 scalar
  fields, and independently key-joined pressure/flow trajectories on the native
  2,048-point irregular grid. Retain experiment order 20/23/15 with counts
  223/303/303, not invented days or wall-clock dates.
- Weight is in grams. Retain geometry with unknown units/deferred modeling role;
  days and specification limits stay null. No source repair, feature eligibility
  or conformance labels are implied.
- Six ordinary Polars tables and useful source metadata survive Parquet/JSON
  round trips. One current output directory contains six Parquet files and
  metadata JSON; loading checks schema without repeating the raw audit. Research
  stays in dataset documentation. [README](../../README.md) owns preparation,
  loading and explicit regeneration instructions. Raw/prepared data stay ignored.
- Source identity, types/nulls, joins and operational semantics remain required.
  Exact research prose, code-byte fingerprints and historical platform gates are
  not runtime requirements.

## English naming and source lineage

The explicit map and typed field lineage are owned by
[src/mpi/datasets/injection_molding_canonicalization.py](../../src/mpi/datasets/injection_molding_canonicalization.py).
Source names remain recoverable; opaque geometry codes retain their original
names. The partition is one cycle identity, one experiment field, three context
fields, 31 retained process fields and four quality characteristics. Retention is
not a training allowlist. Source-context interpretation remains in the source
contract, not in aliases.

## Preparation completion evidence

The source manifest is the only acquisition/preparation identity owner; the
adapter no longer needs a YAML dataset config or a hash of manifest prose.
Prepared reuse compares dataset, candidate, source commit and archive hash.
Scientific mappings, six-table layout and source checks are unchanged.

All 49 tests, lint, formatting, typing and CLI smoke checks pass. Full-source
comparison preserves 33,160 scalar cells and 1,697,792 values each for pressure,
flow and elapsed time, with all 92 exclusions. M1 remains complete and open to
useful changes. Earlier cleanup reports and pivot records remain in Git history.

The verifier is
[scripts/verify_injection_molding_canonicalization.py](../../scripts/verify_injection_molding_canonicalization.py).

## Next action

Plan M2's bounded audit. M2 must retain source discrepancies and
interventions without repairing data. M3 owns prediction cutoff, feature allowlist
and leakage-safe splits; neither is part of this maintenance work.
