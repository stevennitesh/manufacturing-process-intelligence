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

## Accepted MVP use and claim boundary

The revised canonical plan requires **Dataset 2 part weight in grams only** for
v0.1. Geometry remains preserved in the source/canonical quality table, with
unresolved units and experimental/deferred modeling status; resolving it is not
a weight-MVP prerequisite. The project tests whether pressure/flow information
improves scalar-only predictions under experiment shift, without assuming success.

Primary validation is leave-one-experiment-out over IDs 15, 20 and 23; no day
relabeling. The canonical plan's M3 owns exact development, calibration and test
partitions and the prediction-time process allowlist. All source-derived quality
fields are outcomes. Source integral columns are process summaries with unresolved
state/availability semantics, not established quality-derived quantities; exclude
them from baseline predictors until cleared. Retained data is not an approved
training matrix. Context-augmented models, cavity pressure and state/integral
features are optional, separately identified experiments.

The MVP policy is AUTO-PREDICT / MEASURE, evaluated by measurement rate versus
accepted prediction error and by empirical interval coverage under shift. No
specification-based PASS/FAIL, quality-escape rate, longitudinal factory SPC or
physical RCA claim is supported by this contract. SPC/anomaly monitoring belongs
to a later admitted process/assembly source. No source repair or additional
dataset admission follows from the narrowed MVP scope.

