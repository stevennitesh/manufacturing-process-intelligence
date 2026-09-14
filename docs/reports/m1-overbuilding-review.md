# M1 overbuilding review

## Current conclusion

The remaining excess was primarily process/context overhead and acquisition
bookkeeping, not the manufacturing science. This second pass removes those
requirements rather than introducing another refactor architecture.
M1 remains complete and open to useful future changes. M2 audit planning is next,
not started by this cleanup.

## Changes in this pass

| Area | Finding | Correction |
| --- | --- | --- |
| Acquisition | Download receipts, chronology and hard-link/fsync publication for one small pinned ZIP | Read at most expected size + one byte, verify size/SHA, save with exclusive creation; matching local bytes reuse offline |
| Raw validation | Receipt discovery, field checks, chronology ranking and unused producer-version fields | Removed end to end; HDF parsing and scientific checks unchanged |
| CLI/tests | Receipt output/obstruction tests, legacy-lock test and assertions about deleted temporary-file machinery | Removed; retained normal download/reuse, wrong bytes, failed network, joins and raw-to-prepared integration |
| Agent guidance | Root instructions plus five separate governance/routing documents | One 52-line AGENTS.md with conditional context reads and proportionate engineering |
| Master specification | 2,926 lines of science mixed with future scaffolds, recipes and contradictory provenance obligations | 254-line docs/spec.md preserving scientific milestones, acceptance, release priorities and limitations |
| Historical files | Nine abandoned source/plan/script/test files inside .archive | Removed from current tree; recoverable at Git commit 60e3c25 |
| Future scaffold | Unadmitted Bosch/CiP configs and six .gitkeep files | Removed; add real files when their work begins |
| References | Pointers to retired guides/plan/archive and receipt behavior | Reconciled README, roadmap, source contract, licensing, ADR and milestone text |

The five old guides plus root instructions totaled 287 lines; the new root file
has 52. Acquisition fell from 456 to 323 lines; raw validation from 778 to 680.
The spec is about 16 KB. Line counts describe the deletion, not quality targets.
Persistence and canonical tables were not redesigned in this pass.
Ignored raw/prepared data and existing local receipt files were left untouched;
receipt files are no longer read, written or required by the program.

## Why this was overbuilt

### The detailed spec contradicted the simplified context

The retired plan's section 29 still said every processed dataset should generate
download timestamps, processed hashes, adapter versions and Git commits. Its
earlier portfolio-scale disclaimer and the newer M1 contract said otherwise.
An agent could reasonably follow the concrete checklist while missing the broad
exception. The previous cleanup corrected implementations and nearby guidance
but failed to remove that competing instruction.

Its large proposed directory tree and conceptual adapter interface also made
future capabilities look like current implementation tasks. The new spec retains
outcomes and scientific constraints, not that scaffold or provenance checklist.

### A retired consumer left a live subsystem

The first simplification removed chronology from bundle metadata but left receipt
creation, discovery and validation behind. Download time no longer had a consumer
or a scientific role. I followed the earlier recommendation to leave acquisition
alone without tracing what the metadata deletion made unnecessary. That was a
scope-selection mistake, not a need for another receipt framework.

### Anti-ceremony rules became ceremony

The repo instructed agents to read separate engineering, domain and progression
documents, alongside roadmap/milestone material. Tracker templates existed despite
no tracker requirement for direct work. Even though many reads were conditional,
this split inflated the default path and created multiple places to synchronize.
I added more proportionality prose in the previous pass instead of removing the
indirection. The correction is one compact local owner, not another governance layer.

### Reproducibility was conflated with resilience

A source hash, valid joins and correct units protect the result. Receipt chronology,
fsync and hard-link publication address a different operational concern. For one
8.7 MB public archive on a local single-user workflow, a bounded in-memory download
and no-overwrite save are sufficient. I should have separated those concerns
before accepting the implementation obligations.

### Tests and history made mechanisms look permanent

Tests can protect an unnecessary subsystem as effectively as a useful one.
Likewise, archiving old scripts/tests kept retired ideas discoverable in the
checkout. Git already preserves them. The correction is to assess the behavior's
current value, remove its obsolete tests with it, and retain history in Git.

These causes are supported by the reviewed code, context and installed skills.
They do not establish which historical skill revision produced each earlier line;
the planning/review choices I accepted remain my responsibility.

## Do the skills contribute?

Yes, specific defaults can cause overbuilding. Others mainly need proportionate
application. This audit read the installed instructions; it did not execute their
delegation workflows or change personal/global skill files.

