# Prop Open-Air AMI Smoke Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run one compressible sliding-mesh smoke on `obj_2` and record whether the two-revolution mean thrust sits inside the obj_2 MRF band.

**Architecture:** Pure helpers compute the last-revolution mean and the ±25% band (unit-tested, no Docker). Dictionary templates plus `apply_ami_overlay` turn a normal prop MRF case into a `rhoPimpleFoam` + `cyclicAMI` case. A one-shot CLI meshes, solves, writes `result.json`, and stamps a finished run. Docs quote that JSON.

**Tech Stack:** Python 3.12 (uv), pytest, OpenFOAM v2406 Docker (`opencfd/openfoam-default:2406`), existing `build_prop_case` / `OpenFOAMRunner`.

**Spec:** `docs/superpowers/specs/2026-09-23-prop-cfd-ami-smoke-design.md`

## Global Constraints

- STL default: `validation/reference/drone_radial/obj_2_ccw.stl`. RPM **25257**. spin **−1**. freestream **1 m/s**.
- `base_cell` **0.005** m. procs **8**. revolutions **2**. `deltaT` **4e-5** s. `endTime` = `2 * 60 / 25257` s.
- Mean window: samples with `t ≥ endTime − 60/25257`. Reference **938.0 g**. Band inclusive **[703.5, 1172.5] g**. Floor **abs(mean) ≥ 10 g**.
- Regime stamp `compressible-AMI`. Solver `rhoPimpleFoam`. Image `opencfd/openfoam-default:2406`.
- Do **not** call `evaluate_prop_cfd` or `run_solve_prop`. Do **not** overwrite smoke, refine, or GCI fixtures. Do **not** edit the parked DES overlay into AMI.
- A dynamic-mesh rejection is a failed smoke (`mean_thrust_g: null`). Do not rerun as MRF.
- CI unit tests: no Docker. Skip staging `catalog/catalog.db`.
- CadQuery / antivirus teardown after a green JSON (Windows `3221226356` or `-1073741819`) is non-blocking.
- Commit when a task step says to commit.

## File map

| File | Role |
|------|------|
| `fansim/propeller/ami_smoke.py` | constants, mean, band, exit code, overlay, mesh/solve pipeline |
| `fansim/cfd/templates.py` | AMI dictionary strings only (append; do not change `PROP_*` MRF strings) |
| `scripts/run_prop_ami_smoke.py` | CLI |
| `tests/test_prop_ami_smoke.py` | unit coverage |
| `docs/validation/drone_radial_open_air_cfd.md` | AMI section |
| `docs/roadmap.md` | §4.3 note |
| `docs/superpowers/specs/2026-09-23-prop-cfd-ami-smoke-design.md` | status line |
| `validation/reference/drone_radial/cfd/obj_2_ccw_ami_smoke.json` | stamp after a finished run |
| `runs/drone_radial_cfd/ami/` | local case, not committed |

---

### Task 1: Mean window, band, and exit code

**Files:**
- Create: `fansim/propeller/ami_smoke.py`
- Create: `tests/test_prop_ami_smoke.py`

**Interfaces:**
- Produces:
  - `MRF_REF_THRUST_G: float = 938.0`
  - `BAND_FRAC: float = 0.25`
  - `FLOOR_G: float = 10.0`
  - `N_REVS: int = 2`
  - `DELTA_T: float = 4e-5`
  - `rev_period_s(rpm: float) -> float`
  - `end_time_s(rpm: float, n_revs: int = N_REVS) -> float`
  - `band_limits() -> tuple[float, float]` — `(938*0.75, 938*1.25)`
  - `window_thrust_g(rows: list[list[float]], *, end_time: float, rpm: float) -> tuple[float | None, int]` — each row is numeric forces.dat fields; time is column 0; total Fz is column 3. Window is `t >= end_time - rev_period_s(rpm)`. Each sample’s grams are `abs(Fz) / 9.80665 * 1000`. Returns `(mean, count)` or `(None, 0)`.
  - `assess_band(mean_thrust_g: float | None) -> dict` — keys `mean_thrust_g`, `band_pass`, `band_lo_g`, `band_hi_g`, `mrf_ref_thrust_g`, `floor_g`. `band_pass` is true only when the mean is finite, inside the inclusive band, and `abs(mean) >= 10`.
  - `ami_exit_code(summary: dict) -> int` — `1` if mean is missing or non-finite, `0` if `band_pass`, else `2`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_prop_ami_smoke.py
from __future__ import annotations

from fansim.propeller.ami_smoke import (
    DELTA_T,
    N_REVS,
    ami_exit_code,
    assess_band,
    band_limits,
    end_time_s,
    rev_period_s,
    window_thrust_g,
)


def test_locked_time_knobs():
    period = rev_period_s(25257.0)
    assert period == 60.0 / 25257.0
    assert end_time_s(25257.0) == N_REVS * period
    assert DELTA_T == 4e-5


def test_window_uses_last_revolution_and_abs_fz():
    end = end_time_s(25257.0)
    period = rev_period_s(25257.0)
    t0 = end - period
    # column 3 is total Fz (N). 9.80665 N → 1000 g.
    rows = [
        [0.0, 0.0, 0.0, 9.80665],
        [t0 - 1e-6, 0.0, 0.0, -9.80665],
        [t0, 0.0, 0.0, 9.80665],
        [end, 0.0, 0.0, -9.80665],
    ]
    mean, count = window_thrust_g(rows, end_time=end, rpm=25257.0)
    assert count == 2
    assert mean == 1000.0


def test_window_zero_samples_is_none():
    end = end_time_s(25257.0)
    mean, count = window_thrust_g([[0.0, 0.0, 0.0, 1.0]], end_time=end, rpm=25257.0)
    assert mean is None
    assert count == 0


