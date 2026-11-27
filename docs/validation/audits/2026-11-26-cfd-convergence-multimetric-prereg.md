# Pre-registration: multi-metric CFD convergence & shut-off scaling (#88) — 2026-11-26

**Ruling by Cursor.** Written before changing `fansim/cfd/metrics.py` (`AGENTS.md` rule 1).

## Problem

`fansim.cfd.metrics.convergence()` currently inspects only `outletFlow/surfaceFieldValue.dat` and divides
the two-half tail-mean shift by `|mean| + 1e-12`:

1. **Velocity-driven P–Q solves (`FIELD_U`) always pass:** continuity pins `outletFlow == Q_in` from
   iteration 1 (`shift = 0%`), so `convergence()` reports `converged=True` even while `inletP` or rotor
   torque (`forces/moment.dat`) is still drifting or diverging.
2. **Shut-off singularity ($Q \to 0$):** dividing by `|mean| + 1e-12` blows up both `convergence()` shift
   and `oscillation_pct()` to hundreds/thousands of percent on settled near-zero-flow runs.
3. **Pressure / torque drift blindness:** pressure-driven runs whose flow settled can still have drifting
   pressure rise or rotor torque (including CROR `forcesRear/moment.dat`).

## Model rule (ASME V&V 20-2009 / Roache 1998)

Keep Rule A's tail-mean two-half shift criterion (`TAIL_FRAC = 0.25`, default `tol_pct = 2.0`), extended
across every available engineering QoI in `postProcessing/`:

| QoI | Source (when present) | Reference scale floor | Rationale |
|---|---|---|---|
| Flow $Q$ (mandatory) | `outletFlow/surfaceFieldValue.dat` | `FLOW_SCALE_FLOOR_M3S = 1e-4` m³/s (≈ 0.21 CFM) | Identical to `|mean|` for all normal flows ($|Q| \ge 0.21$ CFM); prevents $0/0$ blow-up at shut-off |
| Pressure rise $\Delta p_k$ | `outletP - inletP` (or whichever exists) | `PRESSURE_KIN_SCALE_FLOOR = 0.5` m²/s² (≈ 0.6 Pa) | Identical to `|mean|` on loaded runs; prevents free-delivery $\Delta p \approx 0$ blow-up |
| Torque $M_z$ | `forces/moment.dat` col 3 (and `forcesRear/moment.dat` if present) | `TORQUE_SCALE_FLOOR_NM = 1e-4` N·m | Identical to `|mean|` on spinning rotors; prevents stationary $M_z \approx 0$ blow-up |

`convergence()` returns `(worst_shift < tol_pct, worst_shift)` where `worst_shift = max(shifts)` across
all present QoIs (if any present QoI has `< 4` tail samples, returns `(False, 999.0)`). `oscillation_pct()`
uses the same `FLOW_SCALE_FLOOR_M3S` denominator floor. `outletFlow`-only case directories continue to
work (secondary files are checked whenever present on disk).

## Pass / fail rules (fixed before implementation)

| Id | Rule |
|---|---|
| P1 | Velocity-driven blind spot closed: constant `outletFlow` with drifting `inletP` (or `outletP - inletP`) returns `converged=False` and `shift >= tol_pct`. |
| P2 | Torque drift caught: constant `outletFlow` and pressures with drifting `forces/moment.dat` $M_z$ (and separately drifting CROR `forcesRear/moment.dat` $M_z$) returns `converged=False` and `shift >= tol_pct`. |
| P3 | Multi-metric settled pass: stable or limit-cycling `outletFlow`, pressure rise, and torque all return `converged=True` with `shift < tol_pct`. |
| P4 | Shut-off non-singularity: settled near-zero flow ($Q = 0 \pm 10^{-6}$ m³/s) returns `converged=True`, `shift < 2%`, and `oscillation_pct < 2%`; genuine near-zero flow drift ($0 \to 5\times 10^{-5}$ m³/s) returns `converged=False`. |
| P5 | Backward compatibility: `outletFlow`-only cases, normal-flow shift/oscillation values ($|Q| \ge 10^{-4}$ m³/s), and all existing CFD/sanity/audit tests remain green; zero RV-1 `physics_snapshot.json` drift. |
| P6 | Audit ledger: `cfd.cfm_from_outlet_flow` re-proven and `scripts/audit_status.py --strict` exits 0 (`PROVEN=34 CHANGED=0`). |

## Result

P1–P6 **PASS**. Updated `fansim/cfd/metrics.py` (`convergence()`, `oscillation_pct()`,
`FLOW_SCALE_FLOOR_M3S`, `PRESSURE_KIN_SCALE_FLOOR`, `TORQUE_SCALE_FLOOR_NM`) and `cfd.cfm_from_outlet_flow`
registry claim. Re-proved `cfd.cfm_from_outlet_flow` in `docs/validation/audits/ledger.json`
(`scripts/audit_status.py --strict`: `PROVEN=34 CHANGED=0 AFFECTED=0 NEW=0 UNREGISTERED=0`).
Zero drift on `tests/data/physics_snapshot.json`; 122/122 related CFD/sanity/audit/snapshot tests pass.
