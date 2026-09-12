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

## Scope and starting point

M1 delivers the SoliDAIR data foundation for the predictive-quality MVP. The
[technical specification](../plans/Manufacturing%20Quality%20%26%20Process%20Intelligence%20%E2%80%94%20Greenfield%20Technical%20Specification%20%26%20Implementation%20Plan.md)
owns scope, particularly sections 17–21 and Milestone 1. This document translates
that scope into execution order and evidence needed for completion.

M0 supplies the Python/uv environment, package, CLI shell, configuration, logging,
tests, and CI. The SoliDAIR configuration is disabled with no source URL and an
`unacquired` version. Source discovery and ingestion have not started. This plan
does not establish any facts about the actual distribution.

Included: source verification, acquisition, provenance, dataset-specific parsing,
validation, deterministic Parquet outputs, and a reproducible data audit.

Excluded: train/test split implementation, fitted preprocessing, baselines,
modeling, uncertainty estimation, inspection policies, dashboards, other dataset
adapters, and production services. M1 records evidence needed by M2 to choose
splits and prevent leakage; M2 implements those decisions.

## Subsystem plan

| Subsystem | Responsibility and deliverable | Depends on | Completion evidence |
| --- | --- | --- | --- |
| Source contract | Verify authoritative distribution, release/version, access requirements, license, and raw/derived redistribution terms. Inspect a sample and record file inventory, unit identity, target meaning, measurement units, and simulation/production provenance. | M0 | Cited source notes, license record, and sample inventory; consequential unknowns are resolved or explicitly constrain the usable scope. |
| Acquisition | Provide documented acquisition through `mqi data pull solidair`, using automated download where permitted or actionable manual-placement instructions where required. | Source contract | The supported acquisition path obtains the selected release; missing access, missing files, and failed downloads cannot report success. |
| Raw evidence | Preserve acquired files unchanged; record source, version, acquisition date, file inventory, sizes, and cryptographic hashes in a manifest. | Acquisition | Every input used by preparation is accounted for and hash-verified; reruns reuse matching inputs and identify mismatches. |
| Dataset adapter | Parse SoliDAIR into its declared `DatasetBundle` portion: `units`, `process_features`, `quality`, and `metadata`. Keep source-specific semantics in the adapter. | Verified sample and raw evidence | Synthetic contract fixtures prove identity and target mappings; a real-data run produces the declared bundle without silent row loss or unsupported semantics. |
| Validation | Check source structure and canonical schema, keys, joins, types, target validity, and declared missing-value rules. Separate fatal contract violations from audit findings. | Adapter contract | Valid fixtures pass; malformed and inconsistent inputs fail with actionable diagnostics; real-data findings are accounted for. |
| Processed data | Write stable Parquet tables and provenance linking them to raw hashes, adapter version, preparation configuration, and schema. | Adapter and validation | Reloaded outputs preserve the contract; repeated preparation in the locked environment produces identical processed file hashes. |
| Data audit | Generate `artifacts/audit/solidair_report.html` or an equivalent reproducible report from validated data. | Processed data and metadata | Report covers the required audit topics below, identifies the input version/hashes, and documents implications for M2. |

Each row is a work package, not a detailed implementation checklist. Expand a
subsystem's steps immediately before implementing it, using discoveries from its
prerequisites. Keep the diagram brief and attach completion evidence here as work
finishes.

## Execution sequence and decision points

1. **Discover the source and inspect a sample.** Establish authority, release,
   access, terms, file layout, dimensions, identifiers, targets, and provenance.
   Distinguish real production from simulation. Record upstream process fields,
   downstream measurements, suspicious identifiers, and available time/group
   fields. Confirm whether authoritative specification limits exist.
2. **Record the ingestion contract.** Select the supported release and input
   subset. Define table keys, join cardinalities, target representation, units,
   missingness policy, and metadata from evidence. Settle acquisition behavior,
   local layout, manifest fields, and deterministic output rules. Update this
   plan where discovery changes assumptions before detailing downstream work.
3. **Build acquisition and raw provenance.** Exercise the supported path with
   actual source files. Establish rerun behavior and handling of incomplete or
   changed inputs before preparation consumes them.
4. **Complete one preparation path.** Implement the minimal SoliDAIR bundle,
   validation, and Parquet persistence together. Verify the actual CLI-to-output
   handoff, synthetic failure cases, and real-data contract compliance.
5. **Produce the audit and M2 handoff.** Review findings and document unresolved
   limitations, candidate targets/features, and evidence for chronological or
   grouped evaluation. Do not infer chronology from row order or fabricate groups.
6. **Run the milestone gate.** Reproduce preparation from the documented starting
   state, repeat in an isolated output location, compare hashes, and record the
   commands, input identity, results, and remaining limitations.

