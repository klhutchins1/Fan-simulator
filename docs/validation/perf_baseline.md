# Screening-path performance baseline (2026-09-14)

**Purpose:** Record measured timings for the stock Noctua A12x25 reference recipe (`stock_blade_flat("a12x25")` → `config/problems/a12x25_reference.yaml`) on the **screening** tier (CadQuery loft + axial fan BEM). These numbers do **not** close the Phase 3 free-air validation gap (~**−32%** vs published CFM); they only characterize how fast we reject or rank designs before OpenFOAM.

**Parent commit (Task 4.1 baseline):** `001a47321ce4bd13289de2c702e5cf260581c9bc`  
**Environment:** Windows 11 (10.0.26200), Python 3.12.13, `uv run` from repo root. CadQuery/OCCT may exit non-zero after successful prints (see `docs/validation/suite_baseline_2026-09-14.md`).

---

## 1. Measurement commands

### Fused impeller build (optimizer / CFD STL path)

```powershell
uv run python -c "import time; from fansim.optimize.search_space import stock_blade_flat, blade_from_flat; from fansim.geometry import build_impeller; p=blade_from_flat(stock_blade_flat('a12x25')); t=time.perf_counter(); build_impeller(p); print('build_impeller_s', round(time.perf_counter()-t, 2))"
```

### Preview build (cockpit fast mesh — no boolean fuse)

```powershell
uv run python -c "import time; from fansim.optimize.search_space import stock_blade_flat, blade_from_flat; from fansim.geometry.blade import build_impeller_preview; p=blade_from_flat(stock_blade_flat('a12x25')); t=time.perf_counter(); build_impeller_preview(p); print('build_impeller_preview_s', round(time.perf_counter()-t, 2))"
```

### BEM P–Q screen (`pq_curve`, same path as `--bem-prescreen`)

```powershell
uv run python -c "import time, statistics as s; from fansim.optimize.search_space import stock_blade_flat, blade_from_flat; from fansim.fan_bem import pq_curve; flat=stock_blade_flat('a12x25'); p=blade_from_flat(flat); rpm=float(flat.get('rpm',2000)); c=pq_curve(p,rpm,tip_gap_mm=0.5); xs=[]; 
for _ in range(50):
 t0=time.perf_counter(); pq_curve(p,rpm,tip_gap_mm=0.5); xs.append(time.perf_counter()-t0)
print('free_cfm', c.free_delivery_cfm, 'shutoff_pa', c.shutoff_dp_pa, 'pq_curve_median_s', round(s.median(xs),4))"
```

(Median of ≥50 runs recommended.)

---

## 2. Baseline results (pre–Task 4.2 speedups)

| Step | What | Median / single-run | Notes |
|------|------|---------------------|--------|
| Geometry | `build_impeller` (fused STL) | **13.1 s** | Dominates `evaluate_candidate` when BEM passes |
| Geometry | `build_impeller_preview` | **5.0 s** (1st), **4.6 s** (2nd) | Subprocess preview path; still heavy vs BEM |
| BEM | `pq_curve` @ 2000 RPM, 0.5 mm gap | **15.9 ms** median (50 runs); p95 **18.8 ms** | Free **65.0 CFM**, shutoff **36.4 Pa** (screening calibration, not CFD truth) |

**Ranking (allowed wins, physics preserved):**

| Rank | Hotspot | Safe lever? | Decision |
|------|---------|-------------|----------|
| 1 | Fused CadQuery build (~13 s) | Coarser `n_span`/`n_chord` for screening only would change STL fidelity | **Defer** — needs acceptance criteria, not a silent shortcut |
| 2 | BEM `pq_curve` (~16 ms) | Cache polar family lookup; hoist spanwise interpolators once per sweep | **Implement** (this cycle) |
| 3 | OpenFOAM screening mesh | Coarser `base_cell` for screen-only | **Defer** — tied to Phase 3 validation honesty |
| 4 | Surrogate / Optuna overhead | Already sub-second vs geometry | No change |

---

## 3. Task 4.2 speedups (before / after)

Physics unchanged: same loss knobs, tip-gap handling, and polar fallback rules. Regression: `uv run python -m pytest tests/test_fan_bem.py -q`.

| Change | Files | `pq_curve` median (50 runs) | Speedup |
|--------|-------|-----------------------------|---------|
| **Before** | — | **15.9 ms** | — |
| Polar family + Re-level caching; reuse `_interp_geometry` across P–Q points | `fansim/propeller/polars.py`, `fansim/fan_bem.py` | **13.7 ms** | **~1.16×** (~14%) |

Outputs after change: free **65.0 CFM**, shutoff **36.4 Pa** (unchanged on stock reference).

**Not implemented this cycle:** fused-build time reduction (would dominate Optuna wall clock but requires an explicit screening-resolution policy).

---

## 4. How this relates to absolute performance

- **Screening speed** helps Optuna and BEM pre-gates scale to many trials; it does **not** fix validated free-air error vs the Noctua datasheet.
- Absolute claims remain gated by Phase 3 CFD (`docs/validation/a12x25_pq_report.md`) and geometry acceptance (`docs/validation/a12x25_geometry_acceptance.md`).
