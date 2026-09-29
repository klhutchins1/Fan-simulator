# Air-constant consolidation (2026-09-29)

**What changed.** The 19 module-level copies of air constants (RHO_AIR, NU_AIR, C0_AIR, C_SOUND, C0) in
14 files under `fansim/` and `scripts/` are now imports from `fansim.physics.air`, keeping each local
name as an alias. Fan/CFD/acoustics modules use `RHO_AMCA` (1.2); prop/turbine modules use `RHO_ISA`
(1.225). `KNOWN_COPIES` in `tests/audit/test_air_properties.py` is now empty and a new test asserts it.

**No numeric change.** Every replaced literal equals the value it now imports (1.2, 1.225, 1.5e-5, 343.0).

**Tests run.** `pytest -q -m "not slow"`: 1255 passed, 4 skipped, 2 xfailed. `pytest tests/audit -q -m "slow or not slow"`:
183 passed, 2 xfailed.

**Re-recorded** (fingerprint moved only because target modules changed their import lines; checks pass):
`cfd.cfm_from_outlet_flow`, `cfd.flow_direction_convention`, `physics.air_properties`.
NEW units (`fan.bem_prescreen`, `propeller.bemt`) are left NEW.
