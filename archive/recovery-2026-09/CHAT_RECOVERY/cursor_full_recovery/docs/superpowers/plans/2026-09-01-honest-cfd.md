# Honest Optimizer CFD (Tip Gap + Frame Struts) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every optimizer trial meshes a 0.5 mm tip gap and four stationary exhaust struts, while validation scripts that call `rig_for_impeller` without a frame stay at 1 mm gap and impeller-only.

**Architecture:** CadQuery builds a fused four-bar `frame.stl` sitting **after** the MRF axial band. `build_case` optionally copies it into snappy as a no-slip wall (not in `forces`, listed in `nonRotatingPatches`). `evaluate_candidate` always passes the frame and `tip_gap_mm=0.5`. Square duct and two load points stay.

**Tech Stack:** Python 3.12 via uv, CadQuery, OpenFOAM dictionary templates, pytest. No Docker tests in this slice.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-01-honest-cfd-design.md`
- Python `>=3.12,<3.13` via `uv`; tests: `uv run python -m pytest -q -m "not docker and not slow"`
- Optimizer tip gap is **0.5 mm**; `--tip-gap` overrides; `rig_for_impeller` default stays **1.0 mm**
- Four rectangular bars, 90° apart: thickness **2.4 mm**, axial depth **8 mm**, inner radius `hub_radius`, outer radius `duct_radius_mm − 0.1`
- Z start = `mrf_z_max` (metres) converted to mm **+ 0.5 mm** — after the MRF band, not `impeller_z_max + 1 mm`
- `frame_stl_mm=None` keeps today’s impeller-only case
- Frame is stationary (no-slip); do **not** add `frame` to the `forces` patches (shaft torque stays impeller-only)
- Square screening duct; no system curve; no circular AMCA rig; no Docker/CFD campaign
- Frame build failure → infeasible `frame failed:` (do not silently drop struts)
- Windows: CadQuery teardown exit 3221226356 / -1073741819 is not a test failure — judge by assertion output
- No `★` in CLI help
- Commit after each task; do not `git push`

---

## File structure

| Path | Responsibility |
|---|---|
| `fansim/cfd/frame.py` | `STRUT_*` constants, `build_frame_solid`, `export_frame_stl` |
| `tests/test_frame.py` | Geometry: one body, z after MRF, four-bar volume |
| `fansim/cfd/templates.py` | Optional `frame.stl` in snappy/features; `frame` BCs via `@FRAME_*@` |
| `fansim/cfd/openfoam_case.py` | `build_case(..., frame_stl_mm=None)` copies STL + fills placeholders |
| `tests/test_cfd.py` | Snappy/0/U contain `frame` iff a frame STL was passed |
| `fansim/cfd/domain.py` | `OPTIMIZER_TIP_GAP_MM = 0.5` |
| `fansim/optimize/objectives.py` | Pass 0.5 mm gap + frame STL into `rig_for_impeller` / `build_case` |
| `fansim/optimize/study.py` | `tip_gap_mm` through to `evaluate_candidate` |
| `scripts/run_optimization.py` | `--tip-gap` |
| `docs/roadmap.md` + spec | §1.1 stage 1 done; status accepted |

---

### Task 1: Frame solid

**Files:**
- Create: `fansim/cfd/frame.py`
- Test: `tests/test_frame.py`

**Interfaces:**
- Consumes: `BladeParams`, `TestRig` (`duct_radius`, `mrf_z_max` in metres), `MM_TO_M`
- Produces:
  - `STRUT_THICK_MM = 2.4`, `STRUT_DEPTH_MM = 8.0`, `STRUT_WALL_INSET_MM = 0.1`, `STRUT_AFTER_MRF_MM = 0.5`
  - `build_frame_solid(params, rig) -> cq.Solid` (mm)
  - `export_frame_stl(params, rig, path) -> Path` using `fansim.geometry.export.export_stl`

Z start mm = `rig.mrf_z_max / MM_TO_M + STRUT_AFTER_MRF_MM`.
Outer radius mm = `rig.duct_radius / MM_TO_M - STRUT_WALL_INSET_MM`.
Four bars fused into **one** solid.

Build each bar as a box along +X from `hub_radius` to outer r, thickness 2.4 in Y, depth 8 in Z, centered at z_start + 4 mm, then `rotate` about Z by 0/90/180/270, then `fuse`.

- [ ] **Step 1: Write the failing tests**

```python
from fansim.cfd.domain import MM_TO_M, rig_for_impeller
from fansim.cfd.frame import STRUT_AFTER_MRF_MM, STRUT_DEPTH_MM, build_frame_solid
from fansim.geometry.blade import BladeParams