Here, `raw` means the untouched downloaded **published release**, not a verified
complete dump of all laboratory acquisition records. The paper describes an
upstream AVAPS database; the database-to-ZIP export lineage is not fully supplied.
The [later paper's data-availability statement](https://doi.org/10.1515/ipp-2023-4457)
also points to scatimdata. No more complete public release was identified in the
bounded follow-up search. Preserve that provenance limit rather than claiming
that our matching hashes establish completeness of the original experiment.

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

### Paper-supported material and measurement context

[Paper sections 2.1 and 2.2.3](https://www.mdpi.com/2073-4360/15/4/978)
identify Dataset 2's material as BASF Ultramid B3EG6, PA6-GF30. This is known
dataset-level material context, not an unknown material or a per-part batch key.
The canonicalizer may repeat that source-declared constant for admitted units,
with dataset-level provenance; it must not derive material genealogy from `Charge`.

The paper identifies a Keyence IM-7020 optical measurement projector with maximum
measurement deviation 8 µm and a Sartorius Entris BCE323i-1S balance with maximum
linearity deviation 2 mg. Preserve these as distinct, paper-reported equipment
specifications. They are not part tolerances, acceptance limits, measured error
for each record, or a complete uncertainty budget. In particular, the optical
specification does not establish the HDF5 geometry storage scale.

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
a mean of 101.5591 and population variance of 0.00680747, close to the paper's
101.55 mm and 0.0068 mm². Neither the
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

### Intervention alignment evidence — inferred, not a day assignment

A read-only comparison on 2026-09-12 used the production validator on the pinned
Dataset 2 archive, grouped scalar rows by `Versuch` without sorting, and compared
contiguous runs of context values with [paper Table 2](https://www.mdpi.com/2073-4360/15/4/978).
Run lengths below count labeled scalar rows within an experiment, not machine
cycle-counter differences. This strengthens the day hypothesis beyond total counts.

| Source experiment | Observed runs: length × raw value | Candidate paper day and evidence status |
| --- | --- | --- |
| 20 | Moisture: 76 × 0.086, 86 × 0.180, 61 × 0.046 | Day 2: all three values and segment lengths match. Strong inference, not an explicit source key. |
| 23 | `Twkz`: 99 × 80, 103 × 90, 101 × 70 | Day 3: temperature sequence and segment lengths match. Strong inference, not an explicit source key. |
| 15 | Moisture: 89 × 0.050, 98 × 0.100, 116 × 0.150 | Day 1: lengths match, but paper values are 0.066%, 0.097%, 0.150%. Raw-versus-paper discrepancy remains unresolved. |

For experiment 23, raw moisture is entirely null; for 20 and 15, `Twkz` and
`Charge` are entirely null. Experiment 23's `Charge` runs are 152 rows at 1 and
151 rows at 2, which do not coincide with its temperature boundaries. Do not
equate charge codes to days or temperature settings.

The paper labels experimental moisture in percent and mold temperature in °C.
That supports the paper's intervention context, not a blanket unit assignment to
all machine fields. Keep raw values/nulls unchanged. Do not backfill missing
temperatures/moisture, replace experiment 15's values, reorder experiments to
paper order, or promote candidate days/start-up labels to canonical row facts.
The released values may reflect nominal settings, rounding or another export
choice, but none of these explanations is established. Author/export documentation
is needed to resolve the discrepancy and confirm the crosswalk.

Target measurements were produced online after the corresponding molded part was
removed. They are outcome fields and unavailable at process-prediction time.
Weight and all geometry measurements, any aggregates derived from quality
measurements, and row-order look-ahead are leakage paths if used as features.
`mittlerer Feuchtegehalt`, `Twkz`, `Charge`, and `Versuch` describe deliberate
experimental conditions; their feature availability at inference time must be
decided explicitly in M3 rather than assumed. Process-integral fields may be used
only if their source signals and state windows are complete by the prediction
cutoff selected later.

### Published feature set versus retained source columns

Paper section 2.2.3 says the artificially varied moisture values were recorded
as experimental context and not used as model features. Section 3.2 reports 12
scalar predictors. Section 2.2.1 enumerates the conceptual set: maximum injection
pressure, switchover injection pressure, melt cushion, injection time, hot-runner
temperature, and barrel heating zones 2–8 (4 + 1 + 7 = 12). Eleven have direct
name correspondences in each export; `werkzeugheizkreis_1` is a candidate for
hot-runner temperature, not an explicitly documented crosswalk. That published
modeling input is not the archive's 40 scalar
columns or the canonicalizer's 31 retained process columns. Keep the published
exclusion and feature count in metadata; do not claim paper replication from
ingesting every source field. An exact paper-feature-to-export crosswalk remains
unverified. This does not change the project's admission or remove source values.

M2 must distinguish experimental context from measured process inputs and expose
the moisture discrepancy. M3 must explicitly settle availability and the feature
allowlist before modeling; moisture remains context-only unless a separately
justified project policy changes that role. Any such policy is distinct from
reproducing the paper. Integral eligibility and prediction cutoff remain deferred.

### Follow-up source search and remaining gaps

On 2026-09-12, the publisher repository's current main branch still matched the
pinned commit. Its seven-commit history contained README changes and the three
archive uploads, not an explanatory code release or data dictionary; the API
returned no issues. The
[article XML](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC9959070/fullTextXML)
contained no supplementary-material elements, and its data-availability statement
pointed to the same repository. Dataset 2's single HDF5 member contained only
serialization-related attributes, not hidden unit, day or field descriptions.
These are bounded search findings, not proof that no further author-held material
exists.

The 92 signal-only cycles, geometry-code/scale mappings, machine signal units,
state/index meanings and the sampling discrepancy remain unresolved. Seek the
original export dictionary, preprocessing rules and experiment log to resolve
them; do not infer a missing-cycle cause from counts alone. No author contact or
external write was performed. The same authors' later
[early-cycle prediction paper](https://doi.org/10.1515/ipp-2023-4457) is a possible
M3/M5 research lead; only its abstract was inspected, so it does not resolve this
release's export semantics or authorize a prediction cutoff.

## Candidate selection and exclusions

### All-candidate evidence refresh — 2026-09-12

This refresh covers all three pinned archives, the full article XML (including
the final rows of Tables 1–3), publisher repository metadata, and targeted online
searches for the repository name, target names and corrections. It resolves
additional context, not every source ambiguity. The same pinned main commit,
zero issues, zero tags and zero releases were verified again. No located public
dictionary or correction established the missing export semantics. Related
papers' accessible abstracts are research leads, not substitutes for their
uninspected full texts or the original measurement/export logs.

#### Product and experimental context

The [article sections 2.2.2–2.2.4](https://pmc.ncbi.nlm.nih.gov/articles/PMC9959070/)
declare the following dataset-level context:

| Candidate | Product and material | Intervention families |
| --- | --- | --- |
| 1 | Housing; Repol Dinalon B1S25 G30-0288, PA6-GF30 | Four days; barrel/hot-runner temperatures, flow, pauses and mold temperatures |
| 2 | Stacking box I; BASF Ultramid B3EG6, PA6-GF30 | Three days; moisture and mold temperature |
| 3 | Stacking box II; Repol Dinalon B1S25 G30-0288, PA6-GF30 | Four days; flow, holding pressure, pauses and barrel/hot-runner temperatures |

These are controlled experiments, not uninterrupted factory production logs.
Shared polymer class, machine or mold does not make the candidates exchangeable:
do not pool them or use one candidate's material/units as another's row metadata.
The equipment context above applies to the shared experimental setup; it still
does not supply quality tolerances or per-record measurement uncertainty.

#### Target agreement and disagreement

After rechecking all archive sizes and hashes against the manifest, full CSV
inspection reconfirmed all Dataset 1/3 labeled joins and no scalar nulls. The
following are locally calculated full-population summaries, not rounded source
claims. Geometry is multiplied by 0.001 **only for this comparison**, not converted
in raw or canonical data. Variance uses denominator N (`statistics.pvariance`),
not N−1; small differences from published rounded statistics are not automatically
export defects.

| Candidate / field | N | Observed mean | Observed population variance |
| --- | ---: | ---: | ---: |
| 1 / weight | 1,167 | 58.920575 | 0.00230470 |
| 1 / distanceA × 0.001 | 1,167 | 85.963989 | 0.00080618 |
| 2 / GE-GE002* × 0.001 | 829 | 101.559141 | 0.00680747 |
| 3 / weight | 1,332 | 113.542345 | 0.19274482 |
| 3 / distanceB × 0.001 | 1,332 | 101.444400 | 0.01156231 |

Dataset 1 geometry disagrees with the paper's mean 84.9372 and variance 0.00043;
an additive offset cannot fix the variance mismatch. No located evidence identifies
a typo, alternate measurement or filtering rule as the cause. Do not offset or
rescale it to fit a published statistic. Dataset 3's corresponding rounded values
101.44 and 0.0116 agree closely, strengthening (but not proving) the proposed scale.
CSV target names identify intended Distance A/B more directly than Dataset 2's
opaque code, but none of the three archives supplies an authoritative geometry
storage-unit declaration. Weight remains the physical-unit-supported target.

#### Chronology corrections and indexing hypotheses

**Correction to our previous notes:** Table 3 does not stop at 1,240. The full
table includes **1,241–1,340**, day 4, with a +10% temperature intervention.
Withdraw the previous claim of 92 unassigned final labeled rows. This was our
incomplete table reading, not a newly corrected publisher release.

- Dataset 1 Table 1 reaches ordinal 1,174, equal to its signal count, not its
  1,167 labeled count. Its 385–467 / 458–528 overlap remains. Signal ordinals
  166/167 correspond to counters 25301/25315; ordinals 528/529 correspond to
  25679/25681. Those boundaries align with some counter discontinuities and
  zero `cycle_time` observations. This supports a **signal-ordinal hypothesis**,
  not a complete or authoritative day mapping. Labeled-row indexing would differ.
- Dataset 3 Table 3 still assigns 620–669 to both day 2 and a day-3 interval
  beginning at 620. Its final ordinal 1,340 equals neither 1,332 labeled rows nor
  1,405 signal columns. Signal ordinals 374/375 map to counters 23875/23987, a
  large discontinuity at the first paper day boundary. That partial alignment
  does not resolve the remaining day boundaries or the table's indexing basis.
- Both CSV scalar files are strictly increasing by cycle counter, with no day,
  experiment or wall-clock field. Dataset 1 has 24 counters absent within its
  labeled min/max range, Dataset 3 has 210. Those are not their signal-only
  counts: some counters occur in neither released table. Counter gaps cannot
  establish elapsed time, actual dates or a machine stop's duration.

Keep table ordinals, scalar row indices, signal column positions and machine
cycle counters as distinct coordinate systems. Never repair the overlaps, shift
all boundaries by a missing-row count, or assign startup/paused labels from
these hypotheses. The Dataset 2 intervention alignment above remains stronger
because an explicit experiment field exists, but canonical days still stay null.

#### Missing-record and scalar-value findings

- Dataset 1's seven signal-only counters are 25181, 25261, 25698, 25843, 25987,
  26167 and 26304. Dataset 3 has 73, including a contiguous run of 46 counters
  24535–24580. Their absence from the quality table does not establish rejection,
  measurement failure or intentional filtering.
- Dataset 2's 92 signal-only counters partition as 29 within experiment 15's
  labeled counter range, 42 within experiment 20's, none within experiment 23's,
  and 21 outside those ranges. Range membership is not an authoritative experiment
  assignment for an unlabeled cycle; exclusion reason remains
  `no_released_scalar_quality_row`.
- Dataset 1 has eight literal zero `cycle_time` values; Dataset 3 has twelve.
  Their zero-based scalar row indices are respectively
  `0,164,321,526,586,648,708,769` and
  `0,367,418,469,514,563,611,661,669,686,696,697`.
  No source explains whether zero is a reset/sentinel/measurement value.
  Preserve it if these candidates are later admitted; do not silently impute,
  reject, or label a physical zero-duration molding cycle from it.

#### What still needs the source owner

| Gap | Evidence needed | Until then |
| --- | --- | --- |
| Geometry scale/codes and Dataset 1 discrepancy | Optical measurement program, export unit/scale dictionary and evaluated target series | Keep native geometry and unknown units; no paper-equivalence claim |
| Days, ordinal overlaps and missing cycles in 1/3 | Experiment log plus exact ordinal-to-counter crosswalk and preprocessing/filter log | No canonical days or day-held-out claim for those candidates |
| Dataset 2 moisture and day mapping | Actual-versus-nominal moisture log and experiment/day crosswalk | Preserve discrepancy and source nulls |
| Machine units, integrals and state codes | Original controller node IDs, units, state definitions and AVAPS export schema | English names do not establish units, phases or feature availability |
| Shared 2,048-point irregular grid | Original acquisition/export and sampling configuration | Preserve explicit times; no padding or resampling in M1 |
| Quality limits, real dates, zero durations | Part specification and timestamp/controller logging semantics | Leave absent semantics unresolved; observed ranges are not tolerances |

For example, [EUROMAP 63](https://www.euromap.org/media/recommendations/63/2000/eu63.pdf)
distinguishes cushion stroke in mm from cushion volume in cm³; a generic translated
`melt_cushion` name cannot select between them. The
[AVAPS project owner](https://www.micromata.de/referenzen/avaps-machine-learning-spritzguss/)
and paper authors are appropriate clarification routes. No external contact was made.

Reproduction: use the identity-checked inspection command below for schemas,
counts and means. Additional CSV calculations stream the scalar members with
`csv.DictReader`, parse decimal commas as periods, compute full-column
`statistics.mean` / `statistics.pvariance`, and compare integer signal headers
against scalar counters by set difference. Zero-duration indices use original
zero-based scalar order; candidate boundary comparisons use one-based signal
positions. Dataset 2 comparisons use the production raw validator without sorting
its scalar experiment blocks. No raw file was modified by these checks.

### Admission consequence

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

Dataset 3 is not admitted. Its weight and inferred `distanceB / 1,000` summaries
agree closely with the paper, and all labeled cycles join. However, its paper
intervention table has an overlapping day assignment and an unresolved ordinal
basis, as corrected above; the CSV has no day/experiment field. It remains a
promising later candidate, not a scientifically unusable dataset. Dataset 2's
explicit experiment boundaries still provide the stronger primary validation
contract. Before either additional candidate enters implementation, establish a
defensible grouping/split contract (or explicitly accept a narrower claim), rerun
its admission gates, and plan its dataset-specific mapping. No pooled dataset or
additional adapter is authorized by this evidence refresh.

## Canonical bundle handoff

The admitted source can populate only supported sections:

| Bundle section | Supported mapping |
| --- | --- |
| `units` | `unit_id = injection_molding/dataset2/<cycle_counter>`; one physical part per cycle. Product family is stacking box; material is the paper-declared Dataset 2 constant BASF Ultramid B3EG6 (PA6-GF30), with dataset-level lineage. Exact production time is absent. |
| `operations` | One injection-molding operation per unit; process stage is injection molding. Machine model is source metadata, not a per-row machine field. Start/end wall-clock times are absent. |
| `process_features` | Source scalar process fields mapped to explicit English canonical names, preserving values, missingness and unresolved units; exact native names remain in lineage metadata and the raw-validation handoff. |
| `signals` | Injection pressure and flow keyed by namespaced cycle counter and explicit elapsed signal time. Cavity pressure is supported but optional. |
| `quality` | Weight in grams. Native geometry fields may be retained with unresolved storage units. Do not publish a millimetre conversion until authoritative scale evidence exists; an adapter assertion may enforce an evidence-backed conversion but cannot establish its unit. Spec limits are absent. |
| `context` | `Versuch` as experiment boundary; material/product/machine and three-day intervention plan as source metadata. Moisture, mold temperature, and charge remain nullable per row. Exact day labels and real timestamps are absent. |
| `metadata` | Paper/repository citation, commit, archive hash, source column descriptions, observed signal grid, license, and transformations. |

Canonical naming and its exhaustive scalar mapping are owned by the
[M1 English naming plan](../milestones/m01-injection-molding-ingestion.md#english-naming-and-source-lineage).
English aliases do not establish units or new source semantics. Raw files and
source-native validation retain original names; opaque geometry characteristic
codes remain unchanged in the canonical quality table. `Versuch` becomes
`experiment_id`, not a production-day label, and `Charge` becomes
`source_charge_code`, not an inferred batch identifier.

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
and writes an immutable local receipt beneath the source-version directory. This
is a local single-writer workflow; it does not create or clear acquisition locks.
A matching existing archive is rehashed and reused without a network request.

If existing bytes differ, the command exits nonzero and leaves them untouched;
investigate and preserve or remove those bytes manually before retrying. An HTTP,
timeout, truncation, excess-size, checksum, destination, or receipt failure also exits
nonzero. Only partial files owned by the failing invocation are removed. A verified
archive retained after receipt failure is safely recovered by rerunning the command,
which reuses the bytes and writes a new receipt.

Connection and blocking reads use a finite transport timeout. Size and SHA-256 are
checked before publication; truncated, oversized or mismatched downloads are never
published.

The typed acquisition result and acquisition CLI output mean byte-verified only.
They do not establish archive structure, the 829-cycle schema/join contract, or
preparation readiness. Production raw validation checks archive identity once before
reading the pinned member.
The dataset configuration is enabled for the verified preparation adapter.

## Prepare the admitted bundle

From the repository root, prepare and independently reload the pinned source with:

```powershell
$env:UV_CACHE_DIR = Join-Path (Get-Location) '.uv-cache'
uv run mpi data prepare injection_molding --raw-root data/raw/injection_molding
```

Preparation performs no download or source repair. It preserves the six canonical
tables, typed field lineage and the complete packaged research dossier in the
current metadata record. Reload verifies the required file hashes and scientific
whole-bundle invariants before publication. An exact existing destination
is reused unchanged; other existing destinations fail with guidance to choose a
new output. The default is `data/processed/injection_molding/dataset2`.
The artifact has no schema version or compatibility machinery.
The small artifact manifest records only required payload file
hashes; it is integrity evidence, not publisher authentication.

## Next action

Use the [roadmap](../implementation-roadmap.md) for current work and the
[M1 summary](../milestones/m01-injection-molding-ingestion.md#preparation-completion-evidence)
for the completed preparation handoff. The portfolio-scale simplification changes
engineering obligations, not the source evidence recorded here. A later M2
audit must not repair discrepancies or begin M3 feature/split decisions.
