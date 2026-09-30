# Unregistered physics triage — 2026-09-30 (updated close)

`scripts/audit_status.py --unregistered` after §19.5 close: **0** (scaffolding
exempted; owed physics units registered — see `2026-09-30-audit-19-5-close.md`).

## Registered in the close pass

| Unit | Checks |
|------|--------|
| `propeller.bemt` | narrowed claim; Audit #3 / §20.2 |
| `propeller.polars` | `tests/test_uiuc_polars.py` |
| `propeller.neuralfoil_polars` | `tests/test_neuralfoil_polars.py` (skip w/o extra) |
| `propeller.noise` | ranking-only |
| `acoustics.loading` | ranking-only |
| `centrifugal.bem` | mixed BEM screen |
| `cror.noise` | ranking-only + \|thrust\| |

## Policy

New public physics under `PHYSICS_PACKAGES` that is not scaffolding must get a
registry unit + checks before claiming PROVEN. Re-run `scripts/audit_status.py`
on physics changes (CHANGED / AFFECTED / NEW).
