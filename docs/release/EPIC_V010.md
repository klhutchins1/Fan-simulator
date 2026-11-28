# Epic Plan: Fan Simulator v0.1.0 Close-Out

**Tracking issue:** [#169](https://github.com/klhutchins1/Fan-simulator/issues/169)  
**Board:** [`docs/release/RELEASE_PLAN.md`](RELEASE_PLAN.md) · **Completed log:** [`docs/release/RELEASE_DONE.md`](RELEASE_DONE.md)  
**Created:** 2026-11-28 (agreed with Kimball)

Purpose: give every session one authoritative map of what is **already verified and frozen**, what **remains before `v0.1.0`**, and what is **explicitly parked for `v0.1.1` / `v0.2`** — so we move forward methodically instead of re-checking the same code over and over.

---

## Operating Rules (Anti-Churn)

1. **Do not re-audit the Frozen Baseline.** Items under *Section 0* are closed. Re-open only if GitHub CI, `scripts/audit_status.py --strict`, or `tests/test_physics_snapshot.py` (RV-1) regresses.
2. **One check-off per item.** Every row closes with a merged PR + commit SHA (or an explicit dated `deferred` / `wontfix` note). Update both this file and [#169](https://github.com/klhutchins1/Fan-simulator/issues/169) when a phase finishes.
3. **Follow `AGENTS.md` strictly on every PR:**
   - Rule 1: pre-register before running data (`docs/validation/audits/<date>-<topic>-prereg.md`), committed and pushed before code.
   - Rule 2: no heavy CPU between 4 PM and 9 PM local time.
   - Rule 3: one worktree + branch off `origin/master`; merge `--no-ff` on 5/5 green CI; remove our own worktree after merge.
   - Rule 4: tests first (watch them fail before editing implementation).
   - Rule 5: `scripts/audit_status.py --strict` must exit 0 (`PROVEN=34 CHANGED=0 AFFECTED=0 NEW=0 UNREGISTERED=0`).
4. **Other worktrees stay untouched (Kimball, 2026-11-28):** Leave pre-existing worktrees (`cad-preview-perf`, `lazy-loading`, `math-rv3-prop-struct`, `intent-fast-design-check`, `fan01-rv2`, `readme-105`) alone — other agents may be actively using them. Only create and clean up our own fresh worktrees.

---

## 0. Frozen Baseline — Already Verified (Do Not Re-Audit)

| Area | Scope | Proof / Merged PRs |
|---|---|---|
| **M0** Trustworthy flow card | `R0.1`–`R0.4` | Merged (`RELEASE_DONE.md`) |
| **M1** Axial validated | `R1.1`–`R1.11` (A12x25, lt120 TRENDS, R1.3 wrap bounds, R1.10 claims, R1.11 surrogate fix) | Merged (`RELEASE_PLAN.md`) |
| **M2** Other tabs decided | `R2.1` Prop BEMT + `R2.6`–`R2.7` done; `R2.2`–`R2.5` frozen/labelled experimental for v0.1.0 | Merged (Kimball freeze 2026-11-15) |
| **M3** Releasable repo | `R3.1`–`R3.9` (`docs/VALIDATION.md`, CI 3-chunk + Windows geometry, `fansim-cockpit`, Docker badge, `RELEASE_EXCLUDE`) | Merged (`RELEASE_PLAN.md`) |
| **RV-0..RV-5** Review & safety nets | Strict audit ledger (`PROVEN=34`), RV-1 16-case snapshot, RV-2 scoreboard, all 8 RV-3 modules reviewed & merged, RV-4 script triage, RV-5 mypy (51 files) + shared CAD fixtures | Merged (`d837929`–`ce3a872`) |
| **UX-1 / UX-2 & CI-1** | Home page, 27 min/max control preview PNGs, UI-35/UI-36 tooltips, headless VTK/Xvfb CI fix | Merged through PR #153 |
| **Recent math, perf & cleanup** | `#86` (`CFD_VERSION=7`, PR #164), `#124` FW-H (PR #160), `#154`/`#159` dead code (PR #155, PR #161), `#165` lazy-load (PR #166), `#93`/`#94` pre-registered FAIL records (PR #158, PR #162), `#90`/`#125` scope comments (PR #163) | Merged through `96ddb00` |

---

## Master Checklist

| ID | Phase | Item | Issues / PRs | Status | Exit Gate |
|---|---|---|---|---|---|
| **P0.1** | Phase 0 | Pull `origin/master` (`96ddb00`) and remove our merged `issue-86-amca-static` worktree | PR #164 | `done` | Clean `master`, our merged worktree gone |
| **P0.2** | Phase 0 | Land `docs/release/EPIC_V010.md` + `RELEASE_PLAN.md` pointer and link #169 | #169 | `in progress` | PR merged to `master` |
| **P0.3** | Phase 0 | Track open perf PR #168 (`cad-preview-perf`, owned by another session) until merged | #167 / PR #168 | `tracking` | Merged to `master` (do not touch its worktree) |
| **P1A** | Phase 1 | Geometry math: thickness-about-camber (`apply_le_te_thickness`, dimples), CAD/BEM radius fraction & negative `max_camber` | #116, #117 | `ready` | Pre-reg + tests-first + `geometry.stock_handedness` PROVEN + issues closed |
| **P1B** | Phase 1 | Propeller BEMT & Polars math: Prandtl `F` + windmill swirl, `_analytic_section` drag/camber, post-stall polars & radial camber/thickness, air temp + hover FM guard | #109, #110, #111, #112 | `ready` | Pre-reg vs UIUC APC E 9x6 & SF 9x4.7 BEFORE code; honest PASS/FAIL; `propeller.*` PROVEN |
| **P1C** | Phase 1 | Structural math: root station bending, tapered centrifugal & airfoil `I`, RESIN knockdown | #123 | `ready` | Pre-reg Audit #5 amendment + RV-1 snapshot trail + `structural.*` PROVEN |
| **P1D** | Phase 1 | Acoustics math close-out: remaining #124 items (CV force sign, `proxies.py`) and #125 (`tonal.py` harmonic weighting / `m_max`) | #124, #125 | `ready` | Remaining items fixed (pre-reg) or explicitly closed/deferred to v0.2 |
| **P2.1** | Phase 2 | Triage open LOW/MED UI rows in `docs/QA_REVIEW.md` (`UI-23`, `UI-26`–`UI-29`, `UI-37`–`UI-38`, `UI-41`–`UI-42`, `QA-77`) | `QA_REVIEW.md` | `queued` | One batched UX PR or explicit `deferred v0.1.1` on every row |
| **P2.2** | Phase 2 | Prune completed blocks from `docs/release/RELEASE_PLAN.md` into `docs/release/RELEASE_DONE.md` | `RELEASE_PLAN.md` | `queued` | Board lists only live open work |
| **P3.1** | Phase 3 | **R4.3 Refresh:** sync `RELEASE_NOTES_v0.1.0.md`, `docs/VALIDATION.md`, `scoreboard.md`, `CHANGELOG.md` for all merges since PR #108 | R4.3 | `queued` | `test_r38_validation_doc`, `test_r43_release_notes`, `test_export_release` pass |
| **P3.2** | Phase 3 | **R4.1 Linux:** fresh `scripts/export_release.py` tarball → clean clone → `uv sync --extra dev` → `fansim-cockpit` + fast suite | R4.1 | `queued` | Clean-clone install & test pass logged |
| **P3.3** | Phase 3 | **R4.2 + W1 Windows (Kimball):** Windows `scripts/stray_work.py` rescue (`stock-outline`, `r22a-wake-aspect`, `r110-g2-merge`), clean Windows install + 1 OpenFOAM Assess (outside 4–9 PM) | R4.2, W1 | `needs Kimball` | Windows install + Assess pass; W1 closed |
| **P3.4** | Phase 3 | **R4.4 Tag & Publish:** finalize `CHANGELOG.md` (`v0.1.0`), tag `v0.1.0` on 5/5 green CI, publish GitHub release from clean export | R4.4 | `blocked (P3.1–P3.3)` | `v0.1.0` tagged & published |

---

## Phase Details & Concrete Scope

### Phase 0 — Repo & Worktree Hygiene
- Keep local `master` clean and fast-forwarded to `origin/master`.
- Leave all pre-existing non-ours worktrees untouched (`cad-preview-perf`, `lazy-loading`, `math-rv3-prop-struct`, `intent-fast-design-check`, `fan01-rv2`, `readme-105`).
- Only remove worktrees created by this Epic after their PRs merge to `master`.

### Phase 1 — Remaining RV-3 Math Issues (Before `v0.1.0`)
Each sub-phase is **one branch, one pre-registration (committed & pushed before code), one PR**:

1. **P1A — Geometry math (`#116`, `#117`):**
   - Files: `fansim/geometry/airfoil.py`, `fansim/geometry/blade.py`, `tests/test_geometry.py`, `tests/test_rv3_geometry.py`.
   - Fix `apply_le_te_thickness` and dimples to scale thickness about the camber line $y_c(x)$ rather than scaling total $y$.
   - Align CAD vs BEM radius-fraction convention (`hub - root_embed` vs `hub`) and make negative `max_camber` behavior explicit (validated or supported without silent zeroing).
   - Check RV-1 snapshot & re-prove `geometry.stock_handedness`.

2. **P1B — Propeller BEMT & Polars math (`#109`, `#110`, `#111`, `#112`):**
   - Files: `fansim/propeller/bemt.py`, `fansim/propeller/polars.py`, `fansim/propeller/polar.py`, `tests/test_bemt.py`, `tests/test_prop_polar.py`, `tests/audit/test_prop_bemt_audit.py`.
   - Pre-register acceptance criteria against UIUC APC E 9×6 and APC SF 9×4.7 (`docs/validation/scoreboard.md`) BEFORE changing code.
   - Address: Prandtl tip/hub loss $F$ in angular momentum + allowing windmill swirl $v_\theta < 0$ (`#109`); `_analytic_section` angle/stall drag rise and $2\pi$ thin-airfoil camber lift (`#110`); post-stall polar extrapolation beyond $[-5^\circ, +18^\circ]$ and radial interpolation of station camber/thickness (`#111`); consistent air temperature (`RHO_AMCA`/`NU_AIR`/`C0_AIR`) and static-hover FM guard when $J > 0$ (`#112`).
   - Record honest PASS/FAIL in the pre-reg doc (never re-tune to pass). Re-prove affected `propeller.*` units and update RV-1 snapshot + `scoreboard.md` if accepted.

3. **P1C — Structural math (`#123`):**
   - Files: `fansim/structural/{deflection,stress,flutter,balance}.py`, `tests/test_{deflection,stress,flutter,balance}.py`.
   - Pre-register an Audit #5 amendment covering: root bending at `_root_station` instead of `_tip_station`, tapered-blade centrifugal load & airfoil section modulus $I$ instead of uniform-bar/rectangular-$I$, and RESIN isotropic adhesion knockdown.
   - Re-prove affected `structural.*` units and update RV-1 snapshot with audit trail.

4. **P1D — Acoustics math close-out (`#124` leftovers, `#125`):**
   - Audit remaining open clauses after PR #160 (FW-H near-field/permeable/window fixes) and PR #163 (`tip_loading.py` scope docs): CV force sign convention and `proxies.py` Curle/Proudman gaps (`#124`), `tonal.py` harmonic weighting & `m_max` sensitivity (`#125`).
   - Either land pre-registered fixes and close both issues, or explicitly document & defer non-v0.1.0 items so neither issue stays half-open.

### Phase 2 — QA Ledger & Board Hygiene
- One pass over open rows in `docs/QA_REVIEW.md`: fix the small worthwhile UX items (`UI-37` proxy tooltips, `UI-38` design-pick notice, `UI-41`/`UI-42` input validation/formatting) in a single PR, and explicitly mark low-priority or hardware-dependent rows (`UI-23`, `UI-26`–`UI-29`, `QA-77`) as `deferred v0.1.1`.
- Move completed blocks out of `docs/release/RELEASE_PLAN.md` into `docs/release/RELEASE_DONE.md`.

### Phase 3 — v0.1.0 Release Candidate & Ship (M4)
- Refresh `docs/release/RELEASE_NOTES_v0.1.0.md`, `docs/VALIDATION.md`, `docs/validation/scoreboard.md`, and `CHANGELOG.md` so every claim matches the final `master` commit (including `CFD_VERSION = 7`, FW-H, perf, and any Phase 1 math updates).
- Run Linux clean-clone export verification (`R4.1`) and coordinate Kimball's Windows verification + W1 rescue (`R4.2`, `W1`).
- Finalize `CHANGELOG.md`, tag `v0.1.0` on 5/5 green CI, and publish (`R4.4`).

---

## 4. Explicitly Out of Scope for v0.1.0 (Parked — Do Not Touch Yet)

- **v0.1.1 (Physical rig & experimental surfaces):** Print session 1 (`P4`/`P6` hub & glyph coupons), anemometer rig measurements, lead 15 balance trim & lead 16 tap-test calibration, and validating the 4 frozen experimental surfaces (`R2.2` Prop CFD, `R2.3` CROR, `R2.4` Mixed-flow, `R2.5` Volute transient).
- **v0.2 (Major physics redesigns / Windows-data-blocked):**
  - `#90` (`flow_report.py` mass-flux slab weighting — requires 25 saved CFD fields on Windows + `FLOW_REPORT_VERSION = 5`).
  - `#93` + `#95` (unified cascade / radial-equilibrium fan BEM redesign; un-retuned 1-D viscous Euler pre-registered FAIL recorded in PR #162).
  - `#96` (negative-$\alpha$ polar CSVs requiring XFOIL/NeuralFoil generation).

---

## Progress Log

- **2026-11-28:** Epic created ([#169](https://github.com/klhutchins1/Fan-simulator/issues/169)) and committed in `docs/release/EPIC_V010.md`. Completed **P0.1** (synced `master` to `96ddb00`, removed our merged `issue-86-amca-static` worktree). All other pre-existing worktrees left untouched per Kimball's directive. Next up: **P1A** (`#116`, `#117`).
