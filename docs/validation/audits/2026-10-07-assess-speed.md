# Assess speed: why runs timed out, and what changed (2026-10-07)

Question: cockpit Assess runs kept hitting the 60-minute timeout. Where does the time go, and what
can be made faster without changing the validated (v5) CFD answer?

## Where the time goes

A 1.07M-cell Assess (design_9000, 2026-10-07) on a quiet machine:

| Stage | Time |
|---|---|
| Meshing (snappyHexMesh serial, ~7 of it) | ~8–9 min |
| Free-air solve, 500 iters | ~10–11 min |
| Load solve, 500 iters | ~10–11 min |
| Refine-op solve (optional) | +~10 min |

In September an Assess mesh was ~95k cells and a solve took ~40 s. The validated v5 setup (ring,
frame, wall-resolving surface floor) produces 850k–1.07M cells, ~10x the work. On a quiet box an
Assess is ~30–40 min, i.e. most of the old 60-min budget.

Measured on 60-iteration solves of the same 1.07M-cell case (Ryzen 7 5800X3D, dual-channel
DDR4-3200, Docker/WSL2 capped at 8 vCPUs):

- **Ranks:** 4 → 8 ranks only ~12% faster (95 s vs 82–86 s); 6 ranks matched 8 (79 s). simpleFoam
  is memory-bandwidth bound here; more cores on one case do not help.
- **Concurrency:** two 4-rank cases at once took 154 s each (vs 95 s alone) in one trial and
  392 s each in another — no throughput gain, and a large downside.
- **Run-to-run variance:** identical work varied 69–140 s. The Docker VM has no priority over
  desktop apps, so a busy desktop slows a solve 1.5–3x. design_9000's free-air solve took ~23 min
  where ~10 was expected.
- **Disk:** the T: HDD vs NVMe made ~6% difference to the solve. Not the cause.

## Changes

1. **Watchdog instead of a flat timeout** (`fansim/isolated_job.py`). A CFD worker is killed when
   its case dir shows no new output for 15 min (`FANSIM_CFD_STALL_TIMEOUT`), or at a 3 h hard cap
   (`FANSIM_CFD_EVAL_TIMEOUT`, was a flat 60 min). Slow-but-progressing runs finish; hung runs die.
   Applies to axial and mixed-flow Assess.
2. **Live solver logs** (`fansim/cfd/runner.py`). OpenFOAM stdout streams to `logs/<app>.log` while
   the command runs (it was written only on exit, so a killed solve left no log), and the log is
   named for the app (`simpleFoam.log`), not `mpirun.log` (potentialFoam's was overwritten).
3. **Free-air salvage** (`objectives.PARTIAL_FREE_FILE`). The free-air metrics are written as soon
   as that solve finishes; a timeout during the load solve reports them.
4. **Progress hint** shows the live iteration and, for axial, whether free-air is done.
5. **Parallel snappyHexMesh** (`openfoam_case.mesh_pipeline`, `evaluate_candidate(parallel_mesh=)`),
   decompose → snappy on 8 ranks → `reconstructParMesh -constant`, so everything downstream sees
   the same single-region case. A/B below.

Validation scripts keep the serial mesher; only the Assess path is a candidate for the switch.

## Rejected

- **Early stop on convergence.** Replayed on 85 solved histories on disk: rules strict enough to be
  safe save only ~10–16% of iterations and still move the reported tail-mean by up to 0.7–1.3%
  vs the fixed 500 (the tail window moves with the stop point). Not worth a new error source.
- **Warm-starting the load solve from free-air.** Without early stop it saves under a minute, and
  `scripts/test_bistability.py` exists because loaded solves near stall can depend on the initial
  field. Not worth the risk.

## Parallel-mesh A/B

### Mesh only (design_9000 inputs)

| | Serial | Parallel (8) |
|---|---|---|
| snappyHexMesh | 418 s | 140 s |
| Mesh stage total | 477 s | 230 s |
| Cells | 1,067,497 | 1,068,232 (+0.07%) |
| Max non-ortho / skewness | 64.91 / 6.66 | 64.95 / 6.66 |
| checkMesh flagged items | 1 | 1 (same item; present in production meshes too) |

### Stock through the Assess path (`scripts/ab_assess_speed.py`)

Pre-registered acceptance (written before the run): parallel vs serial
|Δ cfm_free| ≤ 1.0%, |Δ cfm_load| ≤ 2.0%, |Δ efficiency| ≤ 1.0 point, same `converged` flag.
Fail → the switch stays off.

Result (2026-10-07, Stock a12x25, "case" hose 8 Pa, 865k cells):

| | Serial | Parallel mesh | Δ | Limit |
|---|---|---|---|---|
| cfm_free | 50.25 | 50.28 | +0.05% | ≤ 1.0% |
| cfm_load | 41.43 | 41.49 | +0.15% | ≤ 2.0% |
| efficiency | 19.72 % | 19.83 % | +0.10 pt | ≤ 1.0 pt |
| converged | yes | yes | same | same |
| wall time | 24.2 min | 21.2 min | −3.0 min | |

**PASS.** Cockpit Assess now passes `parallel_mesh=True`. The difference is far below the screening
mesh's own uncertainty (GCI_fine ≈ 21%), so `CFD_VERSION` is not bumped and earlier v5 results stay
comparable. Validation scripts, mixed-flow, volute and the optimizer keep the serial mesher until
someone A/Bs them. Raw rows: `runs/assess_speed_ab/*/ab_result.json`.

## Net effect

A quiet-box Stock Assess went from ~24 to ~21 min; a 1.07M-cell design saves ~4 min of meshing.
The bigger change is that a slow-but-progressing run is no longer killed. The solve itself (~2/3 of
the time) cannot be made faster by more cores on this machine.