| Skill/reference | Concrete pressure | Recommended skill correction |
| --- | --- | --- |
| repo-bootstrap, references/setup-defaults.md and agent-instructions.md | Initial setup seeds four separate agent documents and domain/tracker routes; instruction guidance expects a separate engineering pointer | Default small single-user repos to one AGENTS.md. Split only when content has a demonstrated separate reader. Make tracker setup conditional on actual tracker use. Preserve a compact local override on later refreshes. |
| shape-work, references/durable-decisions.md | Directs wholly obsolete documents into repository-root .archive | Allow deletion of Git-tracked obsolete material after preserving active decisions and fixing links. Make an archive directory opt-in, not universal. |
| shape-work, SKILL.md and acceptance-meaning.md | Detailed boundary/state questions can be expanded into failure-state catalogs | Keep the existing supported-workflow/cheapest-evidence rules; explicitly stop details that do not change a consequential outcome. These instructions already say optional mechanisms are not acceptance. |
| cost-aware-coding, SKILL.md and references/planned-delivery.md | Pair custody, review and checkpoint records add fixed coordination cost | Use its existing direct-work exception when a handoff cannot repay its cost. Use final-only review when no intermediate boundary justifies a checkpoint; do not turn each subsystem into a gate. |
| writing-for-agents | Reconciliation can become another document inventory if applied mechanically | Use its existing one-owner/prune rules to consolidate documents, as here; no additional workflow is needed. |

The strongest actual default problems are bootstrap's file inventory and shaping's
mandatory local archiving. Cost-aware coding does not prescribe receipts, hashes
for generated files, defensive dataframe wrappers or a large runtime framework.
Its guidance already limits trivial-task delegation and unnecessary reviewers.
Blaming the implementer or the entire skill pack would miss the faulty accepted
requirements and competing project instructions.

The repo now explicitly records the compact-file/Git-history convention in
AGENTS.md so future skill-template refreshes should not recreate the removed
structure. Global skill edits remain a separate, cross-repository decision.

## What was deliberately kept

- Exact source commit/hash/license and all dataset research, including unresolved
  units, chronology, quality limits and paper/release discrepancies.
- Source membership, pressure/flow joins and native time-grid checks.
- Existing HDF parser, canonical transformation and six-table shape. Some internal
  format checks and transformation self-checks remain more exact than necessary,
  but rewriting them here would add risk without advancing analysis.
- A small injectable transport for offline tests, bounded network timeout, source
  URL/config agreement and basic destination handling. These have current callers;
  they are not a generic downloader framework.
- Existing completed milestone summaries, source ADR, independent comparison
  script, CI and locked environment. Small useful evidence need not be deleted
  simply because the phase is complete.

For later adapters, verify source identity, parse needed data and check meaningful
keys/shapes. Do not reproduce the exhaustive source-discovery audit at every helper.
Keep transformation correctness primarily in focused reference tests.

## Verification and tradeoffs

- 56 tests pass, plus Ruff lint/format, Pyright and CLI version.
- Actual local archive acquisition/reuse and raw validation pass:
  829 matched, zero labeled-only and 92 signal-only cycles.
- The raw-to-prepared CLI integration uses a generated HDF fixture; scientific
  parsing/mapping behavior remains covered. No new live network download was needed.
- Current prepared-output reuse and independent full-source comparison pass:
  all 33,160 scalar cells, pressure/flow/time values and 92 exclusions match.
- Local Markdown file links and Git whitespace checks pass.
- No model training, M2 implementation, commit or push was performed.

The downloader now holds roughly 8.7 MB in memory. A filesystem write failure can
leave a partial destination; a later hash check rejects it and tells the user to
inspect/remove it. It does not promise atomic publication, concurrent-writer
recovery or download chronology. These are explicit local-workflow tradeoffs,
not missing production features.

## Previous pass, retained as history

Commit 60e3c25 removed artifact manifests/checksums/staging, Git-state metadata,
runtime research payloads and copy-on-access wrappers. Persistence fell from 461
to 140 lines and canonical types from 150 to 84; tests went from 69 to 59.
All 15 research records moved unchanged to dataset documentation.
Independent verification matched 33,160 scalar cells and 1,697,792 pressure,
flow and time values each, with all 92 exclusions. Fresh and existing Parquet
files were byte-identical. That proof remains relevant to unchanged transformations;
it did not justify keeping the now-unused receipt subsystem.