def test_band_edges_are_inclusive():
    lo, hi = band_limits()
    assert lo == 703.5
    assert hi == 1172.5
    assert assess_band(lo)["band_pass"] is True
    assert assess_band(hi)["band_pass"] is True
    assert assess_band(938.0)["band_pass"] is True
    assert assess_band(lo - 1e-6)["band_pass"] is False
    assert assess_band(hi + 1e-6)["band_pass"] is False
    assert assess_band(5.0)["band_pass"] is False
    assert assess_band(None)["band_pass"] is False
    assert assess_band(None)["mean_thrust_g"] is None


def test_exit_codes():
    assert ami_exit_code(assess_band(938.0)) == 0
    assert ami_exit_code(assess_band(2000.0)) == 2
    assert ami_exit_code(assess_band(5.0)) == 2
    assert ami_exit_code(assess_band(None)) == 1
    assert ami_exit_code({"mean_thrust_g": float("nan"), "band_pass": False}) == 1
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run python -m pytest tests/test_prop_ami_smoke.py -v --tb=short`

Expected: FAIL — `ModuleNotFoundError: No module named 'fansim.propeller.ami_smoke'`.

- [ ] **Step 3: Implement the helpers**

```python
# fansim/propeller/ami_smoke.py
"""obj_2 compressible AMI smoke helpers (roadmap §4.3)."""
from __future__ import annotations

import math

MRF_REF_THRUST_G = 938.0
BAND_FRAC = 0.25
FLOOR_G = 10.0
N_REVS = 2
DELTA_T = 4e-5
G_PER_NEWTON = 1000.0 / 9.80665


def rev_period_s(rpm: float) -> float:
    return 60.0 / float(rpm)


def end_time_s(rpm: float, n_revs: int = N_REVS) -> float:
    return float(n_revs) * rev_period_s(rpm)


def band_limits() -> tuple[float, float]:
    return (
        MRF_REF_THRUST_G * (1.0 - BAND_FRAC),
        MRF_REF_THRUST_G * (1.0 + BAND_FRAC),
    )


def window_thrust_g(
    rows: list[list[float]],
    *,
    end_time: float,
    rpm: float,
) -> tuple[float | None, int]:
    t0 = float(end_time) - rev_period_s(rpm)
    window = [r for r in rows if len(r) > 3 and float(r[0]) >= t0]
    if not window:
        return None, 0
    grams = [abs(float(r[3])) * G_PER_NEWTON for r in window]
    return sum(grams) / len(grams), len(grams)


def assess_band(mean_thrust_g: float | None) -> dict:
    lo, hi = band_limits()
    finite = mean_thrust_g is not None and math.isfinite(float(mean_thrust_g))
    mean = float(mean_thrust_g) if finite else None
    passed = bool(finite and mean is not None and lo <= mean <= hi and abs(mean) >= FLOOR_G)
    return {
        "mean_thrust_g": mean,
        "band_pass": passed,
        "band_lo_g": lo,
        "band_hi_g": hi,
        "mrf_ref_thrust_g": MRF_REF_THRUST_G,
        "floor_g": FLOOR_G,
    }


def ami_exit_code(summary: dict) -> int:
    mean = summary.get("mean_thrust_g")
    if mean is None:
        return 1
    try:
        value = float(mean)
    except (TypeError, ValueError):
        return 1
    if not math.isfinite(value):
        return 1
    return 0 if summary.get("band_pass") else 2
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run python -m pytest tests/test_prop_ami_smoke.py -v --tb=short`

Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add fansim/propeller/ami_smoke.py tests/test_prop_ami_smoke.py
git commit -m "feat(prop): AMI smoke thrust window and MRF band"
```

---

### Task 2: AMI dictionaries and case overlay

**Files:**
- Modify: `fansim/cfd/templates.py` (append after `PROP_ALPHAT`, before the DES section)
- Modify: `fansim/propeller/ami_smoke.py`
- Modify: `tests/test_prop_ami_smoke.py`

**Interfaces:**
- Consumes: `build_prop_case`, `PropOpenAir`, `_write` from existing prop CFD. Does not change their MRF output.
- Produces: `apply_ami_overlay(case_dir, *, omega_signed: float, ami_radius: float, ami_z_min: float, ami_z_max: float, end_time: float, delta_t: float, u_freestream: float, k: float, omega_turb: float) -> None`
  - Rewrites `system/controlDict`, `system/fvSchemes`, `system/fvSolution`, `system/dynamicMeshDict`, `system/createBafflesDict`, and `0/{U,T,p,k,omega,nut,alphat,pointDisplacement}`.
  - Deletes `constant/MRFProperties` if present.
  - Leaves `constant/thermophysicalProperties`, `constant/turbulenceProperties`, and `system/fvOptions` (`limitTemperature`) in place.

- [ ] **Step 1: Write the failing overlay test**

Append to `tests/test_prop_ami_smoke.py`:

