"""Circular screening-duct honesty helpers (roadmap §10.10)."""

from __future__ import annotations

import math
import re
from pathlib import Path


def expected_circular_area_m2(duct_radius_m: float) -> float:
    r = float(duct_radius_m)
    return math.pi * r * r


def circular_inlet_area_ok(
    area_m2: float,
    duct_radius_m: float,
    *,
    tol_frac: float = 0.15,
) -> bool:
    """True when measured inlet patch area is within ``tol_frac`` of πR².

    Tube-in-oversized-hex meshes can leave corner plenum cells if snappy fails to
    delete the exterior — inlet area then ≫ πR² and outletFlow counts leak.
    """
    expected = expected_circular_area_m2(duct_radius_m)
    if expected <= 0.0:
        return False
    a = float(area_m2)
    lo = expected * (1.0 - float(tol_frac))
    hi = expected * (1.0 + float(tol_frac))
    return lo <= a <= hi


def circular_inlet_area_error(
    area_m2: float,
    duct_radius_m: float,
) -> str:
    """Human-readable mismatch for mesh/evaluate failures."""
    expected = expected_circular_area_m2(duct_radius_m)
    a = float(area_m2)
    if expected <= 0:
        return f"invalid duct radius {duct_radius_m}"
    ratio = a / expected
    return (
        f"circular inlet area {a:.6g} m² vs πR²={expected:.6g} m² "
        f"(ratio {ratio:.3f}); leftover hex plenum / snappy bypass?"
    )


_FACE_RE = re.compile(r"^(\d+)\((.*)\)\s*$")
_PATCH_RE = re.compile(
    r"(?P<name>\w+)\s*\{\s*type\s+\w+\s*;"
    r"(?:[^}]*?nFaces\s+(?P<n>\d+)\s*;[^}]*?startFace\s+(?P<s>\d+)\s*;"
    r"|[^}]*?startFace\s+(?P<s2>\d+)\s*;[^}]*?nFaces\s+(?P<n2>\d+)\s*;)"
    r"[^}]*\}",
    re.DOTALL,
)


def _require_ascii_foam(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    if re.search(r"format\s+binary\s*;", text):
        raise RuntimeError(f"binary polyMesh not supported for inlet area: {path}")
    return text


def _patch_face_range(boundary_text: str, patch: str) -> tuple[int, int]:
    for m in _PATCH_RE.finditer(boundary_text):
        if m.group("name") != patch:
            continue
        n = m.group("n") or m.group("n2")
        s = m.group("s") or m.group("s2")
        return int(s), int(n)
    raise RuntimeError(f"patch {patch!r} not found in polyMesh/boundary")


def _load_points(points_path: Path) -> list[tuple[float, float, float]]:
    _require_ascii_foam(points_path)
    pts: list[tuple[float, float, float]] = []
    in_list = False
    with points_path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            s = line.strip()
            if not in_list:
                if s == "(":
                    in_list = True
                continue
            if s == ")":
                break
            if not s.startswith("("):
                continue
            nums = s.strip("()").split()
            pts.append((float(nums[0]), float(nums[1]), float(nums[2])))
    return pts


def _iter_faces(faces_path: Path, start: int, n_faces: int):
    _require_ascii_foam(faces_path)
    in_list = False
    idx = 0
    end = start + n_faces
    with faces_path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            s = line.strip()
            if not in_list:
                if s == "(":
                    in_list = True
                continue
            if s == ")":
                break
            if idx < start:
                idx += 1
                continue
            if idx >= end:
                break
            m = _FACE_RE.match(s)
            if m is None:
                raise RuntimeError(f"unrecognized face line at index {idx}: {s[:80]!r}")
            yield [int(x) for x in m.group(2).split()]
            idx += 1


def _polygon_area_m2(verts: list[tuple[float, float, float]]) -> float:
    """Newell polygon area (m²) for a planar-ish OpenFOAM face."""
    nx = ny = nz = 0.0
    n = len(verts)
    for i in range(n):
        x0, y0, z0 = verts[i]
        x1, y1, z1 = verts[(i + 1) % n]
        nx += (y0 - y1) * (z0 + z1)
        ny += (z0 - z1) * (x0 + x1)
        nz += (x0 - x1) * (y0 + y1)
    return 0.5 * math.sqrt(nx * nx + ny * ny + nz * nz)


def inlet_patch_area_m2(case_dir: str | Path, patch: str = "inlet") -> float:
    """Sum face areas of ``patch`` from ASCII ``constant/polyMesh`` after snappy."""
    mesh = Path(case_dir) / "constant" / "polyMesh"
    boundary = _require_ascii_foam(mesh / "boundary")
    start, n_faces = _patch_face_range(boundary, patch)
    points = _load_points(mesh / "points")
    area = 0.0
    for face in _iter_faces(mesh / "faces", start, n_faces):
        area += _polygon_area_m2([points[i] for i in face])
    return area


def require_circular_inlet_area(
    case_dir: str | Path,
    duct_radius_m: float,
    *,
    patch: str = "inlet",
    tol_frac: float = 0.15,
) -> float:
    """Measure inlet area after snappy; raise if it is not ≈ πR².

    Returns the measured area (m²) when the check passes.
    """
    area = inlet_patch_area_m2(case_dir, patch=patch)
    if not circular_inlet_area_ok(area, duct_radius_m, tol_frac=tol_frac):
        raise RuntimeError(circular_inlet_area_error(area, duct_radius_m))
    return area
