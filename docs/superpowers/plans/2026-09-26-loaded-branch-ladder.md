# Loaded-Branch Diagnostic Ladder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Build the plenum, frame and URANS rungs and a ladder runner. Then find which lever restores the
A12x25 loaded branch (shut-off 22.9 ± 5 Pa).

**Architecture:** Small additive options on `casing.py` and `build_case` (`plenum_z_mm`, `box_scale`), a
URANS overlay beside the existing DES overlay, and one runner script with a pure verdict function.

**Spec:** `docs/superpowers/specs/2026-09-26-loaded-branch-ladder-design.md`

## Global Constraints

- Keep the direction fix intact: axial CFD always goes through `prepare_axial_cfd` (flipped, spin −1).
  Never weaken `check_placement`.
- Defaults are unchanged. With no new arguments, `build_case` and `casing` behave exactly as before.
- Pass criteria: shut-off within 22.9 ± 5 Pa; loaded points converged; free air within 60.1 × (1 ± 0.10).
- Branch `master`. Commit per task with the trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
  Do not commit `runs/` or `.superpowers/`.
- Judge pytest by the summary line; exit codes 127, 139 or −1073740940 at teardown are a known crash.
  Do not run CFD in Tasks 1–3.

---

### Task 1: Plenum casing + `box_scale`

**Files:** Modify `fansim/cfd/casing.py` and `fansim/cfd/openfoam_case.py`. Test: `tests/test_plenum_casing.py`.

**Interfaces:**
- `build_casing_solid(rig, stepped=False, plenum_z_mm=None) -> cq.Solid`
- `export_casing_stl(rig, path, *, stepped=False, plenum_z_mm=None) -> Path`
- `build_case(..., box_scale: float | None = None)`

- [ ] **Step 1: Write the failing tests**

```python
"""Outlet-chamber (plenum) domain: duct ends downstream of the rotor, box is 3x duct radius."""

from __future__ import annotations

import re

import pytest
import trimesh

from fansim.cfd.casing import export_casing_stl
from fansim.cfd.domain import MM_TO_M, TestRig as _Rig
from fansim.cfd.openfoam_case import build_case


def _rig() -> _Rig:
    return _Rig(duct_radius=0.056, tip_gap=0.0005, inlet_length=0.224, outlet_length=0.448,
                impeller_z_min=-0.0085, impeller_z_max=0.0085, mrf_z_min=-0.0105, mrf_z_max=0.0105,
                rpm=2000.0, inlet_velocity=2.0)


def test_plenum_casing_ends_at_plenum_z(tmp_path):
    rig = _rig()
    zp = 60.0
    p = export_casing_stl(rig, tmp_path / "c.stl", plenum_z_mm=zp)
    m = trimesh.load(str(p))
    assert m.bounds[0, 2] == pytest.approx(rig.domain_z_min / MM_TO_M, abs=0.05)
    assert m.bounds[1, 2] == pytest.approx(zp, abs=0.05)


def test_default_casing_unchanged(tmp_path):
    rig = _rig()
    m = trimesh.load(str(export_casing_stl(rig, tmp_path / "c.stl")))
    assert m.bounds[1, 2] == pytest.approx(rig.domain_z_max / MM_TO_M, abs=0.05)


def test_plenum_must_be_downstream_of_rotor(tmp_path):
    with pytest.raises(ValueError, match="plenum"):
        export_casing_stl(_rig(), tmp_path / "c.stl", plenum_z_mm=5.0)


def test_box_scale_sets_block_half_width(tmp_path):
    rig = _rig()
    stl = tmp_path / "r.stl"
    trimesh.creation.box(extents=(20.0, 20.0, 10.0)).export(str(stl))
    casing = export_casing_stl(rig, tmp_path / "c.stl", plenum_z_mm=64.0)
    case = build_case(tmp_path / "case", stl, rig, casing_stl_mm=casing, box_scale=3.0,
                      back_pressure_pa=0.0)
    text = (case / "system/blockMeshDict").read_text(encoding="utf-8")
    xs = [float(v) for v in re.findall(r"\(\s*([-\d.eE+]+)\s+[-\d.eE+]+\s+[-\d.eE+]+\s*\)",
                                        text.split("blocks")[0])[:8]]
    assert max(xs) == pytest.approx(3.0 * rig.duct_radius)
```

- [ ] **Step 2: Run and see it fail.** `uv run pytest tests/test_plenum_casing.py -v` fails, because the unknown keyword `plenum_z_mm` raises a TypeError.

- [ ] **Step 3: Implement**
  - `build_casing_solid`: when `plenum_z_mm` is given, raise `ValueError("plenum_z_mm must be downstream of the impeller …")` if `plenum_z_mm <= rig.impeller_z_max / MM_TO_M`. Otherwise use `zmax = plenum_z_mm` instead of `rig.domain_z_max / MM_TO_M`. It applies to both the plain and the stepped outline.
  - `export_casing_stl` passes the value through.
  - `build_case` accepts `box_scale`: `H = (box_scale if box_scale is not None else BOX_SCALE) * rig.duct_radius` when `casing_stl_mm` is given. Without a casing, keep the current behaviour. Mention it in the docstring.

