# Rotor Direction Fix (Audit #1 follow-up) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every axial-fan CFD solve the rotor in its designed rotation, size the MRF zone from the real rotor, judge convergence on the tail mean, stop masking prop thrust sign, then re-verify with CFD so the §19.1 freeze can lift.

**Architecture:**
- A new `fansim/cfd/orientation.py` owns the CFD orientation convention (rotor flipped 180° about X, spin −1) and fits the rig's impeller and MRF z-range to the oriented STL. Every axial caller uses it before exporting frame, stator or casing and before calling `build_case`.
- `build_case` gains a placement check that fails loudly if a rotor sits outside its MRF zone or a frame or stator overlaps it.
- `convergence()` switches to a tail-mean-shift rule, and the swing is reported as `oscillation_pct`.
- The prop pipeline takes its direction from the mesh-only proof (`fansim/audit/direction.py`) and no longer flips spin.

**Tech Stack:** Python 3.12, uv, pytest, numpy, trimesh, OpenFOAM v2406 (Docker) via `fansim.cfd.runner`.

**Spec:** `docs/superpowers/specs/2026-09-25-rotor-direction-fix-design.md`. Evidence: `docs/validation/audits/2026-09-25-audit-01-flow-direction.md`.

## Global Constraints

- This plan IS the §19.1 fix, so edits to spin, orientation, glyph and direction code are allowed where a task says so. Nothing else changes solver templates, BCs, `TestRig.spin` (stays −1) or `flow_sign` (stays +1).
- The printed/exported impeller STL and all geometry authoring (`fansim/geometry/*`) are **not** modified. Only the CFD copy is oriented.
- The orientation constant is `AXIAL_CFD_ORIENTATION = "flipped"` (180° about X). An orientation string must be `"as_built"` or `"flipped"`; anything else raises `ValueError`.
- CROR (`fansim/cror/*`) and mixed-flow/centrifugal (`fansim/centrifugal/*`, `fansim/volute/*`) keep their current orientation. They only get the `build_case` placement check. If a check trips there, record it in the task report and fix that caller's rig sizing the same way (from STL bounds). Never weaken the check.
- `CFD_VERSION` becomes 3.
- Convergence rule: split the last `TAIL_FRAC` (0.25) of the outletFlow history into two equal halves. The run is converged iff `|mean(h2) − mean(h1)| / |mean(tail)| × 100 < 2.0`. The peak-to-peak swing is reported separately as `oscillation_pct`.
- Branch: `master`, no worktree, no PRs. Commit after every task with the trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Run tests with `uv run pytest ...`. Importing `fansim.cfd` can crash CPython at interpreter teardown on this machine (exit 127, 139 or −1073740940 after the summary line). Judge by the pytest summary line or the script's output/JSON.
- Before committing, run `git status`. Restore any tracked reference STL or golden files that tests rewrote (`git checkout -- <file>`). Do not commit `runs/` or `.superpowers/`.
- `.superpowers/sdd/progress.md` belongs to another session. This plan's ledger is `.superpowers/sdd/progress-rotor-fix.md`.

---

### Task 1: Orientation module

**Files:**
- Create: `fansim/cfd/orientation.py`
- Modify: `fansim/audit/direction.py`. Replace the body of `flip_about_x` with a re-export from the new module, so there is one implementation.
- Test: `tests/test_cfd_orientation.py`

**Interfaces:**
- Produces:
  - `AXIAL_CFD_ORIENTATION: str = "flipped"`
  - `ORIENTATIONS = ("as_built", "flipped")`
  - `flip_about_x(mesh: trimesh.Trimesh) -> trimesh.Trimesh`, which returns a proper-rotation copy
  - `orient_impeller_for_cfd(src_stl_mm: Path, dst_stl_mm: Path, orientation: str = AXIAL_CFD_ORIENTATION) -> tuple[float, float]`, which writes the file and returns `(z_min_mm, z_max_mm)`
  - `fit_rig_to_stl(rig: TestRig, stl_mm: Path, *, mrf_margin_mm: float = 2.0) -> TestRig`
  - `prepare_axial_cfd(stl_mm: Path, rig: TestRig, workdir: Path, *, orientation: str = AXIAL_CFD_ORIENTATION, mrf_margin_mm: float = 2.0) -> tuple[Path, TestRig]`, which writes `workdir/"impeller_cfd.stl"`

- [ ] **Step 1: Write the failing test**

`tests/test_cfd_orientation.py`:

```python
"""CFD orientation convention (Audit #1): rotor flipped 180° about X, rig fitted to the real STL."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
import trimesh

from fansim.cfd.domain import MM_TO_M, TestRig
from fansim.cfd.orientation import (
    AXIAL_CFD_ORIENTATION,
    fit_rig_to_stl,
    flip_about_x,
    orient_impeller_for_cfd,
    prepare_axial_cfd,
)


def _rig() -> TestRig:
    return TestRig(duct_radius=0.056, tip_gap=0.0005, inlet_length=0.224, outlet_length=0.448,
                   impeller_z_min=-0.003, impeller_z_max=0.003, mrf_z_min=-0.005, mrf_z_max=0.005,
                   rpm=2000.0, inlet_velocity=2.0)


def _asym_box(tmp_path: Path) -> Path:
    # z from -8 to +2 mm: asymmetric so a flip is visible in the bounds.
    m = trimesh.creation.box(extents=(20.0, 10.0, 10.0))
    m.apply_translation([0.0, 0.0, -3.0])
    p = tmp_path / "asym.stl"
    m.export(str(p))
    return p


def test_convention_constant():
    assert AXIAL_CFD_ORIENTATION == "flipped"


def test_flip_is_proper_rotation_about_x():
    m = trimesh.creation.box(extents=(1.0, 2.0, 3.0))
    m.apply_translation([1.0, 2.0, 3.0])
    f = flip_about_x(m)
    assert np.allclose(f.bounds, [[0.5, -3.0, -4.5], [1.5, -1.0, -1.5]])
    assert np.isclose(abs(f.volume), abs(m.volume))
    assert np.allclose(m.bounds, [[0.5, 1.0, 1.5], [1.5, 3.0, 4.5]])  # input untouched


def test_orient_writes_flipped_copy_and_returns_bounds(tmp_path):
    src = _asym_box(tmp_path)
    before = src.read_bytes()
    z0, z1 = orient_impeller_for_cfd(src, tmp_path / "out.stl")
    assert (z0, z1) == pytest.approx((-2.0, 8.0))
    assert src.read_bytes() == before
    z0b, z1b = orient_impeller_for_cfd(src, tmp_path / "same.stl", orientation="as_built")
    assert (z0b, z1b) == pytest.approx((-8.0, 2.0))


def test_orient_rejects_unknown(tmp_path):
    with pytest.raises(ValueError, match="orientation"):
        orient_impeller_for_cfd(_asym_box(tmp_path), tmp_path / "x.stl", orientation="flip")


def test_fit_rig_to_stl_contains_rotor(tmp_path):
    src = _asym_box(tmp_path)
    rig = fit_rig_to_stl(_rig(), src, mrf_margin_mm=2.0)
    assert rig.impeller_z_min == pytest.approx(-8.0 * MM_TO_M)
    assert rig.impeller_z_max == pytest.approx(2.0 * MM_TO_M)
    assert rig.mrf_z_min == pytest.approx(-10.0 * MM_TO_M)
    assert rig.mrf_z_max == pytest.approx(4.0 * MM_TO_M)
    # Everything else is unchanged.
    assert replace(rig, impeller_z_min=-0.003, impeller_z_max=0.003,
                   mrf_z_min=-0.005, mrf_z_max=0.005) == _rig()


def test_prepare_axial_cfd(tmp_path):
    src = _asym_box(tmp_path)
    stl, rig = prepare_axial_cfd(src, _rig(), tmp_path)
    assert stl == tmp_path / "impeller_cfd.stl" and stl.is_file()
    assert rig.impeller_z_min == pytest.approx(-2.0 * MM_TO_M)
    assert rig.impeller_z_max == pytest.approx(8.0 * MM_TO_M)
    assert rig.spin == -1


def test_audit_reexports_same_flip():
    from fansim.audit import direction
    from fansim.cfd import orientation
    assert direction.flip_about_x is orientation.flip_about_x
```

