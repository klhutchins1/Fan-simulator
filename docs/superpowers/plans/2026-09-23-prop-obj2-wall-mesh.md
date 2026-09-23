# obj_2 Wall-Resolved MRF Diagnostic Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run one compressible MRF solve on `obj_2` with a wall-based surface mesh and prism layers, and record thrust, power, figure of merit, and whether the STL is an axial rotor or a radial impeller.

**Architecture:** Pure helpers measure wall thickness, layout, and figure of merit. `evaluate_prop_cfd` gains an optional `mesh` argument and keeps today's mesh when that argument is omitted. A one-shot script prepares the STL, measures it, solves, and stamps only a finite result.

**Tech Stack:** Python 3.12 (`uv`), pytest, trimesh, `rtree` (required by trimesh ray queries), OpenFOAM v2406 Docker (`opencfd/openfoam-default:2406`).

**Spec:** `docs/superpowers/specs/2026-09-23-prop-obj2-wall-mesh-design.md`

## Global Constraints

- STL `validation/reference/drone_radial/obj_2_ccw.stl`. RPM **25257**. spin **−1**. `base_cell` **0.005** m. iters **400**. procs **8**.
- Solver `rhoSimpleFoam`. Regime `compressible-MRF`. Image `opencfd/openfoam-default:2406`.
- Prism layers on, `n_surface_layers` **3**. Surface level stays inside existing `SURF_LEVEL_MAX` (4). Do not edit `for_blade` or `surface_level_for_wall`.
- Wall thickness is `float(np.percentile(hits, 5))` after inward rays. Ignore hits closer than **0.05 mm**. Fewer than **20** hits raises `RuntimeError`. The absolute minimum does not pick the level.
- Layout is `axial` when `2 * tip_radius_mm / axial_extent_mm >= 2`, else `radial`. `faces_outward` is true when area-weighted mean `|n_r|` **>** mean `|n_z|` on faces with centroid radius **> 0.3** tip radius.
- Figure of merit uses `rho = P_INF * 28.9 / (8314.462618 * T_INF)` with `P_INF` and `T_INF` from `fansim.propeller.cfd`. Disk area `pi * R**2`.
- `evaluate_prop_cfd` without `mesh` still builds `MeshResolution(base_cell=base_cell)` (`surf_min` 1, `surf_max` 2, `add_layers` false).
- Do not edit `_compressibility_cl_cd`, the BEMT loop, AMI code, or the smoke, refine, and GCI fixtures.
- Stamp `validation/reference/drone_radial/cfd/obj_2_ccw_wall.json` only when thrust and shaft power are both finite. Workdir `runs/drone_radial_cfd/wall/obj_2` is not committed.
- `main` catches only `RuntimeError`, writes null thrust and power, exits **1**. Other exceptions propagate.
- CI unit tests do not run Docker. On Windows, pytest may exit `-1073741819` or `-1073740940` after a printed pass line. Treat the pass line as success.
- PowerShell: do not chain commands with `&&`. Do not stage `.superpowers/sdd/progress.md`, `catalog/catalog.db`, or `runs/`.
- Mark roadmap §4.4 step 2 done only after a finite stamp. A failed solve leaves step 2 open.

## File map

| File | Role |
|------|------|
| `fansim/propeller/wall_mesh.py` | thickness, layout, figure of merit, resolved flag, `for_blade` wrapper |
| `pyproject.toml`, `uv.lock` | add `rtree` |
| `fansim/propeller/cfd.py` | optional `mesh` argument |
| `scripts/run_prop_obj2_wall.py` | one-shot CLI |
| `tests/test_prop_wall_mesh.py` | unit tests, no Docker |
| `docs/validation/drone_radial_open_air_cfd.md` | wall-mesh section |
| `docs/roadmap.md` | step 2 text after the solve |
| `validation/reference/drone_radial/cfd/obj_2_ccw_wall.json` | stamp only if the solve is finite |
| `runs/drone_radial_cfd/wall/obj_2/` | local case, not committed |

---

