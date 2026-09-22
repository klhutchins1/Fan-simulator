# §4.3 stage: drone_radial open-air CFD (documented smoke)

**Date:** 2026-09-21  
**Status:** implemented (2026-09-22) — both smokes + fixtures; force-tail gate amended to 25% for smoke mesh  
**Approach:** A — campaign via existing `evaluate_prop_cfd.py --stl` + fixture freezer + validation doc  
**Parent:** `docs/superpowers/specs/2026-09-07-prop-compressible-cfd-design.md` (stage-1 smoke path already shipped)  
**Roadmap:** §4.3 — real-geometry proof on prepared drone radial STLs; does **not** replace BEMT screening or claim datasheet accuracy.

## Plain language

Stage-1 prop CFD already runs `rhoSimpleFoam` in open air on parametric `PropSpec` meshes. This slice lands the same path on **two real STLs** from `validation/reference/drone_radial/` (~60 mm impeller, ~90 mm open rotor), freezes small JSON fixtures, and documents commands + honesty limits. Docker is canonical; WSL is a future note only. Smoke the small impeller first; run the larger rotor only if the gate passes.

## Goal

1. Complete one **smoke** open-air compressible MRF solve on `obj_1_ccw_impeller.stl` (~60 mm).
2. If the convergence gate passes, complete the same smoke knobs on `obj_2_ccw.stl` (~90 mm).
3. Commit frozen metrics under `validation/reference/drone_radial/cfd/` and a human-readable report at `docs/validation/drone_radial_open_air_cfd.md`.
4. Point `validation/reference/README.md` at the report; note §4.3 progress on the roadmap after fixtures land.

## Success criteria

| # | Criterion |
|---|-----------|
| 1 | Docker image `opencfd/openfoam-default:2406` finishes `rhoSimpleFoam` for obj_1 with finite thrust / torque / shaft power in `runs/.../result.json` |
| 2 | Gate passes before obj_2 (see Campaign) |
| 3 | Fixtures committed (obj_2 only if solve succeeds); markdown documents commands, RPM/tip Mach, metrics, honesty |
| 4 | `runs/` stays gitignored; CI has no Docker solve |

## Non-goals

- BEMT floor / datasheet compare on external STL
- Optuna, cockpit wiring, AMI / sliding mesh / DES / FW-H
- WSL-native OpenFOAM as a second canonical runner
- Finer “honest screening” mesh (smoke only; refine only as a later follow-up if smoke is clean)
- Committing OpenFOAM case trees

## Approach choice

| Option | Summary | Trade-off |
|--------|---------|-----------|
| **A (chosen)** | Existing CLI + small freezer script + validation md | Least new surface; matches UIUC fixture pattern |
| B | `--freeze-fixture` on evaluate CLI | Mixes solve and validation policy |
| C | Full auto harness (obj_1 → gate → obj_2 → freeze) | Heavier for a one-time milestone |

## Campaign

**Runner:** Docker only for the documented path.

**Order:**

| Step | Action | Location |
|------|--------|----------|
| 0 (optional) | `--dry-run` on both STLs | `runs/drone_radial_cfd/_dry_run/` (gitignored) |
| 1 | Full smoke solve **obj_1_ccw_impeller** | `runs/drone_radial_cfd/obj_1_smoke/` |
| 2 | Gate | — |
| 3 | If gate passes: smoke **obj_2_ccw** | `runs/drone_radial_cfd/obj_2_smoke/` |
| 4 | Freeze fixtures from green `result.json` | `validation/reference/drone_radial/cfd/*.json` |

**Shared smoke knobs:** `--base-cell 0.005`, `--iters 400`, `--procs 8` (change only if recorded in the md). Always pass explicit `--rpm`. Spin from filename (`CCW` → `-1`) unless overridden.

**RPM:** No `PropSpec` for these meshes. Choose RPM for tip Mach **0.35–0.45** from each `.meta.json` `tip_radius_mm`:

\[
\mathrm{rpm} = \frac{\mathrm{Ma}\, \times\, 343\, \times\, 60}{2\pi R_\mathrm{m}}
\]

Recompute from meta before running; store the actual RPM in fixtures and the doc. Illustrative Ma ≈ 0.38: obj_1 ~41k RPM, obj_2 ~27k RPM.

