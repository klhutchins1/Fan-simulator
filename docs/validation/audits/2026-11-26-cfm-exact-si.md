# Derive CFM_PER_M3S from exact NIST SI international foot (#87) — 2026-11-26

Before this change, `CFM_PER_M3S = 2118.882` was a rounded literal (+0.94 ppm above exact SI).

By the International Yard and Pound Agreement (1959) and NIST SP 811:
- $1\text{ ft} \equiv 0.3048\text{ m}$ (exact)
- $1\text{ ft}^3 = 0.3048^3\text{ m}^3 = 0.028316846592\text{ m}^3$ (exact)
- $\text{CFM\_PER\_M3S} = 60 / 0.3048^3 = 2118.880003289315\ldots\text{ (ft}^3/\text{min})/(\text{m}^3/\text{s})$

**Change:** `CFM_PER_M3S = 60.0 / (0.3048**3)` in `fansim/cfd/metrics.py` (single source, #49).
Registry claim for `cfd.cfm_from_outlet_flow` updated. Physics snapshot regenerated
(`scripts/physics_snapshot.py --write`) citing this file (~−0.94 ppm shift on CFM entries only;
all pressures, efficiencies, powers, and propeller coefficients unchanged). Re-prove
`cfd.cfm_from_outlet_flow` and check-affected units (`cfd.duct_area`, `fan.bem_prescreen`).

No model-vs-data judgment — exact SI unit conversion.