```python
from pathlib import Path

from fansim.cfd import templates as T
from fansim.propeller.ami_smoke import apply_ami_overlay
from fansim.propeller.cfd import PropOpenAir, build_prop_case


def test_mrf_control_dict_unchanged():
    assert "rhoSimpleFoam" in T.PROP_CONTROL_DICT
    assert "phiMRF" in T.PROP_FV_SCHEMES


def test_apply_ami_overlay_writes_sliding_case(tmp_path: Path):
    stl = Path("validation/reference/drone_radial/obj_2_ccw.stl")
    dom = PropOpenAir(
        tip_radius=0.045,
        domain_radius=0.225,
        z_min=-0.1,
        z_max=0.2,
        mrf_z_min=-0.02,
        mrf_z_max=0.02,
        rpm=25257.0,
        omega_signed=-2644.0,
        u_freestream=1.0,
    )
    build_prop_case(tmp_path, stl, dom, n_iters=10, n_subdomains=8)
    assert (tmp_path / "constant/MRFProperties").is_file()
    assert "rhoSimpleFoam" in (tmp_path / "system/controlDict").read_text(encoding="utf-8")

    apply_ami_overlay(
        tmp_path,
        omega_signed=dom.omega_signed,
        ami_radius=1.05 * dom.tip_radius,
        ami_z_min=dom.mrf_z_min,
        ami_z_max=dom.mrf_z_max,
        end_time=end_time_s(25257.0),
        delta_t=DELTA_T,
        u_freestream=1.0,
        k=1.0e-4,
        omega_turb=10.0,
    )
    control = (tmp_path / "system/controlDict").read_text(encoding="utf-8")
    schemes = (tmp_path / "system/fvSchemes").read_text(encoding="utf-8")
    solution = (tmp_path / "system/fvSolution").read_text(encoding="utf-8")
    motion = (tmp_path / "system/dynamicMeshDict").read_text(encoding="utf-8")
    baffles = (tmp_path / "system/createBafflesDict").read_text(encoding="utf-8")
    velocity = (tmp_path / "0/U").read_text(encoding="utf-8")
    assert "rhoPimpleFoam" in control
    assert "rhoSimpleFoam" not in control
    assert "writeInterval   1" in control
    assert "backward" in schemes
    assert "steadyState" not in schemes
    assert "phiMRF" not in schemes
    assert "nOuterCorrectors 1" in solution
    assert "nCorrectors     2" in solution
    assert "nNonOrthogonalCorrectors 1" in solution
    assert "SIMPLE" not in solution
    assert "rotatingMotion" in motion
    assert "cellZone        rotor" in motion
    assert "cyclicAMI" in baffles
    assert "transform       rotational" in baffles
    assert "searchableCylinder" in baffles
    assert "movingWallVelocity" in velocity
    assert "AMI1" in velocity and "AMI2" in velocity
    assert not (tmp_path / "constant/MRFProperties").exists()
    for name in ("T", "p", "k", "omega", "nut", "alphat", "pointDisplacement"):
        text = (tmp_path / "0" / name).read_text(encoding="utf-8")
        assert "AMI1" in text and "AMI2" in text
    assert "limitTemperature" in (tmp_path / "system/fvOptions").read_text(encoding="utf-8")
    assert "hePsiThermo" in (tmp_path / "constant/thermophysicalProperties").read_text(encoding="utf-8")
```

Import `DELTA_T` and `end_time_s` in that test (they already come from Task 1).

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run python -m pytest tests/test_prop_ami_smoke.py::test_apply_ami_overlay_writes_sliding_case -v --tb=short`

Expected: FAIL — `ImportError: cannot import name 'apply_ami_overlay'`.

- [ ] **Step 3: Append AMI templates**

Append these constants in `fansim/cfd/templates.py` immediately after `PROP_ALPHAT` and before the DES comment. Do not edit `PROP_CONTROL_DICT` or `PROP_FV_SCHEMES`.

```python
AMI_CYCLIC = """
    AMI1 { type cyclicAMI; }
    AMI2 { type cyclicAMI; }
"""

PROP_AMI_CONTROL_DICT = """@HEADER@
application     rhoPimpleFoam;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         @ENDTIME@;
deltaT          @DELTAT@;
writeControl    timeStep;
writeInterval   @WRITEINT@;
purgeWrite      2;
writeFormat     ascii;
writePrecision  7;
writeCompression off;
timeFormat      general;
runTimeModifiable true;

functions
{
    forces
    {
        type            forces;
        libs            (forces);
        patches         (impeller);
        rho             rho;
        CofR            (0 0 0);
        writeControl    timeStep;
        writeInterval   1;
    }
}
"""

PROP_AMI_FV_SCHEMES = """@HEADER@
ddtSchemes { default backward; }
gradSchemes { default Gauss linear; }
divSchemes
{
    default         none;
    div(phi,U)      Gauss linearUpwind grad(U);
    div(phi,K)      Gauss upwind;
    div(phi,h)      Gauss upwind;
    div(phi,e)      Gauss upwind;
    div(phi,Ekp)    Gauss upwind;
    div(phi,k)      Gauss upwind;
    div(phi,omega)  Gauss upwind;
    div(phid,p)     Gauss upwind;
    div(((rho*nuEff)*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes { default corrected; }
wallDist        { method meshWave; }
"""

PROP_AMI_FV_SOLUTION = """@HEADER@
solvers
{
    p
    {
        solver          GAMG;
        tolerance       1e-7;
        relTol          0.01;
        smoother        GaussSeidel;
    }
    pFinal
    {
        $p;
        relTol          0;
    }
    "(rho|U|h|e|k|omega)"
    {
        solver          smoothSolver;
        smoother        symGaussSeidel;
        tolerance       1e-8;
        relTol          0.1;
    }
    "(rho|U|h|e|k|omega)Final"
    {
        $U;
        relTol          0;
    }
}
PIMPLE
{
    nOuterCorrectors 1;
    nCorrectors     2;
    nNonOrthogonalCorrectors 1;
    momentumPredictor yes;
    transonic       no;
}
"""

PROP_AMI_DYNAMIC_MESH = """@HEADER@
dynamicFvMesh   dynamicMotionSolverFvMesh;
motionSolverLibs (fvMotionSolvers);
motionSolver    solidBody;
cellZone        rotor;
solidBodyMotionFunction  rotatingMotion;
origin      (0 0 0);
axis        (0 0 1);
omega       @OMEGA@;
"""

