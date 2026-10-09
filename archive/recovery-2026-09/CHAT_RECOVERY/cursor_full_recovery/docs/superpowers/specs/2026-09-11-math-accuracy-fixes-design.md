# Math / simulator accuracy fixes (§10.1–10.11)

**Date:** 2026-09-11  
**Status:** accepted (verified against source; implement)  
**Roadmap:** `docs/roadmap.md` §10

## Verification summary

| ID | Claim | Verdict |
|---|---|---|
| 10.1 | FWH `c₀²` vs Farassat `c₀`; Curle `1/r²` | CONFIRMED |
| 10.2 | Extra `½ρW³cB Cd` on shaft power | CONFIRMED |
| 10.3 | Prandtl on ducted fan BEM | CONFIRMED |
| 10.4 | Prop BEMT no `a′` / turbine `Vt` sign | FIXED (`Vt=Ωr(1−a′)`) |
| 10.5 | Analytic `0.020 Cl²` induced | CONFIRMED |
| 10.6 | Re≤4e4 clamps up to table | CONFIRMED |
| 10.7 | BEM shutoff = max(ΔP) | CONFIRMED |
| 10.8 | No screening “not grid-converged” stamp | FIXED (axial + mixed + CROR) |
| 10.9 | ρ 1.225 on fan acoustics; CFM factor drift | CONFIRMED |
| 10.10 | No inlet area ≈ πR² check | FIXED (post-snappy wire) |
| 10.11 | δ/f1 use full E | CONFIRMED |

## Implementation decisions

1. **10.1** — Both kernels: `p' = (r̂·Ḟ)/(4π c₀ r)`. Add unit-force amplitude test.
2. **10.2** — Delete extra Cd power term; recalibrate `SLIP`/`K_FRICTION` if a12x25 band breaks.
3. **10.3** — Fan BEM: gap leakage only (no Prandtl); full rotating ring still `F=1`. Prop keeps Prandtl.
4. **10.4** — Iterate `a′` with `Vt = Ωr(1−a′)` (propeller / QProp / fan BEM), angular momentum close; retune BEMT tests to physics.
5. **10.5** — `cd = cd0` only in analytic polar.
6. **10.6** — `cl_cd_table` returns `None` when `re <` lowest table Re → analytic fallback.
7. **10.7** — BEM shutoff = first-point / Q→0 interp like `curve_report.shut_off_pa`.
8. **10.8** — Stamp `grid_converged=False` / note on every screening evaluate (`evaluate_candidate`, mixed, CROR).
9. **10.9** — Single `CFM_PER_M3S` from `cfd.metrics`; proxies default `ρ=1.2` (AMCA / CFD).
10. **10.10** — Pure `circular_inlet_area_ok(area, R)`; call `require_circular_inlet_area` after snappy on plain circular ducts.
11. **10.11** — FDM `E × 0.70` knockdown on δ and f1 (documented; not same as yield 0.60); stamp `e_fdm_knockdown`.
