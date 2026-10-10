# Builder rotor direction cross-check: false refusals on flat, leaned blades (pre-registered 2026-10-09)

Written before the fix was run against any design.

## The defect

`fansim.cfd.orientation._resolve_direction(source="builder")` refuses CFD when the mesh-only proof
(`fansim.audit.direction.prove_direction`) is CONCLUSIVE and its `(omega, pump)` reading differs from
the builder convention `(+1, −1)`. Screen r3 designs **9605** (design camber 0.004, tip lean 26°) and
**9606** (camber 0.016, tip lean 42°) were refused. The proof read `(−1, +1)` from 22–33 sections whose
*measured* camber ratio (0.031–0.038) exceeds its 0.02 floor, although the blades are nearly flat. A
cylindrical cut through a strongly leaned blade is curved by the lean, not by camber. 9613 (camber
0.002, lean 8°) read flat and passed.

In both refusals the proof's **chirality** (−1, from surface normals, independent of camber) agrees with
the builder: omega × pump = (+1)(−1) = −1. Only the camber-derived split into spin vs pump direction
was wrong.

## The fix

For builder rotors the spin is set by construction (pinned by `tests/audit/test_search_space_handedness.py`).
The cross-check exists to catch a part whose geometry contradicts that, above all a **mirrored** part,
which flips chirality. New rule:

1. **Chirality must agree** whenever the proof is CONCLUSIVE (a mirrored part is always refused).
2. The camber-based `(omega, pump)` split is used to refuse only when the sections' **median measured
   camber ratio ≥ `TRUSTED_SPLIT_CAMBER` = 0.05**. Then the concave side is real camber, not lean.
   Below that it is reported (direction_meta note) but does not refuse.

## Pass criteria (fixed now)

| id | rule |
|---|---|
| P1 | No false refusals: every builder STL among Stock, the 16 `cfd_designs.csv` designs and the 30 screen-r3 designs passes the cross-check. That includes 9605 and 9606. |
| P2 | Mirror caught: the y-mirrored STLs of Stock, t9005, bem_9504 and 9605 are all **refused**. |
| P3 | Backwards camber caught on a well-cambered blade: Stock with every station's camber negated (concave side flipped, chirality unchanged) is **refused**. |
| P4 | Existing direction checks are green: `tests/audit/test_direction_geometry.py`, `tests/test_cfd_orientation.py`, `tests/test_axial_scripts_oriented.py` and every registered check of the units `audit_status.py` marks CHANGED/AFFECTED. |

Any FAIL → do not merge; report.

## Result (2026-10-09) — **FAIL (P3). Not merged**; code reverted.

| id | verdict | evidence |
|---|---|---|
| P1 | PASS | 46 builder STLs (Stock, 16 CFD-dataset designs, 30 screen-r3 designs incl. 9605 / 9606): 0 refused |
| P2 | PASS | y-mirrored Stock, t9005, bem_9504, 9605: all refused as mirrored (chirality flip) |
| P3 | **FAIL** | Stock with negated camber builds (volume 41686 vs 41970 mm³), and the proof reads the flip: (−1, +1), median measured camber 0.0441. But that is below 0.05, so the split was untrusted and the backwards blade **passed** |
| P4 | not run | (FAIL above) |

**Why it failed:** the proof's measured `camber_ratio` (|a|·(c/2)²/c from a quadratic fit of the cut) is on
a different scale from the design `max_camber`. Real Stock (design 0.083–0.097) measures only **0.0375**.
The lean artifact on 9605 measures 0.031–0.038, so **genuine camber and lean-curvature overlap on this
metric, and no camber-magnitude threshold can separate them.** 0.05 made the split untrusted everywhere.

**What a next attempt needs (new pre-registration):** a discriminator that is not camber magnitude.
Options:
- (a) The builder knows the design: compare the measured split against the sign of the design's
  camber, and refuse only on disagreement with real design camber, e.g. |max_camber| ≥ 0.02.
- (b) Cut normal to the blade's stacking line instead of on cylinders, which removes the lean curvature.
- (c) Use chirality alone for low-camber designs (|design camber| < 0.02, where "backwards" barely
  matters aerodynamically).

Chirality-based mirror detection (P2) worked and should be kept in any version.
