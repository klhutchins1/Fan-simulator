# OpenFOAM DES + permeable FW-H (stage A) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One-shot runner that meshes/solves a short OpenFOAM DES transient on a fixed permeable box, reduces six-face loads with existing Farassat 1A panels, and writes `analogy=openfoam_des_fwh` JSON — no NSGA, no catalog mix, no 22.6 dB(A) claim.

**Architecture:** Keep today’s snappy/MRF case builder. Add a DES overlay (pimpleFoam + kOmegaSSTDES + six `surfaceFieldValue` face samplers). Collect face forces into the same CSV contract as LBM permeable. Reduce via `fansim/cfd/des_fwh.py` → `analyze_permeable_csv` + stamp overrides. CLI `scripts/evaluate_des_fwh.py` owns mesh→solve→reduce.

**Tech Stack:** Python 3.12 (uv), OpenFOAM v2406 Docker (`opencfd/openfoam-default:2406`), existing `fansim.acoustics.fwh`, pytest (no Docker in CI).

**Spec:** `docs/superpowers/specs/2026-09-06-openfoam-des-fwh-design.md`

## Global Constraints

- Stamp exactly: `analogy=openfoam_des_fwh`, `turbulence=kOmegaSSTDES`, `rotation=MRF`, `surface=permeable_box`.
- CSV contract: `t_s, F0x,F0y,F0z, …, F5x,F5y,F5z` face order `+x,-x,+y,-y,+z,-z` (same as LBM permeable).
- Box geometry: reuse `cv_box_from_dia_mm` / sidecar keys `cx_m,cy_m,cz_m,half_xy_m,half_z_m`.
- Steady `simpleFoam` path unchanged; DES is opt-in only.
- No libAcoustics, no AMI/sliding mesh, no NSGA/cockpit, no catalog Curle mixing.
- Unit tests: synthetic CSV only — never require Docker/GPU (`-m "not docker and not slow"` stays green).
- Do not claim calibrated dB(A). Document MRF honesty in runner docstring + short `docs/openfoam-des-fwh.md`.
- Skip staging `catalog/catalog.db`. Commit only if the user explicitly asks (plan steps may still list commits).

## File map

| File | Role |
|------|------|
| `fansim/cfd/des_fwh.py` | Box sidecar IO, FO→CSV collector, `reduce_des_permeable` stamp helper |
| `fansim/cfd/templates.py` | DES controlDict / turbulence / fvSchemes / fvSolution / FO snippets |
| `fansim/cfd/openfoam_case.py` | `apply_des_transient(...)`, `run_solve_des(...)` |
| `scripts/evaluate_des_fwh.py` | End-to-end CLI |
| `tests/test_des_fwh.py` | Unit tests (reduction, collector, CLI flags) |
| `docs/openfoam-des-fwh.md` | Operator note + honesty |
| `docs/roadmap.md` | §1.4 stage A note |

---

### Task 1: Reduction stamp helper

**Files:**
- Create: `fansim/cfd/des_fwh.py`
- Test: `tests/test_des_fwh.py`

**Interfaces:**
- Consumes: `fansim.acoustics.fwh.analyze_permeable_csv`, `cv_box_from_dia_mm`
- Produces:
  - `reduce_des_permeable(csv, box=None, *, dia_mm=None, cutoff_hz=2500.0, **kw) -> dict`
  - Returns same keys as permeable FW-H plus required DES stamps (overrides `analogy`)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_des_fwh.py
from __future__ import annotations
from pathlib import Path
import numpy as np
import pytest

def _write_six_face_csv(path: Path, n: int = 200, fs: float = 20000.0):
    t = np.arange(n) / fs
    # small BPF-like Fz on +z face only
    bpf = 7 * 2000 / 60
    rows = []
    for ti in t:
        F = [0.0] * 18
        F[14] = 0.02 * np.sin(2 * np.pi * bpf * ti)  # F4z (+z face)
        rows.append((ti, *F))
    hdr = "t_s," + ",".join(
        f"F{i}{c}" for i in range(6) for c in "xyz"
    )
    with path.open("w", encoding="utf-8") as f:
        f.write(hdr + "\n")
        for r in rows:
            f.write(",".join(f"{x:.8g}" for x in r) + "\n")


