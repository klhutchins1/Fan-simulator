# Prop Compressible Open-Air CFD (Stage 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Smoke-evaluate a drone prop in open air with steady compressible MRF (`rhoSimpleFoam`), reporting thrust/torque/power — without touching the ducted fan `simpleFoam` path.

**Architecture:** Parallel case builder under `fansim/propeller/cfd.py` sizes a far-field box from tip radius, writes compressible OpenFOAM templates (thermo + `T` + absolute `p`), meshes impeller-only, solves with `rhoSimpleFoam`, and parses the existing `forces` FO. CLI mirrors `evaluate_cror.py`. BEMT and fan CFD stay unchanged.

**Tech Stack:** Python 3.12 (uv), OpenFOAM v2406 Docker (`opencfd/openfoam-default:2406`), CadQuery/trimesh prop STL, pytest (no Docker in CI).

**Spec:** `docs/superpowers/specs/2026-09-07-prop-compressible-cfd-design.md`

## Global Constraints

- Do **not** overload `fansim.cfd.openfoam_case.build_case` with prop BCs; new builder only.
- Stamp exactly: `solver=rhoSimpleFoam`, `domain=open_air`, `regime=compressible-MRF`.
- Static thrust only: freestream `U = (0, 0, 0.1)` m/s (ε axial). No `V∞` sweep.
- Default smoke: `--spec fpv_5inch`, RPM = `0.7 * rpm_max`, tip Mach ≳ 0.3.
- Forces FO on `impeller`; parse thrust_z / torque_z (compressible: force in Newtons — do **not** multiply by `RHO_AIR`).
- No Optuna, cockpit, AMI, DES, FW-H, or fan-path changes.
- Unit tests: case wiring only (`-m "not docker and not slow"`). Manual Docker smoke.
- Skip staging `catalog/catalog.db`. Commit only when the user asks (plan steps may still list commits).

## File map

| File | Role |
|------|------|
| `fansim/propeller/cfd.py` | `PropOpenAir` domain, `build_prop_case`, `parse_prop_metrics`, `evaluate_prop_cfd` |
| `fansim/cfd/templates.py` | Compressible / open-air template strings (`PROP_*`) |
| `scripts/evaluate_prop_cfd.py` | Smoke CLI |
| `tests/test_prop_cfd.py` | Unit tests |
| `docs/roadmap.md` | §4.3 stage-1 note |
| `docs/superpowers/specs/2026-09-07-prop-compressible-cfd-design.md` | Mark implemented after smoke |

---

### Task 1: Open-air domain sizing

**Files:**
- Create: `fansim/propeller/cfd.py`
- Test: `tests/test_prop_cfd.py`

**Interfaces:**
- Consumes: tip radius in metres (caller converts mm)
- Produces:
  - `@dataclass PropOpenAir` with SI fields: `tip_radius`, `domain_radius`, `z_min`, `z_max`, `mrf_z_min`, `mrf_z_max`, `rpm`, `omega_signed`, `u_freestream` (default 0.1)
  - `prop_open_air(tip_radius_m, z_lo_m, z_hi_m, rpm, *, spin=-1, radial_mult=5.0, up_mult=2.0, down_mult=4.0, u_eps=0.1) -> PropOpenAir`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_prop_cfd.py
from __future__ import annotations
import math
import pytest

