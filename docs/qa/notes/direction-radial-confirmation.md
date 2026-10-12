# Radial-plane direction cut: pre-registered confirmation (QA round 8, Task B; QA-19, roadmap 25.3b / 27.2)

- **Code:** master `f86df9a`. Prereg: `PREREG_R8.md`, commit `6b0aedf` on branch `prereg/round8` in the QA-only clone
  `/workspace/fansim/qa/prereg_r6`, sha256 `b958dda3a884a3ec7aac0899131e0b9f3efdabf6a951c3745dbcd5940fec67e9`.
  It was committed before any B build. A copy is in `docs/qa/PREREG_R8.md`.
- **Readers:**
  - cylinder = `prove_direction` at `f86df9a`;
  - radial = round 7's `prove_direction_stacking(mode="radial")`, byte-identical copy in
    `handoff/2026-10-12_from-qa-8/scripts/stacking_cut.py`. No tuning.
- **Scripts:** `scripts/sample_b.py` (seed 20261012), `run_b.py`, `run_b_flip_v2.py`, `analyse_b.py`.
  Data: `data/b_results.jsonl.gz` (v1, as registered), `data/b_results_v2merged.jsonl.gz` (scored set),
  `data/b_analysis_v2.json.gz`.
- **Sample.** All parts are new: none of round 7's 67 F parts, none of the 65 round-7 stress builds, no 9601–9630.
  Drawn from the round-7 stress `inputs.jsonl`:
  - 22 parts in the S3_0014 cell (|camber| 0.02–0.04, lean_tip ≥ 30°);
  - 16 flat leaned parts (|camber| < 0.02, lean ≥ 20°);
  - 26 ordinary parts (camber ≥ 0.04, round-robin over S1–S8);
  - 10 featured parts across those cells;
  - 5 flipped-camber parts;
  - S3_0014 as a named extra;
  - both references.
  Every part was also read mirrored (y → −y). No part moved cell after the build.
- **Blade count:** **2-blade rebuilds**, as in round 7. References were used as supplied.

## Deviation: the brief's flipped parts are flat, not backwards
Setting `max_camber = −0.03` and bypassing `validate_blade_params` builds a **flat** blade. The NACA camber
line returns zero camber for m ≤ 0 (`fansim/geometry/airfoil.py:61` in `naca4`, `:102` in
`_naca_camber_line`). In v1 (as registered) all 5 such parts read "no cambered sections" or a lean-induced
split, and one (S2_0088) failed to build with OCCT "Courbes non jointives".

So v2 wraps `blade.section_loop_2d` **in the QA process only**. For m < 0 it builds the |m| section and
mirrors it across the chord line, which gives a true negative-camber NACA section. v2 is the scored set; v1
results are kept in the data.

This is not a bug: the validator refuses negative camber upstream. But a negative camber that slips past the
validator is silently flattened, not rejected.

## Results (72 parts; mirrors give identical counts)

| reader | OK | can't tell | **WRONG** | OK on cambered parts (\|camber\| ≥ 0.02, n=54) | mirror chirality flips |
|---|---|---|---|---|---|
| cylinder (`prove_direction`) | 48 | 18 | **6** | 46/54 | 54/54 of CONCLUSIVE |
| radial-plane | 61 | 11 | **0** | **54/54** | 61/61 |
| combined, R5 (both CONCLUSIVE and equal, else ask) | 45 | 27 (ask) | **0** | 43/54 (79.6 %) | 45/45 |

By cell (cylinder / radial / combined):
- S3cell (22): cyl 13 OK + 9 INC; radial 22 OK; combined 13 OK + 9 ask.
- flatlean (16): cyl 3 OK, 8 INC, **5 WRONG**; radial 5 OK + 11 INC; combined 16 ask.
- ordinary (26): cyl 25 OK + 1 INC (S5_0231, featured); radial 26 OK; combined 25 OK + 1 ask.
- flipped v2 (5): both read (−1, +1, −1), i.e. OK for a negative-camber design.
- S3_0014: cyl **WRONG** (−1, +1, −1) again, radial OK; combined asks.
- references: both OK under both readers.

**Wrong or can't-tell parts:**

