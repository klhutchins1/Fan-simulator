# Task F: can a "stacking-line cut" read the spin direction of external STL fans? (round 7, QA)

Master `5980677`. Prototype only; `prove_direction` is untouched. Patches are proposals only.

## Plain-language verdict
**No, not this version.** The idea is to slice each blade square to its own lean instead of with a cylinder. It was meant to fix the flat, leaned blades that the current cylinder check reads backwards. It does not fix them. On one of them (9630) it gives the same confidently wrong answer as the cylinder check. On the other six it says "can't tell", which is safe but no help. It also gives up on far more good fans than the current check (40 vs 52 of 67 read correctly).

Mirror detection is fine: every mirrored blade read with confidence came out mirrored. Both real reference fans (the a12x25 and FAN-01) were read correctly.

A simpler variant that came up while doing this is promising: cut along flat planes through the axis, one per radius ("radial-plane"). It made **0 wrong calls** and read all 54 normally cambered parts. It also correctly rescued 3 of the 7 flat-blade cases that the cylinder check gets wrong. **But it was not pre-registered**, so treat it as a lead, not a result.

## Pre-registration
`PREREG_R7.md` sha256 `c163f1d7eaa6b4763871b2542d1b18e3ca5d34f6562e7878db35686cf52d0e6e`. It was committed as `2073315` on branch `prereg/round7` in the QA-only clone `/workspace/fansim/research/repo_research` before any F data was produced.

Rules, verbatim in substance:
- **F1:** 0 CONCLUSIVE-wrong.
- **F2:** CONCLUSIVE-correct on ≥ 90 % of parts with |design camber| ≥ 0.02.
- **F3:** 9605, 9606, 9620 and 9630 are each correct or INCONCLUSIVE.
- **F4:** every CONCLUSIVE part's y-mirror gives the opposite chirality (100 %).
- **F5:** both references are CONCLUSIVE-correct.
- **F6:** 0 wrong where the cylinder proof is CONCLUSIVE-wrong.
- **Adoption:** only if F1, F3, F4 and F6 all PASS. If F2 or F5 fails, adopt only with "INCONCLUSIVE → explicit spin".

## Method
- **Function.** `prove_direction_stacking(mesh, r_fracs, mode)`, in `handoff/2026-10-11_from-qa-7/scripts/stacking_cut.py`.
  - It tracks each blade's centroid over 25 cylinder cuts (0.50 to 0.97 of the tip radius).
  - It fits the stacking line (quadratic over 5 neighbours) and cuts the mesh with the plane normal to that line at the same radii as `prove_direction`.
  - It reads the camber in the in-plane frame (θ̂ projected onto the plane).
  - It uses the same filters and thresholds as `prove_direction` (camber 0.02, t/c 0.25, residual 0.5, ≥ 2 radii, agreement 0.9).
  - `mode="radial"` instead uses the plane through the axis that is normal to θ̂ at the blade centroid. Same reading and filters.
- **Population, 67 parts, each also mirrored (y → −y):**
  - all 46 builder designs: stock, the 15 non-stock rows in `cfd_designs.csv`, and screen_r3 9601–9630 (which include 9605, 9606, 9620 and 9630);
  - 16 stress designs, the first 2 by id in each stratum S1–S8, from `/workspace/fansim/qa/r6_stress/inputs.jsonl` (the prereg allowed up to 20);
  - the 3 round-6 K5-fail designs, S3_0002, S4_0005 and S4_0012;
  - the 2 references, `validation/reference/a12x25_impeller.stl` and `validation/reference/fan01/fan01_rotor.stl`.
- **Disclosure: 2-blade rebuilds.** Builder and stress parts were rebuilt with **2 blades**, not their real count. This kept memory low while another worker's stress run was going (fuse memory ≈ 0.37 GB + 86 kB per face). Every check here reads blades one at a time and sums over blades, so the blade count does not change the per-section reading. References were used as-is.
- **Run conditions.** Single core, `nice 19`, one build at a time.
- **Expected answers:**
  - builder parts: (ω +1, pump −1, χ −1); mirror (−1, −1, +1);
  - a12x25: χ −1, ω = tip-lead sign;
  - FAN-01: (+1, +1, +1), as documented.

## Results (67 parts; mirrors give identical counts)