### Task 1: Wall sample, figure of merit, resolved flag

**Files:**
- Create: `fansim/propeller/wall_mesh.py`
- Create: `tests/test_prop_wall_mesh.py`

**Interfaces:**
- Consumes: `P_INF`, `T_INF` from `fansim.propeller.cfd`. `MeshResolution.for_blade` from `fansim.cfd.openfoam_case`.
- Produces: `wall_sample(mesh) -> dict` with keys `min_wall_mm`, `abs_min_mm`, `n_hits`, `layout`, `mean_abs_nr`, `mean_abs_nz`, `faces_outward`. `min_wall_mm(mesh) -> float`. `figure_of_merit(thrust_n: float, power_w: float, tip_radius_m: float) -> float`. `wall_resolved(base_cell_m: float, surf_max: int, min_wall_mm: float) -> bool`. `mesh_for_wall(base_cell_m: float, min_wall_mm: float) -> MeshResolution`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_prop_wall_mesh.py`:

```python
"""Wall thickness, layout, and hover figure of merit for the obj_2 diagnostic."""

from __future__ import annotations

import pytest
import trimesh

from fansim.propeller.wall_mesh import (
    figure_of_merit,
    mesh_for_wall,
    min_wall_mm,
    wall_resolved,
    wall_sample,
)


def _slab():
    mesh = trimesh.creation.box(extents=(20.0, 20.0, 2.0))
    return mesh.subdivide()


def test_thin_slab_percentile_is_about_2mm():
    sample = wall_sample(_slab())
    assert sample["n_hits"] >= 20
    assert sample["min_wall_mm"] == pytest.approx(2.0, abs=0.15)
    assert sample["abs_min_mm"] <= sample["min_wall_mm"] + 1e-6
    assert min_wall_mm(_slab()) == pytest.approx(sample["min_wall_mm"], abs=1e-6)


def test_too_few_hits_raises():
    mesh = trimesh.creation.box(extents=(20.0, 20.0, 2.0))
    with pytest.raises(RuntimeError, match="20"):
        wall_sample(mesh)


def test_slab_is_axial_and_not_outward():
    sample = wall_sample(_slab())
    assert sample["layout"] == "axial"
    assert sample["faces_outward"] is False
    assert sample["mean_abs_nz"] > sample["mean_abs_nr"]


def test_tall_cylinder_is_radial_and_outward():
    mesh = trimesh.creation.cylinder(radius=5.0, height=30.0, sections=24)
    sample = wall_sample(mesh)
    assert sample["layout"] == "radial"
    assert sample["faces_outward"] is True
    assert sample["mean_abs_nr"] > sample["mean_abs_nz"]


def test_figure_of_merit_matches_smoke_density():
    fm = figure_of_merit(9.1980953, 2034.2277232229224, 45.38854474432168 / 1000.0)
    assert fm == pytest.approx(0.111245, rel=1e-4)


def test_figure_of_merit_zero_when_power_or_thrust_missing():
    assert figure_of_merit(0.0, 10.0, 0.05) == 0.0
    assert figure_of_merit(1.0, 0.0, 0.05) == 0.0


def test_wall_resolved_three_cell_rule():
    # 0.005 m / 2**4 = 0.3125 mm. Needs min wall >= 0.9375 mm.
    assert wall_resolved(0.005, 4, 1.0) is True
    assert wall_resolved(0.005, 4, 0.5) is False


def test_mesh_for_wall_enables_layers():
    mesh = mesh_for_wall(0.005, 2.0)
    assert mesh.base_cell == 0.005
    assert mesh.add_layers is True
    assert mesh.n_surface_layers == 3
    assert mesh.surf_max == 3
    assert mesh.surf_min == 2
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run python -m pytest tests/test_prop_wall_mesh.py -q --tb=line`

Expected: FAIL with `ModuleNotFoundError` for `fansim.propeller.wall_mesh`.

- [ ] **Step 3: Implement the helpers**

Create `fansim/propeller/wall_mesh.py`:

```python
"""STL wall thickness and hover figure of merit for one prop CFD diagnostic."""