| part | cell | design camber | lean_tip ° | cylinder | radial |
|---|---|---|---|---|---|
| S3_0014 | extra (S3 cell) | 0.0242 | 42.0 | **WRONG** (−1,+1,−1) | OK |
| S4_0176 | flatlean | 0.0091 | 39.4 | **WRONG** | INC |
| S1_0225 | flatlean | 0.0079 | 40.9 | **WRONG** | INC |
| S8_0053 | flatlean | 0.0122 | 36.4 | **WRONG** | OK |
| S4_0068 | flatlean | 0.0084 | 33.6 | **WRONG** | INC |
| S5_0203 (featured) | flatlean | 0.0165 | 40.0 | **WRONG** | OK |
| S5_0209 (featured), S4_0333, S1_0105, S4_0194, S4_0065, S4_0155, S1_0515, S8_0102, S1_0304 | S3cell | 0.020–0.034 | 30.8–45.0 | INC | OK |
| S5_0231 (featured) | ordinary | 0.0428 | 39.2 | INC | OK |
| S5_0164 (featured), S1_0188, S1_0452 | flatlean | 0.008–0.020 | 21.9–44.5 | INC | OK |
| S4_0225, S3_0128, S4_0181 | flatlean | 0.005–0.011 | 20.8–27.2 | OK | INC |
| S8_0048, S4_0122, S4_0385, S1_0514, S4_0316 | flatlean | 0.002–0.020 | 31.3–39.5 | INC ("no cambered sections") | INC (same) |

## Pre-registered rules

| rule | result | verdict |
|---|---|---|
| R1: radial 0 CONCLUSIVE-wrong (originals + mirrors) | 0/144 | **PASS** |
| R2: radial ≥ 95 % on cambered parts | 54/54 = 100 % (v1, with the flat "flipped" parts counted as cambered: 49/53 = 92.5 %) | **PASS** (v2) |
| R3: every CONCLUSIVE radial part's mirror flips chirality | 61/61 | **PASS** |
| R4: both references radial-correct | a12x25 OK, FAN-01 OK | **PASS** |
| R5: combined rule 0 wrong **and** ≥ 90 % read | 0 wrong; 43/54 = 79.6 % | **FAIL** (on coverage: the cylinder is INC on 9/22 S3-cell parts) |
| R6: builder rule refuses no S3-cell part, every mirror, all 5 flipped | S3 cell + S3_0014: 0 refused ✓; mirrors: 5 not refused ✗ (the 5 fully flat parts, where neither reader finds a cambered section, so chirality is unknown); flipped: **0/5 refused** ✗ | **FAIL** |
| R6b (secondary, 0.02 trust gate) | identical to R6 | FAIL |

**Why R6 cannot catch a flipped part as written.** The rule compares the geometry with
`sign(design camber)`. For a −0.03 design the geometry agrees with that sign (both readers give (−1, +1)),
so "both disagree" is never true. The production caller passes `signed_design_camber(params)`
(`blade.py:791`, used in `objectives.py:369` and `quick_screen.py:73`), so the shipped
`builder_direction_refusal` would not refuse it either.

A backwards blade can only be caught against the **intended spin**. Post hoc and not registered: comparing
the split with the builder's fixed (ω +1, pump −1) when both readers are CONCLUSIVE refuses all 5 flipped
parts and no other part in this sample. Today the builder cannot produce such a blade anyway: the
validator rejects m < 0, and the builder flattens it.

## Plain-language verdict
- **The radial-plane cut is confirmed on fresh parts.** It made 0 wrong calls on 72 new parts and their
  mirrors, read every cambered part (including all 22 in the S3_0014 cell where the cylinder check fails
  or gives up), and detected every mirror it could read. Where it can't tell, the parts are essentially flat.
- **The combined "both must agree" rule is safe but too timid.** The cylinder check gives up on 9 of the 22
  S3-cell parts, so requiring agreement throws away good radial readings.
- **The builder rule as worded can't catch a backwards blade**, because it trusts the design's own camber
  sign. It does correctly leave all S3-cell parts alone (it would have fixed the S3_0014 false refusal).

## Proposal (no diff)
- **External STLs (25.3b):** add `prove_direction_radial` beside `prove_direction` and use a **radial-led**
  rule:
  - accept the radial reading when it is CONCLUSIVE and the cylinder is either INCONCLUSIVE or agrees;
  - ask for the spin when they disagree, or when the radial reading is INCONCLUSIVE.
  This is post hoc, not registered. On this sample it gives 0 wrong (originals and mirrors) and reads
  53/54 cambered parts; only S3_0014 is asked. It needs its own pre-registered confirmation, ideally on more
  real external STLs than the two references.
- **Builder (27.2):**
  - refuse on chirality ≠ −1 from either reader;
  - refuse on the split only when **both** readers are CONCLUSIVE and both disagree. This removes the
    S3_0014-type false refusals (0/23 refused here).
  - If a backwards-blade check is wanted, compare with the intended spin, not with the design camber sign.
  - Optionally have `validate_blade_params` keep rejecting m < 0 at every entry point. The builder
    flattens such sections silently.
