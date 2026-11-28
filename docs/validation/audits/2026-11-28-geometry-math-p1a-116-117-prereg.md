# Pre-registration: Geometry Math Fixes — Thickness About Camber, Signed Camber & Radius Mapping (P1A: #116, #117)

- **Date:** 2026-11-28
- **Issues:** #116 (`apply_le_te_thickness` and dimples scale total section `y` including camber line `yc`), #117 (geometry radius-fraction mismatch between CAD `[hub - root_embed, tip]` and `blade_solidity`/`fan_bem` `[hub, tip]`, plus silent zeroing of negative `max_camber`)
- **Epic:** #169 (`docs/release/EPIC_V010.md`, Phase **P1A**)
- **Review source:** `docs/review/2026-11-26-rv3-geometry.md` (items A3, B8, B9) and prior audit `docs/validation/audits/2026-10-09-station-mapping.md`
- **Ruling by:** Cursor (lead; committed and pushed before any implementation or test edits per `AGENTS.md` Rule 1)

---

## 1. Defects & Mathematical Specification

### 1.1 Issue #116 — Scale thickness about camber line `yc(x)`, not total `y`
In a NACA 4-digit or cambered rounded-plate section, every surface coordinate decomposes into the mean camber line and local thickness offset:
$$y(x) = y_c(x) + \delta y(x), \qquad b(x) = y_c(x)\,c + \bigl(b(x) - y_c(x)\,c\bigr).$$
Currently:
- `fansim/geometry/blade.py:apply_le_te_thickness` multiplies total `b` by `le_te_thick_factors(x, le, te)`, distorting the camber line `yc` by up to $+12.5\%$ at mid-chord when `le = te = 1.5`, and applies the TE blunt lift against `|out|` (relative to $y = 0$) instead of `|b - yc_mm|`, causing a sign jump on cambered thin sections where $y_l = y_c - y_t\cos\theta > 0$ near $x \in [0.92, 0.98]$.
- `fansim/geometry/features.py:apply_features` scales total `b` for dimples, shifting the camber line instead of indenting both faces equally toward `yc`.

**Fix:**
- Add optional `yc_mm: np.ndarray | None = None` to both `apply_le_te_thickness` and `apply_features`.
- In `blade.py:_section_loop`, compute exact `yc_mm = _naca_camber_line(x, max_camber, camber_pos)[0] * chord` and pass it to both `apply_le_te_thickness` and `apply_features`.
- When `apply_le_te_thickness` is called directly with `yc_mm=None` on a standard symmetric-`x` closed airfoil loop, infer `yc_mm` from the upper/lower pair average `0.5 * (b_u + b_l)` (exact to machine precision for `naca4` and `rounded_plate`; zeros otherwise).
- Scale only `db = b - yc_mm`, compute TE blunt floor `t_peak` and `te_half` on `|db|`, lift relative to `yc_mm` (`out = yc_mm + s * mag`), and for dimples apply `b = yc_mm + (b - yc_mm) * factor`.

### 1.2 Issue #117 (Part A) — Support signed negative `max_camber`
In `fansim/geometry/airfoil.py`, `_naca_camber_line` (`if m <= 0.0`) and `rounded_plate` (`if m > 1e-9`) silently return symmetric zero-camber sections for any $m < 0$, contradicting `validate_blade_params` (`BACKWARDS_CAMBER = -0.02`) and `signed_design_camber`. Because the NACA 4-digit parabolic meanline is strictly linear in $m$, replacing those guards with `abs(m) <= 1e-12` produces the exact vertical reflection $y_c(x; -|m|, p) = -y_c(x; +|m|, p)$, $\theta(-|m|) = -\theta(+|m|)$ for $m < 0$, while remaining bit-for-bit identical for all $m \ge 0$.

### 1.3 Issue #117 (Part B) — Single builder radius-fraction mapping (`hub - root_embed` .. `tip`)
Every CAD builder places station `r_frac` at
$$r(f) = r_0 + (r_{\text{tip}} - r_0)\,f, \qquad r_0 = r_{\text{hub}} - \text{root\_embed},$$
so the station fraction built at exposed physical radius $r \in [r_{\text{hub}}, r_{\text{tip}}]$ is
$$f(r) = \operatorname{clip}\!\left(\frac{r - r_0}{r_{\text{tip}} - r_0},\; 0,\; 1\right).$$