from __future__ import annotations

import math

import numpy as np
import trimesh

from fansim.cfd.openfoam_case import MeshResolution
from fansim.propeller.cfd import P_INF, T_INF

MOL_WEIGHT = 28.9
R_UNIV = 8314.462618
HIT_MIN_MM = 0.05
MIN_HITS = 20


def rho_cfd() -> float:
    return P_INF * MOL_WEIGHT / (R_UNIV * T_INF)


def _thicknesses_mm(mesh: trimesh.Trimesh) -> np.ndarray:
    centers = np.asarray(mesh.triangles_center, dtype=float)
    normals = np.asarray(mesh.face_normals, dtype=float)
    inward = -normals
    origins = centers + inward * (HIT_MIN_MM * 0.4)
    locs, ray_idx, _tri = mesh.ray.intersects_location(
        ray_origins=origins,
        ray_directions=inward,
        multiple_hits=False,
    )
    if len(locs) == 0:
        return np.array([], dtype=float)
    dist = np.linalg.norm(locs - centers[ray_idx], axis=1)
    return dist[dist >= HIT_MIN_MM]


def wall_sample(mesh: trimesh.Trimesh) -> dict:
    """Percentile wall, axial/radial label, and outward-facing flag."""
    hits = _thicknesses_mm(mesh)
    if hits.size < MIN_HITS:
        raise RuntimeError(
            f"wall ray hits {int(hits.size)} < {MIN_HITS}"
        )
    xy = np.asarray(mesh.vertices[:, :2], dtype=float)
    tip = float(np.sqrt((xy * xy).sum(axis=1)).max())
    axial = float(mesh.bounds[1, 2] - mesh.bounds[0, 2])
    layout = "axial" if (2.0 * tip) / max(axial, 1e-9) >= 2.0 else "radial"

    centers = np.asarray(mesh.triangles_center, dtype=float)
    radius = np.sqrt(centers[:, 0] ** 2 + centers[:, 1] ** 2)
    mask = radius > 0.3 * tip
    if not np.any(mask):
        raise RuntimeError("no faces outside 0.3 tip radius")
    areas = np.asarray(mesh.area_faces, dtype=float)[mask]
    normals = np.asarray(mesh.face_normals, dtype=float)[mask]
    safe_r = np.maximum(radius[mask], 1e-9)
    nr = np.abs(
        normals[:, 0] * centers[mask, 0] / safe_r
        + normals[:, 1] * centers[mask, 1] / safe_r
    )
    nz = np.abs(normals[:, 2])
    weight = float(areas.sum())
    mean_nr = float(np.sum(areas * nr) / weight)
    mean_nz = float(np.sum(areas * nz) / weight)
    return {
        "min_wall_mm": float(np.percentile(hits, 5)),
        "abs_min_mm": float(hits.min()),
        "n_hits": int(hits.size),
        "layout": layout,
        "mean_abs_nr": mean_nr,
        "mean_abs_nz": mean_nz,
        "faces_outward": bool(mean_nr > mean_nz),
    }


def min_wall_mm(mesh: trimesh.Trimesh) -> float:
    return float(wall_sample(mesh)["min_wall_mm"])


def figure_of_merit(thrust_n: float, power_w: float, tip_radius_m: float) -> float:
    thrust = float(thrust_n)
    power = float(power_w)
    if thrust <= 0.0 or power <= 0.0:
        return 0.0
    area = math.pi * float(tip_radius_m) ** 2
    ideal = thrust ** 1.5 / math.sqrt(2.0 * rho_cfd() * area)
    return ideal / power


def wall_resolved(base_cell_m: float, surf_max: int, min_wall_mm: float) -> bool:
    finest_mm = float(base_cell_m) / (2.0 ** int(surf_max)) * 1000.0
    return finest_mm <= float(min_wall_mm) / 3.0


def mesh_for_wall(base_cell_m: float, min_wall_mm: float) -> MeshResolution:
    return MeshResolution.for_blade(
        float(base_cell_m), float(min_wall_mm), add_layers=True
    )