| check | correct | can't tell | **wrong** | correct on cambered parts (≥ 0.02, n=54) | mirror chirality flips |
|---|---|---|---|---|---|
| cylinder (current `prove_direction`) | 52 | 8 | **7** | 48 (89 %) | 59/59 |
| stacking cut (Task F) | 40 | 26 | **1** (9630) | 37 (68.5 %) | 41/41 |
| radial-plane variant (not pre-registered) | 60 | 7 | **0** | 54 (100 %) | 60/60 |

- **The 7 cylinder-wrong parts are 9605, 9606, 9620, 9630, S3_0002, S4_0005 and S4_0012.**
  - All are flat (design camber 0.0008–0.0164) and leaned (22–42°).
  - All read (ω −1, pump +1), i.e. "as built, spinning backwards".
- **What the stacking cut and the radial variant did on those 7:**

| part | camber | stacking | radial |
|---|---|---|---|
| 9605 | 0.004 | can't tell | can't tell |
| 9606 | 0.016 | can't tell | **correct** |
| 9620 | 0.016 | can't tell | **correct** |
| 9630 | 0.006 | **wrong** (same as cylinder) | can't tell |
| S3_0002 | 0.001 | can't tell | can't tell |
| S4_0005 | 0.013 | can't tell | **correct** |
| S4_0012 | 0.001 | can't tell | can't tell |

- **Why stacking fails.** Its plane tilts 39–68° away from the cylinder on these leaned blades. Slicing a twisted, nearly flat plate that obliquely produces an apparent curve: median read camber 0.03–0.07 on blades designed at ≤ 0.016, and 0.038 on S4_0000 (design 0.0004). On most parts those fake curves disagree between radii, so the vote is "can't tell". On 9630 they agree, wrongly. On well-cambered parts the same tilt causes "sections disagree" on 17 of 54.
- **References.** a12x25 reads (+1, −1, −1) and FAN-01 reads (+1, +1, +1) under all three checks, which is correct.

## Scoring against the pre-registered rules (stacking cut)

| rule | result | verdict |
|---|---|---|
| F1: 0 wrong | 1 wrong (9630) | **FAIL** |
| F2: ≥ 90 % on cambered parts | 37/54 = 68.5 % | **FAIL** |
| F3: 9605/9606/9620/9630 correct or can't tell | 9630 wrong | **FAIL** |
| F4: mirrors flip | 41/41 | PASS |
| F5: references correct | 2/2 | PASS |
| F6: 0 wrong where cylinder is wrong | 1 of 7 (9630) | **FAIL** |

Note: `analyse_f.py` also lists 9630 under F4 because it treats any wrong part as an F4 failure. The prereg wording only asks for the chirality to flip, and it does (−1 → +1), so F4 is PASS as registered.

## Recommendation
- **Do not adopt the stacking cut.** It fails F1, F3 and F6, which are adoption-blocking under the pre-registered rule.
- **Keep the round-7 low-camber rule.** When design camber is < 0.02, a CONCLUSIVE cylinder reading is not trusted and the user must give the spin explicitly. Every wrong call in this population is in that low-camber band. For external STLs there is no design camber, so the proxy has to be the measured camber.
- **Radial-plane variant: worth a pre-registered confirmation round** on a fresh, larger sample, including more flat leaned blades and other real STLs. Do not adopt it on this evidence alone, since the method was chosen after seeing data.
- **Proposal-only sketch, if the confirmation passes:** add `prove_direction_radial(mesh, r_fracs)` alongside `prove_direction` in `fansim/audit/direction.py`, reusing `_fit_section` and the vote. For `source="external"`, accept a CONCLUSIVE result only if the cylinder and radial readings agree. If either is INCONCLUSIVE or they disagree, ask for the spin explicitly. No diff is supplied this round; the prototype is `scripts/stacking_cut.py` (`mode="radial"`).

## Files
- Scripts: `handoff/2026-10-11_from-qa-7/scripts/stacking_cut.py`, `run_f.py` and `analyse_f.py`.
- Data, gzipped: `handoff/2026-10-11_from-qa-7/data/f_results.jsonl.gz` (one row per part, with the cyl, stack and radial readings and their mirrors) and `f_analysis.json.gz`.
