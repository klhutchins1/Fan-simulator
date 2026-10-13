# Claude → Cursor, 2026-10-13

Thanks for the brief. Kimball wants your ideas kept, with my evaluation and a reason wherever I disagree.
I'm low on weekly tokens, so **you're carrying the work until Thursday.** Everything below is current as
of master `ae3f1c4` plus the docs commits after it.

## State at hand-over

| item | state |
|---|---|
| **Wrap (27.4 option i)** | **MERGED** in `ae3f1c4` (branch `hang-limit`, which contains `cylinder-sections`). Axial designs build `section_wrap="cylinder"`. Built blade = sliders within camber 0.001 / stagger 0.1° wherever the hub cut doesn't reach. |
| **Old saves** | Stamped `planar` by `scripts/migrate_section_wrap.py`: 79 `design.json` + 80 catalog rows. Backup: `runs/_backup_section_wrap_20261013/`. They rebuild exactly as scored and show an "Old blade shape" note. |
| **Stock v3** | `config/problems/a12x25_reference.yaml`; v2 is kept as `a12x25_reference_planar.yaml`. Refit with **sharp 0.2 edges**: the first v3 had round edges because `fit_recipe_to_stl.py` dropped the settings after the station list. That's fixed, with `recipe_settings()` and a test. Refit again under the hub-cut correction. |
| **QA-32** | **Done the way Kimball chose: (a), not BEM-on-clipped.** Blades may hang **≤ 2 mm below the hub's motor face, as designed** (`MAX_HANG_BELOW_HUB_MM`, `blade_hang_below_hub_mm`, refused in `validate_blade_params`, and only for wrapped + clipped designs). Under that limit, `chord_realisation.correct_clipped_sections` corrects camber and stagger at the stations the cut changes. |
| **Fuse safety net** | `fuse_impeller` requires exactly one solid. If an all-at-once fuse leaves loose pieces, it redoes the fuse one blade at a time. The first sharp-edge v3 had fused into 2 solids / 6 bodies. |
| **Tests** | Last full suite on the branch: 1748 passed, 3 failed, then all 3 fixed and their files re-run green (29 passed). **I did not re-run the full 2.5 h suite after those last fixes.** Please run it once before anything else lands. |
| **Audit** | `docs/validation/audits/2026-10-12-cylinder-sections.md` (V1–V6, the sharp-edge correction). It doesn't yet cover the hang limit or the fuse net. Adding those is a small doc task for you (numbers below). |

### Numbers to use (final Stock v3, validation rig, base cell 5 mm, frame, 1000 iterations)

| back pressure | real STL (close-ref) | Stock v2 planar | **Stock v3 wrapped (final)** |
|---|---|---|---|
| 0 Pa | 58.3 | 54.5 (−6.5 %) | **55.7** (−4.5 %) |
| 5 Pa | 49.5 | 46.9 (−5.3 %) | 48.0 (−3.0 %)* |
| 10 Pa | 37.1 | 36.6 (−1.3 %) | 37.5 (+1.1 %)* |

\* 5 and 10 Pa were run on the sharp-edge v3 **before** the hub-cut refit. That refit didn't change free
air (55.8 → 55.7), so I didn't repeat the loaded points.

**Your brief's 57.6 / 2.1 % are from the round-edge v3. Please don't use them.** Assess setup (V5):
v3 free 55.93 raw vs v2 54.63 (+2.4 %), loaded 39.56 vs 41.88 (−5.6 %).

## Your seven items, evaluated

1. **Adopt wrap + merge: done.**
2. **Don't CFD grok's surface-fit YAML: agreed.** T3 failed. The airflow-vs-real-STL test already shows v3
   is closer than v2 (2.8 % vs 4.4 % mean gap), so the surface fit is parked as a diagnostic.
3. **Rewrite `first_print_measure_plan.md`: agreed, and it's your first task (roadmap 27.9).** Use the table
   above.
   - The old B/A 0.89 band came from the planar recipe.
   - Article B is printed Stock v3. A natural prediction is B/A ≈ 55.7 / 58.3 = 0.955 for the CFD geometry
     alone, before print roughness and tolerance.
   - Re-derive the band from the plan's own print-effect terms rather than copying the old ±.
   - Pre-register the new band in the plan before anyone prints.
4. **27.2 "refuse only when both readers agree": I disagree, and I've closed 27.2.**
   - **Reason:** the "radial-plane" reader cuts the **tangent plane** at the blade. That is exactly where the
     old *planar* sections lived, which is why it read them well.
   - On wrapped blades the tangent plane is the mismatched cut, so adding it to the builder rule now adds
     the wrong reader.
   - The wrap already fixed the false refusal: V4 gave 0 wrong calls on 30 parts, and S3_0014 now reads
     correctly with the cylinder proof alone.
   - QA-33 (more INCONCLUSIVE) is harmless, because INCONCLUSIVE never refuses.
   - The radial reader stays relevant only for external STLs (27.2b), and that's unconfirmed.
5. **27.1 fuse guard on remaining growth + a shroud term: agreed, it's yours.** Notes:
   - grok's constants are **Linux**. Refit on Windows: peak working set minus working set at the
     `check_fuse_memory` call, via `GetProcessMemoryInfo`. Use the same hook idea as
     `handoff/2026-10-12_from-qa-8/scripts/hook_c/`.
   - The shroud cost is about **+66 KiB per blade face** (round 9 E, post hoc). Measure it on Windows before
     baking in a constant.
   - Wrapped builds peak about 4 % higher than planar (featured S5_0167: 7.7 vs 7.4 GB).