```

Distance is from the face centroid to the hit, not from the inset ray origin. Do not add another density constant.

`trimesh` ray queries import `rtree`. It is not in `pyproject.toml` today. Add it before the tests:

```powershell
uv add rtree
```

That updates `pyproject.toml` and `uv.lock`. Do not write a face-by-face intersector. `obj_2` has about 191000 faces.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run python -m pytest tests/test_prop_wall_mesh.py -q --tb=line`

Expected: PASS (`8 passed`). A Windows teardown code after that line is non-blocking.

- [ ] **Step 5: Commit**

```powershell
git add -- fansim/propeller/wall_mesh.py tests/test_prop_wall_mesh.py pyproject.toml uv.lock
git commit -m @"
feat(prop): measure STL wall thickness and hover figure of merit

"@
```

---

### Task 2: Optional mesh on `evaluate_prop_cfd`

**Files:**
- Modify: `fansim/propeller/cfd.py` (the `evaluate_prop_cfd` signature and the `build_prop_case` call)
- Modify: `tests/test_prop_wall_mesh.py`
- Test: `tests/test_prop_wall_mesh.py`

**Interfaces:**
- Consumes: `mesh_for_wall` from Task 1. Existing `evaluate_prop_cfd` in `fansim/propeller/cfd.py`.
- Produces: `evaluate_prop_cfd(..., mesh: MeshResolution | None = None)`. `None` keeps `MeshResolution(base_cell=base_cell)`. A passed mesh is the one `build_prop_case` uses, including that mesh's `base_cell`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_prop_wall_mesh.py`:

```python
def _fake_solve(work):
    fo = work / "postProcessing" / "forces" / "10"
    fo.mkdir(parents=True)
    (fo / "force.dat").write_text("#\n10  (0 0 2.0) (0 0 2) (0 0 0)\n", encoding="utf-8")
    (fo / "moment.dat").write_text("#\n10  (0 0 -0.1) (0 0 -0.1) (0 0 0)\n", encoding="utf-8")


def test_default_mesh_stays_coarse(tmp_path, monkeypatch):
    import trimesh

    from fansim.prop_spec import get_prop_spec
    from fansim.propeller import cfd as prop_cfd

    mesh = trimesh.creation.cylinder(radius=30.0, height=12.0, sections=32)
    src = tmp_path / "impeller.stl"
    mesh.export(str(src))
    work = tmp_path / "case"

    monkeypatch.setattr(prop_cfd, "run_mesh", lambda *_a, **_k: None)
    monkeypatch.setattr(prop_cfd, "run_solve_prop", lambda *_a, **_k: _fake_solve(work))
    import fansim.cfd.runner as runner_mod

    monkeypatch.setattr(
        runner_mod,
        "OpenFOAMRunner",
        lambda workdir: type("R", (), {"run": staticmethod(lambda *a, **k: None)})(),
    )
    prop_cfd.evaluate_prop_cfd(
        get_prop_spec("cine_3inch"),
        work,
        rpm=20000.0,
        base_cell=0.005,
        stl_mm=src,
        prepare_stl=False,
    )
    text = (work / "system" / "snappyHexMeshDict").read_text(encoding="utf-8")
    assert "addLayers       false;" in text
    assert "level (1 2);" in text


def test_passed_mesh_writes_layers(tmp_path, monkeypatch):
    import trimesh

    from fansim.prop_spec import get_prop_spec
    from fansim.propeller import cfd as prop_cfd
    from fansim.propeller.wall_mesh import mesh_for_wall

    mesh = trimesh.creation.cylinder(radius=30.0, height=12.0, sections=32)
    src = tmp_path / "impeller.stl"
    mesh.export(str(src))
    work = tmp_path / "layered"
    monkeypatch.setattr(prop_cfd, "run_mesh", lambda *_a, **_k: None)
    monkeypatch.setattr(prop_cfd, "run_solve_prop", lambda *_a, **_k: _fake_solve(work))
    import fansim.cfd.runner as runner_mod

    monkeypatch.setattr(
        runner_mod,
        "OpenFOAMRunner",
        lambda workdir: type("R", (), {"run": staticmethod(lambda *a, **k: None)})(),
    )
    prop_cfd.evaluate_prop_cfd(
        get_prop_spec("cine_3inch"),
        work,
        rpm=20000.0,
        stl_mm=src,
        prepare_stl=False,
        mesh=mesh_for_wall(0.005, 2.0),
    )
    text = (work / "system" / "snappyHexMeshDict").read_text(encoding="utf-8")
    assert "addLayers       true;" in text
    assert "nSurfaceLayers 3;" in text
    assert "level (2 3);" in text
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `uv run python -m pytest tests/test_prop_wall_mesh.py::test_default_mesh_stays_coarse tests/test_prop_wall_mesh.py::test_passed_mesh_writes_layers -q --tb=line`

Expected: FAIL. The passed-mesh test fails because `evaluate_prop_cfd` does not accept `mesh` yet, or the snappy dict still says `addLayers       false`.

- [ ] **Step 3: Add the argument**

In `evaluate_prop_cfd`, add a keyword-only argument `mesh: MeshResolution | None = None` next to `base_cell`. Replace the `build_prop_case` mesh line with:

```python
    mesh_used = mesh if mesh is not None else MeshResolution(base_cell=float(base_cell))
    build_prop_case(
        workdir,
        stl,
        dom,
        mesh=mesh_used,
        n_iters=int(iters),
        n_subdomains=int(procs),
    )
