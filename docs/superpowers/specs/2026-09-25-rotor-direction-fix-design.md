# Rotor direction fix (Audit #1 follow-up): design

Date: 2026-09-25 · Roadmap: §19.1 · Evidence: `docs/validation/audits/2026-09-25-audit-01-flow-direction.md`
Status: approved design, not yet implemented. This spec is what lifts the §19.1 freeze on spin and flow.

## Problem

1. **Reversed rotor.** Both A12x25 rotor models (Stock recipe, close-ref STL) are designed to turn
   ω_z = +1 (CCW seen from +Z) and pump −Z. That matches the real fan: CCW seen from the intake, tips
   leading, air toward the struts. Production CFD uses them as built with `spin = −1`, so it solves the
   reversed rotation.
2. **MRF zone clips the rotor and the frame overlaps the blades** (found while designing this fix).
   - `rig_for_impeller` estimates the rotor's axial extent from the recipe sweeps: ±3 mm, with the MRF
     zone at ±5 mm. The Stock STL actually spans −8.1 to +8.4 mm, so the blade ends lie outside the MRF
     zone and are treated as stationary walls.
   - `default_frame_z_start_mm` puts the struts at `mrf_z_max + 0.5 = 5.5` mm, inside the blade band.
   - This affects the optimizer (`optimize/objectives.py`), the cockpit Assess path (via
     `evaluate_candidate`), and the scripts that use `rig_for_impeller`. The Audit #1 runs are not
     affected, because they sized the rig from the STL bounds.
3. **Steady solves in the designed direction limit-cycle** (flow drift 4–10%). The current
   `convergence()` rule (tail peak-to-peak < 2%) flags them as unconverged, even though the reported
   metric is already the tail mean.
4. **Prop sign masking.** `propeller/calibrate.normalize_metrics_sign` flips spin until thrust is
   positive, which hides exactly this class of bug.

## Decisions (user-approved)

- **Orientation, approach A:** rotate the rotor STL 180° about X as it enters CFD, and keep `spin = −1`.
  The printed or exported STL, templates, BCs, frame/stator/casing placement (duct frame) and the
  lab-frame swirl sense all stay unchanged. The alternatives were rejected:
  - B (per-design proof) is deferred to roadmap §19.2;
  - C (spin +1 with a reversed duct) touches too much.
- **Convergence, rule A:** judge the tail **mean**; report the oscillation separately. No URANS and no
  solver damping.
- **Scope extras:** included are prop sign masking and a Stock P–Q re-run with a rewrite of
  `a12x25_pq_report.md`. Re-scoring the saved optimizer catalog is excluded; the `CFD_VERSION` bump marks
  it stale.

## Design

### 1. Orientation + rig sizing (`fansim/cfd/domain.py`, new helpers)

```python
AXIAL_CFD_ORIENTATION = "flipped"   # Audit #1 (2026-09-25): designed ω_z=+1 pumps −Z as built;
                                    # flipped 180° about X it pumps +Z (the duct direction) at spin −1.

def orient_impeller_for_cfd(src_stl_mm: Path, dst_stl_mm: Path,
                            orientation: str = AXIAL_CFD_ORIENTATION) -> tuple[float, float]:
    """Write the CFD-oriented copy; return its (z_min_mm, z_max_mm)."""

def fit_rig_to_stl(rig: TestRig, stl_mm: Path, *, mrf_margin_mm: float = 2.0) -> TestRig:
    """Return rig with impeller_z_min/max from the STL bounds and the MRF zone = bounds ± margin."""
```

- `orientation` accepts `"as_built"` or `"flipped"`. Any other value raises `ValueError`.
- The flip is `flip_about_x` from `fansim/audit/direction.py`, which moves to a shared place so that CFD
  code does not import the audit package. The audit module re-exports it.
- **Axial call order, everywhere:**
  1. build the STL,
  2. `orient_impeller_for_cfd`,
  3. `rig_for_impeller(...)`, then `fit_rig_to_stl(rig, oriented_stl)`,
  4. export the frame / stator / casing from the fitted rig,
  5. `build_case(oriented_stl, fitted_rig, …)`.
- `TestRig.spin` stays −1, and `flow_sign` stays +1.

### 2. `build_case` safety check (all callers, including CROR and mixed-flow)

Before writing the case, load the impeller STL (mm) and raise `ValueError` with a clear message in
either of these cases:

- its z-bounds are not inside `[mrf_z_min, mrf_z_max]`, with a 1e-6 m tolerance;
- a frame or stator STL overlaps the impeller z-range (frame/stator `z_min < impeller z_max`).

For dual-MRF (CROR), check each rotor against its own zone if the rotor STLs are separate. If they are
not separate, check the union against `[front_z_min, rear_z_max]`. If CROR or mixed-flow trips the check,
record that as a finding and fix its rig sizing in the same way; do not weaken the check.

### 3. Callers

- **Updated to the new order:** `fansim/optimize/objectives.py` (which covers the cockpit Assess path via
  `evaluate_candidate` / `evaluate_candidate_isolated`), and the scripts `run_a12x25_validation.py`,
  `run_fan_curve.py`, `run_baseline.py`, `validate_a12x25.py`, `capture_convergence.py`,
  `run_grid_convergence.py`, `test_bistability.py`, `validate_stl.py`, `grid_convergence_stl.py` and
  `evaluate_des_fwh.py`.
- **Deleted:** `scripts/run_spin_ab_smoke.py` (BC-biased and misleading; superseded by
  `scripts/audit_direction_cfd.py`).