PROP_AMI_CREATE_BAFFLES = """@HEADER@
internalFacesOnly true;

baffles
{
    AMI
    {
        type        searchableSurface;
        surface
        {
            type            searchableCylinder;
            point1          (0 0 @ZMIN@);
            point2          (0 0 @ZMAX@);
            radius          @RADIUS@;
        }
        patches
        {
            master
            {
                name            AMI1;
                type            cyclicAMI;
                neighbourPatch  AMI2;
                transform       rotational;
                rotationAxis    (0 0 1);
                rotationCentre  (0 0 0);
            }
            slave
            {
                name            AMI2;
                type            cyclicAMI;
                neighbourPatch  AMI1;
                transform       rotational;
                rotationAxis    (0 0 1);
                rotationCentre  (0 0 0);
            }
        }
    }
}
"""

PROP_AMI_U = """@HEADER@
dimensions [0 1 -1 0 0 0 0];
internalField uniform (0 0 @U_EPS@);
boundaryField
{
    inlet    { type freestreamVelocity; freestreamValue uniform (0 0 @U_EPS@); value uniform (0 0 @U_EPS@); }
    outlet   { type freestreamVelocity; freestreamValue uniform (0 0 @U_EPS@); value uniform (0 0 @U_EPS@); }
    walls    { type freestreamVelocity; freestreamValue uniform (0 0 @U_EPS@); value uniform (0 0 @U_EPS@); }
    impeller { type movingWallVelocity; value uniform (0 0 0); }
@AMI_CYCLIC@
}
"""

PROP_AMI_T = """@HEADER@
dimensions [0 0 0 1 0 0 0];
internalField uniform @T_INF@;
boundaryField
{
    inlet    { type fixedValue; value uniform @T_INF@; }
    outlet   { type inletOutlet; inletValue uniform @T_INF@; value uniform @T_INF@; }
    walls    { type zeroGradient; }
    impeller { type zeroGradient; }
@AMI_CYCLIC@
}
"""

PROP_AMI_P = """@HEADER@
dimensions [1 -1 -2 0 0 0 0];
internalField uniform @P_INF@;
boundaryField
{
    inlet    { type freestreamPressure; freestreamValue uniform @P_INF@; value uniform @P_INF@; }
    outlet   { type freestreamPressure; freestreamValue uniform @P_INF@; value uniform @P_INF@; }
    walls    { type zeroGradient; }
    impeller { type zeroGradient; }
@AMI_CYCLIC@
}
"""

PROP_AMI_K = """@HEADER@
dimensions [0 2 -2 0 0 0 0];
internalField uniform @K@;
boundaryField
{
    inlet    { type inletOutlet; inletValue uniform @K@; value uniform @K@; }
    outlet   { type inletOutlet; inletValue uniform @K@; value uniform @K@; }
    walls    { type inletOutlet; inletValue uniform @K@; value uniform @K@; }
    impeller { type kqRWallFunction; value uniform @K@; }
@AMI_CYCLIC@
}
"""

PROP_AMI_OMEGA = """@HEADER@
dimensions [0 0 -1 0 0 0 0];
internalField uniform @OMEGAT@;
boundaryField
{
    inlet    { type inletOutlet; inletValue uniform @OMEGAT@; value uniform @OMEGAT@; }
    outlet   { type inletOutlet; inletValue uniform @OMEGAT@; value uniform @OMEGAT@; }
    walls    { type inletOutlet; inletValue uniform @OMEGAT@; value uniform @OMEGAT@; }
    impeller { type omegaWallFunction; value uniform @OMEGAT@; }
@AMI_CYCLIC@
}
"""

PROP_AMI_NUT = """@HEADER@
dimensions [0 2 -1 0 0 0 0];
internalField uniform 0;
boundaryField
{
    inlet    { type calculated; value uniform 0; }
    outlet   { type calculated; value uniform 0; }
    walls    { type calculated; value uniform 0; }
    impeller { type nutkWallFunction; value uniform 0; }
@AMI_CYCLIC@
}
"""

PROP_AMI_ALPHAT = """@HEADER@
dimensions [1 -1 -1 0 0 0 0];
internalField uniform 0;
boundaryField
{
    inlet    { type calculated; value uniform 0; }
    outlet   { type calculated; value uniform 0; }
    walls    { type calculated; value uniform 0; }
    impeller { type compressible::alphatWallFunction; value uniform 0; }
@AMI_CYCLIC@
}
"""

PROP_AMI_POINT_DISPLACEMENT = """@HEADER@
dimensions      [0 1 0 0 0 0 0];
internalField   uniform (0 0 0);
boundaryField
{
    inlet    { type fixedValue; value uniform (0 0 0); }
    outlet   { type fixedValue; value uniform (0 0 0); }
    walls    { type fixedValue; value uniform (0 0 0); }
    impeller { type fixedValue; value uniform (0 0 0); }
    AMI1     { type fixedValue; value uniform (0 0 0); }
    AMI2     { type fixedValue; value uniform (0 0 0); }
}
"""
```

- [ ] **Step 4: Implement `apply_ami_overlay`**

Add to `fansim/propeller/ami_smoke.py`:

```python
from pathlib import Path

from fansim.cfd import templates as T
from fansim.cfd.openfoam_case import _write
from fansim.propeller.cfd import P_INF, T_INF