def test_frame_is_one_solid_after_mrf():
    params = BladeParams()
    rig = rig_for_impeller(params, tip_gap_mm=0.5)
    solid = build_frame_solid(params, rig)
    bb = solid.BoundingBox()
    assert bb.zmin >= rig.mrf_z_max / MM_TO_M + STRUT_AFTER_MRF_MM - 0.05
    assert bb.zmax <= bb.zmin + STRUT_DEPTH_MM + 0.2
    # fused
    assert solid.Volume() > 4 * 100.0  # four chunky bars, not a speck


def test_frame_does_not_start_inside_mrf():
    params = BladeParams()
    rig = rig_for_impeller(params, tip_gap_mm=0.5)
    bb = build_frame_solid(params, rig).BoundingBox()
    assert bb.zmin > rig.mrf_z_max / MM_TO_M
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_frame.py -q --tb=short`

Expected: import fail (no `fansim.cfd.frame`).

- [ ] **Step 3: Implement `fansim/cfd/frame.py`**

Use CadQuery `Workplane("XY").box(...)` / `.rotate((0,0,0),(0,0,1), ang)` / `.val().fuse`. If fuse fails, still return the first bar and raise — do not silently export four loose bodies unless the test is changed; the spec wants **one fused solid**.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_frame.py -q --tb=short`

Expected: PASS (ignore CadQuery teardown exit).

- [ ] **Step 5: Commit**

```bash
git add fansim/cfd/frame.py tests/test_frame.py
git commit -m "Add a four-bar stationary exhaust frame solid"
```

---

### Task 2: Optional frame in the OpenFOAM case

**Files:**
- Modify: `fansim/cfd/templates.py` (`SNAPPY`, `SURFACE_FEATURES`, `MRF_PROPERTIES`, all `0/` field templates that name `impeller`)
- Modify: `fansim/cfd/openfoam_case.py` (`build_case`)
- Test: `tests/test_cfd.py`

**Interfaces:**
- Consumes: `frame_stl_mm: str | Path | None = None`
- Produces: when a path is passed, `constant/triSurface/frame.stl` exists (scaled mm→m like the impeller) and dictionaries mention `frame`; when `None`, no `frame.stl` and no `frame` patch in `0/U`

Placeholders (empty string when no frame):

```
@FRAME_GEOM@      # inside geometry { } : `frame.stl { type triSurfaceMesh; name frame; }`
@FRAME_FEAT@      # inside features ( ) : `{ file "frame.eMesh"; level @FEATLVL@; }`
@FRAME_SURF@      # inside refinementSurfaces : `frame { level (@SURFMIN@ @SURFMAX@); patchInfo { type wall; } }`
@FRAME_EXTRACT@   # extra SURFACE_FEATURES block for frame.stl
@FRAME_PATCH@     # ` frame` appended inside nonRotatingPatches ( ... )
@FRAME_U@         # `    frame { type noSlip; }\n`  (and analogous for p/k/omega/nut)
```

`forces` patches stay `(impeller)` only.

Copy+scale the frame STL the same way as the impeller (`trimesh.load` → metres → `constant/triSurface/frame.stl`).

