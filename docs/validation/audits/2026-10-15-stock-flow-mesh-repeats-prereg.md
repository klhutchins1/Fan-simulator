# Stock flow-card repeats on varied meshes (roadmap 27.3b): pre-registration

Written 2026-10-15, **before** any of these solves. HEAD at writing is master after `7db7351`.

## Why

The ±3 % / 0.5 dB thresholds (27.3) came from five re-solves of the **same** mesh: free-air spread ~0.1 %,
which is solver noise only. A design-vs-Stock comparison always has a different mesh. On the old setup,
mesh differences alone moved Stock's mean push ~5 % and single bands ~14 % (F2). This campaign measures
mesh-to-mesh scatter on Stock itself.

## Setup (fixed)

Identical to `2026-10-13-stock-flow-repeats-prereg.md`, except the background cell size:

| run | base_cell |
|---|---|
| m1 | 0.0056 m |
| m2 | 0.0058 m |
| m3 | 0.0062 m |
| m4 | 0.0064 m |
| m5 | 0.0066 m |

Everything else is the same: Stock v3 (`stock_blade_flat("a12x25")`), spec a12x25, hose "case", 8 procs, 500 iterations, PETG,
refine_op False, parallel_mesh True.
- The adaptive surface level (`MeshResolution.for_blade`) follows the base cell as it does in Assess. A level
  change at some size is part of the scatter being measured, because designs with different walls get
  different levels too.
- Each run gets a new case directory `runs/stock_flow_mesh_repeats/m{1..5}/`.
- Runner: `scripts/stock_flow_mesh_repeats.py`, launched as a Windows Scheduled Task.
- Flow metrics come from `load_or_compute_metrics` at `FLOW_REPORT_VERSION` 3, on the loaded field.
- n must be 5 OK solves. A failed eval is not replaced; stop and report.

## Rule (fixed now; apply only after n = 5)

1. Apply the same 2σ formula as 27.3 to the five varied-mesh runs: `proposed_tolerances` in
   `scripts/stock_flow_repeats.py`, with the same floors and rounding up.
2. **Never tighten:**
   - new `BAND_TOL` = max(0.03, proposed);
   - new `NOISE_MARGIN_DB` = max(0.5, proposed).
3. If the proposed `BAND_TOL` exceeds **0.15**, or the proposed noise margin exceeds **3.0 dB**, don't bake.
   Report it and ask Kimball: the card would then say "about the same" for almost everything, which is a
   finding about mesh dependence, not a threshold.
4. Report the free and loaded CFM spread as well (mesh dependence of the score itself, information only).

## After baking

Judge m2–m5 against m1 with the new constants. Every mean-push row should read "about as hard", and no noise row
should read ⚠. A failure is recorded, not re-widened.

## Results

n = 5 OK solves, 2026-10-16. All at surface level 4, so only the background mesh changed. The first launch
died at start-up (a `cmd.exe` wrapper killed by a console signal) and was relaunched with no code change.

| run | base cell | CFM free / load | mean push Pa | Proudman SWL dB |
|---|---|---|---|---|
| m1 | 5.6 mm | 53.31 / 43.61 | 12.54 | −13.7 |
| m2 | 5.8 mm | 53.04 / 43.27 | 12.77 | 22.2 |
| m3 | 6.2 mm | 53.58 / 43.66 | 12.98 | −4.7 |
| m4 | 6.4 mm | 52.45 / 42.77 | 12.71 | 19.4 |
| m5 | 6.6 mm | 53.13 / 43.21 | 12.95 | 18.2 |

- **The score is mesh-robust:** free 52.45–53.58 (±1 %), loaded 42.77–43.66 (±1 %).
- **Push:** proposed `BAND_TOL` **0.08**, set by the single bands. The mean push alone gives 2σ ≈ 2.9 %. That is
  below the 0.15 stop line.
- **Noise:** proposed `NOISE_MARGIN_DB` **32.8 dB**. The Proudman level swings −14 to +22 dB on mesh alone, against
  0.2 dB on same-mesh repeats. That is above the 3.0 dB stop line.

**Verdict: STOP AND ASK, as pre-registered. Nothing baked.** `flow_verdicts.py` is unchanged (0.03 / 0.5 dB).
What this shows:
1. Between designs, the noise row is not a measurement. The turbulence near the blades that feeds Proudman is not
   mesh-converged at the Assess mesh.
2. Mesh noise on the push bars is about 8 %, not 3 %.

Kimball decides.

## Decision (Kimball, 2026-10-16)

- **Push:** the mean-push verdict keeps `BAND_TOL` 0.03, because the mean alone gave 2.9 %. The single bars get
  their own `BAR_TOL` **0.08**. They now say "stronger/weaker" only past 8 %.
- **Noise:** not judged (`NOISE_JUDGED = False`). The row is shown only in Expert mode, marked "Not judged",
  and it never enters the verdict or the overall better/worse line. The raw Proudman number stays in the
  Expert numbers table, labelled mesh-dependent. A mesh-robust noise estimate is roadmap 27.3c.

## After-bake check (m2–m5 judged against m1 with the new constants)

| run | push (mean) | bars | dead / blocked | noise | overall line |
|---|---|---|---|---|---|
| m2 | about as hard | all similar | **⚠ weak tips** (tip ratio 0.846 vs 0.954 × 0.90 = 0.859) | not judged | Worse at: dead or blocked air |
| m3 | **+3.5 % "harder"** | all similar | ok | not judged | Better at: push |
| m4 | about as hard | all similar | ok | not judged | About the same |
| m5 | **+3.3 % "harder"** | **hub "stronger"** (+9.5 %) | ok | not judged | Better at: push |

**FAIL, recorded, not re-widened.** The pre-registered pass condition was that every mean-push row reads
"about as hard", and it fails twice. The 2σ rule sizes the *scatter of one run*, but a design-vs-Stock comparison
is the *difference of two runs*, whose spread is about √2 larger (about 4 %). Mesh alone also tripped two
rules this campaign did not size: the tip-speed check (TIP_FACTOR 0.90, m2 −11 %) and one hub bar (m5, +9.5 %).

What this means for reading the card today:
- A mean-push "harder/less" under about 4 % can be mesh.
- A lone "weak tips" warning can be mesh.

Roadmap 27.3d covers sizing these for a two-run difference.

