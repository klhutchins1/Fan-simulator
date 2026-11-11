# Round 29 for grok (Cursor, 2026-11-11)

Do First is on master: QA-73 HIGH (mirrored print-id) at `2bfde35`, r27 leftovers at `107989b`. **No new research-lead round.** Scout work, if any leftover time, should lean print-quality and measurement (glyphs, hub coupon, T1–T6), not more papers.

**Build:** `fansim_master.bundle` in this folder is **master including the commit that adds this brief**. No Docker, CFD, OpenFOAM, Assess, Sweep or Optimize run. Write `docs/qa/rounds/r29.md` only (do not edit `docs/QA_REVIEW.md` or the board). Re-check a fix only when it was HIGH. Pre-register A before measuring an exported STL.

## Tasks

| # | task | board |
|---|---|---|
| A | **QA-73 HIGH re-check.** Export Stock with a known print-id. From outside +Z the recessed code must read left-to-right, un-mirrored, matching the README / `*_print_fit.json`. Cap is **5.0 mm**, stroke **0.9 mm**, band r **11.5–16.5** (P6 after H7MQ8 T3 FAIL). Red: same tests fail on pre-fix `eeb0e2d`. Green: `tests/test_print_id.py` + `tests/test_print_id_glyphs.py`. | QA-73, QA-80 |
| B | **QA-79 hub face, not bbox.** On a t9002-class design (blades above the hub): the mark is on the hub +Z face. A section at `z_hub − 0.25 mm` shows the code; a section at blade `zmax − 0.25 mm` does not. | QA-79 |
| C | **r27 leftovers** (`107989b`). QA-57 Volute Assess label; UI-39/40 refuse Sweep steps / Optimize trials; QA-70 noise-hint row; QA-71/72 G4 leftover copy. Do not click Run. | QA-57, UI-39, UI-40, QA-70, QA-71, QA-72 |
| D | Do not CFD the pocket. Do not re-prove G2/G3. Do not open leads 34+. QA-74/75/76 travel with A. | — |

## Print session (record only)

Kimball printed H7MQ8 (Stock v3, PLA+, 0.6 mm, 27.41 g). T3 FAIL on the 3.2 mm glyphs; coupon `scripts/export_id_coupon.py` is the T3 re-check, not another fan. E0MWW (t9002 extra) first STL missed the ID (QA-79). Do not treat the coupon as article B.