- [ ] **Step 2: Run it and see it fail**

Run: `uv run pytest tests/test_cfd_orientation.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'fansim.cfd.orientation'`

- [ ] **Step 3: Implement**

`fansim/cfd/orientation.py`:

```python
"""CFD orientation of the axial rotor (Audit #1, docs/validation/audits/2026-09-25-audit-01-flow-direction.md).

The A12x25 rotors are designed to turn ω_z = +1 (CCW seen from +Z) and pump −Z *as built*. The ducted
CFD flows +Z (inlet −Z → outlet +Z) with ``spin = −1``. Rotating the rotor 180° about X maps body
ω → −ω and delivery −Z → +Z, so the flipped rotor at ``spin = −1`` IS the designed rotation pumping
down the duct. Only the CFD copy is oriented. The printed/exported STL is unchanged.

The rig's impeller and MRF z-range are fitted to the oriented STL's real bounds. The recipe-based
estimate in ``rig_for_impeller`` under-sizes them (±3 mm vs the Stock STL's −8.1…+8.4 mm), which
left blade ends outside the MRF zone.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import trimesh

from fansim.cfd.domain import MM_TO_M, TestRig

AXIAL_CFD_ORIENTATION = "flipped"
ORIENTATIONS = ("as_built", "flipped")


def flip_about_x(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Proper 180° rotation about X (y → −y, z → −z): same rotor, turned over. Returns a copy."""
    m = mesh.copy()
    m.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1.0, 0.0, 0.0]))
    return m


def orient_impeller_for_cfd(src_stl_mm: Path, dst_stl_mm: Path,
                            orientation: str = AXIAL_CFD_ORIENTATION) -> tuple[float, float]:
    if orientation not in ORIENTATIONS:
        raise ValueError(f"orientation must be one of {ORIENTATIONS}, got {orientation!r}")
    mesh = trimesh.load(str(src_stl_mm), force="mesh")
    out = flip_about_x(mesh) if orientation == "flipped" else mesh
    Path(dst_stl_mm).parent.mkdir(parents=True, exist_ok=True)
    out.export(str(dst_stl_mm))
    return float(out.bounds[0, 2]), float(out.bounds[1, 2])


def fit_rig_to_stl(rig: TestRig, stl_mm: Path, *, mrf_margin_mm: float = 2.0) -> TestRig:
    mesh = trimesh.load(str(stl_mm), force="mesh")
    z0, z1 = float(mesh.bounds[0, 2]), float(mesh.bounds[1, 2])
    return replace(
        rig,
        impeller_z_min=z0 * MM_TO_M,
        impeller_z_max=z1 * MM_TO_M,
        mrf_z_min=(z0 - mrf_margin_mm) * MM_TO_M,
        mrf_z_max=(z1 + mrf_margin_mm) * MM_TO_M,
    )


def prepare_axial_cfd(stl_mm: Path, rig: TestRig, workdir: Path, *,
                      orientation: str = AXIAL_CFD_ORIENTATION,
                      mrf_margin_mm: float = 2.0) -> tuple[Path, TestRig]:
    """Orient the rotor for CFD and fit the rig to it. Use the returned STL and rig for everything
    downstream (frame, stator, casing export, and ``build_case``)."""
    dst = Path(workdir) / "impeller_cfd.stl"
    orient_impeller_for_cfd(Path(stl_mm), dst, orientation)
    return dst, fit_rig_to_stl(rig, dst, mrf_margin_mm=mrf_margin_mm)
```

In `fansim/audit/direction.py`:
- delete the `flip_about_x` function body;
- add `from fansim.cfd.orientation import flip_about_x  # noqa: F401  (re-export; one implementation)` next to the other imports;
- keep `flip_about_x` in any `__all__`.

This import pulls in `fansim.cfd.domain`. That is fine inside pytest, but the audit-status CLI must not import `fansim.audit.direction`. Check that `scripts/audit_status.py` doesn't; it only reads files.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_cfd_orientation.py tests/audit/test_direction_geometry.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add fansim/cfd/orientation.py fansim/audit/direction.py tests/test_cfd_orientation.py
git commit -m "feat(cfd): axial CFD orientation convention + rig fitted to oriented STL

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: `build_case` placement check

**Files:**
- Modify: `fansim/cfd/openfoam_case.py`. Add a helper `check_placement` and call it in `build_case` right after the STLs are loaded, before any scaling or writing.
- Test: `tests/test_cfd_placement_check.py`

**Interfaces:**
- Produces: `check_placement(impeller_mm: trimesh.Trimesh, rig: TestRig, *, dual_mrf: dict | None = None, downstream_mm: dict[str, trimesh.Trimesh] | None = None) -> None`, which raises `ValueError`.

- [ ] **Step 1: Write the failing test**

`tests/test_cfd_placement_check.py`:

```python
"""build_case refuses rotors outside the MRF zone and frames/stators overlapping the rotor."""

from __future__ import annotations

import pytest
import trimesh

from fansim.cfd.domain import TestRig
from fansim.cfd.openfoam_case import build_case, check_placement


def _rig(mrf=(-0.010, 0.010)) -> TestRig:
    return TestRig(duct_radius=0.06, tip_gap=0.0005, inlet_length=0.24, outlet_length=0.48,
                   impeller_z_min=-0.008, impeller_z_max=0.008, mrf_z_min=mrf[0], mrf_z_max=mrf[1],
                   rpm=2000.0, inlet_velocity=2.0)


def _box(z_lo_mm: float, z_hi_mm: float) -> trimesh.Trimesh:
    m = trimesh.creation.box(extents=(20.0, 20.0, z_hi_mm - z_lo_mm))
    m.apply_translation([0.0, 0.0, 0.5 * (z_lo_mm + z_hi_mm)])
    return m


def test_ok_when_inside_and_frame_downstream():
    check_placement(_box(-8.0, 8.4), _rig(), downstream_mm={"frame": _box(10.5, 18.5)})


def test_rotor_outside_mrf_raises():
    with pytest.raises(ValueError, match="MRF"):
        check_placement(_box(-8.1, 8.4), _rig(mrf=(-0.005, 0.005)))


def test_frame_overlapping_rotor_raises():
    with pytest.raises(ValueError, match="frame"):
        check_placement(_box(-8.0, 8.4), _rig(), downstream_mm={"frame": _box(5.5, 13.5)})


def test_dual_mrf_uses_front_to_rear_span():
    dual = {"front_z_min": -0.012, "front_z_max": 0.0, "rear_z_min": 0.0, "rear_z_max": 0.012,
            "omega_front": -200.0, "omega_rear": 200.0}
    check_placement(_box(-11.0, 11.0), _rig(mrf=(-0.001, 0.001)), dual_mrf=dual)
    with pytest.raises(ValueError, match="MRF"):
        check_placement(_box(-13.0, 11.0), _rig(), dual_mrf=dual)


def test_build_case_runs_the_check(tmp_path):
    stl = tmp_path / "rotor.stl"
    _box(-8.1, 8.4).export(str(stl))
    with pytest.raises(ValueError, match="MRF"):
        build_case(tmp_path / "case", stl, _rig(mrf=(-0.005, 0.005)), back_pressure_pa=0.0)
```