`test_case_build_files` is `@pytest.mark.docker` — **do not rely on it**. Add non-docker tests that call `build_case` with a tiny dummy STL pair (a one-triangle mesh is enough if snappy isn't run). `build_case` already writes dictionaries without Docker.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_cfd.py`:

```python
def _tiny_stl(path: Path):
    import numpy as np
    import trimesh
    m = trimesh.Trimesh(
        vertices=np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=float),
        faces=np.array([[0, 1, 2]], dtype=int), process=False)
    m.export(str(path))
    return path


def test_build_case_without_frame_has_no_frame_patch(tmp_path):
    from fansim.cfd.openfoam_case import MeshResolution, build_case
    stl = _tiny_stl(tmp_path / "imp.stl")
    rig = rig_for_impeller(BladeParams(), tip_gap_mm=1.0)
    case = build_case(tmp_path / "c0", stl, rig, mesh=MeshResolution(), n_iters=10)
    u = (case / "0/U").read_text(encoding="utf-8")
    snap = (case / "system/snappyHexMeshDict").read_text(encoding="utf-8")
    assert "frame.stl" not in snap
    assert "frame {" not in u
    assert not (case / "constant/triSurface/frame.stl").exists()


def test_build_case_with_frame_wires_snappy_and_walls(tmp_path):
    from fansim.cfd.openfoam_case import MeshResolution, build_case
    stl = _tiny_stl(tmp_path / "imp.stl")
    fr = _tiny_stl(tmp_path / "frame.stl")
    rig = rig_for_impeller(BladeParams(), tip_gap_mm=0.5)
    case = build_case(tmp_path / "c1", stl, rig, mesh=MeshResolution(), n_iters=10,
                      frame_stl_mm=fr)
    snap = (case / "system/snappyHexMeshDict").read_text(encoding="utf-8")
    u = (case / "0/U").read_text(encoding="utf-8")
    mrf = (case / "constant/MRFProperties").read_text(encoding="utf-8")
    feat = (case / "system/surfaceFeatureExtractDict").read_text(encoding="utf-8")
    assert "frame.stl" in snap and "name frame" in snap
    assert "frame.eMesh" in snap or "frame.eMesh" in feat
    assert "frame {" in u
    assert "frame" in mrf
    assert (case / "constant/triSurface/frame.stl").exists()
    forces = (case / "system/controlDict").read_text(encoding="utf-8")
    assert "patches         (impeller);" in forces  # shaft torque: rotor only
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_cfd.py::test_build_case_with_frame_wires_snappy_and_walls -q --tb=short`

Expected: FAIL (`frame_stl_mm` unexpected / no frame in dict).

- [ ] **Step 3: Implement templates + `build_case`**

Every `0/` template that has `impeller {` needs `@FRAME_U@` (use distinct names `@FRAME_U@` `@FRAME_P@` `@FRAME_K@` `@FRAME_OMEGA@` `@FRAME_NUT@` **or** one `@FRAME_WALL@` only if the BC text is identical — it is not: U is noSlip, p is zeroGradient, k/omega wall functions, nut nutkWallFunction). Pass the right snippet from `build_case`.

When `frame_stl_mm is None`, every `@FRAME_*@` is `""`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_cfd.py -q --tb=short -m "not docker"`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add fansim/cfd/templates.py fansim/cfd/openfoam_case.py tests/test_cfd.py
git commit -m "Snap a stationary frame STL into the OpenFOAM case"
```

---

### Task 3: Optimizer 0.5 mm gap + frame on every trial

**Files:**
- Modify: `fansim/cfd/domain.py` (add `OPTIMIZER_TIP_GAP_MM = 0.5` only; do **not** change `rig_for_impeller` default 1.0)
- Modify: `fansim/optimize/objectives.py`
- Modify: `fansim/optimize/study.py`
- Modify: `scripts/run_optimization.py`
- Test: `tests/test_optimize.py` and/or `tests/test_frame.py`

**Interfaces:**
- `evaluate_candidate(..., tip_gap_mm: float | None = None)`
  - `None` → `OPTIMIZER_TIP_GAP_MM` (0.5)
  - `rig_for_impeller(..., tip_gap_mm=tip_gap_mm)`
  - After impeller STL: `export_frame_stl(params, rig0, workdir / "frame.stl")` inside try/except → `_infeasible(f"frame failed: ...")`
  - `build_case(..., frame_stl_mm=frame_path)` for **both** the mesh-once call and `solve_at` rebuilds
- `run_study(..., tip_gap_mm: float = 0.5)` passes through
- CLI: `--tip-gap` type=float default=0.5, help without `★`

Cheap tests (no CFD):

```python
def test_optimizer_tip_gap_constant_is_half_mm():
    from fansim.cfd.domain import OPTIMIZER_TIP_GAP_MM
    assert OPTIMIZER_TIP_GAP_MM == 0.5


def test_run_optimization_declares_tip_gap_flag():
    from pathlib import Path
    text = Path("scripts/run_optimization.py").read_text(encoding="utf-8")
    assert "--tip-gap" in text
    assert "★" not in text


def test_evaluate_candidate_writes_frame_before_geometry_fail_is_not_required():
    """Unprintable still fails printability first; printable baseline should write frame.stl
    if we stop before Docker. Use bem_prescreen_cfm=500 so we never reach CFD, but AFTER
    printability — currently BEM prescreen is after printability and BEFORE geometry.
    So this cannot see frame.stl.

    Instead: export_frame_stl on BladeParams()+rig_for_impeller(..., 0.5) writes a file.
    """
    from fansim.cfd.domain import rig_for_impeller
    from fansim.cfd.frame import export_frame_stl
    from fansim.geometry.blade import BladeParams
    p = BladeParams()
    rig = rig_for_impeller(p, tip_gap_mm=0.5)
    out = tmp_path / "frame.stl"
    export_frame_stl(p, rig, out)
    assert out.exists() and out.stat().st_size > 1000
```

(Put the last test in `tests/test_frame.py` with `tmp_path`.)

Inspect `evaluate_candidate` after edits: both `build_case` calls must include `frame_stl_mm`.

- [ ] **Step 1: Write the failing tests**
- [ ] **Step 2: Run them — expect FAIL**
- [ ] **Step 3: Implement**
- [ ] **Step 4: `uv run python -m pytest tests/test_frame.py tests/test_optimize.py tests/test_cfd.py -q --tb=short -m "not docker"`** — PASS
- [ ] **Step 5: Commit**

```bash
git add fansim/cfd/domain.py fansim/cfd/frame.py fansim/optimize/objectives.py fansim/optimize/study.py scripts/run_optimization.py tests/test_frame.py tests/test_optimize.py
git commit -m "Mesh optimizer trials with a 0.5 mm gap and exhaust struts"
```

---

### Task 4: Spec accepted + roadmap

**Files:**
- `docs/superpowers/specs/2026-09-01-honest-cfd-design.md` — `Status: accepted`
- `docs/roadmap.md` — mark §1.1 stage 1 done; leave §1.2 open; recommended sequence next is §1.2 or §7.5

Suggested §1.1 replacement:

```markdown
- [x] **1.1 Tip clearance + frame struts in the optimizer CFD (stage 1). DONE 2026-09-01**
  Optimizer uses **0.5 mm** tip gap (`--tip-gap`) and a four-bar stationary `frame.stl`
  downstream of the MRF zone. Square duct and two load points unchanged. Remaining:
  system curve (§1.2), circular AMCA rig, designed shroud-to-frame gap (§7.5).
```

- [ ] **Step 1: Edit the two docs**
- [ ] **Step 2: Run** `uv run python -m pytest tests/test_frame.py tests/test_cfd.py tests/test_optimize.py tests/test_shroud.py -q --tb=short -m "not docker"`
- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/specs/2026-09-01-honest-cfd-design.md docs/roadmap.md
git commit -m "Accept the honest-CFD spec and mark roadmap 1.1 stage 1 done"
```

---

## Self-review

1. Spec coverage: 0.5 mm optimizer gap, 1.0 mm rig default, four bars, Z after MRF, 0.1 mm inset, optional frame, no-slip frame, forces impeller-only, infeasible on frame fail, no Docker campaign, no system curve.
2. Placeholders: none.
3. Names: `OPTIMIZER_TIP_GAP_MM`, `build_frame_solid`, `export_frame_stl`, `frame_stl_mm`, `--tip-gap` consistent.