```

Do not change the solver, the thermo constants, or the default when `mesh` is omitted.

- [ ] **Step 4: Run the wall-mesh tests**

Run: `uv run python -m pytest tests/test_prop_wall_mesh.py tests/test_prop_stl_import.py tests/test_prop_cfd.py -q --tb=line`

Expected: PASS. The existing external-STL test still returns a finite result with no Docker.

- [ ] **Step 5: Commit**

```powershell
git add -- fansim/propeller/cfd.py tests/test_prop_wall_mesh.py
git commit -m @"
feat(prop): let a prop CFD evaluate use a caller-supplied mesh

"@
```

---

### Task 3: obj_2 wall CLI, stamp rule, no Docker

**Files:**
- Create: `scripts/run_prop_obj2_wall.py`
- Modify: `tests/test_prop_wall_mesh.py`
- Test: `tests/test_prop_wall_mesh.py`

**Interfaces:**
- Consumes: `wall_sample`, `figure_of_merit`, `wall_resolved`, `mesh_for_wall` from Task 1. `evaluate_prop_cfd(..., mesh=...)` from Task 2. `prepare_prop_stl` and `measure_prop_stl` from `fansim.propeller.stl_import`.
- Produces: `scripts/run_prop_obj2_wall.py` with `main() -> int`. Defaults: the locked STL, RPM 25257, spin -1, base_cell 0.005, iters 400, procs 8, out `runs/drone_radial_cfd/wall/obj_2`. `STAMP` points at `validation/reference/drone_radial/cfd/obj_2_ccw_wall.json`.

- [ ] **Step 1: Write the failing CLI tests**

Append to `tests/test_prop_wall_mesh.py`:

```python
def test_cli_defaults():
    from scripts.run_prop_obj2_wall import build_parser

    args = build_parser().parse_args([])
    assert args.stl.name == "obj_2_ccw.stl"
    assert args.rpm == 25257.0
    assert args.spin == -1
    assert args.base_cell == 0.005
    assert args.iters == 400
    assert args.procs == 8


def test_cli_runtime_error_writes_null_and_skips_stamp(tmp_path, monkeypatch):
    import scripts.run_prop_obj2_wall as wall_cli

    stamp = tmp_path / "obj_2_ccw_wall.json"
    monkeypatch.setattr(wall_cli, "STAMP", stamp)
    monkeypatch.setattr(
        wall_cli, "run_case", lambda **_k: (_ for _ in ()).throw(RuntimeError("solve failed"))
    )
    out = tmp_path / "run"
    code = wall_cli.main(["--out", str(out)])
    assert code == 1
    payload = json.loads((out / "result.json").read_text(encoding="utf-8"))
    assert payload["thrust_g"] is None
    assert payload["shaft_power_w"] is None
    assert not stamp.exists()