- [ ] **Step 2: Run it and see it fail**

Run: `uv run pytest tests/test_cfd_placement_check.py -v`
Expected: FAIL with `ImportError: cannot import name 'check_placement'`

- [ ] **Step 3: Implement**

In `fansim/cfd/openfoam_case.py`, add above `build_case`:

```python
_PLACEMENT_TOL_M = 1e-6


def check_placement(impeller_mm: trimesh.Trimesh, rig: TestRig, *, dual_mrf: dict | None = None,
                    downstream_mm: dict[str, trimesh.Trimesh] | None = None) -> None:
    """Refuse cases whose rotor pokes out of the MRF zone, or whose frame/stator overlaps the rotor.

    Blade parts outside the MRF zone are solved as stationary walls, and a frame inside the blade
    band intersects the rotor. Both silently corrupt CFM, so fail loudly instead.
    """
    z0 = float(impeller_mm.bounds[0, 2]) * MM_TO_M
    z1 = float(impeller_mm.bounds[1, 2]) * MM_TO_M
    if dual_mrf is not None:
        lo, hi = float(dual_mrf["front_z_min"]), float(dual_mrf["rear_z_max"])
    else:
        lo, hi = float(rig.mrf_z_min), float(rig.mrf_z_max)
    if z0 < lo - _PLACEMENT_TOL_M or z1 > hi + _PLACEMENT_TOL_M:
        raise ValueError(
            f"impeller z [{z0 * 1e3:.2f}, {z1 * 1e3:.2f}] mm is not inside the MRF zone "
            f"[{lo * 1e3:.2f}, {hi * 1e3:.2f}] mm — size the rig from the STL "
            f"(fansim.cfd.orientation.fit_rig_to_stl)")
    for name, part in (downstream_mm or {}).items():
        pz0 = float(part.bounds[0, 2]) * MM_TO_M
        if pz0 < z1 - _PLACEMENT_TOL_M:
            raise ValueError(
                f"{name} starts at z={pz0 * 1e3:.2f} mm, inside the impeller (z_max "
                f"{z1 * 1e3:.2f} mm) — export it from the fitted rig")
```

In `build_case`:
- Load the impeller mesh into `surf` as it does today, but call the check **before** `surf.apply_scale`.
- Also load the frame and stator meshes before scaling. Refactor the existing load blocks so each mesh is loaded once and scaled after the check.
- Call `check_placement(surf, rig, dual_mrf=dual_mrf, downstream_mm={...})`, including `"frame"` and/or `"stator"` when those STLs are given.
- The casing is not checked, because it surrounds the rotor.

- [ ] **Step 4: Run the tests plus the existing CFD case tests**

Run: `uv run pytest tests/test_cfd_placement_check.py tests/test_cfd.py tests/audit/test_cfd_direction_contract.py tests/test_cror.py tests/test_mixed_flow.py tests/test_casing.py tests/test_frame.py -q -m "not docker"`
Expected: all pass.

If an existing test now raises, its fixture STL is outside its rig's MRF zone or its frame overlaps. Fix the **fixture**: size the rig from the STL with `fit_rig_to_stl`, or move the fixture frame downstream. Never weaken the check. List each fixture change in the report.

If a CROR or mixed-flow test fails, that is a real finding. Fix that module's rig sizing from its STL bounds (the same pattern as `fit_rig_to_stl`), add a regression test, and report it.

- [ ] **Step 5: Commit**

