# Derive NU_AIR from MU_AIR / RHO_AMCA (#48) — 2026-11-25

Before this change, `NU_AIR = 1.5e-5` was a rounded literal (~0.55 % below `MU_AIR / RHO_AMCA`).
`tests/audit/test_air_properties.py` already required agreement within 3 %.

**Change:** `NU_AIR = MU_AIR / RHO_AMCA` (exact). Registry claim updated. Physics snapshot `air`
row regenerated (`scripts/physics_snapshot.py --write`) citing this file. Re-prove
`physics.air_properties`. Downstream units that only *depend_on* air stay fingerprint-stable
once air is PROVEN again.

No model-vs-data judgment — same physical air, consistent ν.

Side effects of ν ≈ +0.55 %: Euler Stock planar shut-off 38.87→38.88 Pa; E_rand1396 axial-force
peak η 0.99→0.968 (still ≤1). Physics snapshot rewritten; `physics.air_properties` +
`physics.regime` re-proven. Dependants fingerprint-stable → PROVEN again.