**Disclosure from prior audit (`docs/validation/audits/2026-10-09-station-mapping.md`):**
The 2026-10-09 attempt bundled builder radius mapping **and** switching `fan_bem` / `propeller.bemt` to `pchip` interpolation, and failed B2 ($\rho$: $0.714 \to 0.429$) and P1 (`propeller.bemt` APC SF RMS $0.0203 > 0.020$). Its post-verdict diagnostic split showed that **builder radius mapping only** (retaining linear interpolation in `fan_bem`) kept Audit #4 $\rho = 0.714$ and passed `L1` on `blade_solidity`. This pre-registration explicitly adopts **mapping-only** (explicitly chosen after seeing that split), scoped to geometry + axial fan BEM (`blade.py`, `chord_realisation.py`, `fan_bem.py`, `near_stall.py`). Propeller BEMT is excluded here and covered separately under Epic **P1B** (#109–#112).

**Fix:**
- Add shared public helpers in `fansim/geometry/blade.py`: `station_root_radius(params)`, `radius_at_r_frac(params, r_frac)`, `r_frac_at_radius(params, r_mm)`, plus `_interp_stations_at(params, q)`.
- Refactor CAD callers (`build_blade_solid`, `open_tip_rmax_mm`, `blade_hang_below_hub_mm`, `tip_le_te_z`, `chord_realisation._station_measure_fracs`) to use them (bit-for-bit identical CAD output).
- Update `blade_solidity(params)` to evaluate chord and stagger at `[r_frac_at_radius(params, r) for r in (r_hub, r_mid, r_tip)]` while keeping physical annulus radii `(r_hub, r_mid, r_tip)` in the $2\pi r$ denominator.
- Update `fansim/fan_bem.py:operating_point` and `fansim/optimize/near_stall.py:_span_loading` to query `_interp_geometry` at `r_frac_at_radius(params, r * 1000.0)` (retaining linear station interpolation).

---

## 2. Pre-Registered Acceptance Criteria (Fixed Before Running Code)

All 7 criteria must pass; any failure is recorded honestly and blocks merge without re-tuning:

| ID | Check | Pass Criterion |
|---|---|---|
| **C1** | `#116` Camber-line invariance | For cambered NACA (`m=0.08, p=0.4, t=0.08, c=40`) under `apply_le_te_thickness` (`le=1.5, te=1.5` and `le=1.0, te=2.0`) and `apply_features` (dimples `amp=0.3`), upper/lower pair midpoint `0.5 * (b_u + b_l)` matches `yc_mm` within `1e-9 mm` at every station; TE blunt on thin cambered NACA (`m=0.06, t=0.03, te=2.0`) keeps lower surface smoothly below `yc_mm` (`b_l - yc_mm < 0`) with no discontinuity across `y = 0`. Symmetric sections (`m = 0`) remain bit-for-bit identical. |
| **C2** | `#117A` Signed negative camber | `naca4(-m, p, t)` and `rounded_plate(t, max_camber=-m)` equal the exact vertical reflection (`x_u(-m) == x_l(+m)`, `y_u(-m) == -y_l(+m)`) within `1e-12`; `m >= 0` is bit-for-bit identical; `tests/test_direction_crosscheck_2.py` passes (`BACKWARDS_CAMBER = -0.02` unchanged). |
| **C3** | `#117B` CAD builder invariance | Stock v3, lt120, `tests/test_outline_hub.py`, `tests/test_a12x25_reference_geometry.py`, `tests/test_blade_golden.py`, `tests/test_geometry.py`, and `tests/test_hub_hang.py` pass with zero tracked reference STL changes. |
| **C4** | `#117B` `blade_solidity` accuracy | `blade_solidity` matches analytical `B * c(f(r)) * cos(beta(f(r))) / (2*pi*r)` at `(r_hub, r_mid, r_tip)` for both `root_embed = 0` and `root_embed > 0`; `tests/test_solidity.py` and `tests/test_blade_validation.py` pass; Stock v3 hub/mid/tip solidity stays within 5% of baseline. |
| **C5** | `#117B` Fan BEM & near-stall consistency | `tests/audit/test_fan_bem_audit.py`, `tests/test_fan_bem.py`, `tests/test_bem_exploit_guard.py`, `tests/test_near_stall.py`, `tests/test_multi_point.py`, `tests/test_mixed_flow_bem.py` all pass. |
| **C6** | `#117B` Audit #4 ranking skill | Spearman $\rho$ (BEM free CFM vs CFD free CFM on the 7 Audit #4 designs) $\ge 0.60$ **and** within $0.05$ of pre-edit baseline ($0.714$). |
| **C7** | Hygiene, ledger & RV-1 snapshot | `ruff check` (critical + changed `.py` files), `mypy`, and `scripts/audit_status.py --strict` (`PROVEN=34 CHANGED=0 AFFECTED=0 NEW=0 UNREGISTERED=0`) pass; RV-1 `tests/data/physics_snapshot.json` is regenerated with this audit file as `--reason` (only `fan_bem.*` cases expected to shift slightly from `root_embed` mapping; propeller/structural/acoustics cases unchanged). |

---

## 3. Results

*(To be recorded after implementation and verification.)*
