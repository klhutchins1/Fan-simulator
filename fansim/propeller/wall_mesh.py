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
RAY_CHUNK = 2000


def rho_cfd() -> float:
    return P_INF * MOL_WEIGHT / (R_UNIV * T_INF)


def _thicknesses_mm(mesh: trimesh.Trimesh) -> np.ndarray:
    centers = np.asarray(mesh.triangles_center, dtype=float)
    normals = np.asarray(mesh.face_normals, dtype=float)
    inward = -normals
    origins = centers + inward * (HIT_MIN_MM * 0.4)
    dist_chunks: list[np.ndarray] = []
    for start in range(0, len(origins), RAY_CHUNK):
        stop = min(start + RAY_CHUNK, len(origins))
        locs, ray_idx, _tri = mesh.ray.intersects_location(
            ray_origins=origins[start:stop],
            ray_directions=inward[start:stop],
            multiple_hits=False,
        )
        if len(locs) == 0:
            continue
        chunk_centers = centers[start:stop]
        dist = np.linalg.norm(locs - chunk_centers[ray_idx], axis=1)
        keep = dist[dist >= HIT_MIN_MM]
        if keep.size:
            dist_chunks.append(keep)
    if not dist_chunks:
        return np.array([], dtype=float)
    return np.concatenate(dist_chunks)


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
