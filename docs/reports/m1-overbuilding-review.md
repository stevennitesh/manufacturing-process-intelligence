# M1 overbuilding review and bounded simplification

## Conclusion

The feedback is substantially right. M1 had accumulated production-style
reliability around a small, local, reproducible dataset. The source investigation
was valuable; the artifact-management machinery was not proportional to this
personal manufacturing-data-science portfolio.

This follow-up simplifies that machinery and leaves M1 complete. M2's dataset
audit is next; M1 remains open to useful changes as the project evolves.

## What changed

| Area | Excess | Replacement |
| --- | --- | --- |
| Persistence | Per-payload hashes, manifest models, staged publication, fsync, link checks, serialized self-validation and exact candidate comparison | Six Parquet writes plus metadata; ordinary loading and table-schema checks |
| Reuse | Revalidate raw data, reconstruct every table and compare with saved tables | Load existing output and check configured source identity; regeneration is explicit |
| Bundle | Private table handles and clone-on-every-access properties | Frozen dataclass containing ordinary Polars tables |
| Metadata | Git discovery/dirty state, acquisition-time state machine, copied validation log, runtime research dossier | Source commit/archive identity, citations/license, lineage, transformations, exclusions and limitations |
| Research | Packaged JSON required to canonicalize and copied into every output | All 15 records preserved in dataset documentation, linked from the source contract |
| Tests | Mechanism-specific tampering, staging, context-state and defensive-copy cases | Table/metadata round trip, missing table/schema errors, no overwrite, source mismatch and real raw-to-CLI integration |
| Context | Standing instructions and progress text describing the elaborate artifact contract | Reconciled README, source contract, M1 contract/summary and roadmap; concrete scope rules at existing guidance owners |

Persistence fell from 461 to 140 lines; the canonical data types fell from 150 to
84. The suite went from 69 to 59 tests. These are consequences of deleting
requirements, not targets or evidence of correctness by themselves.

No schema versions, compatibility readers or new dependencies were added.
The current ignored prepared output was cut over to the smaller metadata and its
obsolete generated manifest removed. Its six Parquet files were unchanged.

## What remains justified

- Pinned source commit, raw archive hash and licensing evidence.
- 829 labeled cycles, 92 actual signal-only exclusions and independent cycle-key
  alignment for pressure and flow.
- Native 2,048-point irregular timestamps, weight in grams, preserved nulls and
  honest unknown geometry units, chronology and specification limits.
- Validation of raw inputs and the canonical transformation. Loading now checks
  structure rather than repeating the full scientific audit.
- The six existing tables and explicit English/source field mapping. Their shape
  is larger than a single modeling dataframe, but another redesign now would
  spend time without advancing the experiment.
- Configured lint, formatting, typing, tests and one useful CLI integration.

Acquisition still has more defensive machinery than this project strictly needs.
It was left unchanged: it works, and replacing it would enlarge this maintenance
pass without improving the next analysis. It is not a template for later phases.
The independent source-comparison script remains an occasional verification tool,
not an additional mandatory gate for unrelated edits.

## Deliberate tradeoffs

This is a trusted local workflow, not a tamper-resistant artifact store.
Schema-valid manual changes to saved values are not automatically detected.
Reuse does not detect changed transformation code; explicitly regenerate when
transformations change. An interrupted write may leave a partial directory for
inspection/removal. Concurrent publication and automatic recovery are not supported.
These limitations are now documented instead of hidden behind extensive machinery.

## Where the overbuilding happened and why

These are inferences from the reviewed code, tests, active contracts and supplied
feedback, not a reconstruction of every prior agent decision.

1. **Scientific reproducibility expanded into artifact certification.** Keeping a
   raw hash and correct cycle joins was necessary. Rehashing derived Parquet,
   checking producer Git state and validating staged publication solved different,
   lower-value reliability problems. I should have kept that distinction explicit.
2. **Preserving research became a runtime contract.** Important source facts,
   inferences and discrepancies were treated as mandatory machine payloads.
   Documentation was the appropriate owner for the dossier; useful lineage and
   limitations still belong with the tables.
3. **Defensive programming became a default rather than a response to a caller.**
   Protected dataframe handles and candidate equality assumed consumers and failure
   modes beyond the actual single-user workflow.
4. **Requirements reinforced themselves through tests and plans.** Once a
   hardening mechanism appeared in an acceptance checklist, removing it looked
   like losing coverage. The correct question was whether that requirement helped
   the supported experiment, not whether its implementation could be cleaner.
5. **Earlier simplification did not sufficiently challenge the contract.**
   Removing duplication or rearranging helpers could leave the expensive behavior
   intact. Broad reminders to avoid production engineering were already present;
   the failure was applying them to concrete decisions, not merely missing wording.

Responsibility rests with the planning/review decisions I accepted, not simply
with an implementer producing code to the assigned contract.

## Corrections in context and future skill use

The existing engineering guide now distinguishes scientific metadata from a
research dossier and explicitly excludes a derived-data artifact registry by
default. It also requires reviewing the usefulness of a mechanism before adding
tests for it. The progression guide clarifies that milestone completion does not
restrict later changes; improvements are assessed by their current value.

For future planning, implementation and review skill use:

- State the current scientific/demo outcome and its stopping condition in the
  existing brief. Do not create a separate governance document.
- Admit additional requirements only for a concrete wrong result, broken ordinary
  workflow or substantial maintenance burden. Hypothetical production use is not
  sufficient.
- Assign an implementer the smallest complete path and the actual acceptance
  scenarios, not a list of desirable infrastructure properties.
- Have reviewers challenge unnecessary requirements as well as incorrect code.
  Optional robustness should not silently become a delivery blocker.
- Verify the authorized result. Judge further improvements by concrete project
  value, not by the possibility of adding more defenses or abstractions.

These are recommended operating changes for the planning/cost-aware workflows,
not claims that their skills mandated the excess. Global skill files were not
changed or audited in this pass. The writing-for-agents skill guided the local
context reconciliation: concrete decisions at existing owners, without a new
workflow or extra approval gate.

## Verification

- 59 tests passed; Ruff lint and formatting, Pyright and CLI version passed.
- Fresh offline preparation and existing-output reuse passed.
- Independent full-source comparison passed for both the freshly written bundle
  and the current local output: all 33,160 scalar cells, 1,697,792 values each for
  pressure, flow and elapsed time, plus lineage, nulls and all 92 exclusions.
- All six fresh Parquet files were byte-identical to the existing files.
- All 15 research records were preserved structurally during the documentation move.
- Raw source bytes and acquisition code were unchanged.

The upstream source is scatimdata commit
`7bd35941d75c97a3f276439377dc430ab47402be`; source hashes remain owned by
the version-controlled source manifest. No training, M2 implementation, commit or
push was performed.
