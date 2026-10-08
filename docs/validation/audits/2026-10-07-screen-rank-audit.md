# Screening-tier rank audit (pre-registered 2026-10-07)

Question: can a quick CFD run decide which design ideas deserve a full Assess (20–40 min)? A
screening tier is only useful if it ranks designs the way the full Assess does. A coarse mesh is
exactly what under-read thin blades in September (31 vs 45 CFM, mesh under-resolution), so this
must be shown, not assumed.

## Candidate tiers

| Tier | Mesh | Operating point | Iters | Cost |
|---|---|---|---|---|
| Full Assess (truth) | 6 mm background, surface level ≥ 3 (0.75 mm), parallel snappy | free + "case" hose (8 Pa) | 500 + 500 | ~21–40 min |
| Q1 | same as full | free-air only | 300 | ~half (replayed from the full run's free-air history) |
| Q2 | 8 mm background, surface level 3 (1.0 mm) | free-air only | 300 | own run, measured by `--pilot` |

The quick score is raw CFD free-air CFM. The truth is the Assess output (`cfm_free`, `cfm_load`
after motor derate and print penalty, `efficiency`).

## Designs (13, chosen before any run)

Stock; Stock with blade thickness ×0.7 (thinnest wall 1.55 mm — the regime where coarse meshes
under-read); Stock with dimples (amp 0.2); saved designs t9000, t9001, t9012 (tubercles +
serrations), t9016 (tubercles), t9002 (7 blades), t9003, t9015, t9005, t9006 (high free, collapse
under load), t9008. Designs the full Assess rejects drop out.

## Criteria (fixed before any data)

Per tier, over designs with both a quick and a feasible full result:

| id | rule |
|---|---|
| n | at least 8 designs, else **INCONCLUSIVE** |
| a | Spearman ρ(quick, full `cfm_free`) ≥ 0.90 |
| b | Spearman ρ(quick, full `cfm_load`) ≥ 0.80 |
| c | the full Assess top 3 by `cfm_load` are all in the quick top 5 |

PASS = a, b and c. ρ against efficiency is reported, not judged. A tier that FAILs is not used to
skip full Assess runs. If both pass, the cheaper one is used. Thresholds are not changed after
seeing data.

## Procedure

`uv run python scripts/screen_rank_audit.py --pilot` (times Q2 on Stock, writes `pilot.json` with
an ETA), then the full run, sequentially, nothing else heavy on the machine. Results:
`runs/screen_rank_audit/<design>/{full,quick}/result.json`, verdicts in `report.json`.

## Result (run 2026-10-08 01:34–04:19)

**Both quick tiers FAIL. Neither may be used to skip a full Assess.**

| Tier | n | ρ vs full free | ρ vs full load | full top 3 (load) in quick top 5 | Verdict |
|---|---|---|---|---|---|
| Q1 full mesh, free-air, 300 it | 8 | 0.79 (≥ 0.90) | 0.55 (≥ 0.80) | no — t9000 missed | FAIL |
| Q2 coarse 8 mm, free-air, 300 it | 8 | 0.79 (≥ 0.90) | 0.60 (≥ 0.80) | no — t9000 missed | FAIL |

Efficiency (report only): ρ 0.24 / 0.26.

Per design (full Assess, "case" hose; quick = raw CFD free-air CFM):

| Design | Full free | Full load | Full η % | Q2 quick | Full cells | Full time |
|---|---|---|---|---|---|---|
| t9016 | 68.1 | 46.3 | 29.2 | 85.9 | 892k | 20 min |
| t9000 | 51.6 | 45.5 | 29.5 | 57.6 | 1.07M | 24 min |
| t9015 | 54.4 | 44.4 | 24.2 | 58.8 | 352k | 8 min |
| t9008 | 55.1 | 44.3 | 23.7 | 59.3 | 344k | 7 min |
| t9006 | 52.5 | 42.8 | 24.3 | 54.4 | 341k | 7 min |
| stock | 50.3 | 41.5 | 19.9 | 58.5 | 865k | 19 min |
| stock_dimples | 50.3 | 41.5 | 19.9 | 58.6 | 865k | 19 min |
| t9012 | 22.7 | 22.2 | 3.5 | 26.5 | 1.41M | 35 min |

Rejected by the Assess gates in ~5 s (blade bend frequency too close to blade-pass tone): stock_thin,
t9001, t9002, t9003, t9005.

Why it fails: free-air ranking is only moderately predictive, and the designs differ mostly in how
they hold up under load (t9000: 5th by free air, 2nd by load). A free-air-only screen cannot see that.
Q2 costs ~3 min and ranks exactly like Q1, so the coarse mesh is not the problem; the missing load
point is.

Caveats found while checking:

- **"stock" here is the 3-station flat build, not the 7-station signed-off recipe** (roadmap
  §23.1, found 2026-10-08). The ranking verdict doesn't depend on it; redo the row after the fix.
- **stock_dimples had no dimples** (setup error: only `dimple_amp` was set; dimples need rows and
  cols too). Its STL is byte-identical to Stock. Effective n is 7 distinct designs; the verdict does
  not depend on it.
- **Full-Assess meshes differ by design.** The wall-adaptive surface level gives thin-walled blades
  level 4 (0.86–1.41M cells) and thicker ones the level-3 floor (~0.35M). Rankings between the two
  groups carry a mesh-resolution difference. Not changed here; flagged for its own check.
- The 5 vibration rejections come from the flutter gate, whose beam model is order-of-magnitude
  (§19.18) and is applied as a hard reject.

Next candidate (needs its own pre-registered test, not a threshold change): a quick tier that also
solves the load point (coarse mesh, free + load, 300 it each, ~6 min).
