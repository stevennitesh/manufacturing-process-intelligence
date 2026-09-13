# Injection-molding source contract

**Decision:** Accept with limitations

**Admitted input:** scatimdata `dataset2.zip`, labeled subset of 829 cycles

**Source version:** commit
`7bd35941d75c97a3f276439377dc430ab47402be`

**Verified:** 2026-09-12

This contract admits a source for M1 implementation. It does not claim that an
adapter, prepared bundle, split, or model exists. Exact acquired-file identities
are owned by the
[source manifest](../../data/manifests/injection-molding-source.json).

## Authority, relationship, and terms

The source is the publisher-maintained
[`sc4t1m/scatimdata`](https://github.com/sc4t1m/scatimdata) repository. Its README
names the three archives as the data for Bogedale et al., *Online Prediction of
Molded Part Quality in the Injection Molding Process Using High-Resolution Time
Series*, and gives the paper DOI and required citation. The
[peer-reviewed paper](https://doi.org/10.3390/polym15040978) likewise describes
three public data sets containing 1,167, 829, and 1,332 labeled cycles. This
two-way agreement establishes the relationship between the repository and paper.

The repository README at the pinned commit states that **the data set** is
licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/legalcode.en). This is
data-specific license evidence, not an inference from the paper's separate
license. CC BY 4.0 grants reproduction, sharing, and adaptation, including
database extraction and reuse where database rights apply. Sharing requires
attribution, a license notice and link, a source link where practicable, and a
modification notice when applicable. It does not grant patent, trademark,
privacy, or endorsement rights.

Consequently:

- anonymous automated Git retrieval and local inspection/processing are
  permitted and were verified;
- raw and derived material may be published under the stated conditions;
- published project material must cite Bogedale et al., link this source and CC
  BY 4.0, and identify transformations; and
- project policy remains stricter than the license: raw and prepared data stay
  outside Git. Public portfolio outputs should be aggregate or derived and carry
  attribution even though compliant raw redistribution is legally available.

The repository has no tag or GitHub release. The immutable source identity is
therefore commit `7bd35941d75c97a3f276439377dc430ab47402be`, dated
2023-02-21, with all recovery URLs pinned to that commit. The three archives were
acquired only after the preceding terms were checked.

## Source-declared manufacturing meaning

All experiments used an Arburg Allrounder 520E 1500-800 injection-molding
machine and single-cavity molds with hot runners. At each cycle a handling robot
removed one molded part and presented it to automated weighing and optical
measurement. The paper states that the machine cycle counter was assigned to
both process and quality records during the experiment, making one cycle counter
the link among the injection cycle, its process data, and its physical part.

The paper describes:

- scalar actual-value-log process measurements, including maximum and
  switchover injection pressure, melt cushion, injection time, hot-runner
  temperature, and barrel-zone temperatures;
- per-cycle injection-pressure and injection-flow trajectories;
- part weight and 15 optical geometry measurements for each part, of which the
  study selected one high-variance geometry target per data set; and
- deliberately varied settings/disturbances, start-up operation, pauses, and
  multiple production days.

The physical entity of an admitted labeled record is one molded part produced by
one machine cycle. The released HDF5 is wide: a trajectory column represents one
cycle, and its suffix is the machine cycle counter. Rows represent elapsed signal
time samples. This is not a real production timestamp.

## Frozen inventory and observed structure

All sizes below are locally observed uncompressed member sizes. Archive sizes and
SHA-256 hashes are intentionally not duplicated here; the manifest owns them.

| Candidate | Archive members and roles | Observed labeled shape | Observed signal shape |
| --- | --- | --- | --- |
| Dataset 1, housing part | `ds1_scalar_and_quality.csv` (scalar process plus weight and `distanceA`); injection-flow and injection-pressure CSVs | 1,167 × 21 | each 2,048 time rows × 1,174 cycle columns; 24.97 MB flow and 35.91 MB pressure members |
| Dataset 2, stacking box I | `dynamic_data_versuch_large.h5` containing `scalars`; injection pressure, injection flow, and cavity pressure; plus three state matrices | 829 × 40 | each main signal is 2,048 time rows × 921 cycle columns; 91.27 MB HDF5 member |
| Dataset 3, stacking box II | `ds3_scalar_and_quality.csv` (scalar process plus weight and `distanceB`); injection-flow and injection-pressure CSVs | 1,332 × 20 | each 2,048 time rows × 1,405 cycle columns; 30.35 MB flow and 42.92 MB pressure members |

The CSV files use comma delimiters and encode many decimal fractions with a
comma inside quoted fields. Dataset 2 is a pandas fixed-format HDF5 file. Its
top-level groups are `scalars`, `Einspritzdruck`, `Einspritzstrom`,
`Werkzeuginnendruck`, and corresponding `_states` groups. Inspection reads data
only; it never executes source code.

### Dataset 2 scalar and quality fields

The 40 observed columns are:

```text
Versuch, mittlerer Feuchtegehalt, Twkz, Charge, cycle_counter, cycle_time,
Max. Spritzdruck, Umschaltspritzdruck, staudruck_ist, einspritzzeit,
Massepolster, dosierzeit, zylinderheizzone_1..8, werkzeugheizkreis_1,
integral_idx_0_werkzeuginnendruck_ist_state_1/2/8,
integral_idx_0_messgrafik_state_1/2/8,
integral_idx_1_messgrafik_state_1/2/8,
integral_idx_0_einspritzdruck_ist_state_1/2/8,
integral_idx_0_einspritzstrom_ist_state_1/2/8,
weight, GE-GE002*, GERADEHEIT-L*, PT-PT002L*
```

`cycle_counter`, `Versuch`, and several geometry fields are stored as integers;
the remaining scalar blocks are floating point. The only HDF5 missing values are
526 each in `Charge` and `Twkz`, and 303 each in `mittlerer Feuchtegehalt` and
`PT-PT002L*`. Weight, `GE-GE002*`, and `GERADEHEIT-L*` are present for all 829
admitted cycles. Missing context values are source nulls, not zeros.

The paper supplies grams for weight and millimetres for the selected geometry
measure. Released `GE-GE002*` values are integer-like and dividing by 1,000 gives
a mean of 101.5591, which corroborates the paper's 101.55 mm mean. Neither the
repository nor paper explicitly documents that storage scale or maps the HDF5
name to the published "Distance B" label. The adapter must therefore preserve
native values and treat `GE-GE002* × 0.001 mm` as a proposed conversion, not an
established unit contract. An adapter assertion cannot establish that unit: an
authoritative scale source is required before publishing converted millimetre
values. Weight alone is a fully source-supported physical target, so this geometry
limitation does not defeat source admission.
Units for individual machine-native scalar and signal values are not declared in
the released files and remain unknown unless supported during adapter work.

No authoritative lower or upper quality specification limits are supplied.
They must remain absent; observed ranges are not specification limits.

## Signal length and sampling discrepancy

The paper says every trajectory has 2,049 points at 6 ms resolution. Every
released trajectory inspected across all three archives has **2,048** elapsed-time
rows from 0.000 through 12.276 seconds. The dominant increment is 0.006 seconds,
but three transitions are 0.004 seconds (at rows 512, 1,024, and 1,536 using a
zero-based destination index). Thus the release is neither 2,049 rows nor a
perfectly uniform 6 ms grid.

The release, not the prose expectation, governs ingestion. A future adapter must
validate and preserve all 2,048 observed samples and their explicit time values;
it must not pad, resample, or fabricate the missing duration. M5 may later decide
how to represent the slightly irregular grid. That decision is outside M1.

## Identity, joins, and admitted membership

All counts below cover full candidate inputs, not samples.

| Candidate | Labeled unique cycles | Signal unique cycles | Labeled matched to required pressure + flow | Signal-only | Duplicate cycle keys | Labeled without required signals |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Dataset 1 | 1,167 | 1,174 | 1,167 | 7 | 0 | 0 |
| Dataset 2 | 829 | 921 | 829 | 92 | 0 | 0 |
| Dataset 3 | 1,332 | 1,405 | 1,332 | 73 | 0 | 0 |

Within each candidate the required pressure and flow cycle sets are identical.
Dataset 2's cavity-pressure set is also identical to its pressure and flow sets.
The join key is `(dataset identity, machine cycle counter)`; the dataset namespace
is required because counters are machine-local and the three candidates are
different experiments/products. Each admitted Dataset 2 cycle has exactly one
scalar/quality row and exactly one column in each required signal matrix, so the
admitted joins are one-to-one at the cycle level.

The 92 Dataset 2 signal-only cycles have no released scalar/quality row. Their
meaning is not stated. They remain immutable source evidence but are excluded
from the labeled MVP population by an explicit anti-join. This is not silent row
dropping. A future adapter must assert the exact `829 matched / 0 labeled-only /
92 signal-only` cardinality against the pinned source before selecting the 829
labeled cycles.

## Chronology, experiments, and availability

`cycle_time` is a machine-cycle duration, not a wall-clock timestamp. No admitted
field contains a date or time of day. Consequently, exact real production
timestamps, elapsed time across cycles, and the chronological duration of pauses
cannot be reconstructed.

Dataset 2 contains three contiguous `Versuch` (experiment/trial) groups in file
order:

| `Versuch` | Rows | Machine-cycle range |
| ---: | ---: | ---: |
| 20 | 223 | 20627–20897 |
| 23 | 303 | 20933–21235 |
| 15 | 303 | 20191–20528 |

The paper's experimental plan describes three production days with ordinal block
sizes 303, 223, and 303 and controlled changes in granulate moisture and mold
temperature. Those counts agree with the three file groups, but the HDF5 group
order is 223, 303, 303 and the paper does not directly map `Versuch` values to day
numbers. It is therefore supported to use `Versuch` as an experiment boundary;
calling a particular value "day 1", "day 2", or "day 3" would be an inference.
Experiment-held-out validation is feasible later without that inference. Sorting
all rows globally by `cycle_counter` would change source order and is not an
authorized substitute for a real timestamp.

Target measurements were produced online after the corresponding molded part was
removed. They are outcome fields and unavailable at process-prediction time.
Weight and all geometry measurements, any aggregates derived from quality
measurements, and row-order look-ahead are leakage paths if used as features.
`mittlerer Feuchtegehalt`, `Twkz`, `Charge`, and `Versuch` describe deliberate
experimental conditions; their feature availability at inference time must be
decided explicitly in M3 rather than assumed. Process-integral fields may be used
only if their source signals and state windows are complete by the prediction
cutoff selected later.

## Candidate selection and exclusions

Dataset 2 is the primary MVP input because it provides complete physical weight,
two complete released geometry measurements, the required pressure and flow
signals for every labeled cycle, an explicit experiment boundary, and
source-declared three-day process interventions. Its HDF5 format and additional
cavity-pressure/state matrices add adapter work but do not weaken the scientific
or validation contract. The admitted feature floor is scalar process values plus
injection pressure and injection flow; cavity pressure, state matrices, and
integrals are optional extensions and must not enlarge the MVP silently.

Dataset 1 is not admitted. Its released `distanceA / 1,000` mean is 85.9640,
whereas the paper reports 84.9372 mm, and its paper intervention table has an
overlapping ordinal interval (385–467 and 458–528). The CSV has no day field with
which to resolve the conflict. Its weight remains scientifically usable, but it
does not improve the primary contract enough to justify unresolved chronology
and target-scale ambiguity.

Dataset 3 is not admitted. Its weight and inferred `distanceB / 1,000` mean agree
with the paper, and all labeled cycles join. However, the paper intervention
table overlaps ordinal 620–669 with a day-three block beginning at 620 and stops
at ordinal 1,240 despite 1,332 labeled rows. The CSV has no day field. The missing
92 ordinal assignments happen to equal the 92-row shortfall but have no
authoritative mapping to the 73 signal-only cycles or any other source construct;
no repair is inferred.

## Canonical bundle handoff

The admitted source can populate only supported sections:

| Bundle section | Supported mapping |
| --- | --- |
| `units` | `unit_id = injection_molding/dataset2/<cycle_counter>`; one physical part per cycle. Product family is stacking box; exact production time is absent. |
| `operations` | One injection-molding operation per unit; process stage is injection molding. Machine model is source metadata, not a per-row machine field. Start/end wall-clock times are absent. |
| `process_features` | Source scalar process fields, preserving native names, values, missingness, and unresolved units. |
| `signals` | Injection pressure and flow keyed by namespaced cycle counter and explicit elapsed signal time. Cavity pressure is supported but optional. |
| `quality` | Weight in grams. Native geometry fields may be retained with unresolved storage units. Do not publish a millimetre conversion until authoritative scale evidence exists; an adapter assertion may enforce an evidence-backed conversion but cannot establish its unit. Spec limits are absent. |
| `context` | `Versuch` as experiment boundary; material/product/machine and three-day intervention plan as source metadata. Moisture, mold temperature, and charge remain nullable per row. Exact day labels and real timestamps are absent. |
| `metadata` | Paper/repository citation, commit, archive hash, source column descriptions, observed signal grid, license, and transformations. |

Unsupported sections stay null or absent. In particular, do not invent batch IDs
from `Charge` where it is null, wall-clock production times, per-row day labels,
quality limits, signal units, or complete geometry-unit mappings.

## Admission gates

### Scientific suitability — pass with limitations

The paper and full-file joins establish a direct process-telemetry-to-physical-part
weight relationship for 829 cycles. Required scalar, injection-pressure, and
injection-flow inputs exist for every admitted target. Geometry-unit ambiguity
limits geometry claims but does not affect the admitted weight target. This
source supports predictive-quality and virtual-metrology work; it does not by
itself support causal claims, production deployment claims, or conformance
classification without quality limits.

### Validation suitability — pass with limitations

Unique namespaced cycle IDs prevent cross-table identity leakage. `Versuch`
provides three non-overlapping experiment groups, and the paper independently
describes three production days and interventions with matching group sizes,
making experiment-held-out validation possible. Exact group-to-day labels and
wall-clock times are unavailable, so downstream work must describe this as
experiment-group generalization unless a stronger mapping is found. Final split
design belongs to M3.

### Portfolio suitability — pass

The data-specific CC BY 4.0 statement permits public derived artifacts with
attribution and modification notice. The dataset contains machine/process and
physical measurements, not personal data. Project policy will keep raw and
prepared records out of Git and publish only compliant derived evidence.

### Overall decision — accept with limitations

All three gates pass for the Dataset 2 labeled subset. The admitted contract is
bounded to 829 namespaced cycles, weight as the fully supported physical target,
and required pressure/flow signals at their observed 2,048-point grid. The
limitations above constrain claims and adapter behavior without changing the
accepted MVP requirement.

## Reproduce the inspection

From the repository root, clone the immutable source beneath the ignored raw-data
directory, then run the read-only evidence tool:

```powershell
git clone --no-checkout https://github.com/sc4t1m/scatimdata.git data/raw/injection_molding/scatimdata-7bd35941d75c97a3f276439377dc430ab47402be
git -C data/raw/injection_molding/scatimdata-7bd35941d75c97a3f276439377dc430ab47402be checkout --detach 7bd35941d75c97a3f276439377dc430ab47402be
$env:UV_CACHE_DIR = Join-Path (Get-Location) '.uv-cache'
uv run --with h5py==3.16.0 python scripts/inspect_injection_molding_source.py data/raw/injection_molding/scatimdata-7bd35941d75c97a3f276439377dc430ab47402be
```

The verified run used Python 3.12.12, transient `h5py` 3.16.0, and its resolved
NumPy 2.5.3. The tool streams the CSV members, temporarily extracts the HDF5
member to the operating system temporary directory, prints JSON evidence, and
deletes that temporary copy. Before opening any archive, it compares every local
archive's byte size and SHA-256 with the default repository manifest; use
`--manifest <path>` only to verify against another explicitly reviewed manifest.
An identity mismatch names the file and exits nonzero without parsing it. After
identity passes, the tool verifies member inventory,
schemas, nulls, trajectory grids, cycle-key uniqueness, full joins, and selected
target summaries. It does not prepare or alter data.

The inspected local clone and temporary manual extracts are ignored by Git.
Exact expected hashes are in the source manifest. An identity mismatch is a hard
failure: preserve and report mismatched bytes rather than replacing or admitting
them.

## Acquire the admitted archive

Production acquisition is intentionally narrower than the three-candidate
inspection workflow above. From the repository root, acquire only the admitted
Dataset 2 archive through its immutable HTTPS URL:

```powershell
$env:UV_CACHE_DIR = Join-Path (Get-Location) '.uv-cache'
uv run mpi data acquire injection_molding
```

The default destination is
`data/raw/injection_molding/scatimdata-7bd35941d75c97a3f276439377dc430ab47402be/dataset2.zip`.
Use `--raw-root <directory>` to isolate the destination. The command validates
configuration/manifest agreement before effects, streams to an invocation-owned
partial file, checks the manifest size and SHA-256, publishes without overwriting,
and writes an immutable local receipt beneath the source-version directory. A
matching existing archive is rehashed and reused without a network request.

If existing bytes differ, the command exits nonzero and leaves them untouched;
investigate and preserve or remove those bytes manually before retrying. An HTTP,
timeout, truncation, excess-size, checksum, ownership, or receipt failure also exits
nonzero. Only partial files owned by the failing invocation are removed. A verified
archive retained after receipt failure is safely recovered by rerunning the command,
which reuses the bytes and writes a new receipt.

Connection and individual blocking reads use a finite transport timeout. The overall
deadline is checked before and after each read, after transport closure, and before
archive publication. The standard-library HTTPS reader cannot be cancelled in the
middle of a blocking read before its finite transport timeout returns, but a read or
EOF that returns after the overall deadline is rejected and never published.

The typed acquisition result and acquisition CLI output mean byte-verified only.
They do not establish archive structure, the 829-cycle schema/join contract, or
preparation readiness. Production raw validation rechecks archive identity when it
consumes this handoff.
The dataset configuration remains disabled for preparation.

## Next action

Implement the [Dataset 2 canonicalization plan](../milestones/m01-injection-molding-ingestion.md#next-phase--canonicalization)
from the completed raw-validation handoff when authorized. Keep
`configs/datasets/injection_molding.yaml` disabled until adapter preparation can
consume the admitted source. ManufacturingBundle mapping is planned, not implemented;
canonical Parquet, M2 audit, and M3 split design remain deferred.
