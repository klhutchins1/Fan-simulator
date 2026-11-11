# Round 28 pre-registration (grok) — Task E only (28.3 recessed hub glyphs)

**Written:** 2026-11-09 MST, before any test run, export, mesh or measurement on this master.
**Code under test:** fresh clone `/workspace/fansim/repo-r28` of `handoff_in/master_eeb0e2d.bundle` (sha256 962ef99c…f2d, verified), HEAD eeb0e2d.
**Scope:** brief `handoff/2026-11-09_to-qa-28/CLAUDE_TO_QA.md` says "If 27 is already in progress, skip A–D and only do E". Round 27 is done
(r27_out.zip, prereg ef58906), so A–D are skipped. QA-57, UI-39..42, QA-70, QA-71, QA-72: recorded as "no fix commits 9869116..eeb0e2d", not re-tested.
**Seen before writing:** the brief; COORDINATOR_STATUS; commit log 9869116..eeb0e2d and `git show --stat d9491b5`; source of `print_id.py`,
`print_id_mark.py`, the print_export/fan_export/worker diff; mark-spec r10; first 40 lines of `test_print_id_glyphs.py`; r10 `a_mark.py`;
an incidental `grep "No glyphs"` (README.md not in the hits). Static reading raised a suspicion that glyph chirality is mirrored when seen from +Z;
E9 below is written to test that, and is not tuned to any result.
**Rules:** no Docker/CFD/OpenFOAM; no UI clicks; no outside STL; no edits/commits in the clone; glyphs are not re-tuned. Output only `docs/qa/rounds/r28.md`
+ notes/patches under `docs/qa/` + evidence under `handoff/2026-11-09_from-qa-28/`.

## Geometry under test
Stock A12x25 (`config/problems/a12x25_reference.yaml`), A12x25 MotorMount, `export_print_ready(..., mount=, print_id=CODE, also_step=False)`
at default tol 0.02 / ang 0.1, CODE = a fixed valid id with a mixed glyph set (4-char body chosen before data: `K7WB` + its check digit).
Sibling: same call with `print_id=None`. Both in one isolated scratch dir on the box. If time allows, a 2nd code `M3QZ`+check for the collision check only.

## Brief criteria (verdict "brief PASS/FAIL/INCONCLUSIVE")
- E1 `tests/test_print_id.py` + `tests/test_print_id_glyphs.py` green (plus `test_worker_parent_watch.py`, touched by d9491b5).
- E2 marked STL: B-rep 1 solid; STL watertight; 1 body (trimesh split); winding consistent.
- E3 ΔV = V(sibling) − V(marked) > 0 and ≤ 40 mm³ ("order 10"); no through-cut: the deepest removed material is ≥ z_top − 0.5 − 0.03 mm.
- E4 every removed region lies on the +Z face at r 11.5–14.7 mm (tolerance 0.05 mm).
- E5 K7 cup gauge (r9 `cup_measure`) identical for marked and sibling: floor ~13 mm above the motor face (|Δ| ≤ 0.2 of 13.0), 20 grips, same protrusion;
  and marked vs sibling mesh identical below z_top − 0.6 mm (volume difference of the slab ≤ 0.05 mm³).
- E6 README.md does not contain "No glyphs on the part yet"; it says the code is recessed.
- PASS = E1–E6 all pass. FAIL = split, leak, or cup/grips change. INCONCLUSIVE = CAD/OCCT dies before a verdict.

## Tightened / user-asked checks (verdict "28.3 tightened"; any fail here = a new bug, severity stated)
- E7 printability: recess depth 0.5 ± 0.03 (≥ 3 layers at 0.12/0.16); groove width ≥ 0.5 mm (spec) measured on a top-down raster at
  0.02 mm/px of the removed region; lands between grooves inside a glyph and between adjacent glyphs ≥ 0.4 mm (one 0.4 nozzle line);
  a land < 0.4 mm is a LOW printability bug, < 0.2 mm (grooves merge) MED.
- E8 character set and codec: the font covers exactly CROCKFORD ∪ CHECK_ALPHABET; no glyph for I, L, O; `issue_print_id` over 2000 ids (seeded rng
  via `_random_body`) gives only Crockford body chars and `verify_print_id` true; `normalize_read` maps i/l→1, o→0; every single-char substitution
  of 200 ids is rejected by the check digit; every adjacent transposition of differing chars is rejected (report the rate; mod-37 should catch all).
- E9 legibility: (a) **chirality and order** — rasterise the marked part's removed region viewed from outside the +Z face (looking −Z) with glyph
  "up" = radially outward; each glyph must match the font cell un-mirrored and characters must read left-to-right in code order. Mirrored text = MED
  bug (part readable only in a mirror). (b) No two glyphs in CHECK_ALPHABET have identical stroke sets; near-identical pairs (stroke-set symmetric
  difference ≤ 1 short stroke) listed as LOW legibility notes. (c) Footprint dilated by 1 mm stays on the flat face (≥ 1 mm from the bore r 10 and
  rim r 21.5) and adjacent glyph footprints do not overlap.
- E10 silent paths (static + cheap behavioural, CAD-free): hub radius < 15.7 → `engrave_print_id` returns the model unchanged; check whether the
  README / cockpit message still says "recessed" in that case (if yes: LOW bug). Code that normalises to ≠ 5 chars → no strokes (same check).
- Not done: no CFD of the pocket; no aero claim beyond the spec's area ratio, which may be recomputed from the raster (report only).
