# Unregistered physics triage — 2026-09-30

`scripts/audit_status.py --unregistered` listed ~310 public symbols under
`PHYSICS_PACKAGES` with no registry unit. Most are scaffolding, not audited
physics. This note exempts the scaffolding patterns and lists the real clusters
still owed a unit.

## Exempt (scaffolding / I/O / UI helpers)

Added to `registry.yaml` `exempt:` as fnmatch patterns. These are not claims
about equations — workers, persist, params_io, archetype shells, preview/export
wrappers, OpenFOAM runner plumbing, midplane PNG builders, timing helpers.

See `exempt:` in `fansim/audit/registry.yaml`.

## Registered this pass (PROVEN 2026-09-30)

| Unit | Checks |
|------|--------|
| `physics.regime` | `tests/test_motor_regime.py` |
| `cfd.duct_area` | `tests/test_duct_area.py` |
| `cfd.spanwise` | `tests/test_spanwise.py` (§20.3) |

## Still owed units (physics / metrics — do not exempt)

| Cluster | Why |
|---------|-----|
| `fansim.fan_bem:FanCurve` / `FanPoint` | BEM curve types (core ops already under `fan.bem_prescreen`) |
| `fansim.propeller.polars` / `neuralfoil_polars` | polar backends (§20.2 / §19.15) |
| `fansim.propeller.noise` / `cror.noise` | relative noise proxies (§1.4) |
| `fansim.propeller.calibrate` / `power` | datasheet / hover budget |
| `fansim.acoustics.loading` + leftover Curle helpers | ranking proxies not in Audit #6 targets |
| `fansim.centrifugal.bem` | mixed BEM screen honesty |
| `fansim.cror.noise` / evaluate metrics | CROR screening |

Do **not** mark these PROVEN without checks + a report. Next pass: polar backends / prop noise.