- [ ] **Step 4: Run** `uv run pytest tests/test_plenum_casing.py tests/test_casing.py tests/test_cfd.py tests/test_cfd_placement_check.py -q`. All pass.

- [ ] **Step 5: Commit** with the message `feat(cfd): outlet-plenum casing option + box_scale for chamber tests`.

---

### Task 2: URANS overlay

**Files:** Modify `fansim/cfd/openfoam_case.py`. Test: `tests/test_urans_overlay.py`.

**Interfaces:**
- `apply_urans_transient(case_dir, *, end_time: float, delta_t: float = 1e-5, max_co: float = 1.5, fo_interval: int = 1) -> Path`
- `run_solve_urans(runner, n_procs: int = 8) -> None`

- [ ] **Step 1: Write the failing tests**

```python
"""URANS overlay: pimpleFoam, adjustable dt, same RAS model, same metric function objects."""

from __future__ import annotations

import trimesh

from fansim.cfd.domain import TestRig as _Rig
from fansim.cfd.openfoam_case import apply_urans_transient, build_case


def _case(tmp_path):
    rig = _Rig(duct_radius=0.06, tip_gap=0.0005, inlet_length=0.24, outlet_length=0.48,
               impeller_z_min=-0.008, impeller_z_max=0.008, mrf_z_min=-0.01, mrf_z_max=0.01,
               rpm=2000.0, inlet_velocity=2.0)
    stl = tmp_path / "r.stl"
    trimesh.creation.box(extents=(20.0, 20.0, 10.0)).export(str(stl))
    return build_case(tmp_path / "case", stl, rig, back_pressure_pa=5.0)


def test_urans_control_dict(tmp_path):
    case = apply_urans_transient(_case(tmp_path), end_time=0.3, delta_t=1e-5, max_co=1.5)
    cd = (case / "system/controlDict").read_text(encoding="utf-8")
    assert "application     pimpleFoam;" in cd
    assert "adjustTimeStep  yes;" in cd and "maxCo           1.5;" in cd
    assert "endTime         0.3;" in cd and "deltaT          1e-05;" in cd
    for fo in ("forces", "outletFlow", "inletP", "outletP"):
        assert fo in cd


def test_urans_keeps_ras_sst_and_transient_schemes(tmp_path):
    case = apply_urans_transient(_case(tmp_path), end_time=0.3)
    turb = (case / "constant/turbulenceProperties").read_text(encoding="utf-8")
    assert "RAS" in turb and "kOmegaSST" in turb and "LES" not in turb
    sch = (case / "system/fvSchemes").read_text(encoding="utf-8")
    assert "backward" in sch
    sol = (case / "system/fvSolution").read_text(encoding="utf-8")
    assert "PIMPLE" in sol
```

- [ ] **Step 2: Run and see it fail.** You get an ImportError.

- [ ] **Step 3: Implement.** In `openfoam_case.py`:
  - Render the steady `T.CONTROL_DICT` with `ENDTIME=end_time`, `WRITEINT=` about 10 writes over the run (as a time interval: switch `writeControl` to `adjustableRunTime`, `writeInterval end_time/10`), `FOINT=fo_interval` and `RHO=RHO_AIR`.
  - Then replace `application     simpleFoam;` with `application     pimpleFoam;`, and `deltaT          1;` with `deltaT          {delta_t};` plus the two lines `adjustTimeStep  yes;` and `maxCo           {max_co};`.
  - Assert each replacement happened exactly once, so a template change fails loudly.
  - Write `fvSchemes` from `T.DES_FV_SCHEMES` and `fvSolution` from `T.DES_FV_SOLUTION`. Leave `turbulenceProperties` as the steady RAS file that `build_case` wrote.
  - `run_solve_urans` mirrors `run_solve_des`, but with the docstring "URANS (frozen-rotor MRF)".

- [ ] **Step 4: Run** `uv run pytest tests/test_urans_overlay.py tests/test_des_fwh.py tests/test_cfd.py -q`. All pass.

- [ ] **Step 5: Commit** with the message `feat(cfd): frozen-rotor URANS overlay (pimpleFoam, adjustable dt, RAS SST)`.

---

### Task 3: Ladder runner + verdict

**Files:** Create `scripts/run_loaded_ladder.py` and `fansim/validation/loaded_ladder.py`. Test: `tests/test_loaded_ladder.py`.

