"""Far-field FW-H loading (Farassat 1A compact / discrete panels).

Compact Curle in ``farfield.dipole_pressure`` uses the near-field 1/r² kernel. This module is the
far-field loading term:

    p'(x, t) = (r_hat · Ḟ(t_ret)) / (4 π c₀² r)     t_ret = t - r/c₀

A compact source at the origin: the delay is a pure shift and does not change SPL. Several panels
at different r can (permeable six-face or 2×2 face patches). This is **not** calibrated dB(A).
Do not mix these numbers with catalog Curle rows.
"""

from __future__ import annotations

import numpy as np

from fansim.acoustics.farfield import (
    C0_AIR,
    N_BLADES_DEFAULT,
    RPM_DEFAULT,
    blade_pass_frequency,
    dba_from_pressure,
    peak_tone_over_harmonics,
    tone_level_db,
)

_PANEL_R_MIN = 1e-6
PATCH_N = 2  # stage-1 face subdivision (6 * n * n panels)

# Face order matches FluidX3D permeable CSV: +x, -x, +y, -y, +z, -z
_FACE_NORMALS = (
    (1.0, 0.0, 0.0),
    (-1.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
    (0.0, -1.0, 0.0),
    (0.0, 0.0, 1.0),
    (0.0, 0.0, -1.0),
)


def cv_box_from_dia_mm(dia_mm: float) -> dict:
    """SI CV box (fan-centered) matching FluidX3D ``setup.cpp`` noise CV geometry.

    Lattice: Nx=Ny=160, Nz=240, 1 cell = 1 mm. half radial = min(R+12, Nx/2-8);
    half axial = 45 cells.
    """
    nx = 160
    r_cells = 0.5 * float(dia_mm)
    bh = min(r_cells + 12.0, nx / 2.0 - 8.0)
    mm = 0.001
    return {
        "cx_m": 0.0,
        "cy_m": 0.0,
        "cz_m": 0.0,
        "half_xy_m": bh * mm,
        "half_z_m": 45.0 * mm,
        "dia_mm": float(dia_mm),
    }


def _face_centers(box: dict) -> list[tuple[float, float, float]]:
    cx, cy, cz = float(box["cx_m"]), float(box["cy_m"]), float(box["cz_m"])
    hxy, hz = float(box["half_xy_m"]), float(box["half_z_m"])
    return [
        (cx + hxy, cy, cz),
        (cx - hxy, cy, cz),
        (cx, cy + hxy, cz),
        (cx, cy - hxy, cz),
        (cx, cy, cz + hz),
        (cx, cy, cz - hz),
    ]


def _patch_centers(box: dict, n: int = PATCH_N) -> list[tuple[float, float, float]]:
    """Centers for 6*n*n patches. Index p = n*n*face + n*i + j (i,j in 0..n-1)."""
    if n != 2:
        raise ValueError("stage 1 only supports n=2")
    cx, cy, cz = float(box["cx_m"]), float(box["cy_m"]), float(box["cz_m"])
    hxy, hz = float(box["half_xy_m"]), float(box["half_z_m"])
    centers = []
    for face in range(6):
        for i in range(n):
            for j in range(n):
                ou = (i - 0.5)  # -0.5 or +0.5
                ov = (j - 0.5)
                if face == 0:  # +x; local (y,z)
                    r0 = (cx + hxy, cy + ou * hxy, cz + ov * hz)
                elif face == 1:  # -x
                    r0 = (cx - hxy, cy + ou * hxy, cz + ov * hz)
                elif face == 2:  # +y; local (x,z)
                    r0 = (cx + ou * hxy, cy + hxy, cz + ov * hz)
                elif face == 3:  # -y
                    r0 = (cx + ou * hxy, cy - hxy, cz + ov * hz)
                elif face == 4:  # +z; local (x,y)
                    r0 = (cx + ou * hxy, cy + ov * hxy, cz + hz)
                else:  # -z
                    r0 = (cx + ou * hxy, cy + ov * hxy, cz - hz)
                centers.append(r0)
    return centers


def loading_pressure_compact(F, dt, *, r_hat=(0.0, 0.0, 1.0), r_obs: float = 1.0,
                             c0: float = C0_AIR):
    """Far-field compact loading pressure [Pa]. Delay by r_obs/c0 (SPL unchanged for one source)."""
    F = np.asarray(F, float)
    dFdt = np.gradient(F, dt, axis=0)
    r_hat = np.asarray(r_hat, float)
    r_obs = float(r_obs)
    p_inst = (r_hat @ dFdt.T) / (4.0 * np.pi * c0 * r_obs)
    n = p_inst.shape[0]
    t = np.arange(n, dtype=float) * float(dt)
    t_ret = t - r_obs / c0
    return np.interp(t_ret, t, p_inst, left=0.0, right=0.0)


def loading_pressure_panels(t, panels, *, x_obs=(0.0, 0.0, 1.0), c0: float = C0_AIR):
    """Sum far-field loading from discrete panels. Each panel: r0, area, n_hat, f[t,3].

    ``area`` / ``n_hat`` are stored for a later surface dump; stage 1 uses the force history ``f``.
    Skip a panel whose observer distance is below ``_PANEL_R_MIN``.
    """
    t = np.asarray(t, float)
    x_obs = np.asarray(x_obs, float)
    p = np.zeros(t.shape[0], dtype=float)
    if t.shape[0] < 2:
        return p
    dt = float(np.median(np.diff(t)))
    for pan in panels:
        r0 = np.asarray(pan["r0"], float)
        delta = x_obs - r0
        r = float(np.linalg.norm(delta))
        if r < _PANEL_R_MIN:
            continue
        r_hat = delta / r
        F = np.asarray(pan["f"], float)
        dFdt = np.gradient(F, dt, axis=0)
        p_inst = (r_hat @ dFdt.T) / (4.0 * np.pi * c0 * r)
        t_ret = t - r / c0
        p = p + np.interp(t_ret, t, p_inst, left=0.0, right=0.0)
    return p


def noise_from_compact_force(t, F, *, cutoff_hz: float = 2500.0,
                             n_blades: int = N_BLADES_DEFAULT, rpm: float = RPM_DEFAULT,
                             r_hat=(0.0, 0.0, 1.0), r_obs: float = 1.0) -> dict:
    """Reduce a compact force history with the FW-H loading kernel (same metric keys as Curle)."""
    t = np.asarray(t, float)
    F = np.asarray(F, float)
    dt = float(np.median(np.diff(t)))
    thrust = float(F[:, 2].mean())
    Fp = F - F.mean(axis=0)
    p = loading_pressure_compact(Fp, dt, r_hat=r_hat, r_obs=r_obs)
    bpf = blade_pass_frequency(n_blades, rpm)
    return {
        "noise_dba_band": round(dba_from_pressure(p, dt, cutoff_hz), 2),
        "noise_dba_full": round(dba_from_pressure(p, dt, None), 2),
        "bpf_tone_db": round(tone_level_db(p, dt, bpf), 2),
        "peak_tone_db": round(peak_tone_over_harmonics(p, dt, rpm / 60.0), 2),
        "thrust_n": round(thrust, 4),
        "cutoff_hz": cutoff_hz,
        "samples": int(len(t)),
        "analogy": "fwh_compact",
    }


def face_panels_from_csv(path, box: dict) -> list[dict]:
    """Load a six-face permeable CSV into panels for ``loading_pressure_panels``.

    CSV columns: ``t_s, F0x,F0y,F0z, …, F5x,F5y,F5z`` (face order +x,-x,+y,-y,+z,-z).
    ``box`` keys: ``cx_m, cy_m, cz_m, half_xy_m, half_z_m``.
    """
    d = np.genfromtxt(path, delimiter=",", names=True)
    centers = _face_centers(box)
    panels = []
    for i, (r0, n_hat) in enumerate(zip(centers, _FACE_NORMALS)):
        f = np.column_stack([d[f"F{i}x"], d[f"F{i}y"], d[f"F{i}z"]])
        panels.append({"r0": r0, "n_hat": n_hat, "area": 1.0, "f": f})
    return panels


def noise_from_permeable_panels(t, panels, *, cutoff_hz: float = 2500.0,
                                n_blades: int = N_BLADES_DEFAULT, rpm: float = RPM_DEFAULT,
                                x_obs=(0.0, 0.0, 1.0)) -> dict:
    """Reduce six (or more) face force histories with the panel FW-H loading kernel."""
    t = np.asarray(t, float)
    dt = float(np.median(np.diff(t)))
    # Mean-subtract each panel force (loading is about fluctuations)
    pans = []
    thrust = 0.0
    for pan in panels:
        F = np.asarray(pan["f"], float)
        thrust += float(F[:, 2].mean())
        pans.append({**pan, "f": F - F.mean(axis=0)})
    p = loading_pressure_panels(t, pans, x_obs=x_obs)
    bpf = blade_pass_frequency(n_blades, rpm)
    return {
        "noise_dba_band": round(dba_from_pressure(p, dt, cutoff_hz), 2),
        "noise_dba_full": round(dba_from_pressure(p, dt, None), 2),
        "bpf_tone_db": round(tone_level_db(p, dt, bpf), 2),
        "peak_tone_db": round(peak_tone_over_harmonics(p, dt, rpm / 60.0), 2),
        "thrust_n": round(thrust, 4),
        "cutoff_hz": cutoff_hz,
        "samples": int(len(t)),
        "analogy": "fwh_permeable",
        "n_panels": len(panels),
    }


def analyze_permeable_csv(csv, box: dict | None = None, *, dia_mm: float | None = None,
                          cutoff_hz: float = 2500.0, x_obs=(0.0, 0.0, 1.0)) -> dict:
    """Load a permeable multi-face CSV and return noise metrics."""
    if box is None:
        if dia_mm is None:
            raise ValueError("need box or dia_mm for permeable reduction")
        box = cv_box_from_dia_mm(dia_mm)
    d = np.genfromtxt(csv, delimiter=",", names=True)
    t = np.asarray(d["t_s"], float)
    panels = face_panels_from_csv(csv, box)
    return noise_from_permeable_panels(t, panels, cutoff_hz=cutoff_hz, x_obs=x_obs)


def patch_panels_from_csv(path, box: dict, n: int = PATCH_N) -> list[dict]:
    """Load a 2×2-per-face permeable CSV into panels.

    Columns: ``t_s, P0x,P0y,P0z, …, P23x,P23y,P23z`` with
    ``p = n*n*face + n*i + j`` (face order +x,-x,+y,-y,+z,-z).
    """
    if n != PATCH_N:
        raise ValueError(f"stage 1 only supports n={PATCH_N}")
    d = np.genfromtxt(path, delimiter=",", names=True)
    centers = _patch_centers(box, n=n)
    n_panels = 6 * n * n
    panels = []
    for p in range(n_panels):
        face = p // (n * n)
        f = np.column_stack([d[f"P{p}x"], d[f"P{p}y"], d[f"P{p}z"]])
        panels.append({
            "r0": centers[p],
            "n_hat": _FACE_NORMALS[face],
            "area": 1.0,
            "f": f,
        })
    return panels


def analyze_patches_csv(csv, box: dict | None = None, *, dia_mm: float | None = None,
                        cutoff_hz: float = 2500.0, x_obs=(0.0, 0.0, 1.0)) -> dict:
    """Load a 24-patch permeable CSV and return noise metrics (``analogy=fwh_patches``)."""
    if box is None:
        if dia_mm is None:
            raise ValueError("need box or dia_mm for patches reduction")
        box = cv_box_from_dia_mm(dia_mm)
    d = np.genfromtxt(csv, delimiter=",", names=True)
    t = np.asarray(d["t_s"], float)
    panels = patch_panels_from_csv(csv, box)
    m = noise_from_permeable_panels(t, panels, cutoff_hz=cutoff_hz, x_obs=x_obs)
    m["analogy"] = "fwh_patches"
    return m