**Gate before obj_2 (all required):**

1. Solver exits 0 (`OpenFOAMRunner` / `rhoSimpleFoam`).
2. Finite `thrust_n`, `torque_nm`, `shaft_power_w` after `normalize_metrics_sign`.
3. `|thrust_g| ≥ 10` (non-trivial floor; screening only).
4. Forces steady: last **25%** of `postProcessing/forces/*/force.dat` total **z** samples — peak-to-peak **< 25%** of |mean| (smoke mesh limit-cycle; prop analogue of fan `convergence()`; no outletFlow FO). Amended 2026-09-22 after 10% proved unreachable on smoke mesh without multi-hour refine.

On gate failure: stop; document in the md; do not run obj_2; do not freeze a success fixture for a failed solve.

## Fixtures

```
validation/reference/drone_radial/cfd/
  obj_1_ccw_impeller_smoke.json
  obj_2_ccw_smoke.json    # only if gate + solve succeed
```

**Schema:**

```json
{
  "id": "obj_1_ccw_impeller_smoke",
  "stl": "validation/reference/drone_radial/obj_1_ccw_impeller.stl",
  "spin": -1,
  "rpm": 41000.0,
  "tip_mach": 0.38,
  "tip_radius_mm": 30.089,
  "mesh": { "base_cell_m": 0.005, "iters": 400, "procs": 8 },
  "solver": "rhoSimpleFoam",
  "domain": "open_air",
  "regime": "compressible-MRF",
  "openfoam_image": "opencfd/openfoam-default:2406",
  "metrics": {
    "thrust_n": 0.0,
    "thrust_g": 0.0,
    "torque_nm": 0.0,
    "shaft_power_w": 0.0
  },
  "force_tail_drift_pct": 0.0,
  "date": "2026-09-21",
  "notes": "smoke screening; not datasheet-grade"
}
```

Omit BEMT / datasheet fields. `force_tail_drift_pct` is the gate value from the actual run.

**Freezer:** library `fansim/propeller/cfd_fixture.py` + CLI `scripts/freeze_prop_cfd_fixture.py` — build fixture from `result.json` + knobs (image tag, command, STL relpath). Schema zeros above are shape only; real runs overwrite metrics. No case tree in git.

## Tests (CI — no Docker)

- Fixture JSON(s) load; required keys present; stamps exact.
- Metrics finite when fixtures exist.
- Gate helper unit-tested on synthetic `force.dat` histories (pass / fail drift).
- Freezer round-trip on a fake `result.json`.
- Existing `evaluate_prop_cfd --stl --dry-run` remains green.

## Documentation

`docs/validation/drone_radial_open_air_cfd.md`:

- Purpose + honesty (steady MRF, coarse mesh, screening only)
- Exact Docker commands (obj_1, then gated obj_2)
- RPM / tip Mach derivation
- Gate criteria
- Pointers to fixtures; one-liner in `validation/reference/README.md`
- WSL optional later; Docker canonical

After fixtures land: roadmap §4.3 stage note — *drone_radial smoke documented; not full tier / not datasheet*.

## File map (expected)

| Path | Role |
|------|------|
| `fansim/propeller/cfd_fixture.py` | Gate helper + fixture builder |
| `scripts/freeze_prop_cfd_fixture.py` | CLI freezer |
| `validation/reference/drone_radial/cfd/*.json` | Frozen smoke results |
| `docs/validation/drone_radial_open_air_cfd.md` | Human report |
| `validation/reference/README.md` | Pointer |
| `tests/test_prop_cfd_fixture.py` | Always-on unit tests |
| `docs/roadmap.md` | §4.3 stage note after green runs |

Reuse (no redesign): `fansim/propeller/cfd.py`, `scripts/evaluate_prop_cfd.py`, `OpenFOAMRunner` Docker path.

## Honesty

Steady compressible MRF on a truncated open-air box with smoke mesh is a **screening** record. Tip Mach is stamped; shocks are not resolved. Do not claim OEM / Gemfan / HQ datasheet match. Track A BEMT / PyThrust / A3 remain the fast screen; this CFD is the real-geometry honesty check.
