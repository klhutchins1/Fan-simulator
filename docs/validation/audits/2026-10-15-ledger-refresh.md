# Ledger refresh: 2026-10-15

Method: as in `2026-10-10-ledger-refresh.md`.
1. Run `scripts/audit_status.py`.
2. Re-run each CHANGED unit's registered `checks`, plus the dependants' checks (no Docker).
3. When they are green, `record_pass` with the new fingerprint and this report.

Before: PROVEN 23, CHANGED 3, AFFECTED 5, UNREGISTERED 21.

| Unit | Change since its last pass | Verdict |
|------|------|---------|
| `geometry.stock_handedness` | Wrapped sections (27.4), capped ruled lofts, hub-hang limit and cut correction (QA-32), fuse fallback, **Stock v3** YAML (`a12x25_reference.yaml`) | **PASS**: the Stock v3 rotor still proves omega_z +1, pumps −Z, real-fan chirality |
| `optimize.search_space_handedness` | `suggest_params` / `blade_from_flat` set `section_wrap`; `tip_radius_cap_mm` takes the design's wrap; `UNIFORM_WALL_TOL_MM` | **PASS** |
| `fan.bem_prescreen` | Its BEM code-lock test now uses the fixed v2 input (Stock moved to v3); the efficiency-bound QA design is pinned to its v2 base flat | **PASS** |
| dependants: `cfd.archetype_direction`, `cfd.cfm_from_outlet_flow`, `cfd.flow_direction_convention`, `propeller.cfd_setup`, `propeller.thrust_sign` | none of their own code changed | **PASS** with their parents |

Checks run: `tests/audit/test_{cfd_direction_contract, cror_mixed_setup_audit, fan_bem_audit, prop_builder_direction, prop_cfd_audit, prop_search_space_handedness, prop_thrust_sign, search_space_handedness, stock_handedness}.py`, `tests/test_{cfd_orientation, cfd_placement_check, convergence_rule, fan_bem, math_consistency, prop_cfd}.py`, with `-m "not docker"`: **119 passed**.

**New unit `cfd.flow_report`** (the flow report card's maths; it had been unregistered: 21 targets). Registered with
its I/O, pictures and data containers exempt. Checks `tests/test_flow_report.py` and `tests/test_flow_verdicts.py`:
**41 passed** together with `test_air_properties`. QA r7 Task G independently checked the same maths (G1 16/16).

After: all units PROVEN, UNREGISTERED 0.

Not re-proven here, because nothing in it changed: the CFD rigs themselves (Docker), the acoustics, structural
and prop units (PROVEN). QA-12 (prop CT0 creep) is parked as "needs data".