def test_prop_open_air_extents():
    from fansim.propeller.cfd import prop_open_air
    R = 0.0635  # 5-inch tip radius
    d = prop_open_air(R, z_lo_m=-0.01, z_hi_m=0.01, rpm=21000.0)
    assert d.domain_radius == pytest.approx(5.0 * R)
    assert d.z_min == pytest.approx(-0.01 - 2.0 * R)
    assert d.z_max == pytest.approx(0.01 + 4.0 * R)
    assert d.mrf_z_min < -0.01 and d.mrf_z_max > 0.01
    assert d.omega_signed == pytest.approx(-21000.0 * 2.0 * math.pi / 60.0)
    assert d.u_freestream == pytest.approx(0.1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_prop_cfd.py::test_prop_open_air_extents -v`  
Expected: FAIL — `ModuleNotFoundError` or missing `prop_open_air`.

- [ ] **Step 3: Minimal implementation**

```python
# fansim/propeller/cfd.py
"""Open-air compressible MRF evaluate for drone props (roadmap §4.3 stage 1)."""
from __future__ import annotations
import math
from dataclasses import dataclass

@dataclass
class PropOpenAir:
    tip_radius: float
    domain_radius: float
    z_min: float
    z_max: float
    mrf_z_min: float
    mrf_z_max: float
    rpm: float
    omega_signed: float
    u_freestream: float = 0.1

def prop_open_air(
    tip_radius_m: float,
    z_lo_m: float,
    z_hi_m: float,
    rpm: float,
    *,
    spin: int = -1,
    radial_mult: float = 5.0,
    up_mult: float = 2.0,
    down_mult: float = 4.0,
    u_eps: float = 0.1,
    mrf_margin_m: float = 0.005,
) -> PropOpenAir:
    R = float(tip_radius_m)
    omega = float(rpm) * 2.0 * math.pi / 60.0
    return PropOpenAir(
        tip_radius=R,
        domain_radius=radial_mult * R,
        z_min=z_lo_m - up_mult * R,
        z_max=z_hi_m + down_mult * R,
        mrf_z_min=z_lo_m - mrf_margin_m,
        mrf_z_max=z_hi_m + mrf_margin_m,
        rpm=float(rpm),
        omega_signed=float(spin) * omega,
        u_freestream=float(u_eps),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/test_prop_cfd.py::test_prop_open_air_extents -v`  
Expected: PASS

---

### Task 2: Compressible open-air templates

**Files:**
- Modify: `fansim/cfd/templates.py` (append `PROP_*` constants at end)
- Test: `tests/test_prop_cfd.py`

**Interfaces:**
- Produces string templates (placeholders `@NAME@`):
  - `PROP_THERMO` — `hePsiThermo` perfect gas air
  - `PROP_T` — `0/T` with freestream / wall BCs (`@U_WALLS@` style patches: inlet, outlet, walls, impeller)
  - `PROP_P` — absolute pressure Pa (`@P_INF@` = 101325)
  - `PROP_U` — freestream `(0 0 @U_EPS@)` on inlet/outlet/walls; noSlip impeller
  - `PROP_CONTROL_DICT` — `application rhoSimpleFoam;`, `forces` FO with `rho rho;` (field), **no** fan outletFlow/inletP FOs required
  - `PROP_MRF` — single zone `rotor` cellZone
  - Reuse existing `BLOCK_MESH`, `SNAPPY` patterns via builder mappings (empty frame/casing snippets)

- [ ] **Step 1: Write the failing test**

```python
def test_prop_templates_declare_rhosimple():
    from fansim.cfd import templates as T
    assert "rhoSimpleFoam" in T.PROP_CONTROL_DICT
    assert "hePsiThermo" in T.PROP_THERMO or "perfectGas" in T.PROP_THERMO
    assert "forces" in T.PROP_CONTROL_DICT
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_prop_cfd.py::test_prop_templates_declare_rhosimple -v`  
Expected: FAIL — missing `PROP_CONTROL_DICT`.

- [ ] **Step 3: Add templates**

Append to `fansim/cfd/templates.py` (abbreviated; expand BCs to match fan patch names `inlet` `outlet` `walls` `impeller`):

```python
PROP_THERMO = """@HEADER@
thermoType
{
    type            hePsiThermo;
    mixture         pureMixture;
    transport       const;
    thermo          hConst;
    equationOfState perfectGas;
    specie          specie;
    energy          sensibleInternalEnergy;
}
mixture
{
    specie { molWeight 28.9; }
    thermodynamics { Cp 1005; Hf 0; }
    transport { mu 1.8e-05; Pr 0.7; }
}
"""

PROP_CONTROL_DICT = """@HEADER@
application     rhoSimpleFoam;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         @ENDTIME@;
deltaT          1;
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
        writeInterval   @FOINT@;
    }
}
"""

PROP_MRF = """@HEADER@
MRF1
{
    cellZone            rotor;
    active              yes;
    nonRotatingPatches  (walls inlet outlet);
    origin              (0 0 0);
    axis                (0 0 1);
    omega               @OMEGA@;
}
"""
```

Also add `PROP_T`, `PROP_P`, `PROP_U`, `PROP_K`, `PROP_OMEGA`, `PROP_NUT`, `PROP_FV_SCHEMES`, `PROP_FV_SOLUTION`, `PROP_TURBULENCE` suitable for compressible SST (mirror DES/fan patterns; `p` is absolute; initial `p = 101325`). Use freestream / `inletOutlet` where OpenFOAM v2406 expects them for open boundaries.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/test_prop_cfd.py::test_prop_templates_declare_rhosimple -v`  
Expected: PASS

---

### Task 3: `build_prop_case` (dry wiring)

**Files:**
- Modify: `fansim/propeller/cfd.py`
- Test: `tests/test_prop_cfd.py`

**Interfaces:**
- Consumes: `PropOpenAir`, impeller STL (mm), `MeshResolution` from `fansim.cfd.openfoam_case`
- Produces: `build_prop_case(case_dir, impeller_stl_mm, domain: PropOpenAir, *, mesh=None, n_iters=400, n_subdomains=8) -> Path`
  - Scales STL mm→m into `constant/triSurface/impeller.stl`
  - Hex domain: `±domain_radius` in X/Y, `z_min`…`z_max`
  - `topoSet` cylinder cellZone `rotor` radius=`domain_radius` (or tip+margin), z=`mrf_z_*`
  - Writes `PROP_*` dicts; **no** frame/casing
  - `controlDict` application is `rhoSimpleFoam`

- [ ] **Step 1: Write the failing test**

```python
def test_build_prop_case_writes_compressible(tmp_path):
    from fansim.propeller.cfd import prop_open_air, build_prop_case
    from fansim.propeller.geometry import build_prop
    from fansim.prop_spec import get_prop_spec
    from fansim.cfd.openfoam_case import MeshResolution

    spec = get_prop_spec("fpv_5inch")
    stl = tmp_path / "prop.stl"
    build_prop(spec, stl)
    # bounds from report
    from fansim.geometry import watertight_report
    rep = watertight_report(stl)
    (_, _, z0), (_, _, z1) = rep.bounds_mm
    R = spec.diameter_mm / 2000.0
    dom = prop_open_air(R, z0 / 1000.0, z1 / 1000.0, rpm=0.7 * spec.rpm_max)
    case = tmp_path / "case"
    build_prop_case(case, stl, dom, mesh=MeshResolution(base_cell=0.01), n_iters=10, n_subdomains=2)
    ctrl = (case / "system/controlDict").read_text(encoding="utf-8")
    assert "rhoSimpleFoam" in ctrl
    assert (case / "constant/thermophysicalProperties").is_file()
    assert (case / "0/T").is_file()
    mrf = (case / "constant/MRFProperties").read_text(encoding="utf-8")
    assert "rotor" in mrf
    assert "omega" in mrf.lower() or str(int(dom.omega_signed))[:4] in mrf or "omega" in mrf
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_prop_cfd.py::test_build_prop_case_writes_compressible -v --tb=short`  
Expected: FAIL — `build_prop_case` missing.

- [ ] **Step 3: Implement `build_prop_case`**

Reuse helpers from `openfoam_case.py` where possible (`_write`, `_header`, `snappy_layers_mapping`, empty wall snippets). Key differences vs fan:
- Square/hex box sized from `PropOpenAir` (not `TestRig.duct_radius`)
- Patch BCs: freestream / freestreamPressure / inletOutlet — **not** totalPressure hose mode
- Skip `transportProperties` nu-only; write `thermophysicalProperties` instead
- Single MRF zone named `rotor` (topoSet cylinder)

TopoSet cylinder radius: `1.05 * tip_radius` (must enclose blades; domain is larger).

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/test_prop_cfd.py::test_build_prop_case_writes_compressible -v --tb=short`  
Expected: PASS (CadQuery may make this ~1–2 min).

---

### Task 4: Metrics parse + `evaluate_prop_cfd`

**Files:**
- Modify: `fansim/propeller/cfd.py`
- Test: `tests/test_prop_cfd.py`

**Interfaces:**
- Produces:
  - `parse_prop_metrics(case_dir, omega_rad_s) -> dict` with keys `thrust_n`, `thrust_g`, `torque_nm`, `shaft_power_w` (finite floats). Read `postProcessing/forces/*/force.dat` and `moment.dat` like `parse_fan_metrics`, but **no** flow/pressure CFM path and **no** `* RHO_AIR` on forces.
  - `evaluate_prop_cfd(spec, workdir, *, rpm=None, iters=400, procs=8, base_cell=0.005) -> dict`  
    Builds STL, domain from bounds, `build_prop_case`, `run_mesh`, `run_solve` (same runner as fan — `simpleFoam` command must become `rhoSimpleFoam`: either write controlDict application and call a thin `run_solve_prop` that runs `rhoSimpleFoam -parallel`, or generalize `run_solve` to read application from controlDict). **Prefer** `run_solve_prop(runner, n_procs)` that hardcodes `rhoSimpleFoam` so fan path stays untouched.
  - Result stamps: `solver`, `domain`, `regime`, `tip_mach`, `rpm`, `spec`.

- [ ] **Step 1: Write the failing test (parse only — synthetic FO)**

```python
def test_parse_prop_metrics_from_forces(tmp_path):
    from fansim.propeller.cfd import parse_prop_metrics
    fo = tmp_path / "postProcessing" / "forces" / "100"
    fo.mkdir(parents=True)
    # time total(x y z) pressure... viscous...
    (fo / "force.dat").write_text(
        "#\n100  (0 0 12.5) (0 0 12) (0 0 0.5)\n", encoding="utf-8")
    (fo / "moment.dat").write_text(
        "#\n100  (0 0 -0.4) (0 0 -0.4) (0 0 0)\n", encoding="utf-8")
    m = parse_prop_metrics(tmp_path, omega_rad_s=1000.0)
    assert m["thrust_n"] == pytest.approx(12.5)
    assert m["thrust_g"] == pytest.approx(12.5 / 9.80665 * 1000.0, rel=1e-3)
    assert m["torque_nm"] == pytest.approx(0.4)
    assert m["shaft_power_w"] == pytest.approx(0.4 * 1000.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_prop_cfd.py::test_parse_prop_metrics_from_forces -v`  
Expected: FAIL — missing `parse_prop_metrics`.

- [ ] **Step 3: Implement parse + evaluate**

```python
def parse_prop_metrics(case_dir, omega_rad_s: float) -> dict:
    from fansim.cfd.metrics import _last_data_row, _pp_file
    case_dir = Path(case_dir)
    force = _last_data_row(_pp_file(case_dir, "forces", "force.dat"))
    moment = _last_data_row(_pp_file(case_dir, "forces", "moment.dat"))
    thrust = float(force[3])
    torque = abs(float(moment[3]))
    return {
        "thrust_n": thrust,
        "thrust_g": thrust / 9.80665 * 1000.0,
        "torque_nm": torque,
        "shaft_power_w": torque * float(omega_rad_s),
    }

def run_solve_prop(runner, n_procs: int = 8) -> None:
    # mirror run_solve but application rhoSimpleFoam
    ...

def evaluate_prop_cfd(spec, workdir, *, rpm=None, iters=400, procs=8, base_cell=0.005) -> dict:
    ...
```

`evaluate_prop_cfd` must stamp:
```python
out["solver"] = "rhoSimpleFoam"
out["domain"] = "open_air"
out["regime"] = "compressible-MRF"
out["tip_mach"] = spec.tip_mach(rpm)
out["rpm"] = rpm
out["spec"] = spec.name  # or registry key if passed
```

- [ ] **Step 4: Run parse test**

Run: `uv run python -m pytest tests/test_prop_cfd.py::test_parse_prop_metrics_from_forces -v`  
Expected: PASS

---

### Task 5: CLI + unit flags + roadmap

**Files:**
- Create: `scripts/evaluate_prop_cfd.py`
- Modify: `tests/test_prop_cfd.py`, `docs/roadmap.md`, spec status when smoke done
- Test: CLI text asserts + optional tip-Mach default

**Interfaces:**
- CLI args: `--spec` (default `fpv_5inch`), `--rpm` (default `None` → `0.7 * rpm_max`), `--iters`, `--procs`, `--base-cell`, `--out`, `--dry-run`
- `--dry-run`: build case only, write `dry_run.json` with domain + stamps (no Docker)

- [ ] **Step 1: Write failing CLI test**

```python
def test_cli_evaluate_prop_cfd_declares_flags():
    text = Path("scripts/evaluate_prop_cfd.py").read_text(encoding="utf-8")
    assert "--dry-run" in text
    assert "rhoSimpleFoam" in text or "prop" in text.lower()
    assert "--spec" in text
    assert "fpv_5inch" in text
```

- [ ] **Step 2: Implement CLI** (mirror `scripts/evaluate_cror.py` structure)

- [ ] **Step 3: Tip-Mach default test**

```python
def test_default_rpm_tip_mach_compressible():
    from fansim.prop_spec import get_prop_spec
    spec = get_prop_spec("fpv_5inch")
    rpm = 0.7 * spec.rpm_max
    assert spec.tip_mach(rpm) > 0.3
```

- [ ] **Step 4: Run all unit tests**

Run: `uv run python -m pytest tests/test_prop_cfd.py -q --tb=short`  
Expected: all PASS (ignore CadQuery ACCESS_VIOLATION teardown exit code if assertions passed).

- [ ] **Step 5: Update roadmap §4.3**

Mark stage-1 smoke evaluate done after Docker smoke (or note “wiring done; smoke pending” if Docker deferred). Update `docs/roadmap.md` “Last reviewed” line.

---

### Task 6: Manual Docker smoke

**Files:**
- Produce: `runs/prop_cfd_smoke/result.json` (gitignored) + optional `notes.md` in that folder
- Modify: spec status → `implemented` when green

- [ ] **Step 1: Dry-run**

Run: `uv run python scripts/evaluate_prop_cfd.py --dry-run --out runs/prop_cfd_smoke`  
Expected: `dry_run.json` with `solver`/`domain` stamps; case has `rhoSimpleFoam`.

- [ ] **Step 2: Full smoke (when Docker image present)**

Run: `uv run python scripts/evaluate_prop_cfd.py --out runs/prop_cfd_smoke --iters 300 --procs 8 --base-cell 0.005`  
Expected: `feasible`/finite `thrust_g`, `solver=rhoSimpleFoam`, runtime logged. Order-of-magnitude vs `ref_thrust_g` optional note (do not fail if within ~2× at mid RPM — thrust scales with RPM²).

- [ ] **Step 3: Spec + roadmap final stamps**

Set design spec **Status:** `implemented (Docker smoke …)` and §4.3 remaining: BEMT-gate / Optuna / forward flight.

---

## Spec coverage checklist

| Spec requirement | Task |
|------------------|------|
| Open-air domain ~5R / 2R / 4R + ε freestream | Task 1 |
| `build_prop_case` compressible templates, impeller-only | Tasks 2–3 |
| `evaluate_prop_cfd` + force metrics + stamps | Task 4 |
| CLI `--spec fpv_5inch` / dry-run | Task 5 |
| Unit tests, no Docker CI | Tasks 1–5 |
| Manual Docker smoke | Task 6 |
| Non-goals (no Optuna/AMI/fan overwrite) | Global constraints |

## Self-review notes

- No TBD placeholders; `run_solve_prop` explicitly preferred over mutating fan `run_solve`.
- Force parsing does not reuse `parse_fan_metrics` (kinematic-p × ρ would be wrong / CFM irrelevant).
- `PROP_*` template names avoid colliding with fan `CONTROL_DICT`.
