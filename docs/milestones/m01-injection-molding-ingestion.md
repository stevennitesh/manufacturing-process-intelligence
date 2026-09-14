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
  round trips. The research dossier remains in dataset documentation. The offline preparation CLI and independent loader are documented
  in [README](../../README.md). Raw/prepared data and local receipts stay ignored.
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

The [portfolio-sized data contract](m01-contract-simplification.md) owns the current
layout. The latest simplification removes artifact hashing/staging, Git-state
metadata, runtime research payloads and copy-on-access wrappers. Scientific
transformations remain unchanged. See the
[overbuilding report](../reports/m1-overbuilding-review.md) for the changes,
verification and causes. M1 is complete.

The verifier is
[scripts/verify_injection_molding_canonicalization.py](../../scripts/verify_injection_molding_canonicalization.py).

## Next action

Plan M2's bounded audit. M2 must retain source discrepancies and
interventions without repairing data. M3 owns prediction cutoff, feature allowlist
and leakage-safe splits; neither is part of this maintenance work.
