# Ruling & Pre-registration: Decoupled Prop BEMT P1B (#109, #110, #111, #112)

- **Date:** 2026-11-28
- **Supersedes (after honest C6 FAIL):** `docs/validation/audits/2026-11-28-prop-bemt-p1b-109-112-prereg.md`
- **Issues:** #109, #110, #111, #112 (Epic #169, Phase **P1B**)
- **Ruling by:** Cursor (lead; committed and pushed BEFORE editing `fansim/fan_bem.py`, per `AGENTS.md` Rule 1)

---

## 1. Architectural Ruling (Following C6 FAIL)

In `docs/validation/audits/2026-11-28-prop-bemt-p1b-109-112-prereg.md`, landing `#109`–`#112` on `fansim/physics/air.py`, `fansim/propeller/polars.py`, and `fansim/propeller/bemt.py` passed all propeller criteria **C1–C5** — including improving APC E 9×6 static $C_P$ (`-9.3% -> -5.3%`) and bringing APC SF 9×4.7 worst $C_T(J)$ RMS from **FAIL (`0.0175`) to PASS (`0.0139 <= 0.015`)** against the original 2026-09-29 Audit #3 pre-registered gate — **but failed C6** because `fansim/fan_bem.py` imported `propeller.bemt._cl_cd`.

Root cause: `fansim/fan_bem.py` is a v0.1 ranking-only screening model explicitly parked for a v0.2 physics redesign (`#93` + `#95`), whose empirical calibration constants (`SLIP = 0.71`, `AX_SLIP = 0.65`) were fitted specifically to the legacy low-Re analytic helper (`2*pi*m` camber lift, constant `cd0`, flat-clamped table edges at `[-5°, +18°]` inside `fan_bem`'s own `_viterna` wrapper). Coupling an empirically calibrated v0.1 fan screening model to first-principles propeller physics fixes either blocks propeller physics fixes or forces ad-hoc re-tuning of `fan_bem`.

**Ruling:**
1. **Do NOT re-tune `SLIP`, `AX_SLIP`, `K_FRICTION`, `AX_K_FRICTION`, or `K_TIP_LEAK`** in `fansim/fan_bem.py`.
2. **Decouple `fansim/fan_bem.py` from `fansim/propeller/bemt._cl_cd`:** preserve the exact pre-P1B low-Re analytic polar and `[-5°, +18°]` table-edge clamp locally inside `fansim/fan_bem.py` (`_legacy_fan_cl_cd`), explicitly documented as the v0.1 calibrated screening polar to be replaced in v0.2 (`#93`, `#95`).
3. **Keep all `#109`–`#112` physics fixes intact** on `fansim/physics/air.py`, `fansim/propeller/polars.py`, and `fansim/propeller/bemt.py`.
4. **Update RV-2 scoreboard verdict for `bemt.apcsf_9x4.7.ct_j_rms`:** because the recomputed worst $C_T(J)$ RMS (`0.0139`) now clears the **unchanged** 2026-09-29 pre-registered Audit #3 tolerance (`<= 0.015`) with no threshold relaxation and no post-data tuning, record its verdict transition (`FAIL -> PASS`) in `docs/validation/scoreboard_claims.yaml` and regenerate `docs/validation/scoreboard.md`, removing the strict `xfail` on `test_uiuc_apcsf_ct_j_rms_within_preregistered_tolerance` (while keeping `bemt.apcsf_9x4.7.static_cp` honestly **FAIL** at `-20.2%` vs `±20%`).

---

## 2. Pre-Registered Acceptance Criteria (Fixed Before Decoupling Edit)

All 7 criteria must pass to merge:

| ID | Check | Pass Criterion |
|---|---|---|
| **D1** | `#109` Momentum equations | Same as C1 (`denom_th` includes `F`, symmetric windmill `vth`, `abs(sin(phi))`). |
| **D2** | `#110` Prop analytic polar | Same as C2 (`4*pi*m` camber lift, `cd0 + 0.025*cl^2`, symmetric Viterna–Corrigan to `Cl(±90°)=0, Cd(±90°)=1.29`). |
| **D3** | `#111` Prop table polars & radial geom | Same as C3 (Viterna above `+18°`, linear + quadratic drag below `-5°` to finite `a_neg` + Viterna below `a_neg`, `s1223` stalled at `-30°`, `naca4412` attached at `-5°`, radial `camber(r)` and `thickness(r)`). |
| **D4** | `#112` ISA air & hover FM guard | Same as C4 (`T_ISA_K`, `MU_ISA`, `NU_ISA`, `C0_ISA` in `air.py`; `bemt.py` uses `RHO_ISA`/`NU_ISA`/`C0_ISA`; `figure_of_merit` and `figure_of_merit_raw` are `None` for `v_forward > 0`). |
| **D5** | UIUC Audit #3 & GWS & scoreboard | APC E 9×6 static $C_T$ ($\le 15\%$), static $C_P$ ($\le 20\%$), $C_T(J)$ RMS ($\le 0.015$) PASS; APC SF 9×4.7 static $C_T$ ($\le 15\%$) PASS, $C_T(J)$ RMS ($\le 0.015$) PASS, static $C_P$ stays honest FAIL (better than `-25%`); GWS 5×4.3, `test_bemt.py`, `test_bemt_catalog.py`, `test_prop_bemt_audit.py`, `test_prop_fwh_compress.py`, `test_uiuc_polars.py`, `test_rv3_propeller.py`, and `test_scoreboard.py` all pass. |
| **D6** | Fan BEM invariance (no retuning) | `fansim/fan_bem.py` keeps `SLIP=0.71, AX_SLIP=0.65, K_FRICTION=1.7, AX_K_FRICTION=1.9, K_TIP_LEAK=9.0` unchanged; `tests/test_fan_bem.py`, `tests/audit/test_fan_bem_audit.py`, `tests/test_bem_exploit_guard.py`, and `tests/test_math_consistency.py` all pass with zero regression on Stock v2 Euler (`58.2 ± 0.5 CFM`) and `axial_force` (`59.8 CFM / 22.1 Pa`). |
| **D7** | Hygiene, ledger, RV-1 & RV-2 | `ruff check`, `mypy` (51 files), `scripts/audit_status.py --strict` (`PROVEN=34 CHANGED=0 AFFECTED=0 NEW=0 UNREGISTERED=0`), `tests/test_physics_snapshot.py` (regenerated with `--reason` pointing to this file), and `tests/test_scoreboard.py` all pass; tracked `.stl` files untouched. |

---

## 3. Results

*(To be recorded after decoupling implementation and verification.)*
