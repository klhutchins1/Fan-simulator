# 2026-11-14 session 1 — glyphs and the hub face

Write this session into `docs/qa/rounds/r30.md` before you start session 2. If `docs/qa/rounds/r29.md` already records QA-73 and QA-79 on this same code, say so and stop. Do not redo a finished check.

No Docker. No OpenFOAM. No Assess, Sweep, Optimize, or Run. Do not change `cavity_dia_mm`. Do not edit Stock YAML.

| # | task | board |
|---|---|---|
| A | **QA-73 HIGH re-check.** Export Stock with a known print-id. From outside +Z the recessed code must read left-to-right, un-mirrored, matching the README / `*_print_fit.json`. Cap **5.0 mm**, stroke **0.9 mm**, band r **11.5–16.5**. Red: the same tests fail on pre-fix `eeb0e2d`. Green: `tests/test_print_id.py` + `tests/test_print_id_glyphs.py`. | QA-73, QA-80 |
| B | **QA-79 hub face, not bbox.** On a t9002-class design (blades above the hub): the mark is on the hub +Z face. A section at `z_hub − 0.25 mm` shows the code; a section at blade `zmax − 0.25 mm` does not. | QA-79 |
| C | **Hub opening, re-derive.** `grip_protrude_mm` is **0.35**, equal to clearance, so A12x25 pad tips sit on `cavity_dia_mm` **37.25**. The old 0.7 mm protrude put tips at **36.55**. Confirm `tests/test_mountable.py` and the layout in `fansim/fan_spec.py`. Measure one exported Stock the same way: pad tips on the cup side, not the engraved print-id on the inlet face. Prereg: `docs/validation/audits/2026-11-11-hub-opening-prereg.md`. | P4a |
