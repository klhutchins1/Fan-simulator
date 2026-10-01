# Chord basis: legacy designs vs measured chord (2026-10-01)

Question: commit 37728b9 (2026-09-30 11:42 -0600) made station `chord` mean the *measured*
cylinder-cut chord, with the builder raising the loft chord to realise it. That applied to every
parametric design, not only the Stock recipe. Did it silently change saved designs?

## Finding

Yes. Every flat/trial saved before 37728b9 holds *loft* chords. Rebuilt afterwards, its chords were
read as measured targets and lofted wider than the design that was scored. Example, `opt_run1_t9000`:
built volume 39533.41 mm³ before 37728b9, 39916.21 mm³ after (+1.0%). The size of the change depends
on the design (the tip is affected most). `CFD_VERSION` was not bumped and nothing recorded which
meaning a design used. The 19.8 re-score (2026-09-29/30, all before the commit) was scored on the old
builder, so under the new builder its geometry no longer matched its numbers.

## Fix

- `BladeParams.chord_basis`: `"measured"` (default, the 37728b9 meaning) or `"loft"` (legacy, built
  as-is). `prepare_loft_chords` returns `"loft"` params unchanged; its own output is marked `"loft"`,
  so preparing twice is a no-op.
- Flat dicts: `blade_from_flat` reads `chord_basis` (absent = `"measured"`); `blade_to_flat` writes it.
- Optuna: `suggest_params` stamps a `chord_basis` user attr. `trial_attrs.trial_flat` replays a trial
  with its stamp, or classifies an unstamped trial by `datetime_start` against
  `CHORD_BASIS_CUTOFF` (the 37728b9 commit time). It is used by `pareto_summary`, the cockpit study
  loader and `rescore_designs.py`.
- Saved JSON: `scripts/migrate_chord_basis.py` (idempotent) stamped 14 `cockpit_assess/design.json`
  files and 15 catalog rows. Designs 9014–9016 were built after the commit, so they are measured;
  everything older is loft. Prop runs are skipped because their scores are BEMT, which already reads
  station chord as the physical chord.
- Legacy recipe YAMLs (`a12x25.yaml`, `a12x25_approx`, `a12x25_flow_candidate`,
  `a12x25_reference_v1`, `design_space.yaml`) declare `chord_basis: loft`. The Stock
  `a12x25_reference.yaml` stays measured.
- Cockpit editor, CROR params and the stock-cache fingerprint carry the basis.
- `rescore_designs.params_hash` drops `chord_basis` when it is `"loft"`, so legacy hashes in
  `rescore_19_8.json` still match.

## Evidence

- `opt_run1_t9000` stamped `"loft"` rebuilds to **39533.41 mm³ on today's code, identical to the
  pre-37728b9 builder**. So the 19.8 re-score numbers describe the geometry these designs build to
  again; no re-score is needed.
- `tests/test_chord_basis.py` (16 tests) covers the defaults, loft pass-through, idempotence, the flat
  round-trip, legacy YAMLs, cutoff classification (including naive optuna times) and the trial stamp.
- Units `geometry.stock_handedness` and `optimize.search_space_handedness` re-checked (4 passed,
  including slow) and re-recorded.

## Optimizer chord bounds

`search_space` chord bounds keep their numbers; they now mean measured chord. Under the old meaning
the cylinder cut shortened the tip (Stock: 49.8 mm loft → 33.5 mm measured), so a 26–40 mm loft tip
built noticeably narrower than its number, and Stock's tip sat outside the range. The measured
range brackets Stock (33.5 mm), so the numbers are not rescaled. New studies therefore explore wider
tips than `opt_run1` did, and the two studies are not comparable chord for chord.