Source/access/license uncertainty is an initial dependency, not a verified blocker.
If evidence prevents lawful acquisition or a meaningful unit-to-quality mapping,
record the specific blocker and seek a scope decision before substituting a dataset.
Absent optional time/group fields or specification limits must be recorded as
limitations; they must not be manufactured to satisfy the contract.

## Interfaces and artifact ownership

The intended public commands follow the technical specification:

```text
uv run mqi data pull solidair
uv run mqi data prepare solidair
uv run mqi audit solidair
```

These commands are planned, not yet implemented. `data pull` owns acquisition;
`data prepare` owns raw verification, parsing, validation, and processed output;
`audit` consumes validated processed data and its metadata. Failed prerequisites
must yield a nonzero exit and an actionable explanation. Failed preparation must
not leave partial output labeled as a completed dataset.

The single-command reproduction gate is `uv run mqi data prepare solidair` once
the documented acquisition prerequisite is satisfied. Separately verify the
complete acquisition-to-audit sequence starting with no local SoliDAIR data.
If access requires manual download, document that prerequisite explicitly; do not
describe the workflow as an unattended download from an empty directory.

| Location | Planned contents |
| --- | --- |
| `src/mqi/` | Adapter, minimal bundle contract, validation, preparation, audit, and CLI integration; exact module boundaries settled when implementing. |
| `configs/datasets/solidair.yaml` | Verified source/version and preparation settings; enable only when supported. |
| `DATA_LICENSES.md` and dataset documentation under `docs/` | Source citations, access and redistribution terms, data dictionary, acquisition/preparation instructions, and limitations. |
| `data/raw/solidair/` | Unmodified local source files, outside Git. |
| `data/processed/solidair/` | Validated local Parquet outputs, outside Git. |
| `data/manifests/` | Version-controlled provenance and hashes, without credentials or machine-specific private paths. |
| `artifacts/audit/` | Generated local audit report, outside Git. |
| `tests/` | Small synthetic fixtures and contract/integration tests; no downloaded dataset dependency in CI. |

The manifest must include dataset name/version, source, download date, raw and
processed file hashes, adapter version, row/column counts, and preparation settings.
Record split strategy as not yet implemented in M1, with available split evidence;
M2 owns selection and implementation. Keep run-specific timestamps out of
deterministic table content; provenance timestamps may differ between acquisitions.
Pin and record the environment needed for byte-identical Parquet reproduction.

## Audit coverage and handoff to M2

The report must cover dimensions, feature types, target definitions, missingness,
constant/near-constant features, duplicate observations, feature and target
distributions, high correlations, potential target leakage, suspicious identifiers,
simulation versus production distinctions, and available grouping/time variables.

Document each field's known meaning and availability where evidence exists. Flag
unknown timing or provenance explicitly. Preserve original observations; any
filtering, deduplication, coercion, or missing-value treatment requires a documented
rule and counts showing its effect. Do not fit imputation, scaling, or feature
selection across the dataset in M1.

The M2 handoff identifies supported quality targets, candidate upstream features,
fields to exclude or investigate for leakage, available grouping/time keys,
specification-limit availability, and unresolved validity risks. Recommendations
about splits must distinguish source evidence from assumptions.

## Acceptance gate and progress evidence

M1 is complete only when all of the following are verified:

- [ ] Source identity, selected release, access, license, and redistribution terms
  are documented with authoritative references.
- [ ] Acquisition from an empty local SoliDAIR data directory succeeds by the
  documented supported procedure, including any explicit manual prerequisite.
- [ ] Raw files remain unchanged and all consumed inputs have verified hashes.
- [ ] One preparation command produces validated, reloadable Parquet outputs and
  a manifest tying them to raw inputs, adapter, configuration, and environment.
- [ ] Repeating preparation with identical inputs/settings in the locked
  environment produces identical processed hashes in an isolated output location.
- [ ] Contract tests cover identity, joins, target mappings, missingness rules,
  malformed inputs, and observable failure/rerun behavior.
- [ ] The audit is reproducible and covers every required topic, with explicit
  limitations and a usable M2 handoff.
- [ ] Required Ruff lint/format, Pyright, pytest, and CLI smoke checks pass; CI uses
  synthetic data and does not require external downloads or training.
- [ ] Git changes contain only permitted documentation, code, configuration,
  manifests, and synthetic fixtures; generated data and reports remain outside Git.
- [ ] Gate evidence records the tested commit, commands, source/input hashes,
  processed hash comparison, report location, and check results.

Current evidence: planning only; no ingestion completion is claimed. Update the
subsystem diagram as execution progresses. The
[implementation roadmap](../implementation-roadmap.md) owns cross-milestone status;
mark M1 complete there only after this gate passes.