def test_cli_finite_result_stamps(tmp_path, monkeypatch):
    import scripts.run_prop_obj2_wall as wall_cli

    stamp = tmp_path / "obj_2_ccw_wall.json"
    monkeypatch.setattr(wall_cli, "STAMP", stamp)

    def fake_run_case(**_k):
        return {
            "thrust_n": 9.2,
            "thrust_g": 938.0,
            "shaft_power_w": 2034.0,
            "torque_nm": 0.77,
            "figure_of_merit": 0.11,
            "layout": "axial",
            "faces_outward": False,
            "wall_resolved": False,
            "min_wall_mm": 0.4,
        }

    monkeypatch.setattr(wall_cli, "run_case", fake_run_case)
    out = tmp_path / "run"
    code = wall_cli.main(["--out", str(out), "--stl", str(tmp_path / "missing.stl")])
    assert code == 0
    assert stamp.is_file()
    payload = json.loads(stamp.read_text(encoding="utf-8"))
    assert payload["thrust_g"] == pytest.approx(938.0)
    assert payload["shaft_power_w"] == pytest.approx(2034.0)
```

Add `import json` at the top of the test file if it is not already there.

The finite-result test passes a missing `--stl` on purpose: `main` must not touch the STL when `run_case` is monkeypatched. `run_case` is what loads the STL.

- [ ] **Step 2: Run the CLI tests to verify they fail**

Run: `uv run python -m pytest tests/test_prop_wall_mesh.py::test_cli_defaults tests/test_prop_wall_mesh.py::test_cli_runtime_error_writes_null_and_skips_stamp tests/test_prop_wall_mesh.py::test_cli_finite_result_stamps -q --tb=line`

Expected: FAIL with import error for `scripts.run_prop_obj2_wall`.

- [ ] **Step 3: Write the CLI**

Create `scripts/run_prop_obj2_wall.py`:

```python
"""One obj_2 compressible MRF solve with a wall-resolved mesh and prism layers."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import trimesh

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from fansim.prop_spec import get_prop_spec  # noqa: E402
from fansim.propeller.cfd import evaluate_prop_cfd  # noqa: E402
from fansim.propeller.stl_import import measure_prop_stl, prepare_prop_stl  # noqa: E402
from fansim.propeller.wall_mesh import (  # noqa: E402
    figure_of_merit,
    mesh_for_wall,
    wall_resolved,
    wall_sample,
)

STL = PROJECT / "validation/reference/drone_radial/obj_2_ccw.stl"
SMOKE = PROJECT / "validation/reference/drone_radial/cfd/obj_2_ccw_smoke.json"
STAMP = PROJECT / "validation/reference/drone_radial/cfd/obj_2_ccw_wall.json"
DEFAULT_OUT = PROJECT / "runs/drone_radial_cfd/wall/obj_2"


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="obj_2 wall-resolved compressible MRF diagnostic")
    ap.add_argument("--stl", type=Path, default=STL)
    ap.add_argument("--rpm", type=float, default=25257.0)
    ap.add_argument("--spin", type=int, default=-1, choices=(-1, 1))
    ap.add_argument("--base-cell", type=float, default=0.005, dest="base_cell")
    ap.add_argument("--iters", type=int, default=400)
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return ap


def _layout_note(sample: dict) -> str:
    note = f"layout={sample['layout']}"
    if sample["faces_outward"]:
        note += "; outer surfaces face outward"
    return note


def run_case(*, stl: Path, rpm: float, spin: int, base_cell: float, iters: int, procs: int, out: Path) -> dict:
    if not stl.is_file():
        raise RuntimeError(f"prop STL not found: {stl}")
    out.mkdir(parents=True, exist_ok=True)
    prepared = out / "prop.stl"
    prepare_prop_stl(stl, prepared)
    mesh_tm = trimesh.load(str(prepared), force="mesh")
    sample = wall_sample(mesh_tm)
    metrics = measure_prop_stl(prepared)
    resolution = mesh_for_wall(base_cell, sample["min_wall_mm"])
    solved = evaluate_prop_cfd(
        get_prop_spec("fpv_5inch"),
        out,
        rpm=rpm,
        iters=iters,
        procs=procs,
        base_cell=base_cell,
        spin=spin,
        stl_mm=prepared,
        prepare_stl=False,
        mesh=resolution,
        spec_key="obj_2_ccw",
    )
    thrust_n = float(solved["thrust_n"])
    power_w = float(solved["shaft_power_w"])
    tip_m = float(metrics.tip_radius_m)
    smoke = json.loads(SMOKE.read_text(encoding="utf-8"))
    smoke_r = float(smoke["tip_radius_mm"]) / 1000.0
    solved.update(
        {
            "min_wall_mm": sample["min_wall_mm"],
            "abs_min_mm": sample["abs_min_mm"],
            "n_hits": sample["n_hits"],
            "layout": sample["layout"],
            "mean_abs_nr": sample["mean_abs_nr"],
            "mean_abs_nz": sample["mean_abs_nz"],
            "faces_outward": sample["faces_outward"],
            "layout_note": _layout_note(sample),
            "surf_min": resolution.surf_min,
            "surf_max": resolution.surf_max,
            "add_layers": resolution.add_layers,
            "n_surface_layers": resolution.n_surface_layers,
            "wall_resolved": wall_resolved(resolution.base_cell, resolution.surf_max, sample["min_wall_mm"]),
            "figure_of_merit": figure_of_merit(thrust_n, power_w, tip_m),
            "smoke_thrust_g": smoke["metrics"]["thrust_g"],
            "smoke_shaft_power_w": smoke["metrics"]["shaft_power_w"],
            "smoke_figure_of_merit": figure_of_merit(
                smoke["metrics"]["thrust_n"], smoke["metrics"]["shaft_power_w"], smoke_r
            ),
            "stl": str(stl),
        }
    )
    return solved


def _null_payload(message: str) -> dict:
    return {"thrust_g": None, "shaft_power_w": None, "error": message, "band_pass": None}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    try:
        payload = run_case(
            stl=args.stl,
            rpm=float(args.rpm),
            spin=int(args.spin),
            base_cell=float(args.base_cell),
            iters=int(args.iters),
            procs=int(args.procs),
            out=args.out,
        )
    except RuntimeError as exc:
        payload = _null_payload(str(exc))
        (args.out / "result.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(payload, indent=2))
        return 1
    (args.out / "result.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    thrust = payload.get("thrust_g")
    power = payload.get("shaft_power_w")
    if thrust is not None and power is not None and thrust == thrust and power == power:
        STAMP.parent.mkdir(parents=True, exist_ok=True)
        STAMP.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

`thrust == thrust` rejects NaN. Do not catch `Exception`. Do not write `STAMP` on the null path. `fpv_5inch` is only the required spec object for the external-STL path; `spec_key` is `obj_2_ccw`. BEMT is not called for an external STL.

- [ ] **Step 4: Run the wall-mesh tests**

Run: `uv run python -m pytest tests/test_prop_wall_mesh.py -q --tb=line`

Expected: PASS. Count is the Task 1 and Task 2 tests plus these three.

- [ ] **Step 5: Commit**

```powershell
git add -- scripts/run_prop_obj2_wall.py tests/test_prop_wall_mesh.py
git commit -m @"
feat(prop): add the obj_2 wall-resolved MRF diagnostic CLI

"@
```

---

### Task 4: Docker solve and docs

**Files:**
- Modify: `docs/validation/drone_radial_open_air_cfd.md` (append a section)
- Modify: `docs/roadmap.md` (§4.4 item 2 only)
- Create, only if the solve is finite: `validation/reference/drone_radial/cfd/obj_2_ccw_wall.json`
- Test: none new. The solve is the Docker run. Do not commit `runs/`.

**Interfaces:**
- Consumes: `scripts/run_prop_obj2_wall.py` from Task 3.
- Produces: a validation section and a roadmap sentence that match `runs/drone_radial_cfd/wall/obj_2/result.json`.

- [ ] **Step 1: Run the diagnostic**

Run: `uv run python scripts/run_prop_obj2_wall.py`

This meshes and solves. Expect several minutes. Read `runs/drone_radial_cfd/wall/obj_2/result.json` when it exits.

- [ ] **Step 2: Write the validation section from that JSON**

Append this section to `docs/validation/drone_radial_open_air_cfd.md`. Fill the brace fields from `result.json`. Do not invent a thrust or power the file does not contain. Do not edit the smoke, refine, or GCI sections.

If `thrust_g` and `shaft_power_w` are finite:

```markdown
## Wall mesh (obj_2)

**Status:** recorded {date}.

**Case:** `obj_2_ccw.stl` · RPM 25257 · `base_cell` 0.005 · `MeshResolution.for_blade` · prism layers 3 · `rhoSimpleFoam`.

**Stamp:** `validation/reference/drone_radial/cfd/obj_2_ccw_wall.json`.

| | thrust_g | shaft_power_w | figure_of_merit | min_wall_mm | surf_max | wall_resolved | layout |
|---|---:|---:|---:|---:|---:|---|---|
| wall mesh | {thrust_g} | {shaft_power_w} | {figure_of_merit} | {min_wall_mm} | {surf_max} | {wall_resolved} | {layout} |
| smoke fixture | {smoke_thrust_g} | {smoke_shaft_power_w} | {smoke_figure_of_merit} |  |  |  |  |

{layout_note}. This is not a pass band. BEMT Prandtl-Glauert also raises lift past stall, so this CFD result is not a BEMT comparison.
```

If either value is null:

```markdown
## Wall mesh (obj_2)

**Status:** attempted {date} — unstamped (`thrust_g` null or `shaft_power_w` null).

**Stamp:** none. `validation/reference/drone_radial/cfd/obj_2_ccw_wall.json` was not written.

No stamp file was written. BEMT Prandtl-Glauert also raises lift past stall, so this CFD result is not a BEMT comparison.
```

Confirm the stamp file exists only in the finite case, and that `obj_2_ccw_smoke.json`, `obj_2_ccw_refine.json`, and `obj_2_ccw_gci.json` are unchanged (`git diff` on those paths is empty).

- [ ] **Step 3: Update roadmap step 2**

If the stamp is finite, replace the §4.4 item that begins `2. One obj_2 diagnostic solve` with:

```markdown
  2. **Done.** obj_2 wall mesh (`for_blade`, prism layers) is stamped at
     `validation/reference/drone_radial/cfd/obj_2_ccw_wall.json`: {thrust_g} g,
     {shaft_power_w} W, figure of merit {figure_of_merit}, layout {layout},
     wall_resolved {wall_resolved}. Spec/plan:
     `docs/superpowers/specs/2026-09-23-prop-obj2-wall-mesh-design.md`,
     `docs/superpowers/plans/2026-09-23-prop-obj2-wall-mesh.md`.
```

If the solve failed, leave item 2's original wording and add one sentence after it: `Attempted {date}: solve failed, no stamp.`

Leave item 3 and the unchecked `- [ ] **4.4` line unchanged in either case.

- [ ] **Step 4: Commit docs and the stamp if it exists**

Finite:

```powershell
git add -- docs/validation/drone_radial_open_air_cfd.md docs/roadmap.md validation/reference/drone_radial/cfd/obj_2_ccw_wall.json
git commit -m @"
docs(prop): record the obj_2 wall-resolved MRF diagnostic

"@
```

Failed (no stamp file):

```powershell
git add -- docs/validation/drone_radial_open_air_cfd.md docs/roadmap.md
git commit -m @"
docs(prop): record the obj_2 wall-mesh attempt

"@
```

Do not stage `runs/`.
