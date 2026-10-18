# CROR and centrifugal against published data (release R2.3, R2.5): pre-registration

Written 2026-10-17 (late), **before** any digitised value or CFD result is seen. grok round 17 Task B is digitising
both papers in parallel; this document must be committed before that note lands. Data sources (grok r15,
`docs/qa/notes/r15-data-hunt-cror-mixed-centrifugal.md`):

- **CROR:** Shigemitsu et al. 2018, *Performance and Internal Flow of Contra-Rotating Small-Sized Cooling Fan*, Open J.
  Fluid Dyn. 8:181–194, doi:10.4236/ojfd.2018.82013, CC BY 4.0. Ø37.2 mm rotors in a 40 mm casing, 15 000 / 14 000 rpm.
- **Centrifugal:** EPJ Web Conf. 180, 02023 (2018), doi:10.1051/epjconf/201818002023, CC BY 4.0 (grok confirms the licence
  in r17). Ø60 mm, 12 backward-curved blades 4 mm wide, at 6000 / 9000 / 11 000 rpm.

## Step 0: geometry freeze (both cases, before any CFD)

1. Cursor builds each geometry **only** from numbers the paper states (grok r17 B's table).
2. Every number the paper does not give is filled by a rule stated here, never by a fit:
   - blade section: circular-arc camber line from the stated inlet/outlet angles (or stagger and camber if those are
     what Table 1 gives); constant thickness 0.8 mm, the moulded-fan minimum; leading and trailing edges rounded;
   - CROR axial gap between the rotors, if not stated: read from the paper's drawing at its scale, ±0.5 mm. If there is
     no drawing, use 0.25 × chord;
   - CROR casing: the paper's square 40 mm casing is modelled as a round duct with an inscribed diameter of 40 mm
     (a stated deviation). The tip clearance is the stated 0.6 mm;
   - CROR spokes and struts: the 3 spokes per stage are modelled only if the drawing gives their section. Otherwise
     they are left out (a stated deviation);
   - centrifugal volute: from the paper's drawing at its scale. If there is no drawing, use a log spiral with a
     cut-water clearance of 0.1 D;
   - inlet/outlet: our existing rig conventions for each archetype.
3. The geometry and every filled-in value are committed as `validation/reference/<case>/geometry.json` (with a
   `filled_by_rule` list), plus the STL. That **commit hash is the freeze**: results from any other geometry don't
   count.

## Step 1: convergence gate (both cases)

The volute CFD currently oscillates 17–23 % (audit-07).
- A point **counts** only if the tail-mean of ΔP has a peak-to-peak oscillation ≤ 5 % over the last 20 % of
  iterations, and the mass imbalance is ≤ 1 %.
- A point that misses this is INCONCLUSIVE, not a pass.
- If more than one of the compared points is INCONCLUSIVE, the case is INCONCLUSIVE overall.
- Fixing the oscillation (relaxation, iterations, transient averaging) is allowed **before** comparing with data. It
  is judged on the convergence criterion only, never on agreement with the paper.

## Step 2: comparison (fixed rules)

The digitised curves come with grok's stated digitising uncertainty. A model point inside that uncertainty counts
as zero error.

### CROR (Shigemitsu 2018), at 15 000 / 14 000 rpm, front / rear

- **S1, shape:** the rear rotor's share of the total static rise at the paper's design flow Q_o is within ±15 percentage
  points of the paper's share.
- **S2, shape:** the flow at peak total ΔPs is within ±15 % of the paper's.
- **A1, absolute:** total ΔPs is within **±20 %** at three flows on the stable branch: 0.5, 0.75 and 1.0 × Q_o.
- **A2, absolute:** free delivery is within ±20 %.

### Centrifugal (EPJ 180:02023), moulded wheel, at 9000 rpm (plus 6000 and 11 000 for S2)

- **S1, shape:** the flow at peak static pressure is within ±20 % of the paper's.
- **S2, scaling:** the model's ΔP(11 000) / ΔP(6000) at the same φ is within ±10 % of the measured ratio. This is a
  sanity check only, since almost any model scales close to n².
- **A1, absolute:** ΔP is within **±20 %** at three flows: 0.4, 0.7 and 0.9 × the measured free delivery. The top point
  stops at 0.9 to avoid the zero-pressure end.

## Verdicts (and what the release does)

| result | label in v0.1.0 |
|---|---|
| S and A all pass | **validated**: the tab ships with the tolerance quoted (±20 %) |
| S pass, any A fails | **trends validated**: the tab ships with "rankings and curve shapes match published data; absolute numbers can be off by more than 20 %" |
| any S fails, or INCONCLUSIVE | **experimental**: labelled like Mixed, and the result goes to Kimball, who may hide the tab instead |

Failures are recorded, not re-tuned. The geometry freeze cannot be changed after the first CFD run. A second
attempt needs a new pre-registration that says what changed and why, and it cannot be motivated by the comparison.

## Who does what

1. grok: r17 B (digitise, plus the geometry table and licence check).
2. Cursor: step 0 (build + freeze commit) and the case scripts `scripts/validate_cror_shigemitsu.py` and
   `scripts/validate_volute_epj.py`, each writing `runs/<case>/summary.json`.
3. Night queue: the runs.
4. Claude: reads the summaries against this document and records the verdict here.