- **Not changed (checked only by §2):** `fansim/cror/evaluate.py` and `fansim/centrifugal/evaluate.py`.
- **Audit tooling:**
  - `audit_direction_cfd.py` keeps its explicit {as_built, flipped} matrix.
  - `convention_verdict`'s production reference becomes
    `{"orientation": AXIAL_CFD_ORIENTATION, "spin": TestRig default spin}`, which is `{flipped, −1}`.
  - The CFD runner already fits the rig to each oriented STL.

### 4. Convergence rule A (`fansim/cfd/metrics.py`)

- `convergence(case_dir, tail_frac=0.25, tol_pct=2.0)` splits the tail into two equal halves. The run
  is converged iff `|mean(h2) − mean(h1)| / |mean(tail)| × 100 < tol_pct`. It returns
  `(converged, mean_shift_pct)`.
- A new `oscillation_pct(case_dir, tail_frac)` returns the existing tail peak-to-peak as a % of the
  mean, which is today's drift number.
- `FanMetrics`:
  - `flow_drift_pct` keeps its name but now holds the mean shift;
  - a new field `oscillation_pct: float = 0.0` is added.
- Callers that print drift add `osc=` beside it. Optimizer trial attrs gain `oscillation_pct`.
- `CFD_VERSION = 3`, with a history comment covering the orientation, the rig fit and the convergence
  rule.

### 5. Guards, audit registry, docs

- **Handedness guard test.** Every search-space dict in `fansim/optimize/search_space.py` must have
  stagger lower bounds > 0 and `max_camber` lower bound ≥ 0. A mirrored design would need a sign flip,
  which is out of range. Register it as the unit `optimize.search_space_handedness`, and make
  `cfd.flow_direction_convention` depend on it.
- **Registry additions** to `cfd.flow_direction_convention`: `fansim.cfd.domain:AXIAL_CFD_ORIENTATION`,
  `:orient_impeller_for_cfd`, `:fit_rig_to_stl`, and the `build_case` check (already a target). Add a
  `fansim.cfd.metrics:convergence` target to `cfd.cfm_from_outlet_flow`; closure already covers it,
  but it stays explicit.
- **Contract tests.** Update `tests/audit/test_cfd_direction_contract.py`:
  - the axial orientation is flipped at spin −1;
  - the MRF zone contains the oriented rotor;
  - the frame starts downstream of the oriented rotor.

  Replace `tests/test_cfd.py`'s `rig.spin == -1` pin with a test that derives the expected spin from
  the audit: `designed ω_z (+1) × orientation sign (flipped → −1) == spin`.
- **Glyphs.**
  - The as-built preview (`glyphs.schematic_axial_flow_cloud`) draws air toward **−Z**: open intake +Z,
    exhaust past the motor at −Z. Update `tests/test_glyphs.py` to match.
  - CFD field views render the case's own oriented `constant/triSurface/impeller.stl`, never the
    as-built preview mesh, so the rotor and the field agree. Verify in `midplane.py` / `airflow_panel.py`
    and fix if they overlay the preview.
- **Docs.**
  - `domain.py` and `openfoam_case.py` docstrings state the as-built vs CFD orientation.
  - Roadmap §16.1 gets a correction note.
  - `docs/a12x25-reference.md` and `a12x25_pq_report.md` are touched only via §7.

### 6. Prop sign

- `normalize_metrics_sign` no longer flips. It returns the metrics unchanged and adds
  `thrust_sign_ok: bool`, plus `thrust_sign_error: str` when `Fz` is on the wrong side for the given
  spin.
- `preferred_spin_for_positive_thrust` is removed or kept only as an explicitly named diagnostic that no
  pipeline calls.
- **Imported prop STLs** (`stl_import`, `evaluate_prop_cfd.py`):
  - spin = `prove_direction` rotation × orientation convention when the proof is CONCLUSIVE;
  - cross-check against `spin_hint_from_name`, and on disagreement report both and refuse (explicit
    error) rather than guess;
  - if the proof is INCONCLUSIVE, use the filename hint, else error.
- Register `propeller.thrust_sign` checks: `tests/audit/test_prop_thrust_sign.py`.
- **Prop CFD orientation:** determine it as in §1, i.e. the orientation for which the designed rotation
  at the configured spin pumps air toward the domain outlet. If the prop domain's convention differs
  from the axial duct's, document it in `propeller/cfd.py` and test it. Do not assume it.

### 7. Verification (lifts the freeze)

1. `uv run pytest -q` passes. The audit suite includes the slow Stock handedness test.
2. `audit_direction_cfd.py --rotor stock` and `--rotor reference_stl`, then `--reverdict`.
   `convention_verdict` must be **PASS** for Stock, with production `{flipped, −1}` = recommended. The
   close-ref may stay INCONCLUSIVE on margin; it is reported as-is.
3. The Stock P–Q re-run uses `scripts/run_a12x25_validation.py` at the same operating points as the
   2026-09 report. Rewrite `docs/validation/a12x25_pq_report.md` with before/after columns and state the
   new gap to the Noctua datasheet honestly.
4. Ledger: record PASS for each unit whose checks pass. `cfd.flow_direction_convention` passes only on
   (2).
5. Remove the roadmap freeze banner and mark §19.1 done **only if (2) passes for Stock**. Otherwise, keep
   the freeze and report.
6. Memory: update `fan-orientation-convention`, `a12x25-recipe-fidelity-limit` and
   `a12x25-cfd-convergence-fixes`.

## Error handling

- Orientation, rig and overlap problems raise `ValueError` before any mesh work, with a message naming
  the STL, its bounds and the zone.
- An unconverged mean (rule A) still marks the trial `converged=False`. It is never silently accepted.
- Prop sign mismatch or proof disagreement raises an explicit error; it never flips.

## Out of scope

- Re-scoring the optimizer catalog.
- Automatic per-design orientation (§19.2).
- URANS.
- The direction of CROR and mixed-flow, beyond the §2 check.