6. **QA-32 "BEM on hub-clipped sections, not another loft": superseded.** Kimball chose (a) directly, and
   it's implemented and verified: the 8 worst allowed hangs pass V1 after the correction, and 3 failed
   before it.
   - BEM-on-built-sections (option iii) is still a reasonable *cross-check* idea for later.
   - It isn't needed for QA-32 any more, because built = sliders now everywhere the limit allows.
7. **§28 print-part ID: kept, parked; Kimball wants to evaluate whether it's worth it.** My view:
   - **28.2** (registry + export README code, no geometry cut) is cheap and worth doing on its own. A
     sharpie copy of a README code may be all a box of 30 needs.
   - **28.3** (recessed glyphs) only if the sharpie route proves fragile in practice.
   - Let grok's mark-spec (round 10 Task A) report the hub ring first.
   - **Correction to your QA brief:** "current master" is now the **wrapped** Stock (`ae3f1c4`), not planar.
     The hub is the same; the blade roots differ slightly.

Also: **"Don't restart the optimizer until wrap is master."** That condition is met, but **don't restart yet
anyway**: see 27.7 below.

## Your queue until Thursday (in order)

1. **Full suite on master** (2.5 h).
   - Run it via `pytest.main` plus `os._exit`. On this box the OCCT/VTK interpreter crashes on exit, which
     turns a green run into rc 127/139. A three-line wrapper does it:
     `import os, sys, pytest; rc = pytest.main(sys.argv[1:]); sys.stdout.flush(); os._exit(int(rc))`.
   - Restore any tracked reference STLs the tests rewrite before committing (known churn).
2. **27.9: rewrite `docs/validation/first_print_measure_plan.md`** with the numbers above. Pre-register the
   new band. This is the print-blocking item.
3. **Audit addendum** to `docs/validation/audits/2026-10-12-cylinder-sections.md`:
   - **Hang limit:** 2 mm as designed. 8/200 refused; 39/200 hang at all; the realised loft hangs about 1.6×
     the designed value because the chord stretch lengthens the trailing edge. QA r9 reported the
     realised figure.
   - **Cut correction:** S8_0056 camber −0.0080 → −0.0001. The 8 worst allowed designs pass V1. Stock's two
     inner stations −0.0066 / −0.0053 → pass. The reached-station rule is chord > 0.1 mm, camber > 0.001,
     or stagger > 0.2°.
   - **Stock refit under the correction:** inner camber 0.032 → 0.026 and 0.048 → 0.045; free air
     55.8 → 55.7.
   - **Fuse net:** see above. Repro fixture `tests/data/stock_v3_fuse_fragile.yaml`.
4. **27.8 hang-limit UX** (low effort):
   - Make sure Preview shows the plain refusal. Preview uses `build_stl_isolated`, so check that the
     `ValueError` text survives the worker; `stderr_tail` is 400 characters.
   - Make sure the optimizer stamps it as an early infeasible.
5. **27.3 Stock repeats for the flow-card thresholds.** This runs here, on Kimball's Windows box, not on
   grok's: grok has never run CFD in these rounds. Run 5 × the Assess setup on Stock v3 (about 25 min each)
   and set `BAND_TOL` / `NOISE_MARGIN_DB` at about 2σ. **Pre-register the 2σ rule before the runs.** Use a
   Windows Scheduled Task so the runs survive session end. Logs written by PowerShell `*>>` are UTF-16;
   decode them with `iconv`.
6. **27.1 fuse guard** (as above).
7. **27.5 caption leftovers** (QA-26): the Preview caption from the built params, the Export message, and
   the view jump.
8. **27.7, propose only, don't implement:** optimizer camber/stagger bounds under wrap. Use Stock v3 and the
   V1 data. Old candidates (t9005 etc.) are different blades under wrap. **Write the proposal into the
   roadmap for Kimball. No new campaign.**
9. **§28.2** only if 1–8 are done and Kimball says it's worth it.

## Don't

- Re-merge, rebase or rewrite `cylinder-sections` / `hang-limit`; they're merged.
- Touch the loft, `_capped_loft`, `correct_clipped_sections` or the Stock YAML without a pre-registered
  check. Those are physics changes.
- Ship 27.2b (external radial-led rule; unconfirmed), start §26, or print optimizer candidates.
- `git apply` QA patches. Re-implement them instead.
- Treat round-9's "57.6 CFM" or "S1_0400 hangs 2.5 mm" as current. They're the round-edge v3 and the
  realised-loft hang respectively.

## Gotchas on this box

- Long runs: Windows Scheduled Tasks (`Register-ScheduledTask`), not shell `&`. A shell `&` launch once left
  two full suites running at once.
- `FANSIM_CACHE_DIR` gives a fresh loft-chord cache. `LOFT_CACHE_VERSION` is now 5; bump it if you change
  the realisation.
- Memory tier: `fansim.resources.current_tier()` picks from free RAM. The one-at-a-time fuse is about 2× slower
  with wrapped blades (Stock about 6 min).
- Grok's round-10 Task A runs on its own box. Round 10b (the wrap confirmation) is briefed in
  `handoff/2026-10-13_to-qa-10b/` with a bundle at the merge commit.
