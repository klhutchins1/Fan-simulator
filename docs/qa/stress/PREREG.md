# Builder stress test: pre-registration (QA round 6, Task A)

- **Written:** 2026-10-09 (MDT), before any stress build.
- **Code:** master `31228d0`, clean clone `/workspace/fansim/repo-r6`, `uv sync --extra dev`, Linux, 16 GB box, no swap.
- **Committed:** in the QA-only clone `/workspace/fansim/qa/prereg_r6`, branch `prereg/round6`. The commit hash and sha256 are recorded in `handoff/2026-10-09_from-qa-5/README.md`.
- **Role:** QA finds and classifies; it does not fix.

## 1. Sample (brief A1)

**Sampler (S1–S7):**
- `fansim.optimize.search_space.suggest_params(trial, …)` driven by `optuna.samplers.QMCSampler(qmc_type="sobol", scramble=True, seed=<stratum seed>)`, one single-objective study per stratum (in memory).
- Each trial is `study.ask()`, then `suggest_params`, then `study.tell(trial, 0.0)`. Telling is what lets QMC infer the search space; Optuna samples the first trial of each stratum independently, which is a known QMC detail.
- Each design is stored as `blade_to_flat(bp)` plus `asdict(bp.features)`.
- A `ValueError` raised by the sampler itself is recorded as `REJECTED`.

| stratum | space | flags | seed | count (full, before pilot sizing) |
|---|---|---|---|---|
| S1 | open | — | 6001 | 600 |
| S2 | guided | — | 6002 | 300 |
| S3 | guided_lc | — | 6003 | 200 |
| S4 | open | with_extended | 6004 | 400 |
| S5 | open | with_extended, with_features | 6005 | 300 |
| S6 | open | with_winglet, with_spacing | 6006 | 200 |
| S7 | open | with_shroud | 6007 | 200 |
| S8 | edges | see below | 6008 | 141 (always complete) |

**S8, edges** (`with_extended=True`, built through `optuna.trial.FixedTrial`):
- **Centre:** the midpoint of every bound in `BOUNDS["open"]` + `EXTENDED`; `n_blades` = 8.
- **One-at-a-time:** each of the 18 bounded parameters (12 open + 6 extended) is set to its min, then its max, with the rest at the centre. That is 36 designs.
- **Risky corners:** 20 draws each (`numpy.random.default_rng(6008)`). The named parameters are uniform in the stated sub-box; every other parameter is uniform in its full open+extended range. "Top 10 %" means the top tenth of the bound range.
  - c1: `max_camber` ∈ [0, 0.02], `lean_tip` ∈ [20, 45] (the direction false-refusal region).
  - c2: all three thicknesses in the bottom 10 %, `chord_tip` in the top 10 %.
  - c3: `n_blades` ∈ {10, 11}, all three chords in the top 10 % (overlap, solidity > 1.2).
  - c4: `sweep_tip` and `lean_tip` both in the top 10 %.
  - c5: `hub_radius` in the bottom 10 %, `chord_root` in the top 10 %.
- **Controls (5):** Stock (`stock_blade_flat("a12x25")`) and the four refused screen-r3 designs 9605, 9606, 9620, 9630. Their flat params come from repo-r3 `handoff/2026-10-09_from-qa-2/screen_r3/cockpit_import/runs/bem_screen_r3_{top5,reserve}/cockpit_assess/design_<id>/design.json`.
- All 141 inputs are written to `inputs.jsonl` **before any build**. The runner also never builds a design whose input line isn't already on disk.

**Pilot (A2):** the first 5 designs of each of S1–S7 (35), the first 10 of S8 (edges), and the 5 controls. That is 50 designs. They are the first designs of the full run, so the full run resumes after them instead of repeating them.

## 2. Build kinds (brief A3)
- **P (every design):** `build_stl_isolated(flat, features, out, preview=False, timeout=300)`, no motor cup.
  - **Change:** `FANSIM_MEMORY_TIER=8gb` is forced for P and C. Reason: the tier would otherwise be auto-detected from the RAM free at that moment. On this shared box that would make the fuse strategy, and so the time and memory, depend on other jobs. The `16gb` parallel fuse (~7.7 GB) also can't safely run back-to-back here. Every tier is claimed to give an identical solid, and K8 tests that claim.
- **C (1 in 20 of S1–S7 by within-stratum index `idx % 20 == 0`, plus all of S8 and the controls):** the same build with `motor_mount=asdict(get_fan_spec("a12x25").motor_mount)`.
  - Timeout is 600 s. The brief gives none for C, and the lean tiers are 2.7× slower.
  - If `hub_radius < mount_min_hub_radius(spec)`, the design is marked `CUP_NA` and K7–K9 are N/A. That is counted, not a failure.
  - One at a time.
- **T (the S1–S7 C subsample plus the 5 controls; not the S8 edges/corners):** the C build repeated with `FANSIM_MEMORY_TIER` = `16gb`, `8gb`, `6gb`.
  - The C build (already 8gb) is reused as the T-8gb sample.
  - Before a 16gb build the runner waits up to 10 min for MemAvailable ≥ 9.5 GB. If it never gets there, that tier is `SKIPPED_MEM` and its K8/K9 are N/A (counted).
  - Timeout is 600 s.
- **R (global sequence number `seq % 50 == 0`):** the P build repeated from the same params.

**Outcome class for every build:**
- `OK`.
- `REJECTED`: `blade_from_flat`/`validate_blade_params`/the sampler raised `ValueError` in the runner, or the worker's error tail names `ValueError`.
- `BUILD_FAIL`: any other exception, or a worker that exited non-zero with a Python traceback, or exited 0 without its STL.
- `CRASH`: the worker died by a signal, or exited non-zero with no Python traceback in the tail.
- `TIMEOUT`.

