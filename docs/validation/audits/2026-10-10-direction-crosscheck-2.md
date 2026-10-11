# Builder direction cross-check, attempt 2: judge the reading against the design's camber (pre-registered 2026-10-10)

Written before any code change or check run. Attempt 1 (`2026-10-09-direction-crosscheck.md`) failed its P3:
a camber-magnitude threshold on the *measured* sections can't separate real camber from lean curvature.
QA round 6 reviewed option (a) (`docs/qa/notes/direction-attempt-2.md`) and supplied the criteria below,
with small changes noted.

## The rule

`fansim.cfd.orientation._resolve_direction(source="builder")` keeps the builder's spin. When the mesh
proof is CONCLUSIVE it refuses only if:

1. **Mirrored part:** the proof's chirality ≠ `REAL_FAN_CHIRALITY` (−1), or
2. **The geometry contradicts the design:** the design's camber (the station value with the largest
   magnitude) has |camber| ≥ 0.02, and the measured (ω, pump) split differs from what that camber's
   sign implies:
   - (+1, −1) for positive camber;
   - (−1, +1) for negative camber.

**Notes:**
- Below |0.02| the split is reported in `direction_meta.json` but does not refuse; that is the
  lean-artifact zone.
- **Callers that pass no design camber get the chirality check only.** That is option (c), and covers
  mixed flow and the CFD scripts.
- `objectives.py` (Assess and the optimizer) and `quick_screen.py` pass the camber.
- **New in `validate_blade_params`:** any station with camber ≤ −0.02 is refused ("backwards blade"). No
  archetype uses negative camber; CROR's rear rotor gets its opposite swirl from mirrored stagger.

**Out of scope here**, and recorded as roadmap §25.3b:
- **External STLs**, where the measured split sets the spin. The QA proposal (refuse when the median
  measured camber < 0.045) would also refuse the real A12x25 reference STL (0.0375), so it needs its own
  criteria.
- **The 8 INCONCLUSIVE well-cambered stress designs** whose sections disagree.

## Pass criteria (fixed now)

| id | rule |
|---|---|
| P1 | **No false refusals.** Every builder STL among Stock, the 16 `cfd_designs.csv` designs and the 30 screen-r3 designs (`runs/screen_rank_audit/r3_96NN/quick_load/impeller.stl`, including 9605, 9606, 9620 and 9630) passes, each checked with its own design camber |
| P2 | **Mirrors caught.** x- and y-mirrored STLs of Stock, t9005, bem_9504 and 9605 are all refused |
| P3a | **Geometry/design mismatch caught.** Stock built with every station camber negated, but checked against **Stock's own** design camber (positive), is refused |
| P3b | **Backwards design caught at parameter level.** Stock params with every station camber negated raise `ValueError` in `validate_blade_params`; the optimizer's camber bounds are all ≥ 0 |
| P4 | **Stress population (QA r6 Task A, 120 records).** Applying the new rule to the recorded proofs: 0 refusals among non-mirrored builder designs, so all 7 former false refusals pass and no design that passes today is refused |
| P5 | **Existing checks green.** `tests/audit/test_direction_geometry.py`, `tests/test_cfd_orientation.py`, `tests/test_axial_scripts_oriented.py`, `tests/test_axial_direction_source.py`, plus every registered check of the units `audit_status.py` marks CHANGED/AFFECTED |

Any FAIL means do not merge, and report. A chirality misread cannot be counted from P4's records
(QA derived chirality as ω·pump). P1/P2 measure the proof's own chirality.

## Result

(filled in after the run)
