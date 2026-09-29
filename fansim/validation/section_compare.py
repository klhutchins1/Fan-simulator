"""Blade-section comparison: unroll cylinder cuts of a rotor STL and measure per-radius geometry.

Each blade loop from a cylinder cut r = frac * tip is unrolled to (s = r*theta, z) and measured:
chord (principal-axis extent), stagger from the circumferential (s) direction (0-90), camber
(chordwise-binned midline vs. the chord line), thickness, LE position, solidity. Medians over
blades are reported per radius.
"""

from __future__ import annotations

import numpy as np
import trimesh

from fansim.audit.direction import (
    _resample_closed,
    _section_loops,
    _tip_radius,
    prove_direction,
)

DEFAULT_RADII = (0.45, 0.55, 0.65, 0.75, 0.85, 0.95)
N_BINS = 20
MAX_THICKNESS_RATIO = 0.6  # loops thicker than this are hub/junction blobs, not blades

_KEYS = ("chord_mm", "stagger_deg", "camber_ratio", "camber_pos", "max_thickness_mm",
         "thickness_ratio", "axial_extent_mm", "le_theta_deg", "le_z_mm", "solidity")


def _measure_loop(pts: np.ndarray, r0: float, omega_sign: int, n_blades: int) -> dict | None:
    theta = np.arctan2(pts[:, 1], pts[:, 0])
    tm = np.angle(np.mean(np.exp(1j * theta)))
    s = r0 * np.angle(np.exp(1j * (theta - tm)))
    p2 = _resample_closed(np.column_stack([s, pts[:, 2]]))
    c0 = p2.mean(axis=0)
    q = p2 - c0
    _, vecs = np.linalg.eigh(q.T @ q)
    c_hat = vecs[:, 1]
    # Orient chord so the leading edge is at xi = min. The blade moves toward +theta when
    # omega_sign = +1 (prove_direction's convention, CCW seen from +Z), so the LE is the chord end
    # with the larger omega_sign * s; for a near-axial chord (|c_s| ~ 0) the sign is arbitrary.
    if omega_sign * c_hat[0] > 0:
        c_hat = -c_hat
    e_hat = np.array([-c_hat[1], c_hat[0]])
    xi, eta = q @ c_hat, q @ e_hat
    chord = float(xi.max() - xi.min())
    if chord <= 0:
        return None
    stagger = float(np.degrees(np.arctan2(abs(c_hat[1]), abs(c_hat[0]))))
    lo, hi = float(xi.min()), float(xi.max())
    edges = np.linspace(lo, hi, N_BINS + 1)
    idx = np.clip(np.digitize(xi, edges) - 1, 0, N_BINS - 1)
    cx, mid, thick = [], [], []
    for b in range(N_BINS):
        sel = idx == b
        if not np.any(sel):
            continue
        cx.append(0.5 * (edges[b] + edges[b + 1]))
        mid.append(0.5 * (eta[sel].max() + eta[sel].min()))
        thick.append(eta[sel].max() - eta[sel].min())
    if len(cx) < 6:
        return None
    cx, mid, thick = map(np.asarray, (cx, mid, thick))
    # A bin on a sloped midline spans slope * bin-width extra in eta; remove that, then convert the
    # vertical (eta) gap to the thickness normal to the midline.
    slope = np.gradient(mid, cx)
    binw = (hi - lo) / N_BINS
    thick = np.maximum(thick - np.abs(slope) * binw, 0.0) * np.cos(np.arctan(slope))
    line = mid[0] + (mid[-1] - mid[0]) * (cx - cx[0]) / (cx[-1] - cx[0])
    dev = np.abs(mid - line)
    k = int(np.argmax(dev))
    camber_ratio = float(dev[k] / chord)
    camber_pos = float((cx[k] - lo) / chord)
    interior = (cx - lo) / chord
    keep = (interior > 0.1) & (interior < 0.9)
    tmax = float(thick[keep].max() if keep.any() else thick.max())
    # Reject hub/junction loops: too thick, degenerate (zero-thickness), or wrapping the annulus.
    if not (0.01 < tmax / chord <= MAX_THICKNESS_RATIO) or chord > 0.4 * 2.0 * np.pi * r0:
        return None
    le = q[np.argmin(xi)] + c0
    le_theta = np.degrees(tm + le[0] / r0)
    return {
        "chord_mm": chord, "stagger_deg": stagger, "camber_ratio": camber_ratio,
        "camber_pos": camber_pos, "max_thickness_mm": tmax, "thickness_ratio": tmax / chord,
        "axial_extent_mm": float(p2[:, 1].max() - p2[:, 1].min()),
        "le_theta_deg": float(le_theta), "le_z_mm": float(le[1]),
        "solidity": chord * n_blades / (2.0 * np.pi * r0),
    }


def _circ_median_mod(theta_deg: list[float], pitch_deg: float) -> float:
    """Circular mean of LE angles modulo the blade pitch (blades are rotational copies)."""
    ph = np.radians(np.asarray(theta_deg) * 360.0 / pitch_deg)
    return float(np.degrees(np.angle(np.mean(np.exp(1j * ph)))) * pitch_deg / 360.0)


def measure_sections(stl_path, radii_frac=DEFAULT_RADII) -> list[dict]:
    mesh = trimesh.load(str(stl_path), force="mesh")
    mesh.merge_vertices()
    tip = _tip_radius(mesh)
    proof = prove_direction(mesh)
    omega_sign = int(proof.omega_sign) if proof.omega_sign is not None else +1
    # First pass: blade count from the outermost-but-one radius loops.
    out = []
    for f in radii_frac:
        r0 = f * tip
        loops = [pts for pts, _ in _section_loops(mesh, r0)]
        n_est = len(loops)
        rows = [m for m in (_measure_loop(p, r0, omega_sign, max(n_est, 1)) for p in loops) if m]
        n = len(rows)
        if n == 0:
            out.append({"r_frac": float(f), "r_mm": float(r0), "n_blades": 0})
            continue
        for m in rows:  # solidity with the accepted blade count
            m["solidity"] = m["chord_mm"] * n / (2.0 * np.pi * r0)
        rec = {"r_frac": float(f), "r_mm": float(r0), "n_blades": n,
               "omega_sign": omega_sign}
        for k in _KEYS:
            rec[k] = float(np.median([m[k] for m in rows]))
        rec["le_theta_deg"] = _circ_median_mod([m["le_theta_deg"] for m in rows], 360.0 / n)
        out.append(rec)
    # Unwrap the modulo-pitch LE angle along radius so its slope reads as sweep/skew.
    ok = [r for r in out if r["n_blades"] > 0]
    if len(ok) > 1:
        pitch = 360.0 / ok[0]["n_blades"]
        un = np.degrees(np.unwrap(np.radians([r["le_theta_deg"] for r in ok]) * 360.0 / pitch))             * pitch / 360.0
        for r, v in zip(ok, un):
            r["le_theta_deg"] = float(v)
    return out


def compare(stl_a, stl_b, labels=("stock", "reference")) -> dict:
    a, b = measure_sections(stl_a), measure_sections(stl_b)
    diffs = []
    for ra, rb in zip(a, b):
        d = {"r_frac": ra["r_frac"]}
        for k in _KEYS + ("n_blades",):
            if k in ra and k in rb:
                d[k] = ra[k] - rb[k]
        diffs.append(d)
    return {"labels": list(labels), labels[0]: a, labels[1]: b,
            "diff": diffs, "diff_definition": f"{labels[0]} - {labels[1]}"}
