# Task 1 Report: Open-air domain sizing

## Status

**DONE**

## Summary

Implemented `PropOpenAir` dataclass and `prop_open_air()` in `fansim/propeller/cfd.py` per roadmap §4.3 stage 1. This module computes open-air compressible MRF domain extents from tip radius (metres), blade z-bounds, and RPM.

## TDD Evidence

### Step 1 — Failing test

Created `tests/test_prop_cfd.py` with `test_prop_open_air_extents` exactly as specified in the task brief.

### Step 2 — Confirmed failure

```
ModuleNotFoundError: No module named 'fansim.propeller.cfd'
```

Command: `uv run python -m pytest tests/test_prop_cfd.py::test_prop_open_air_extents -v`

### Step 3 — Implementation

Created `fansim/propeller/cfd.py` with:

- `@dataclass PropOpenAir` — SI fields: `tip_radius`, `domain_radius`, `z_min`, `z_max`, `mrf_z_min`, `mrf_z_max`, `rpm`, `omega_signed`, `u_freestream` (default 0.1)
- `prop_open_air(tip_radius_m, z_lo_m, z_hi_m, rpm, *, spin=-1, radial_mult=5.0, up_mult=2.0, down_mult=4.0, u_eps=0.1, mrf_margin_m=0.005) -> PropOpenAir`

Domain sizing rules:

| Field | Formula |
|-------|---------|
| `domain_radius` | `radial_mult * R` (default 5× tip radius) |
| `z_min` | `z_lo_m - up_mult * R` (default 2× R above low blade bound) |
| `z_max` | `z_hi_m + down_mult * R` (default 4× R below high blade bound) |
| `mrf_z_min` | `z_lo_m - mrf_margin_m` (default 5 mm margin) |
| `mrf_z_max` | `z_hi_m + mrf_margin_m` |
| `omega_signed` | `spin * rpm * 2π / 60` (default spin=-1) |
| `u_freestream` | `u_eps` (default 0.1 m/s) |

### Step 4 — Confirmed pass

```
tests/test_prop_cfd.py::test_prop_open_air_extents PASSED
1 passed in 4.30s
```

## Files Changed

| File | Action |
|------|--------|
| `fansim/propeller/cfd.py` | Created |
| `tests/test_prop_cfd.py` | Created |

## Out of Scope (not touched)

- Templates, `build_prop_case`, CLI
- `fansim/propeller/__init__.py` exports (caller imports `fansim.propeller.cfd` directly)
- `catalog/catalog.db` (left unstaged per global constraint)

## Commit

```
Add prop open-air domain sizing for compressible CFD smoke.
```

## Concerns

None.