```bash
git add fansim/cfd/openfoam_case.py tests/test_cfd_placement_check.py
git commit -m "feat(cfd): build_case refuses rotors outside MRF zone and overlapping frame/stator

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

(Add any fixture or CROR/mixed files you changed.)

---

### Task 3: Optimizer / cockpit path uses the oriented, fitted rotor

**Files:**
- Modify: `fansim/optimize/objectives.py` (in `evaluate_candidate`, the block from `rig0 = rig_for_impeller(` through `build_case(`)
- Modify: `fansim/cfd/midplane.py` (around line 648: the context body drawn behind the field)
- Test: `tests/test_objectives_orientation.py`

**Interfaces:**
- Consumes: `prepare_axial_cfd` (Task 1) and `check_placement` via `build_case` (Task 2).

- [ ] **Step 1: Write the failing test**

`tests/test_objectives_orientation.py`:

```python
"""evaluate_candidate meshes the CFD-oriented rotor with a rig fitted to it (Audit #1 fix)."""

from __future__ import annotations

import pytest
import trimesh

from fansim.cfd.domain import MM_TO_M

pytestmark = pytest.mark.slow  # builds the Stock impeller with CadQuery


class _Stop(Exception):
    pass


def test_build_case_gets_flipped_rotor_and_fitted_rig(tmp_path, monkeypatch):
    from fansim.geometry.config import load_blade_params
    from fansim.optimize import objectives

    seen = {}

    def fake_build_case(case_dir, stl, rig, **kw):
        seen["stl"], seen["rig"], seen["kw"] = stl, rig, kw
        raise _Stop

    monkeypatch.setattr(objectives, "build_case", fake_build_case)
    params = load_blade_params("config/problems/a12x25_reference.yaml")
    with pytest.raises(_Stop):
        objectives.evaluate_candidate(params, workdir=tmp_path)

    stl = seen["stl"]
    assert stl.name == "impeller_cfd.stl"
    as_built = trimesh.load(str(tmp_path / "impeller.stl"))
    cfd = trimesh.load(str(stl))
    # Flipped about X: the z-range is mirrored.
    assert cfd.bounds[0, 2] == pytest.approx(-as_built.bounds[1, 2], abs=1e-6)
    assert cfd.bounds[1, 2] == pytest.approx(-as_built.bounds[0, 2], abs=1e-6)
    rig = seen["rig"]
    assert rig.spin == -1
    assert rig.mrf_z_min <= cfd.bounds[0, 2] * MM_TO_M
    assert rig.mrf_z_max >= cfd.bounds[1, 2] * MM_TO_M
    frame = seen["kw"].get("frame_stl_mm")
    if frame is not None:
        assert trimesh.load(str(frame)).bounds[0, 2] >= cfd.bounds[1, 2] - 1e-6
```

Before writing the test, check `evaluate_candidate`'s real signature for the workdir argument (`grep -n "def evaluate_candidate" -A30 fansim/optimize/objectives.py`). Adapt the call to its real required arguments, supplying the minimum a free-air evaluation needs. If it cannot run without extra fixtures (a fan spec, say), use the defaults the cockpit uses in `fansim/cockpit/fan_assess.py`. Record what you used in the report.

- [ ] **Step 2: Run it and see it fail**

Run: `uv run pytest tests/test_objectives_orientation.py -v -m slow`
Expected: FAIL. `stl.name` is `impeller.stl`, or the bounds are not mirrored.

- [ ] **Step 3: Implement**

In `evaluate_candidate`, immediately after the `rig0 = rig_for_impeller(...)` call and **before** the stator/frame/casing exports, insert:

```python
    # Audit #1: CFD solves the designed rotation only with the rotor flipped (spin stays −1), and
    # the MRF zone must contain the whole rotor, so size it from the oriented STL.
    stl, rig0 = prepare_axial_cfd(stl, rig0, workdir)
```

Import `prepare_axial_cfd` from `fansim.cfd.orientation` at the top. Every later use of `stl` and `rig0` in the function (frame, stator, casing exports, `build_case`, `solve_at` / `rig` replacements) then uses the oriented, fitted versions. Check each one:
- `grep -n "rig0\|stl\b" fansim/optimize/objectives.py`.
- Operating-point rigs built by `replace(rig0, ...)` inherit the fit.
- Any second `rig_for_impeller` call in this function must also go through `fit_rig_to_stl(rig, stl)`.

The as-built `workdir/"impeller.stl"` stays as the design file the cockpit previews and prints.

In `fansim/cfd/midplane.py`, where the context body is drawn (`stl = case_dir / "impeller.stl"`), prefer the mesh the solver actually used:

```python
            stl = case_dir / "constant" / "triSurface" / "impeller.stl"
            if not stl.is_file():
                stl = case_dir / "impeller.stl"
```

The existing scale check handles the metre-scale triSurface copy. Keep it.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_objectives_orientation.py -m slow -q` and `uv run pytest tests/test_evaluate_candidate_feasible.py tests/test_objectives_reason.py tests/test_midplane.py tests/test_airflow_panel.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add fansim/optimize/objectives.py fansim/cfd/midplane.py tests/test_objectives_orientation.py
git commit -m "fix(optimize): solve the designed rotation with an MRF zone fitted to the rotor

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Migrate the axial scripts; delete the misleading spin smoke

**Files:**
- Modify: `scripts/run_a12x25_validation.py`, `scripts/run_fan_curve.py`, `scripts/run_baseline.py`, `scripts/validate_a12x25.py`, `scripts/capture_convergence.py`, `scripts/run_grid_convergence.py`, `scripts/test_bistability.py`, `scripts/validate_stl.py`, `scripts/grid_convergence_stl.py`, `scripts/evaluate_des_fwh.py`
- Delete: `scripts/run_spin_ab_smoke.py`
- Test: `tests/test_axial_scripts_oriented.py`

**Interfaces:**
- Consumes: `prepare_axial_cfd`, and `fit_rig_to_stl` for per-point rigs.

**Pattern.** Apply it at every place in these scripts where an axial rotor STL and a rig reach `build_case`:
1. After the rotor STL exists and the rig is built (`rig_for_impeller`, `rig_for_reference_stl`, or a hand-built `TestRig(...)`), and BEFORE any `export_frame_stl` / `export_stator_stl` / `export_casing_stl` and `build_case`, add:
   ```python
   stl, rig = prepare_axial_cfd(stl, rig, <case dir>)
   ```
   Use the script's own variable names. The case dir is the directory later passed to `build_case`.
2. Where a loop builds a fresh rig per operating point (for example `run_fan_curve.py` lines ~83–86, and `validate_a12x25.py`), fit each new rig to the already-oriented STL: `rig = fit_rig_to_stl(rig_for_impeller(...), stl)`. Do not re-orient.
3. Where one oriented STL is shared across cells (`run_a12x25_validation.py` `_resolve_impeller_stl` plus per-cell copies), orient once per case dir and fit the rig to that oriented copy.
4. Add `from fansim.cfd.orientation import prepare_axial_cfd` (plus `fit_rig_to_stl` where used) next to the existing `fansim.cfd` imports, following each script's `# noqa: E402` style.
5. Where a script prints or records `drift`, leave the call; Task 5 changes the metric's meaning.

Delete `scripts/run_spin_ab_smoke.py`. Its A/B is biased by the asymmetric BCs; `scripts/audit_direction_cfd.py` supersedes it.

- [ ] **Step 1: Write the failing guard test**

`tests/test_axial_scripts_oriented.py`:

```python
"""Every axial CFD entry point orients the rotor before build_case (Audit #1 fix)."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AXIAL_SCRIPTS = [
    "run_a12x25_validation.py", "run_fan_curve.py", "run_baseline.py", "validate_a12x25.py",
    "capture_convergence.py", "run_grid_convergence.py", "test_bistability.py", "validate_stl.py",
    "grid_convergence_stl.py", "evaluate_des_fwh.py",
]
# Non-axial or audit tooling that deliberately controls orientation itself.
EXEMPT = {"audit_direction_cfd.py", "evaluate_cror.py"}


def _calls(path: Path) -> set[str]:
    names = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Call):
            f = node.func
            names.add(f.id if isinstance(f, ast.Name) else getattr(f, "attr", ""))
    return names


def test_listed_scripts_orient_before_build_case():
    for name in AXIAL_SCRIPTS:
        calls = _calls(ROOT / "scripts" / name)
        assert "build_case" in calls, name
        assert "prepare_axial_cfd" in calls, f"{name} calls build_case without prepare_axial_cfd"


def test_no_unlisted_script_calls_build_case():
    for p in sorted((ROOT / "scripts").glob("*.py")):
        if p.name in AXIAL_SCRIPTS or p.name in EXEMPT:
            continue
        assert "build_case" not in _calls(p), f"{p.name}: add to AXIAL_SCRIPTS or EXEMPT"


def test_spin_smoke_removed():
    assert not (ROOT / "scripts" / "run_spin_ab_smoke.py").exists()
```

- [ ] **Step 2: Run it and see it fail**

Run: `uv run pytest tests/test_axial_scripts_oriented.py -v`
Expected: FAIL. The listed scripts lack `prepare_axial_cfd`, and the spin smoke still exists.

- [ ] **Step 3: Migrate each script per the pattern, and delete the smoke script**

If a script not in the list turns out to call `build_case` (the second test finds it), decide whether it is axial. If it is, migrate it and add it to `AXIAL_SCRIPTS`. If not, add it to `EXEMPT` with a comment. Report the decision.

- [ ] **Step 4: Run the guard, then smoke-check each script's argument parsing**

Run: `uv run pytest tests/test_axial_scripts_oriented.py -v`
Expected: 3 passed.

For each migrated script, run `uv run python scripts/<name> --help`. Expected: the usage text prints (the exit code may be 127/139 at teardown). Do NOT run any CFD.

- [ ] **Step 5: Commit**

```bash
git add scripts/ tests/test_axial_scripts_oriented.py
git commit -m "fix(scripts): orient the rotor and fit the rig in every axial CFD entry point

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Convergence rule A, `oscillation_pct`, `CFD_VERSION = 3`

**Files:**
- Modify: `fansim/cfd/metrics.py` (`convergence`, a new `oscillation_pct`, `FanMetrics`, `parse_fan_metrics`, `CFD_VERSION` and its history comment)
- Modify: the drift-printing callers so they also show `osc`: `fansim/optimize/objectives.py` (UNCONVERGED note and `_operating_point_reason` args), `fansim/cror/evaluate.py`, `fansim/centrifugal/evaluate.py`, `fansim/volute/evaluate.py`, `scripts/run_a12x25_validation.py`, `scripts/validate_a12x25.py`, `scripts/validate_stl.py`, `scripts/audit_direction_cfd.py`, `scripts/capture_convergence.py`
- Test: `tests/test_convergence_rule.py`

**Interfaces:**
- Produces:
  - `convergence(case_dir, tail_frac=TAIL_FRAC, tol_pct=2.0) -> tuple[bool, float]`, where the float is now the mean shift %
  - `oscillation_pct(case_dir, tail_frac=TAIL_FRAC) -> float`
  - `FanMetrics.oscillation_pct: float = 0.0`
  - `CFD_VERSION == 3`

- [ ] **Step 1: Write the failing test**

`tests/test_convergence_rule.py`:

```python
"""Rule A: converged iff the tail mean is stable; the swing is reported, not judged."""

from __future__ import annotations

import math

import pytest

from fansim.cfd.metrics import CFD_VERSION, convergence, oscillation_pct


def _write_flow(case, values):
    d = case / "postProcessing" / "outletFlow" / "0"
    d.mkdir(parents=True, exist_ok=True)
    (d / "surfaceFieldValue.dat").write_text(
        "".join(f"{i + 1} {v}\n" for i, v in enumerate(values)), encoding="utf-8")


def test_limit_cycle_with_stable_mean_is_converged(tmp_path):
    # 8% peak-to-peak oscillation around 0.03, many periods in the tail.
    vals = [0.03 * (1 + 0.04 * math.sin(2 * math.pi * i / 10)) for i in range(400)]
    _write_flow(tmp_path, vals)
    ok, shift = convergence(tmp_path)
    assert ok and shift < 2.0
    assert oscillation_pct(tmp_path) == pytest.approx(8.0, abs=0.5)  # samples miss the exact peaks


def test_drifting_mean_is_not_converged(tmp_path):
    vals = [0.02 + 0.00004 * i for i in range(400)]  # still climbing through the tail
    _write_flow(tmp_path, vals)
    ok, shift = convergence(tmp_path)
    assert not ok and shift > 2.0


def test_too_short_history(tmp_path):
    _write_flow(tmp_path, [0.03, 0.03, 0.03])
    assert convergence(tmp_path) == (False, 999.0)


def test_cfd_version_bumped():
    assert CFD_VERSION == 3
```

- [ ] **Step 2: Run it and see it fail**

Run: `uv run pytest tests/test_convergence_rule.py -v`
Expected: FAIL. `oscillation_pct` can't be imported, and the version is 2.

- [ ] **Step 3: Implement**

In `fansim/cfd/metrics.py`, replace `convergence` and add `oscillation_pct`:

```python
def _tail_flows(case_dir: Path, tail_frac: float) -> list[float]:
    traj = _flow_trajectory(Path(case_dir))
    if len(traj) < 4:
        return []
    return [f for _, f in traj[max(1, int(len(traj) * (1.0 - tail_frac))):]]


def convergence(case_dir: str | Path, tail_frac: float = TAIL_FRAC,
                tol_pct: float = 2.0) -> tuple[bool, float]:
    """Is the integrated flow's tail MEAN stable? Returns (converged, mean_shift_pct).

    Steady RANS on thin blades settles into a limit cycle rather than a fixed point. The reported
    metrics are the tail mean, so convergence judges that mean: split the tail into two halves, and
    call it converged when their means agree within ``tol_pct`` of the tail mean. The swing itself
    is reported by :func:`oscillation_pct`.
    """
    flows = _tail_flows(Path(case_dir), tail_frac)
    if len(flows) < 4:
        return (False, 999.0)
    h = len(flows) // 2
    m1, m2 = sum(flows[:h]) / h, sum(flows[h:]) / (len(flows) - h)
    mean = sum(flows) / len(flows)
    shift = abs(m2 - m1) / (abs(mean) + 1e-12) * 100.0
    return (shift < tol_pct, shift)


def oscillation_pct(case_dir: str | Path, tail_frac: float = TAIL_FRAC) -> float:
    """Peak-to-peak flow over the tail as a % of its mean (the pre-v3 'drift')."""
    flows = _tail_flows(Path(case_dir), tail_frac)
    if len(flows) < 4:
        return 999.0
    mean = sum(flows) / len(flows)
    return (max(flows) - min(flows)) / (abs(mean) + 1e-12) * 100.0
```

- Add `oscillation_pct: float = 0.0` to `FanMetrics`, after `moment_z_nm`.
- In `parse_fan_metrics`, pass `oscillation_pct=oscillation_pct(case_dir)`.
- Update the `FanMetrics.flow_drift_pct` comment (if any) to say it holds the tail mean shift %.
- Set `CFD_VERSION = 3` and extend the history comment:

```
#   3 (2026-09-25) — Audit #1 fix: rotor solved in its designed rotation (flipped 180° about X,
#                    spin −1; fansim/cfd/orientation.py); MRF zone fitted to the real rotor STL;
#                    convergence judged on tail-mean stability (oscillation reported separately).
```

In each listed caller, print or record `osc` next to drift. Examples:
- objectives UNCONVERGED note: `f"UNCONVERGED (free mean shift {m_free.flow_drift_pct:.1f}%, osc {m_free.oscillation_pct:.1f}%; load … )"`;
- script result dicts: add `"oscillation_pct": round(m.oscillation_pct, 1)`.

`capture_convergence.py` uses `convergence(out)` directly; also print `oscillation_pct(out)`.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_convergence_rule.py tests/test_cfd.py tests/test_evaluate_candidate_feasible.py tests/test_mixed_flow_evaluate.py tests/test_cfd_stale.py tests/audit -q -m "not slow"`
Expected: all pass. `tests/test_cfd_stale.py` may pin the version number; update it to 3 if so, and say so in the report.

- [ ] **Step 5: Commit**

```bash
git add fansim/cfd/metrics.py fansim/optimize/objectives.py fansim/cror/evaluate.py fansim/centrifugal/evaluate.py fansim/volute/evaluate.py scripts/ tests/
git commit -m "feat(cfd): converge on tail-mean stability, report oscillation; CFD_VERSION 3

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Handedness guard, audit registry, contract tests, `convention_verdict`

**Files:**
- Create: `tests/audit/test_search_space_handedness.py`
- Modify: `fansim/audit/registry.yaml`, `fansim/audit/direction_verdict.py` (`convention_verdict` production reference), `scripts/audit_direction_cfd.py` (pass the production orientation), `tests/audit/test_cfd_direction_contract.py`, `tests/audit/test_direction_verdict.py`, `tests/test_cfd.py` (replace the `rig.spin == -1` pin)

**Interfaces:**
- Changes `convention_verdict(matrix, production_spin, production_orientation="as_built")` to `convention_verdict(matrix, production_spin, production_orientation)`. The third argument is now required. PASS iff the matrix passed and `recommended == {"orientation": production_orientation, "spin": production_spin}`.

- [ ] **Step 1: Write the failing tests**

`tests/audit/test_search_space_handedness.py`:

```python
"""Every optimizer search space keeps the Stock handedness (stagger > 0, camber >= 0).

The CFD orientation (flip about X, spin −1) is fixed for all axial designs. That is only valid
while no design can be a mirror image, which would need a negative stagger or camber.
"""

from __future__ import annotations

from fansim.optimize import search_space


def _spaces():
    for name in dir(search_space):
        val = getattr(search_space, name)
        if isinstance(val, dict) and any(str(k).startswith("stagger") for k in val):
            yield name, val


def test_found_spaces():
    assert list(_spaces()), "no search-space dicts found"


def test_stagger_and_camber_bounds_keep_handedness():
    for name, space in _spaces():
        for key, bounds in space.items():
            if str(key).startswith("stagger"):
                assert bounds[0] > 0.0, f"{name}.{key} lower bound {bounds[0]} allows mirrored blades"
            if str(key) == "max_camber":
                assert bounds[0] >= 0.0, f"{name}.{key} lower bound {bounds[0]} allows reversed camber"
```

In `tests/test_cfd.py::test_rig_dimensions_and_operating_point`, replace `assert rig.spin == -1` with:

```python
    # Audit #1: designed ω_z = +1 as built; the CFD copy is flipped about X (body ω → −ω), so the
    # solver spin must be −1 × (+1) = −1. Derive, don't just pin.
    from fansim.cfd.orientation import AXIAL_CFD_ORIENTATION
    designed_omega_as_built = +1
    orientation_sign = -1 if AXIAL_CFD_ORIENTATION == "flipped" else +1
    assert rig.spin == orientation_sign * designed_omega_as_built
```

Append to `tests/audit/test_cfd_direction_contract.py`:

```python
def test_axial_convention_is_flipped_at_spin_minus_one():
    from fansim.cfd.orientation import AXIAL_CFD_ORIENTATION
    assert AXIAL_CFD_ORIENTATION == "flipped"
    assert _Rig.__dataclass_fields__["spin"].default == -1
```

(Use whatever alias the file already uses for `TestRig`; it was aliased to avoid pytest collection.)

In `tests/audit/test_direction_verdict.py`:
- update the existing `convention_verdict` tests to pass `production_orientation="as_built"` explicitly;
- add a test where a matrix PASS recommends `{"orientation": "flipped", "spin": -1}` with production `("flipped", -1)`, giving **PASS**;
- add a test where production is `("as_built", -1)` for the same matrix, giving **FAIL**.

- [ ] **Step 2: Run them and see them fail**

Run: `uv run pytest tests/audit/test_search_space_handedness.py tests/audit/test_direction_verdict.py tests/test_cfd.py::test_rig_dimensions_and_operating_point -v`
Expected: the new `convention_verdict` tests FAIL, because the signature lacks a required orientation or the value is compared to the hard-coded `as_built`. The handedness test may already pass; it is a lock-in.

- [ ] **Step 3: Implement**

- `fansim/audit/direction_verdict.py` `convention_verdict`: make the production orientation a parameter, put it into the `"production"` dict, and compare against it.
- `scripts/audit_direction_cfd.py`: pass `production_orientation=AXIAL_CFD_ORIENTATION`, imported from `fansim.cfd.orientation`, everywhere `convention_verdict` is called, including `--reverdict`.
- `fansim/audit/registry.yaml`:
  - Add a unit:
    ```yaml
      - id: optimize.search_space_handedness
        targets: ["fansim.optimize.search_space"]
        claim: "Optimizer bounds keep stagger > 0 and camber >= 0, so every axial design has Stock handedness"
        source: {kind: derivation, ref: "Audit #1: fixed CFD orientation is valid only without mirrored designs"}
        checks: [tests/audit/test_search_space_handedness.py]
    ```
  - To `cfd.flow_direction_convention`:
    - add `"fansim.cfd.orientation"` (the whole module) and `"fansim.cfd.openfoam_case:check_placement"` to `targets`;
    - add `optimize.search_space_handedness` to `depends_on`;
    - add `tests/test_cfd_orientation.py` and `tests/test_cfd_placement_check.py` to `checks`.
  - To `cfd.cfm_from_outlet_flow`: add `"fansim.cfd.metrics:convergence"` and `"fansim.cfd.metrics:oscillation_pct"` to `targets`, and `tests/test_convergence_rule.py` to `checks`.

- [ ] **Step 4: Run the tests and the status CLI**

Run: `uv run pytest tests/audit tests/test_cfd.py -q -m "not slow"`, then `uv run python scripts/audit_status.py`
Expected:
- all tests pass;
- every unit resolves, with none MISSING;
- `physics.air_properties` and `optimize.reject_dead_designs` still show PROVEN, unless their targets changed;
- the units whose targets or checks changed show CHANGED, NEW or AFFECTED. That is expected and must not be "fixed".

- [ ] **Step 5: Commit**

```bash
git add fansim/audit/ scripts/audit_direction_cfd.py tests/
git commit -m "feat(audit): handedness guard; convention verdict against the flipped production setup

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Preview glyphs show the real airflow direction

**Files:**
- Modify: `fansim/cfd/glyphs.py` (`schematic_axial_flow_cloud`), `tests/test_glyphs.py` (`test_schematic_axial_flow_cloud_is_plus_z_in_annulus`)
- Check: `fansim/cockpit/fan_trials.py` (~line 286), which draws this cloud on the as-built preview, and `fansim/cockpit/fan_viz.py` (the rotation-cue ring, CCW seen from the +Z intake)

The schematic cloud is drawn on the **as-built** preview. On the as-built rotor, air enters the open +Z intake and leaves past the motor at −Z. CFD field glyphs (`build_velocity_cloud`) come from the solved field, which is in the duct frame, and stay as they are.

- [ ] **Step 1: Update the test to the physical direction (it fails first)**

Rename it to `test_schematic_axial_flow_cloud_is_minus_z_in_annulus`, and change the axial assertion and comment:

```python
    # As-built preview: open intake +Z, exhaust past the motor at −Z (user-confirmed real fan;
    # Audit #1). CFD field glyphs are in the duct frame and come from the solve, not this cloud.
    assert np.allclose(u[:, 2], -2.5)
```

Run: `uv run pytest tests/test_glyphs.py -v`
Expected: FAIL, because the cloud is +Z.

- [ ] **Step 2: Implement**

In `schematic_axial_flow_cloud`, set `u[:, 2] = -u_ax` and rewrite the docstring and the inline comment to the as-built statement above.

In `fansim/cockpit/fan_viz.py`, confirm the rotation-cue ring is drawn CCW seen from +Z, i.e. tangent direction +θ. If it is drawn the other way, fix it and add an assertion to the existing fan_viz test. Report which case applied.

- [ ] **Step 3: Run the tests**

Run: `uv run pytest tests/test_glyphs.py tests/test_cockpit_view.py tests/test_airflow_panel.py -q`
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add fansim/cfd/glyphs.py fansim/cockpit/ tests/test_glyphs.py
git commit -m "fix(viz): as-built preview airflow points -Z (intake +Z, exhaust past the motor)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Prop direction from geometry; no spin flipping

**Files:**
- Create: `fansim/propeller/direction.py`
- Modify: `fansim/propeller/calibrate.py` (`normalize_metrics_sign`, remove `preferred_spin_for_positive_thrust`), `fansim/propeller/cfd.py` (`run_prop_cfd`, or whatever the function containing lines ~240–345 is called), `fansim/propeller/polar.py` (~line 196–282), `fansim/propeller/__init__.py` (exports), `scripts/evaluate_prop_cfd.py` (spin-hint use)
- Modify: `tests/test_prop_calibrate.py`
- Create: `tests/audit/test_prop_thrust_sign.py`
- Modify: `fansim/audit/registry.yaml` (`propeller.thrust_sign` checks and targets)

**Physics.** The prop open-air domain has freestream toward +Z, like the duct. A prop in its designed rotation must push air toward +Z, so the fluid force on it is Fz < 0. Thrust magnitude is therefore `−Fz`, and `thrust_sign_ok = Fz < 0`. That matches the fan: spin −1 pumping +Z gave `thrust_n = −0.042` in the 2026-09-24 A/B.

The orientation and spin come from the mesh proof:
- pump_sign = +1: `("as_built", spin = omega_sign)`;
- pump_sign = −1: `("flipped", spin = −omega_sign)`.

A filename CW/CCW label says only the **chirality**, not which side is up. So it is cross-checked against `proof.chirality`: CCW means the real-fan chirality −1, and CW means +1. It cannot choose the orientation.

**Interfaces:**
- Produces:
  - `PropDirection(orientation: str, spin: int, source: str, chirality: int | None, note: str)`, a frozen dataclass
  - `prop_direction(stl_mm: Path, *, name_hint: str | None = None) -> PropDirection`, which raises `ValueError` on an INCONCLUSIVE proof or on a label/chirality disagreement
  - `chirality_hint_from_name(name: str) -> int | None`, where CCW gives −1, CW gives +1, and anything else None
  - `normalize_metrics_sign(metrics: dict, *, spin: int) -> dict`, which no longer flips. It keeps `thrust_n_raw`, sets `thrust_n = -raw`, sets `thrust_g` from it, and adds `thrust_sign_ok: bool` and, when not ok, `thrust_sign_error: str`

- [ ] **Step 1: Write the failing tests**

`tests/audit/test_prop_thrust_sign.py`:

```python
"""Prop thrust sign comes from geometry; a wrong sign is reported, never flipped away."""

from __future__ import annotations

import pytest

from fansim.audit.synthetic import cambered_blade_fan
from fansim.propeller.calibrate import normalize_metrics_sign
from fansim.propeller.direction import chirality_hint_from_name, prop_direction


def _stl(tmp_path, **kw):
    p = tmp_path / "prop.stl"
    cambered_blade_fan(n_blades=2, r_hub=6.0, r_tip=60.0, chord=15.0, **kw).export(str(p))
    return p


def test_correct_sign_is_positive_thrust_and_ok():
    out = normalize_metrics_sign({"thrust_n": -0.5}, spin=-1)
    assert out["thrust_sign_ok"] is True and out["thrust_n"] == pytest.approx(0.5)
    assert out["thrust_n_raw"] == -0.5 and "thrust_sign_error" not in out


def test_wrong_sign_is_flagged_not_flipped():
    out = normalize_metrics_sign({"thrust_n": 0.5}, spin=-1)
    assert out["thrust_sign_ok"] is False and "thrust_sign_error" in out
    assert out["thrust_n"] == pytest.approx(-0.5)   # reported as negative thrust, not masked
    assert out["spin"] == -1 and "spin_recommended" not in out


def test_chirality_hint():
    assert chirality_hint_from_name("obj_2_ccw.stl") == -1
    assert chirality_hint_from_name("obj_8_cw.stl") == 1
    assert chirality_hint_from_name("prop.stl") is None


def test_direction_from_geometry(tmp_path):
    # Synthetic oracle: stagger 60, camber > 0 designs omega +1 pumping -Z as built (chirality -1).
    d = prop_direction(_stl(tmp_path, stagger_deg=60.0, camber=0.06))
    assert (d.orientation, d.spin, d.chirality, d.source) == ("flipped", -1, -1, "geometry")
    d2 = prop_direction(_stl(tmp_path, stagger_deg=60.0, camber=-0.06))  # omega -1, pumps +Z
    assert (d2.orientation, d2.spin) == ("as_built", -1)


def test_label_disagreeing_with_geometry_raises(tmp_path):
    with pytest.raises(ValueError, match="chirality"):
        prop_direction(_stl(tmp_path, stagger_deg=60.0, camber=0.06), name_hint="x_cw.stl")


def test_inconclusive_geometry_raises(tmp_path):
    with pytest.raises(ValueError, match="INCONCLUSIVE"):
        prop_direction(_stl(tmp_path, stagger_deg=60.0, camber=0.0))
```

In `tests/test_prop_calibrate.py`:
- remove the tests of `preferred_spin_for_positive_thrust` and the flipping behaviour;
- keep and adapt the datasheet/affinity tests;
- if a test asserted `spin_flipped` or `spin_recommended`, replace it with the new `thrust_sign_ok` semantics.

- [ ] **Step 2: Run them and see them fail**

Run: `uv run pytest tests/audit/test_prop_thrust_sign.py tests/test_prop_calibrate.py -v`
Expected: FAIL on the imports of `fansim.propeller.direction`, and on the flipping behaviour.

- [ ] **Step 3: Implement**

`fansim/propeller/direction.py`:

```python
"""Prop rotation/orientation from the mesh-only proof (Audit #1), never from the thrust sign.

The open-air prop domain has freestream toward +Z. The prop's designed rotation must push air +Z,
so the CFD copy is oriented so that the proof's delivery is +Z, and spin is the designed rotation
in that frame. A CW/CCW filename label fixes only chirality (CCW = −1, the real-fan hand) and is
used as a cross-check.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import trimesh

from fansim.audit.direction import prove_direction


@dataclass(frozen=True)
class PropDirection:
    orientation: str
    spin: int
    source: str
    chirality: int | None
    note: str


def chirality_hint_from_name(name: str) -> int | None:
    upper = Path(name).stem.upper().replace("-", "_").replace(" ", "_")
    if re.search(r"(^|_)CCW(_|$)", upper):
        return -1
    if re.search(r"(^|_)CW(_|$)", upper):
        return 1
    return None


def prop_direction(stl_mm: Path, *, name_hint: str | None = None) -> PropDirection:
    proof = prove_direction(trimesh.load(str(stl_mm), force="mesh"))
    if proof.verdict != "CONCLUSIVE":
        raise ValueError(f"prop direction INCONCLUSIVE for {stl_mm}: {proof.note} — pass an explicit "
                         f"spin/orientation (direction='manual') after checking the part")
    hint = chirality_hint_from_name(name_hint) if name_hint else None
    if hint is not None and hint != proof.chirality:
        raise ValueError(f"{name_hint}: label implies chirality {hint:+d} but the geometry has "
                         f"{proof.chirality:+d} — mislabelled file or mirrored mesh")
    if proof.pump_sign == 1:
        orientation, spin = "as_built", int(proof.omega_sign)
    else:
        orientation, spin = "flipped", -int(proof.omega_sign)
    return PropDirection(orientation, spin, "geometry", proof.chirality, proof.note)
```

`fansim/propeller/calibrate.py`:
- Delete `preferred_spin_for_positive_thrust`.
- Rewrite `normalize_metrics_sign`:

```python
def normalize_metrics_sign(metrics: dict[str, Any], *, spin: int) -> dict[str, Any]:
    """Report thrust along the designed pumping direction; flag (never flip) a wrong sign.

    The prop is oriented so its designed rotation pushes air toward +Z (fansim.propeller.direction),
    so the fluid force on it is Fz < 0 and thrust = −Fz. A positive Fz means the prop pushed air the
    wrong way: that is reported, not hidden by flipping spin.
    """
    out = dict(metrics)
    raw = float(out.get("thrust_n", 0.0))
    out["thrust_n_raw"] = raw
    out["spin"] = int(spin)
    out["thrust_n"] = -raw
    out["thrust_g"] = -raw / 9.80665 * 1000.0
    out["thrust_sign_ok"] = raw < 0.0
    if raw >= 0.0:
        out["thrust_sign_error"] = (
            f"Fz={raw:+.4g} N pushes the prop toward -Z: air went the wrong way for spin {int(spin):+d}")
    return out
```

Update the module docstring's first paragraph to match; it currently describes picking the spin that yields +Fz.

`fansim/propeller/cfd.py` (the function with `spin: int = -1` and `stl_mm`), and the same pattern in `fansim/propeller/polar.py`:
- Add a parameter `direction: str = "auto"`, one of `"auto"` or `"manual"`.
- With `"auto"`, after the prop STL has been written to `stl` (all three branches: external, `build_prop`, `build_impeller`) and before the bounds are measured:

  ```python
  if direction == "auto":
      d = prop_direction(stl, name_hint=Path(stl_mm).name if external else None)
      if d.orientation == "flipped":
          orient_impeller_for_cfd(stl, stl, "flipped")
      spin_i = d.spin
      direction_source = d.source
  else:
      direction_source = "manual"
  ```

  Then re-measure the bounds (`watertight_report(stl).bounds_mm`), because the flip mirrors z. Record `out["direction_source"] = direction_source` and `out["orientation"]` in the result.
- `"manual"` keeps the caller's `spin` and orientation as-is. That is the explicit override for INCONCLUSIVE parts.
- Remove the docstring line "Default `spin=-1` matches ducted-fan MRF handedness (positive +z thrust)".

`scripts/evaluate_prop_cfd.py`: remove the use of `spin_hint_from_name` to choose spin. The label is now only a cross-check inside `prop_direction`. Add `--direction {auto,manual}` (default `auto`) and pass it through.

`fansim/propeller/stl_import.py`: keep `spin_hint_from_name` only if other code still uses it (check with `grep -rn spin_hint_from_name`). If nothing does, remove it and its export in `fansim/propeller/__init__.py`. Replace the `"spin_hint"` metadata at line ~138 with `"chirality_hint": chirality_hint_from_name(src.name)`.

`fansim/audit/registry.yaml`, unit `propeller.thrust_sign`:
- `targets`: `["fansim.propeller.calibrate:normalize_metrics_sign", "fansim.propeller.direction"]`
- `checks`: `[tests/audit/test_prop_thrust_sign.py]`

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/audit/test_prop_thrust_sign.py tests/test_prop_calibrate.py tests/test_prop_polar.py tests/test_prop_persist.py tests/test_prop_bemt_gate.py -q` and `uv run python scripts/evaluate_prop_cfd.py --help`
Expected: all pass, and the usage text prints.

Also check the drone STLs in `validation/reference/drone_radial/`, and record the results in the report:

```bash
uv run python -c "from pathlib import Path; from fansim.propeller.direction import prop_direction
for p in sorted(Path('validation/reference/drone_radial').glob('*.stl')):
    try: print(p.name, prop_direction(p, name_hint=p.name))
    except ValueError as e: print(p.name, 'ERROR', e)"
```

Radial impellers are expected to be INCONCLUSIVE. That is a correct refusal; `direction='manual'` remains for them.

- [ ] **Step 5: Commit**

```bash
git add fansim/propeller/ fansim/audit/registry.yaml scripts/evaluate_prop_cfd.py tests/
git commit -m "fix(prop): direction from geometry proof; report wrong thrust sign instead of flipping spin

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Docstrings and roadmap corrections

**Files:**
- Modify: `fansim/cfd/domain.py` (the module docstring and the `spin` / `flow_sign` comments), `fansim/cfd/openfoam_case.py` (the comment on `u_axial = float(rig.u_axial)`), `docs/roadmap.md` (§16.1 correction note), `fansim/optimize/objectives.py` (`_operating_point_reason` text mentioning "spin=-1")

- [ ] **Step 1: Make the edits**

- `domain.py`: the module docstring must say:
  - the duct flows +Z at `spin = −1`;
  - the as-built rotor pumps −Z in its designed rotation (CCW seen from +Z, i.e. ω_z = +1);
  - the CFD copy is flipped 180° about X by `fansim.cfd.orientation` (`AXIAL_CFD_ORIENTATION`), so `spin = −1` solves the designed rotation;
  - cite the Audit #1 report path.

  Replace the claim "Blade sections put the LE on the lower-Z side of the chord, so oncoming flow is +Z" and the `spin` field comment ("−1 pumps +Z with this blade handedness") with statements that are true of the **oriented** CFD copy.
- `openfoam_case.py`: the comment becomes `# +Z duct flow (inlet −Z → outlet +Z); rotor oriented by fansim.cfd.orientation`.
- `objectives.py` `_operating_point_reason`: the hint text "Re-Assess with current +Z duct (inlet −Z → outlet +Z, spin=-1)" becomes "reverse/zero flow usually means the rotor orientation or axial BC fought the blades (see fansim/cfd/orientation.py)".
- `docs/roadmap.md` §16.1: append, directly under the §16.1 item:
  `**Correction 2026-09-25 (Audit #1):** the text above describes commit a75da48, which was reverted by ea96f40. The motor cup is on −Z as built; the designed airflow is −Z as built; CFD orients the rotor via fansim/cfd/orientation.py.`

  Edit only that spot. Other sessions may have uncommitted roadmap edits: run `git diff docs/roadmap.md` first, and if it shows changes you didn't make, stage only your hunk (`git add -p` is not available; write the change, then use `git diff` to confirm only your line differs from HEAD before staging).

- [ ] **Step 2: Run the quick suite**

Run: `uv run pytest tests/test_cfd.py tests/test_objectives_reason.py tests/audit -q -m "not slow"`
Expected: all pass. A docstring-only change can still break `test_objectives_reason` if it matches on text; update that expectation in step with the new wording.

- [ ] **Step 3: Commit**

```bash
git add fansim/cfd/domain.py fansim/cfd/openfoam_case.py fansim/optimize/objectives.py docs/roadmap.md tests/test_objectives_reason.py
git commit -m "docs(cfd): state the as-built vs CFD orientation; correct roadmap §16.1

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Verification (lifts the freeze only if it passes)

This task is execution plus writing. The controller does it, with Docker. CFD runs go in the background.

**Files:**
- Update: `docs/validation/audits/direction_cfd_stock.json`, `direction_cfd_reference_stl.json` (script output)
- Create: `docs/validation/audits/2026-09-XX-audit-01b-direction-fix.md` (use the run date)
- Modify: `docs/validation/a12x25_pq_report.md`, `docs/validation/audits/ledger.json` (via `record_pass` only), `docs/roadmap.md` (freeze banner and §19.1 status), and the memory notes

- [ ] **Step 1: Full suite**

Run: `uv run pytest -q`, then `uv run pytest -q -m slow tests/audit tests/test_objectives_orientation.py`.
Expected: all pass. Restore any rewritten reference files.

- [ ] **Step 2: Geometry JSON is still current**

Run: `uv run python scripts/audit_direction_geometry.py`. Expected: both rotors (+1, −1, −1), and the STL hashes unchanged.

- [ ] **Step 3: CFD re-check (background; ~1 h each at 1500 iters, 8 procs each, both in parallel)**

Run:
- `uv run python scripts/audit_direction_cfd.py --rotor stock --procs 8 > runs/audit_direction_fix_stock.log 2>&1`
- `uv run python scripts/audit_direction_cfd.py --rotor reference_stl --procs 8 > runs/audit_direction_fix_ref.log 2>&1`

After each run has exited, run `--reverdict` for that rotor, then read `convention_verdict`.

**Stock must give `convention_verdict` PASS**, with production `{flipped, −1}` equal to the recommended run. The close-ref may be INCONCLUSIVE on margin (it was 10% before); report it as-is.

If Stock is INCONCLUSIVE because the mean shift is still ≥ 2%, re-run it once with `--iters 3000`. Do not loosen any threshold.

- [ ] **Step 4: Stock P–Q re-run**

Run in the background: `uv run python scripts/run_a12x25_validation.py --out runs/validate_a12x25_dirfix --procs 8`. Use the default `--backs` and tip gap 0.5 mm, the same as the 2026-09 Stock P–Q.

Then rewrite `docs/validation/a12x25_pq_report.md`:
- a new top section **"2026-09 direction fix (CFD_VERSION 3)"** with a table: back-pressure | CFM before (reversed) | CFM after | Noctua datasheet | Δ% after, plus the free-air and shut-off verdicts;
- earlier sections kept below a note saying they were solved with the reversed rotor.

State the gap honestly, whatever it is.

- [ ] **Step 5: Ledger and status**

Record PASS (via `record_pass`, as in the Audit #1 report task) for each unit whose checks pass: `cfd.flow_direction_convention` **only if** Stock `convention_verdict` is PASS; `cfd.cfm_from_outlet_flow`, `optimize.search_space_handedness` and `propeller.thrust_sign` if their tests pass. Then run `uv run python scripts/audit_status.py` and paste its output into the report.

- [ ] **Step 6: Report, roadmap and memory**

- Write `docs/validation/audits/<date>-audit-01b-direction-fix.md`: before/after matrix tables, the convention verdict, P–Q before/after, units recorded, and what was not checked.
- **Only if Stock's `convention_verdict` is PASS:** remove the ⛔ FREEZE banner from `docs/roadmap.md`, mark §19.1 `[x]` with the report link, and remove the "0. §19.1 Audit #1" line from the recommended sequence (or mark it done). Otherwise, leave the freeze and add a status line.
- Update the memory notes:
  - `fan-orientation-convention`: the fix landed; the CFD orientation lives in `fansim/cfd/orientation.py`.
  - `a12x25-recipe-fidelity-limit`: the new free-air gap.
  - `a12x25-cfd-convergence-fixes`: rule A and `oscillation_pct`.

- [ ] **Step 7: Commit**

Commit the report, the JSONs, the ledger, `a12x25_pq_report.md` and the roadmap (your hunks only). Hand the results to the user.