def test_reduce_des_permeable_stamps_analogy(tmp_path):
    from fansim.cfd.des_fwh import reduce_des_permeable
    csv = tmp_path / "face_loads.csv"
    _write_six_face_csv(csv)
    m = reduce_des_permeable(csv, dia_mm=110.5)
    assert m["analogy"] == "openfoam_des_fwh"
    assert m["turbulence"] == "kOmegaSSTDES"
    assert m["rotation"] == "MRF"
    assert m["surface"] == "permeable_box"
    assert m["n_panels"] == 6
    assert np.isfinite(m["noise_dba_band"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_des_fwh.py::test_reduce_des_permeable_stamps_analogy -v`  
Expected: FAIL — `ModuleNotFoundError` or import error for `fansim.cfd.des_fwh`.

- [ ] **Step 3: Minimal implementation**

```python
# fansim/cfd/des_fwh.py
"""OpenFOAM DES permeable-box FW-H helpers (stage A)."""
from __future__ import annotations
from pathlib import Path
import json
from fansim.acoustics.fwh import analyze_permeable_csv, cv_box_from_dia_mm

def reduce_des_permeable(csv, box=None, *, dia_mm=None, cutoff_hz=2500.0, **kw) -> dict:
    m = analyze_permeable_csv(csv, box=box, dia_mm=dia_mm, cutoff_hz=cutoff_hz, **kw)
    m = dict(m)
    m["analogy"] = "openfoam_des_fwh"
    m["turbulence"] = "kOmegaSSTDES"
    m["rotation"] = "MRF"
    m["surface"] = "permeable_box"
    return m
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/test_des_fwh.py::test_reduce_des_permeable_stamps_analogy -v`  
Expected: PASS

---

### Task 2: Box sidecar + face-load CSV collector

**Files:**
- Modify: `fansim/cfd/des_fwh.py`
- Test: `tests/test_des_fwh.py`

**Interfaces:**
- Produces:
  - `write_box_sidecar(path, box: dict) -> Path` — JSON with the five SI keys (+ optional `dia_mm`)
  - `read_box_sidecar(path) -> dict`
  - `collect_face_loads_csv(case_dir: Path | str, out_csv: Path | str, *, box: dict) -> Path`  
    Reads six OpenFOAM `surfaceFieldValue` histories under  
    `postProcessing/desFace{0..5}/0/surfaceFieldValue.dat`  
    (columns: Time + areaNormalIntegrate of `p` → Fx,Fy,Fz via face normal × scalar).  
    Writes permeable CSV. If a face file is missing, raise `FileNotFoundError` with the path.

**OpenFOAM FO contract (must match Task 3 templates):**
- FO names: `desFace0` … `desFace5`
- Each writes `areaNormalIntegrate` of field `p` → one scalar per time; force vector = scalar × face outward normal (`_FACE_NORMALS` from fwh order).
- For incompressible OF, `p` is kinematic (`m²/s²`); multiply by `rho=1.2` when forming Newton forces so FW-H units match LBM (document constant `RHO_AIR = 1.2` in `des_fwh.py`).

- [ ] **Step 1: Write failing tests**

```python
def test_box_sidecar_roundtrip(tmp_path):
    from fansim.acoustics.fwh import cv_box_from_dia_mm
    from fansim.cfd.des_fwh import write_box_sidecar, read_box_sidecar
    box = cv_box_from_dia_mm(110.5)
    p = write_box_sidecar(tmp_path / "box.json", box)
    b2 = read_box_sidecar(p)
    assert b2["half_xy_m"] == pytest.approx(box["half_xy_m"])
    assert b2["half_z_m"] == pytest.approx(box["half_z_m"])


def test_collect_face_loads_csv_from_fo(tmp_path):
    from fansim.acoustics.fwh import cv_box_from_dia_mm
    from fansim.cfd.des_fwh import collect_face_loads_csv, reduce_des_permeable
    case = tmp_path / "case"
    normals = [
        (1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1),
    ]
    for i, n_hat in enumerate(normals):
        d = case / "postProcessing" / f"desFace{i}" / "0"
        d.mkdir(parents=True)
        # OpenFOAM-ish: comment header then Time value
        lines = ["# Time areaNormal(p)", "0.001 1.0", "0.002 1.1"]
        (d / "surfaceFieldValue.dat").write_text("\n".join(lines) + "\n", encoding="utf-8")
    out = case / "face_loads.csv"
    collect_face_loads_csv(case, out, box=cv_box_from_dia_mm(110.5))
    text = out.read_text(encoding="utf-8")
    assert text.splitlines()[0].startswith("t_s,")
    m = reduce_des_permeable(out, dia_mm=110.5)
    assert m["analogy"] == "openfoam_des_fwh"
```

- [ ] **Step 2: Run tests — expect FAIL** (functions missing)

Run: `uv run python -m pytest tests/test_des_fwh.py::test_box_sidecar_roundtrip tests/test_des_fwh.py::test_collect_face_loads_csv_from_fo -v`

- [ ] **Step 3: Implement sidecar + collector**

Parse FO `.dat` files: skip `#` lines; columns `Time`, scalar.  
`F_i = (rho * scalar) * n_hat` with `RHO_AIR=1.2`.  
Require identical time vectors across faces (atol 1e-12) or raise `ValueError`.

- [ ] **Step 4: Run tests — expect PASS**

---

### Task 3: DES templates + `apply_des_transient`

**Files:**
- Modify: `fansim/cfd/templates.py` (append DES string constants)
- Modify: `fansim/cfd/openfoam_case.py` (add `apply_des_transient`)
- Test: `tests/test_des_fwh.py`

**Interfaces:**
- Produces: `apply_des_transient(case_dir, *, box: dict, delta_t: float, end_time: float, write_interval: int = 1, fo_interval: int = 1) -> Path`  
  Overwrites/writes:
  - `constant/turbulenceProperties` → LES `kOmegaSSTDES`
  - `system/controlDict` → `application pimpleFoam;` adjustable / fixed `deltaT`/`endTime`; libs empty; functions block with six `surfaceFieldValue` cutting-plane FOs named `desFace0..5` at box face centers, `areaNormalIntegrate` on `p`
  - `system/fvSchemes` / `system/fvSolution` DES-capable (PIMPLE) templates
  - Does **not** remesh. Assumes case already built by `build_case`.
  - Writes `constant/des_perm_box.json` via `write_box_sidecar`

**Cutting plane FO sketch (each face):**

```cpp
desFace0
{
    type            surfaceFieldValue;
    libs            ("libfieldFunctionObjects.so");
    writeControl    timeStep;
    writeInterval   1;
    log             false;
    writeFields     false;
    regionType      sampledSurface;
    name            desFace0;
    sampledSurfaceDict
    {
        type        plane;
        planeType   pointAndNormal;
        pointAndNormalDict
        {
            point   (@CX@ @CY@ @CZ@);   // face center
            normal  (1 0 0);            // outward
        }
    }
    operation       areaNormalIntegrate;
    fields          (p);
}
```

Map face index → center from box + normal from fwh order.

- [ ] **Step 1: Failing test**

```python
def test_apply_des_transient_writes_pimple_and_faces(tmp_path):
    from fansim.acoustics.fwh import cv_box_from_dia_mm
    from fansim.cfd.openfoam_case import apply_des_transient
    case = tmp_path / "case"
    (case / "system").mkdir(parents=True)
    (case / "constant").mkdir(parents=True)
    # minimal stubs so overwrite is obvious
    (case / "system/controlDict").write_text("application     simpleFoam;\n", encoding="utf-8")
    (case / "constant/turbulenceProperties").write_text("simulationType RAS;\n", encoding="utf-8")
    apply_des_transient(case, box=cv_box_from_dia_mm(110.5), delta_t=1e-5, end_time=1e-3)
    cd = (case / "system/controlDict").read_text(encoding="utf-8")
    assert "pimpleFoam" in cd
    assert "desFace0" in cd and "desFace5" in cd
    turb = (case / "constant/turbulenceProperties").read_text(encoding="utf-8")
    assert "kOmegaSSTDES" in turb
    assert (case / "constant/des_perm_box.json").is_file()
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Add template strings + `apply_des_transient`**

Keep RAS templates intact. New constants e.g. `DES_TURBULENCE`, `DES_CONTROL_DICT`, `DES_FV_SCHEMES`, `DES_FV_SOLUTION`. Prefer rewriting whole files for DES overlay (stage A), not surgical edit of steady controlDict.

Also ensure `0/` fields still valid for LES (existing `k`/`omega`/`nut` from `build_case` are OK for SST-DES cold start).

- [ ] **Step 4: Run — expect PASS**

---

### Task 4: `run_solve_des`

**Files:**
- Modify: `fansim/cfd/openfoam_case.py`
- Test: `tests/test_des_fwh.py` (source/string check only — no Docker)

**Interfaces:**
- Produces: `run_solve_des(runner, n_procs: int = 8, reconstruct: bool = False) -> None`  
  Same cleanup as `run_solve` (`rm -rf processor* postProcessing`), `decomposePar`, optional `potentialFoam`, then **`pimpleFoam`** (not simpleFoam).

- [ ] **Step 1: Failing test**

```python
def test_run_solve_des_declares_pimple():
    from pathlib import Path
    text = Path("fansim/cfd/openfoam_case.py").read_text(encoding="utf-8")
    assert "def run_solve_des" in text
    assert "pimpleFoam" in text
```

- [ ] **Step 2–4:** Implement by cloning `run_solve` and swapping the solver binary; run test PASS.

---

### Task 5: CLI `evaluate_des_fwh.py`

**Files:**
- Create: `scripts/evaluate_des_fwh.py`
- Test: `tests/test_des_fwh.py`

**Interfaces:**
- CLI:
  ```text
  uv run python scripts/evaluate_des_fwh.py --stl PATH [--out DIR]
      [--procs 8] [--delta-t 1e-5] [--end-time 0.01]
      [--dia-mm 110.5] [--base-cell 0.005] [--csv-only PATH]
  ```
- `--csv-only`: skip CFD; only reduce an existing face-load CSV (+ optional `--box-json`) and write JSON (for unit/smoke without Docker).
- Full path (Docker): build case via existing evaluate helpers (reuse frame+casing pattern from `evaluate_candidate` / campaign scripts — prefer importing `build_case`, `TestRig`, `build_frame`, circular casing), `run_mesh`, `apply_des_transient`, `run_solve_des`, `collect_face_loads_csv`, `reduce_des_permeable`, write `des_fwh.json` + copy CSV under `--out`.

**Default STL:** `build/a12x25_real_capped.stl` if `--stl` omitted and file exists; else error with a clear message.

- [ ] **Step 1: Failing tests**

```python
def test_evaluate_des_fwh_declares_flags():
    text = Path("scripts/evaluate_des_fwh.py").read_text(encoding="utf-8")
    assert "--csv-only" in text
    assert "openfoam_des_fwh" in text or "des_fwh" in text
    assert "★" not in text


def test_csv_only_writes_json(tmp_path):
    # subprocess or import main helper
    from fansim.cfd.des_fwh import reduce_des_permeable, write_box_sidecar
    from fansim.acoustics.fwh import cv_box_from_dia_mm
    csv = tmp_path / "face_loads.csv"
    _write_six_face_csv(csv)
    box = cv_box_from_dia_mm(110.5)
    write_box_sidecar(tmp_path / "box.json", box)
    m = reduce_des_permeable(csv, box=box)
    out = tmp_path / "des_fwh.json"
    out.write_text(__import__("json").dumps(m, indent=2), encoding="utf-8")
    assert '"analogy": "openfoam_des_fwh"' in out.read_text(encoding="utf-8")
```

Also add a thin `main()` path test: run module with `--csv-only` via `subprocess` or argparse `main` if factored.

- [ ] **Step 2–4:** Implement CLI; csv-only path must work without Docker. Full path may stay lightly smoke-tested manually.

---

### Task 6: Docs + roadmap note

**Files:**
- Create: `docs/openfoam-des-fwh.md`
- Modify: `docs/roadmap.md` §1.4 Remaining line

**Content for `docs/openfoam-des-fwh.md`:**
- What stage A is / is not (MRF, permeable box, not mic-calibrated)
- Commands: csv-only vs full Docker
- FO naming + CSV contract
- Pointer to spec

**Roadmap:** Under §1.4 Remaining, add:  
`OpenFOAM DES+FW-H stage A (pimple + permeable box → openfoam_des_fwh): scripts/evaluate_des_fwh.py — DONE <date> when green;` keep libAcoustics / absolute cal / prop FW-H as later.

- [ ] **Step 1:** Write the doc + roadmap note (no unit test; manually verify links).
- [ ] **Step 2:** Optional: mark plan tasks complete in this file’s checkboxes as you go.

---

## Spec coverage checklist

| Spec requirement | Task |
|------------------|------|
| pimpleFoam + kOmegaSSTDES | 3, 4 |
| MRF kept + stamped | 1, 3, 5 |
| Six-face permeable CSV | 2, 3 |
| Reuse Farassat panel kernel | 1 |
| `analogy=openfoam_des_fwh` + honesty stamps | 1 |
| CLI evaluate_des_fwh | 5 |
| Unit tests no Docker DES | 1–5 |
| Docs + roadmap | 6 |
| Non-goals (libAcoustics, NSGA, AMI, 22.6) | Global + docs |

## Placeholder / consistency scan

- Face FO names consistently `desFace0..5`.
- Rho factor `1.2` documented once in `des_fwh.py`.
- No TBD steps.

---

## Manual Docker smoke (after Task 5)

```bash
uv run python scripts/evaluate_des_fwh.py \
  --stl build/a12x25_real_capped.stl \
  --out runs/campaign_des_fwh \
  --procs 8 --end-time 0.002 --delta-t 2e-5
```

Expect `runs/campaign_des_fwh/des_fwh.json` with `analogy=openfoam_des_fwh`. Short `end-time` is OK for plumbing; longer window is operator choice.