## 3. Checks (brief table; changes marked ▲)

| id | check | how | pass rule |
|---|---|---|---|
| K1 | builds | P outcome class | `OK` or `REJECTED`. `BUILD_FAIL`, `CRASH` and `TIMEOUT` are findings. |
| K2 | printable solid | trimesh on the P STL | `is_watertight`, exactly 1 body (`split(only_watertight=False)`), volume > 0. ▲ "No degenerate faces" is made concrete: 0 faces with area < 1e-9 mm². |
| K3 | nothing below the hub face | mesh z_min vs `_hub_axial_range(params)[0]` | z_min ≥ hub face − 0.05 mm (all designs here are fans) |
| K4 | inside the tip radius | max vertex radius | Open tip: ≤ `tip_radius + TIP_TRIM_TOL_MM`. Shrouded: within ±0.1 mm of the ring outer radius as designed. ▲ That radius is defined as `open_tip_rmax_mm(params) + shroud_thick_mm`, the formula `_shroud_solid` uses. |
| K5 | direction proof | `prove_direction(mesh)` on the P STL | `CONCLUSIVE` must read omega +1, pump −1. `CONCLUSIVE` + disagree = **false refusal** (FAIL). `INCONCLUSIVE` is PASS but counted separately. |
| K6 | mirror | mesh with x → −x, proved again | If both are `CONCLUSIVE`, omega flips sign; otherwise N/A |
| K7 | cup depth (C only) | ray-cast from the axis (as in the r4 E8 check) | Cup floor 13.0 ± 0.2 mm above the hub face (`_hub_axial_range(params)[0]`), and the full grip: 20 pads with protrusion 0.70 ± 0.15 mm |
| K8 | tier equivalence (T only) | STLs from 16gb/8gb/6gb | Volume within 1e-6 relative and the same vertex count, against the 8gb build. Byte-identity (sha256) is reported separately. |
| K9 | tier memory (T only) | peak RSS of the build subprocess tree (sampled every 0.2 s) | ≤ the tier's `min_free_gb` (16gb 10.0, 8gb 6.5, 6gb 5.0 GB), i.e. the free RAM at which `resources.TIERS` declares the tier safe. ▲ Also reported, without a pass/fail: the peak vs the docstring's Stock figures (7.7 / 4.9 / 4.5 GB). |
| K10 | determinism (R only) | rebuild P | Identical STL sha256 |
| K11 | readouts | `grade_printability(params)`, `blade_solidity(params)`, `min_blade_wall_mm(params)` | No exception; all returned numbers finite |

- K2–K6 are N/A when P isn't `OK`.
- **Recorded per design:** n_blades; stagger/chord/sweep/lean at every station; `max_camber`; thickness; hub and tip radius; solidity root and tip; min wall; sampler flags; per-build time, peak RSS and outcome; all measured values.

## 4. Runner
- **Resumable.** `designs.jsonl` is append-only, and on restart the runner skips ids already present. Each design runs in its own child process and its own temp dir, and the STL is deleted after its checks.
- **Kept STLs:** at most 10 STLs under 5 MB, from K2, K3 or K4 failures.
- **Concurrency:** 1.
- **A compact `summary.json`** (counts by stratum × outcome, check fail counts, median times, peak RSS, ETA) is rewritten after every design.
- **Stop rule:** halt only if more than 30 % of the first 200 designs fail K1.

## 5. Report (brief A4)
`designs.jsonl.gz` and `summary.md` contain:
1. a rate table, stratum × K1–K11, as fail/tested;
2. findings clustered by kind, ranked by how often S1–S3 hit them, each with the shared input features, the smallest repro (`repro/<id>.json`) and the exception text or measured value;
3. the K5 map: false-refusal and INCONCLUSIVE rates binned by `max_camber` × `lean_tip`, plus any better-separating axis found afterwards (labelled exploratory);
4. timing and memory per build kind and per tier.

## Amendments after pilot
(Only counts, timeouts and worker count may change here.)

1. **Counts (2026-10-10 08:58 MDT).** S1–S7 are scaled by the same factor, 0.3. The new counts are S1 180, S2 90, S3 60, S4 120, S5 90, S6 60 and S7 60, each taken as the first N designs of that stratum's Sobol sequence. S8 (136 designs) and the controls (5) stay complete. That makes 801 designs. Reason: the pilot medians (a job takes about 25–55 s; a T design takes 3–12 min) put the full sample at more than 30 h, and the brief asks for about 8–12 h.
2. **Timeout: the memory wait before a T-16gb build (made during the pilot).** Originally the runner waited up to 10 min for 9.5 GB to be free. That level is never reached on this shared box. The wait is now: up to 60 s for max(2 × the design's 8gb C peak + 1 GB, 4 GB), and otherwise the build is recorded as `SKIPPED_MEM`. During the pilot the limit was 180 s; it became 60 s on 2026-10-10. The 16gb parallel fuse peaks at about 1.6× the serial fuse (round 4).
3. **Runner logging only (no criteria change).** Each build now also records monotonic seconds, the CPU time of its child processes, and a `suspect_suspend` flag (wall time − monotonic time > 60 s). Reason: in the pilot one T-6gb build showed 30,072 s of wall time while its 600 s subprocess timeout (which uses the monotonic clock) never fired. That is consistent with the box being suspended, not with a slow build. Flagged builds are left out of the timing tables.
4. **The T/C timeout stays at 600 s, as pre-registered.** I deliberately did not add a 20-minute wall-clock timeout. It would turn box suspensions into false `TIMEOUT` findings.