**Interfaces:**
- `ladder_verdict(rows: list[dict], *, published_shutoff: float = 22.9, published_free: float = 60.1, shutoff_tol_pa: float = 5.0, free_tol: float = 0.10) -> dict` returns `{"verdict", "shutoff_pa", "free_air_cfm", "reasons"}`. Rows have `back_pa`, `cfm` and `converged`.
- CLI: `--rung {plenum,frame,urans}`, `--points` (default `0,5,10,15`), `--procs 16`, `--iters 1000`, `--revs 10`, `--base-cell 0.005`, `--tip-gap-mm 0.5`, `--out runs/loaded_ladder`.

- [ ] **Step 1: Write the failing tests** (`tests/test_loaded_ladder.py`):

```python
from fansim.validation.loaded_ladder import ladder_verdict


def R(b, q, c=True):
    return {"back_pa": b, "cfm": q, "converged": c}


def test_pass_when_curve_matches():
    rows = [R(0, 58.0), R(5, 45.0), R(10, 31.0), R(15, 18.0), R(20, 6.0)]
    v = ladder_verdict(rows)
    assert v["verdict"] == "PASS", v
    assert 17.9 <= v["shutoff_pa"] <= 27.9


def test_fail_on_early_collapse():
    rows = [R(0, 58.7), R(5, 21.6, False), R(10, -6.2), R(15, -72.5)]
    assert ladder_verdict(rows)["verdict"] == "FAIL"


def test_unconverged_loaded_point_is_inconclusive_even_if_in_band():
    rows = [R(0, 58.0), R(5, 45.0, False), R(10, 31.0), R(15, 18.0), R(20, 6.0)]
    v = ladder_verdict(rows)
    assert v["verdict"] == "INCONCLUSIVE" and any("converge" in r for r in v["reasons"])


def test_free_air_out_of_tolerance_fails():
    rows = [R(0, 50.0), R(5, 40.0), R(10, 30.0), R(15, 18.0), R(20, 6.0)]
    assert ladder_verdict(rows)["verdict"] == "FAIL"
```

- [ ] **Step 2: Run and see it fail.** You get an ImportError.

- [ ] **Step 3: Implement**
  - **`fansim/validation/loaded_ladder.py`:**
    - Free air is the row with `back_pa == 0`.
    - `shutoff_pa` comes from `fansim.validation.pq_shutoff.shutoff_report_from_pq_rows(rows, published_pa=published_shutoff)["shutoff_pa"]`. Read that function first and use its real return keys.
    - Verdict rules:
      - FAIL if free air is outside the tolerance or the shut-off is outside ±`shutoff_tol_pa`;
      - INCONCLUSIVE if any loaded row (`back_pa > 0`) with `cfm > 0` is unconverged, or if no shut-off can be computed;
      - otherwise PASS.
    - When a rule makes the verdict FAIL but an unconverged row exists, add a reason noting it.
  - **`scripts/run_loaded_ladder.py`** reuses `scripts/run_a12x25_validation.py` building blocks. Import its helpers or copy the minimal logic: `load_blade_params`, `build_impeller`/`export_stl`, `rig_for_impeller` plus `prepare_axial_cfd`, `MeshResolution.for_blade`. For each rung:
    - Always orient and fit via `prepare_axial_cfd`.
    - `plenum_z_mm = rig.impeller_z_max/MM_TO_M + 0.5 * (2 * rig.duct_radius/MM_TO_M)`. Export the casing with `plenum_z_mm`.
    - For `frame` or `urans`, export the frame from the fitted rig, and check that its z_max < `plenum_z_mm`; otherwise raise.
    - `build_case(..., casing_stl_mm=casing, box_scale=3.0, frame_stl_mm=frame or None, back_pressure_pa=b)`.
    - Mesh once, then solve each point: steady `run_solve` for plenum/frame; for urans, `apply_urans_transient(case, end_time=revs*60/rpm)` after each `build_case`, then `run_solve_urans`.
    - `parse_fan_metrics` for each row.
    - Write `docs/validation/loaded_ladder/<rung>.json` after EVERY point: rows, `ladder_verdict`, and the config (rung, iters or revs, base_cell, box_scale, plenum_z_mm, cfd_version).
    - If the verdict is PASS and 20 Pa isn't in the points, run 20 Pa too and recompute.
    - Print one line per point: CFM, converged, shift, osc.

- [ ] **Step 4: Run** `uv run pytest tests/test_loaded_ladder.py -q` and `uv run python scripts/run_loaded_ladder.py --help`, judging by the output. Do not run CFD.

- [ ] **Step 5: Commit** with the message `feat(validation): loaded-branch ladder runner + verdict`.

---

### Task 4: Run the ladder and report (controller)

- [ ] Run the `plenum` rung, then `frame`, each in the background on 16 procs. Stop at the first PASS.
- [ ] If neither passes, schedule `urans` overnight (points 5, 10 and 15 plus a 0 Pa check, 10 revs).
- [ ] Write `docs/validation/a12x25_loaded_ladder.md`: a table of rungs × points (CFM, converged, osc), the shut-off per rung, the delta each rung added, the verdict, and which lever mattered. Update `a12x25_pq_report.md` (top section) and roadmap §19.6. Commit.