def apply_ami_overlay(
    case_dir,
    *,
    omega_signed: float,
    ami_radius: float,
    ami_z_min: float,
    ami_z_max: float,
    end_time: float,
    delta_t: float,
    u_freestream: float,
    k: float,
    omega_turb: float,
) -> None:
    case_dir = Path(case_dir)
    cyclic = {"AMI_CYCLIC": T.AMI_CYCLIC}
    _write(case_dir / "system/controlDict", T.PROP_AMI_CONTROL_DICT, "dictionary", "controlDict", {
        "ENDTIME": end_time,
        "DELTAT": delta_t,
        "WRITEINT": 50,
    })
    _write(case_dir / "system/fvSchemes", T.PROP_AMI_FV_SCHEMES, "dictionary", "fvSchemes", {})
    _write(case_dir / "system/fvSolution", T.PROP_AMI_FV_SOLUTION, "dictionary", "fvSolution", {})
    _write(case_dir / "system/dynamicMeshDict", T.PROP_AMI_DYNAMIC_MESH, "dictionary", "dynamicMeshDict", {
        "OMEGA": omega_signed,
    })
    _write(case_dir / "system/createBafflesDict", T.PROP_AMI_CREATE_BAFFLES, "dictionary", "createBafflesDict", {
        "ZMIN": ami_z_min,
        "ZMAX": ami_z_max,
        "RADIUS": ami_radius,
    })
    _write(case_dir / "0/U", T.PROP_AMI_U, "volVectorField", "U", {"U_EPS": u_freestream, **cyclic})
    _write(case_dir / "0/T", T.PROP_AMI_T, "volScalarField", "T", {"T_INF": T_INF, **cyclic})
    _write(case_dir / "0/p", T.PROP_AMI_P, "volScalarField", "p", {"P_INF": P_INF, **cyclic})
    _write(case_dir / "0/k", T.PROP_AMI_K, "volScalarField", "k", {"K": k, **cyclic})
    _write(case_dir / "0/omega", T.PROP_AMI_OMEGA, "volScalarField", "omega", {"OMEGAT": omega_turb, **cyclic})
    _write(case_dir / "0/nut", T.PROP_AMI_NUT, "volScalarField", "nut", cyclic)
    _write(case_dir / "0/alphat", T.PROP_AMI_ALPHAT, "volScalarField", "alphat", cyclic)
    _write(
        case_dir / "0/pointDisplacement",
        T.PROP_AMI_POINT_DISPLACEMENT,
        "pointVectorField",
        "pointDisplacement",
        {},
    )
    mrf = case_dir / "constant/MRFProperties"
    if mrf.is_file():
        mrf.unlink()
```

Field snapshots use `writeInterval 50`. Forces stay at `writeInterval 1` inside the forces function object. The test looks for `writeInterval   1` in `controlDict`, which matches the forces block. Keep that spacing (three spaces) so the test string matches.

- [ ] **Step 5: Run the overlay tests**

Run: `uv run python -m pytest tests/test_prop_ami_smoke.py -v --tb=short`

Expected: PASS, including `test_mrf_control_dict_unchanged` and `test_apply_ami_overlay_writes_sliding_case`.

- [ ] **Step 6: Commit**

```bash
git add fansim/cfd/templates.py fansim/propeller/ami_smoke.py tests/test_prop_ami_smoke.py
git commit -m "feat(prop): AMI dictionary overlay for rhoPimpleFoam"
```

---

### Task 3: Smoke CLI (no Docker in the tests)

**Files:**
- Modify: `fansim/propeller/ami_smoke.py`
- Create: `scripts/run_prop_ami_smoke.py`
- Modify: `tests/test_prop_ami_smoke.py`

**Interfaces:**
- Consumes: Task 1 helpers, `apply_ami_overlay`, `build_prop_case`, `prop_open_air`, `_turb_from_u`, `prepare_prop_stl`, `measure_prop_stl`, `OpenFOAMRunner`, `image_available`.
- Produces:
  - `AMI_MESH_PIPELINE: list[str]`
  - `run_mesh_ami(runner) -> None`
  - `run_solve_ami(runner, n_procs: int = 8) -> None` — `rhoPimpleFoam` only, no `potentialFoam`.
  - `read_force_rows(case_dir) -> list[list[float]]` — uses `fansim.cfd.metrics._pp_file` + `_all_data_rows` on `forces/force.dat`.
  - `summary_from_rows(rows, *, stl: str, rpm: float, base_cell: float, reason: str | None = None) -> dict` — spec JSON keys. `reason` is present only when the mean is missing.
  - `result_is_resumable(path) -> bool` — true when JSON has a finite `mean_thrust_g`.
  - `scripts/run_prop_ami_smoke.py` `build_parser()` defaults: STL `PROJECT / "validation/reference/drone_radial/obj_2_ccw.stl"`, `--rpm 25257`, `--out PROJECT / "runs/drone_radial_cfd/ami/obj_2"`, `--procs 8`, `--base-cell 0.005`, `--force` off.
  - `main(argv=None) -> int` — missing STL prints `ERROR` to stderr and returns 1. Resume skips Docker when `result.json` is resumable unless `--force`. On `RuntimeError` from the runner, write `mean_thrust_g: null` plus `reason` and return 1. When the mean is finite and the STL name is `obj_2_ccw.stl` and rpm is 25257, copy JSON to `validation/reference/drone_radial/cfd/obj_2_ccw_ami_smoke.json`. Do not copy a null mean.

- [ ] **Step 1: Write the failing CLI tests**

Append to `tests/test_prop_ami_smoke.py`:

```python
import importlib.util
import json

from fansim.propeller.ami_smoke import result_is_resumable, summary_from_rows


def test_summary_from_rows_band_pass():
    end = end_time_s(25257.0)
    period = rev_period_s(25257.0)
    fz = 938.0 / (1000.0 / 9.80665)  # newtons for 938 g
    rows = [[end - period, 0.0, 0.0, fz], [end, 0.0, 0.0, fz]]
    summary = summary_from_rows(
        rows, stl="obj_2_ccw.stl", rpm=25257.0, base_cell=0.005,
    )
    assert summary["regime"] == "compressible-AMI"
    assert summary["solver"] == "rhoPimpleFoam"
    assert summary["thrust_g_samples"] == 2
    assert summary["mean_thrust_g"] == pytest.approx(938.0, rel=1e-6)
    assert summary["band_pass"] is True
    assert summary["delta_t"] == 4e-5
    assert "reason" not in summary
    assert ami_exit_code(summary) == 0


