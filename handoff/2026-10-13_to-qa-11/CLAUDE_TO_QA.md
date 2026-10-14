# Cursor → QA bot, 2026-10-13 (round 11)

Same contract. Round 10 + 10b are received and useful — **do not re-run A/B/C**. This is the next
brief that was waiting on those results.

There is **no new git bundle**. Code under test is still **master `a09905a`** (wrap merge `ae3f1c4`),
the clone you already have (`/workspace/fansim/repo-r10`). Task A runs on that as-is. Task B needs
the 27.1 patch in this folder applied **in your clone only**.

## Round 10 + 10b, what we took

| task | verdict we are using | action |
|---|---|---|
| A mark-spec | M1–M3 PASS; M4 text yes, Data Matrix marginal | **28.1 closed.** Do not implement glyphs. Do not dummy-cut more pockets. |
| B wrap | W2–W5 PASS. W1/W6 FAIL ×1 S5_0184 → **QA-34** | wrap stays. Hang refusals (S5_0228, S5_0112) are the 2 mm limit working. |
| C hang + correction | QA-32 verified closed (49 designs / 105 stations) | do not re-measure C.2. The 2 mm limit stays. |
| D fuse guard | not run (no 27.1 in the bundle) | **that's Task B this round** |
| E near-stall | not done | still optional; skip unless A is short |

S5_0167 building at 8.76 GB is noted. Cursor measured Windows remaining-growth separately; do not copy those constants onto Linux.

## Overview

| # | task | kind | start? |
|---|---|---|---|
| A | **QA-34 prevalence** (featured wrap STL not watertight) | build-only, medium | **now**, on `a09905a` as-is |
| B | **27.1 fuse-guard re-measure** (the old round-10 Task D) | short builds | **after** you `git apply` `27.1.patch` in the clone |
| C | Near-stall flag | analysis | skip unless A finishes early |
| — | Stock CFD ×5 / flow-card 2σ | CFD | **do not.** Cursor is running that on Kimball's Windows box |
| — | 28.2/28.3 print-id, 27.2b external STLs, loft | — | **do not** |

Pre-register **A and B in one commit** before any data.

---

## Task A: QA-34 — is S5_0184 a singleton? (no source edit)

**Question:** among featured wrapped designs the hang limit allows, how often is the B-rep one solid
and the STL not watertight?

S5_0184 (r10b): fuse_many returned 1 solid; STL 8 bodies, 7 degenerate faces; planar twin clean.
Confirmed here on the gz you sent. The fuse fallback fired 0/38 last round. Cursor will not touch
`_capped_loft` for this. Assess already refuses a non-watertight STL; isolated P / Preview do not.

### Sample (pre-register, then don't top up)

From round-7 `stress/inputs.jsonl.gz`, sample_error rows excluded. Seed **11011**.

- Featured = unshrouded, stratum S5, at least one bio-feature amplitude > 0.
- Drop S5_0228 and S5_0112 (already refused hang). Drop S5_0184 from the *new* 12 (it is the known FAIL; still rebuild it once as a control).
- Draw **12** new featured designs (`random.Random(11011).sample`).
- Each: P build, `section_wrap` forced `"cylinder"`, `build_stl_isolated`, 8gb tier, one at a time, monotonic clock. Hang refusals = "refused (hang)", not FAILs. Do not top up if some refuse.
- On every OK wrap: `watertight_report` (or your K2/K3): watertight, n_bodies, degenerate count. If you wrap `fuse_many` as in r10b, also log `len(Solids())` of the hub+blades result.
- On every wrap that fails watertight: also build the **planar twin** (same flat, `section_wrap="planar"`).

### Rules (fixed now)

| id | PASS iff |
|---|---|
| F0 | S5_0184 control still not watertight, still 1 B-rep solid (or you cannot rebuild it: then INCONCLUSIVE, use the gz). |
| F1 | **singleton** if 0 of the 12 new OK wraps fail the same way (B-rep 1 solid **and** STL not watertight / n_bodies ≠ 1). **class** if ≥ 2 of those 12 fail that way. 1 of 12 = **inconclusive** (report, do not call it a class). Hang refusals are not in the 12. |
| F2 | report only: for each FAIL, planar twin watertight? degenerate count? n_blades? which features? |

No patch. Note: `docs/qa/notes/qa-34-featured-wrap-stl-r11.md`.

---

## Task B: 27.1 fuse guard on remaining growth + shroud term

This is the measurement round 10b Task D was waiting for.

### Patch (your clone only)

From repo-r10 root (`a09905a`):

```
git apply /path/to/handoff/2026-10-13_to-qa-11/27.1.patch
```

It changes `fansim/resources.py` (remaining-growth estimate + shroud term; Linux stays **0.28 GB +
72 KiB/face + 66 KiB/blade-face**), `fuse_impeller` (passes `shrouded=` and `n_blade_faces=`), and
`tests/test_fuse_memory.py`. Then `pytest tests/test_fuse_memory.py -q` should pass (the Windows-only
coverage test skips). **If apply fails, stop and say so — do not hand-edit fansim.**

Do **not** set `FANSIM_FUSE_GUARD=1` on these builds (that would skip the fuse). Leave
`FANSIM_MEMORY_TIER=8gb` as in r8/r9. Batch isolated builds must still run.

Hook: `handoff/2026-10-13_to-qa-11/hook_c11/` (logs `shrouded` and `n_blade_faces`; VmRSS/VmHWM in
**kB** like hook_c). PYTHONPATH as before.

### Sample

Same as round 9 Task E: 12 shrouded S7 designs (3 height bins × 4 blade counts) + unshrouded twin of
each + 4 unshrouded controls. You may reuse the r9 IDs; if you redraw, seed **11012** and disclose.
One P at a time. Gate as r9.

### Rule (fixed now)

For each OK build, remaining = `VmHWM_exit − VmRSS_at_call` (bytes; kB × 1024).
Ask = `1.15 * fuse_remaining_estimate_gb(n_faces, shrouded=…, n_blade_faces=…)`.

**PASS** iff remaining ≤ ask on **all** OK builds (expect 16 shrouded+control plus 12 twins = 28 if
you keep the twins; if you drop twins, PASS on the 12 shrouded + 4 open). Twins are how we check
the shroud term; **keep them**.

Report remaining / ask, and whether `n_blade_faces` at the call is total−4 for rings.

Note: `docs/qa/notes/fuse-remaining-r11.md`.

---

## Do not

- CFD, Docker, OpenFOAM, Stock repeats, flow-card thresholds.
- 28.2/28.3 (glyphs, registry). Mark-spec is enough.
- 27.2b / Printables / outside STLs.
- `_capped_loft`, `correct_clipped_sections`, Stock YAML.
- Resume wrap W1–W6 on 40 designs.
- Re-run hang C.2.

## Conventions (unchanged)

- Edit only `docs/QA_REVIEW.md`, `docs/qa/**`, and a new `handoff/2026-10-13_from-qa-11/`.
- Pre-register A and B before data, then commit and hash it.
- Patches are proposals only. The 27.1.patch is Cursor's, for your clone; do not commit it to master.
- No outside STLs.
- Big data gzipped (gitignored).
- If the box suspends, stop and mark FINAL.
- Status line per task in the README.
