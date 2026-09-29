"""OpenFOAM DES permeable-box FW-H helpers (stage A).

Collects six-face force histories from ``surfaceFieldValue`` function objects and
reduces them with the Farassat 1A panel kernel. Stamps ``analogy=openfoam_des_fwh``.
Not calibrated dB(A); MRF rotation is an honesty limitation.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from fansim.acoustics.fwh import (
    _FACE_NORMALS,
    analyze_permeable_csv,
    cv_box_from_dia_mm,
)

# Match openfoam_case.RHO_AIR — OF stores kinematic p; force [N] = rho * ∫ p n dA
from fansim.physics.air import RHO_AMCA as RHO_AIR
# Default DES observer (m). Keep r/c0 << typical short DES windows.
DEFAULT_X_OBS = (0.0, 0.0, 0.2)

def box_from_duct(
    duct_radius_m: float,
    *,
    half_z_m: float = 0.045,
    cz_m: float = 0.0,
    radial_frac: float = 0.90,
) -> dict:
    """Permeable box that fits inside an OpenFOAM duct (not the LBM CV lattice).

    ``cv_box_from_dia_mm`` follows FluidX3D noise geometry and can place face planes
    outside a tighter snappy duct — which makes ``surfaceFieldValue`` fatal.
    """
    r = float(duct_radius_m)
    return {
        "cx_m": 0.0,
        "cy_m": 0.0,
        "cz_m": float(cz_m),
        "half_xy_m": float(radial_frac) * r,
        "half_z_m": float(half_z_m),
    }

def reduce_des_permeable(
    csv,
    box=None,
    *,
    dia_mm=None,
    cutoff_hz=2500.0,
    x_obs=(0.0, 0.0, 0.2),
    **kw,
) -> dict:
    """Reduce a six-face permeable CSV and stamp OpenFOAM DES analogy metadata.

    Default observer is 0.2 m on +z (not 1 m): short DES windows are often only a few
    milliseconds, and ``r/c0`` at 1 m (~3 ms) would put every retarded sample before
    the force history → silent ``-inf`` dB.
    """
    m = analyze_permeable_csv(
        csv, box=box, dia_mm=dia_mm, cutoff_hz=cutoff_hz, x_obs=x_obs, **kw
    )
    m = dict(m)
    m["analogy"] = "openfoam_des_fwh"
    m["turbulence"] = "kOmegaSSTDES"
    m["rotation"] = "MRF"
    m["surface"] = "permeable_box"
    m["r_obs_m"] = float(np.linalg.norm(np.asarray(x_obs, float)))
    return m


def write_box_sidecar(path, box: dict) -> Path:
    """Write permeable-box SI geometry JSON (cx/cy/cz, half_xy, half_z, optional dia_mm)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = ("cx_m", "cy_m", "cz_m", "half_xy_m", "half_z_m")
    payload = {k: float(box[k]) for k in keys}
    if "dia_mm" in box:
        payload["dia_mm"] = float(box["dia_mm"])
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def read_box_sidecar(path) -> dict:
    """Load a box sidecar written by ``write_box_sidecar``."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {k: float(data[k]) for k in ("cx_m", "cy_m", "cz_m", "half_xy_m", "half_z_m")
            } | ({"dia_mm": float(data["dia_mm"])} if "dia_mm" in data else {})


def _parse_surface_field_value(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Parse OpenFOAM surfaceFieldValue.dat → (time, scalar)."""
    times: list[float] = []
    vals: list[float] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.replace(",", " ").split()
        if len(parts) < 2:
            continue
        times.append(float(parts[0]))
        vals.append(float(parts[1]))
    if not times:
        raise ValueError(f"no data rows in {path}")
    return np.asarray(times, float), np.asarray(vals, float)


def collect_face_loads_csv(case_dir, out_csv, *, box: dict | None = None) -> Path:
    """Build permeable face-load CSV from desFace0..5 surfaceFieldValue histories.

    Each FO writes ``areaIntegrate(p)`` (kinematic). Force [N] =
    ``RHO_AIR * scalar * n_hat`` with face order +x,-x,+y,-y,+z,-z.
    (``areaNormalIntegrate`` on cutting planes was returning exact zeros in OF2406.)
    """
    case_dir = Path(case_dir)
    out_csv = Path(out_csv)
    if box is None:
        side = case_dir / "constant" / "des_perm_box.json"
        box = read_box_sidecar(side) if side.is_file() else cv_box_from_dia_mm(110.5)

    times = None
    forces = []  # list of (n, 3)
    for i, n_hat in enumerate(_FACE_NORMALS):
        fo = case_dir / "postProcessing" / f"desFace{i}" / "0" / "surfaceFieldValue.dat"
        if not fo.is_file():
            raise FileNotFoundError(fo)
        t, scalar = _parse_surface_field_value(fo)
        if times is None:
            times = t
        elif t.shape != times.shape or not np.allclose(t, times, atol=1e-12, rtol=0.0):
            raise ValueError(f"time vector mismatch for desFace{i}: {fo}")
        n = np.asarray(n_hat, float)
        F = (RHO_AIR * scalar)[:, None] * n[None, :]
        forces.append(F)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    hdr = "t_s," + ",".join(f"F{i}{c}" for i in range(6) for c in "xyz")
    with out_csv.open("w", encoding="utf-8") as f:
        f.write(hdr + "\n")
        for j, tj in enumerate(times):
            row = [tj]
            for Fi in forces:
                row.extend(Fi[j].tolist())
            f.write(",".join(f"{x:.8g}" for x in row) + "\n")
    return out_csv