def test_summary_from_rows_empty_window():
    summary = summary_from_rows(
        [[0.0, 0.0, 0.0, 1.0]],
        stl="obj_2_ccw.stl",
        rpm=25257.0,
        base_cell=0.005,
        reason="mean window has zero samples",
    )
    assert summary["mean_thrust_g"] is None
    assert summary["band_pass"] is False
    assert summary["thrust_g_samples"] == 0
    assert summary["reason"] == "mean window has zero samples"
    assert ami_exit_code(summary) == 1


def test_result_is_resumable(tmp_path: Path):
    path = tmp_path / "result.json"
    assert result_is_resumable(path) is False
    path.write_text(json.dumps({"mean_thrust_g": None}), encoding="utf-8")
    assert result_is_resumable(path) is False
    path.write_text(json.dumps({"mean_thrust_g": 900.0}), encoding="utf-8")
    assert result_is_resumable(path) is True


def _load_cli():
    path = Path("scripts/run_prop_ami_smoke.py")
    spec = importlib.util.spec_from_file_location("run_prop_ami_smoke", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_cli_parser_defaults():
    mod = _load_cli()
    args = mod.build_parser().parse_args([])
    assert args.stl.name == "obj_2_ccw.stl"
    assert args.rpm == pytest.approx(25257.0)
    assert args.procs == 8
    assert args.base_cell == pytest.approx(0.005)
    assert args.force is False
    assert args.out.as_posix().endswith("runs/drone_radial_cfd/ami/obj_2")


def test_cli_missing_stl(tmp_path: Path, capsys):
    mod = _load_cli()
    code = mod.main([
        "--stl", str(tmp_path / "missing.stl"),
        "--out", str(tmp_path / "out"),
    ])
    assert code == 1
    assert "ERROR" in capsys.readouterr().err
```

Add `import pytest` at the top of the test module if it is not already there.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run python -m pytest tests/test_prop_ami_smoke.py::test_cli_parser_defaults tests/test_prop_ami_smoke.py::test_summary_from_rows_band_pass -v --tb=short`

Expected: FAIL — missing `summary_from_rows` and missing script.

- [ ] **Step 3: Add pipeline and summary helpers**

Append to `fansim/propeller/ami_smoke.py`:

```python
AMI_MESH_PIPELINE = [
    "surfaceFeatureExtract",
    "blockMesh",
    "snappyHexMesh -overwrite",
    "createBaffles -overwrite",
    "topoSet",
    "renumberMesh -overwrite",
    "checkMesh -allTopology",
]


def run_mesh_ami(runner) -> None:
    for cmd in AMI_MESH_PIPELINE:
        runner.run(cmd)


def run_solve_ami(runner, n_procs: int = 8) -> None:
    runner.run("rm -rf processor* postProcessing", check=False)
    if n_procs and int(n_procs) > 1:
        runner.run("decomposePar -force")
        mpi = f"mpirun --allow-run-as-root --oversubscribe -np {int(n_procs)}"
        runner.run(f"{mpi} rhoPimpleFoam -parallel")
    else:
        runner.run("rhoPimpleFoam")


def read_force_rows(case_dir) -> list[list[float]]:
    from fansim.cfd.metrics import _all_data_rows, _pp_file

    path = _pp_file(Path(case_dir), "forces", "force.dat")
    return _all_data_rows(path)


def summary_from_rows(
    rows: list[list[float]],
    *,
    stl: str,
    rpm: float,
    base_cell: float,
    reason: str | None = None,
) -> dict:
    end = end_time_s(rpm)
    mean, count = window_thrust_g(rows, end_time=end, rpm=rpm)
    summary = assess_band(mean)
    summary.update({
        "thrust_g_samples": count,
        "regime": "compressible-AMI",
        "solver": "rhoPimpleFoam",
        "rpm": float(rpm),
        "end_time": end,
        "delta_t": DELTA_T,
        "stl": stl,
        "base_cell": float(base_cell),
    })
    if mean is None:
        summary["reason"] = reason or "non-finite mean thrust"
    return summary


def result_is_resumable(path) -> bool:
    path = Path(path)
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return math.isfinite(float(data["mean_thrust_g"]))
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return False
```

Add `import json` next to the other imports in `ami_smoke.py`.

- [ ] **Step 4: Write the CLI**

```python
# scripts/run_prop_ami_smoke.py
"""One compressible AMI smoke on obj_2 (roadmap §4.3).

Usage:
    uv run python scripts/run_prop_ami_smoke.py
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from fansim.cfd.openfoam_case import MeshResolution  # noqa: E402
from fansim.cfd.runner import DEFAULT_IMAGE, OpenFOAMRunner, image_available  # noqa: E402
from fansim.propeller.ami_smoke import (  # noqa: E402
    DELTA_T,
    ami_exit_code,
    apply_ami_overlay,
    end_time_s,
    read_force_rows,
    result_is_resumable,
    run_mesh_ami,
    run_solve_ami,
    summary_from_rows,
)
from fansim.propeller.cfd import _turb_from_u, build_prop_case, prop_open_air  # noqa: E402
from fansim.propeller.stl_import import measure_prop_stl, prepare_prop_stl  # noqa: E402

DEFAULT_STL = PROJECT / "validation/reference/drone_radial/obj_2_ccw.stl"
DEFAULT_OUT = PROJECT / "runs/drone_radial_cfd/ami/obj_2"
STAMP = PROJECT / "validation/reference/drone_radial/cfd/obj_2_ccw_ami_smoke.json"
SPIN = -1


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="obj_2 compressible AMI smoke")
    ap.add_argument("--stl", type=Path, default=DEFAULT_STL)
    ap.add_argument("--rpm", type=float, default=25257.0)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--base-cell", type=float, default=0.005, dest="base_cell")
    ap.add_argument("--force", action="store_true")
    return ap


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _maybe_stamp(stl: Path, rpm: float, payload: dict) -> None:
    mean = payload.get("mean_thrust_g")
    if mean is None:
        return
    if stl.name != "obj_2_ccw.stl" or abs(float(rpm) - 25257.0) > 1e-6:
        return
    _write_json(STAMP, payload)


def run_case(stl: Path, rpm: float, out: Path, procs: int, base_cell: float) -> dict:
    if not image_available(DEFAULT_IMAGE):
        raise RuntimeError(f"Docker image not available: {DEFAULT_IMAGE}")
    out.mkdir(parents=True, exist_ok=True)
    prepared = out / "prop.stl"
    prepare_prop_stl(stl, prepared)
    metrics = measure_prop_stl(prepared)
    from fansim.geometry import watertight_report

    rep = watertight_report(prepared)
    (_, _, z0), (_, _, z1) = rep.bounds_mm
    dom = prop_open_air(
        metrics.tip_radius_m,
        z0 / 1000.0,
        z1 / 1000.0,
        rpm=rpm,
        spin=SPIN,
    )
    build_prop_case(
        out,
        prepared,
        dom,
        mesh=MeshResolution(base_cell=float(base_cell)),
        n_iters=100,
        n_subdomains=int(procs),
    )
    k, omega_turb = _turb_from_u(dom.u_freestream, dom.tip_radius)
    apply_ami_overlay(
        out,
        omega_signed=dom.omega_signed,
        ami_radius=1.05 * dom.tip_radius,
        ami_z_min=dom.mrf_z_min,
        ami_z_max=dom.mrf_z_max,
        end_time=end_time_s(rpm),
        delta_t=DELTA_T,
        u_freestream=dom.u_freestream,
        k=k,
        omega_turb=omega_turb,
    )
    runner = OpenFOAMRunner(out)
    run_mesh_ami(runner)
    run_solve_ami(runner, n_procs=int(procs))
    rows = read_force_rows(out)
    return summary_from_rows(
        rows,
        stl=str(stl),
        rpm=rpm,
        base_cell=base_cell,
        reason="mean window has zero samples",
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    stl = Path(args.stl)
    out = Path(args.out)
    result_path = out / "result.json"
    if result_is_resumable(result_path) and not args.force:
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        print(json.dumps(payload, indent=2))
        return ami_exit_code(payload)
    if not stl.is_file():
        print(f"ERROR: STL not found: {stl}", file=sys.stderr)
        return 1
    try:
        payload = run_case(stl, float(args.rpm), out, int(args.procs), float(args.base_cell))
    except Exception as exc:
        payload = summary_from_rows(
            [],
            stl=str(stl),
            rpm=float(args.rpm),
            base_cell=float(args.base_cell),
            reason=str(exc),
        )
        _write_json(result_path, payload)
        print(json.dumps(payload, indent=2))
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    _write_json(result_path, payload)
    _maybe_stamp(stl, float(args.rpm), payload)
    print(json.dumps(payload, indent=2))
    return ami_exit_code(payload)


if __name__ == "__main__":
    raise SystemExit(main())
```

`shutil` is unused. Do not import it. `watertight_report` is imported inside `run_case` so a missing-STL CLI test does not need geometry. That import pulls CadQuery on the real run; write `result.json` before process exit so a later Windows teardown is non-blocking (Task 4).

Do not call `evaluate_prop_cfd`.

- [ ] **Step 5: Run the unit tests**

Run: `uv run python -m pytest tests/test_prop_ami_smoke.py tests/test_prop_gci_ladder.py -v --tb=short`

Expected: PASS. No Docker. `test_mrf_control_dict_unchanged` still passes.

- [ ] **Step 6: Commit**

```bash
git add fansim/propeller/ami_smoke.py scripts/run_prop_ami_smoke.py tests/test_prop_ami_smoke.py
git commit -m "feat(prop): CLI for obj_2 compressible AMI smoke"
```

---

### Task 4: Docker smoke, stamp, and docs

**Files:**
- Modify: `docs/validation/drone_radial_open_air_cfd.md`
- Modify: `docs/roadmap.md` (the §4.3 remaining-tier sentence)
- Modify: `docs/superpowers/specs/2026-09-23-prop-cfd-ami-smoke-design.md` (status line only)
- Create after a finished run: `validation/reference/drone_radial/cfd/obj_2_ccw_ami_smoke.json`
- Do not commit: `runs/drone_radial_cfd/ami/`

**Interfaces:**
- Consumes: `scripts/run_prop_ami_smoke.py` and `result.json` fields from Task 3.

- [ ] **Step 1: Confirm the image, then run the smoke**

Run: `docker image inspect opencfd/openfoam-default:2406 --format "{{.Id}}"`

Expected: an image id. If the image is missing, stop and report that. Do not pull a different tag and do not fall back to MRF.

Run from the repo root:

```bash
uv run python scripts/run_prop_ami_smoke.py
```

This is one coarse mesh plus two revolutions. It can take a long time. Do not start a second STL.

- [ ] **Step 2: Read the result and classify it**

Read `runs/drone_radial_cfd/ami/obj_2/result.json`.

| What you see | What to do |
|--------------|------------|
| Finite `mean_thrust_g` and `band_pass` true | Continue. Process exit 0, or Windows `3221226356` / `-1073741819` after the JSON exists, both count as a finished pass. |
| Finite `mean_thrust_g` and `band_pass` false | Continue. This is an honest miss (exit 2, or the same Windows teardown code). Stamp it. Do not rerun with a different mesh or RPM to chase the band. |
| `mean_thrust_g` null, reason mentions dynamic mesh / `rhoPimpleFoam` / `createBaffles` | Stop. Do not rerun as MRF. If the log names an unknown dictionary keyword in `createBafflesDict` or `dynamicMeshDict`, fix that keyword so the spec’s baffle and `rotatingMotion` still exist, then rerun **once** with `--force`. If the solver binary is absent, leave the null JSON unstamped and write the docs as “attempted, solver rejected”. |
| Any other null mean | Leave it unstamped. Document the `reason`. Do not invent a thrust number. |

Confirm the stamp file exists only when `mean_thrust_g` is finite. If the CLI wrote it, do not hand-edit the numbers.

- [ ] **Step 3: Add the validation section**

Append to `docs/validation/drone_radial_open_air_cfd.md`. Fill the bracketed fields from `result.json`. Do not change the smoke, refine, or GCI tables.

```markdown
## AMI smoke (obj_2)

**Status:** recorded 2026-09-23
**Case:** `obj_2_ccw.stl` · RPM 25257 · `base_cell` 0.005 · 2 revolutions · `deltaT` 4e-5 s
**Solver:** `rhoPimpleFoam` + cylindrical `cyclicAMI` (`regime` compressible-AMI)
**Script:** `scripts/run_prop_ami_smoke.py`
**Stamp:** `validation/reference/drone_radial/cfd/obj_2_ccw_ami_smoke.json`
**Reference:** obj_2 MRF smoke thrust **938 g**. Band **703.5–1172.5 g**. Floor **10 g**.

| mean_thrust_g | samples | band_pass | band |
|---------------|---------|-----------|------|
| [mean_thrust_g from JSON, or "null"] | [thrust_g_samples] | [band_pass] | 703.5–1172.5 g |

**Interpretation:** [If band_pass is true: "The two-revolution sliding-mesh mean on the smoke mesh is inside the MRF band for this prop and RPM. This is not a time-averaged campaign and does not retire the obj_2 GCI caveat (~16% fine GCI)."] [If band_pass is false and the mean is finite: "The run finished and the mean is outside the MRF band (or under the 10 g floor). Recorded as a miss. Not datasheet-grade."] [If the mean is null: "Attempted. No finite mean. Reason: [reason]. Not stamped as a pass."]

AMI here is one short sliding-mesh smoke — not datasheet-grade. Forward-flight polars and bench calibration remain out of scope.
```

Replace the GCI section’s last sentence (`AMI/sliding mesh, forward-flight polars, and bench calibration remain out of scope.`) with: `Forward-flight polars and bench calibration remain out of scope. The obj_2 AMI smoke is a separate section below.`

- [ ] **Step 4: Update roadmap §4.3 and the spec status**

In `docs/roadmap.md`, replace:

```markdown
  **§4.3 screening stages** (parametric smoke + drone_radial smoke/refine/GCI + cockpit
  knobs) are in place. Remaining for a full tier: AMI/sliding,
  forward-flight polars, datasheet calibration — not claimed here (GCI is a screening stamp only).
```

with:

```markdown
  **drone_radial AMI smoke (2026-09-23):** obj_2 only, `rhoPimpleFoam` + `cyclicAMI`,
  two revolutions, mean thrust vs the 938 g MRF smoke band (±25%). Report
  `docs/validation/drone_radial_open_air_cfd.md`. Spec/plan:
  `docs/superpowers/specs/2026-09-23-prop-cfd-ami-smoke-design.md`,
  `docs/superpowers/plans/2026-09-23-prop-cfd-ami-smoke.md`.
  **§4.3 screening stages** (parametric smoke + drone_radial smoke/refine/GCI + AMI smoke + cockpit
  knobs) are in place. Remaining for a full tier: forward-flight polars, datasheet calibration.
  AMI is one obj_2 smoke, not a sliding-mesh campaign (GCI remains a screening stamp only).
```

In the spec, replace the status line with one of:

- Finished pass: `**Status:** implemented (2026-09-23) — obj_2 AMI smoke finished inside the MRF band`
- Finished miss: `**Status:** implemented (2026-09-23) — obj_2 AMI smoke finished outside the MRF band (honest miss)`
- Null mean: `**Status:** attempted (2026-09-23) — obj_2 AMI smoke produced no finite mean`

- [ ] **Step 5: Commit the stamp and the docs**

Do not stage `runs/` or `catalog/catalog.db` or `.superpowers/sdd/progress.md`.

If `mean_thrust_g` is finite, stage the stamp. If it is null, do not stage a stamp.

```bash
git add docs/validation/drone_radial_open_air_cfd.md docs/roadmap.md docs/superpowers/specs/2026-09-23-prop-cfd-ami-smoke-design.md
git add validation/reference/drone_radial/cfd/obj_2_ccw_ami_smoke.json
git commit -m "docs(prop): record obj_2 compressible AMI smoke"
```

Omit the stamp `git add` when the mean is null, and use commit message `docs(prop): record obj_2 AMI smoke attempt` instead.

---

## Self-review

Spec coverage: Task 1 is the band, floor, window, and exit codes. Task 2 is the sliding case and the MRF-path regression. Task 3 is the CLI, resume, null-mean failure JSON, and conditional stamp. Task 4 is the Docker run, honest miss, validation note, and roadmap. Non-goals (obj_1, DES, cockpit, fixture overwrite, MRF fallback) are global constraints, not extra tasks.

Placeholder scan: the validation table brackets are filled from `result.json` in Task 4 Step 3; they are not deferred design choices.
