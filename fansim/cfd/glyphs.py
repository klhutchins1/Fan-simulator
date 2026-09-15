"""Stage-2 duct velocity glyphs for the Fan cockpit 3-D plotter.

After reconstruct (shared readiness with midplane), load the internal mesh ``U``
field, subsample cell centers near the impeller, scale meters→millimeters to match
the impeller STL, and build arrow glyphs for overlay in the same PyVista plotter.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from fansim.cfd.midplane import case_has_flow_fields, ensure_reconstructed

# OpenFOAM cases are SI meters; cockpit impeller STL is millimeters.
M_TO_MM = 1.0e3
# Keep arrows near the rotor — the screening duct is long in Z.
DEFAULT_Z_HALF_SPAN_M = 0.05
DEFAULT_MAX_CLOUD = 2000
DEFAULT_STRIDE = 1
DEFAULT_MAX_ARROWS = 700
DEFAULT_FACTOR = 2.0  # |U| [m/s] * factor ≈ arrow length in mm


@dataclass(frozen=True)
class VelocityGlyphs:
    """Subsampled velocity point cloud (mm) ready to glyph in the cockpit."""

    case_dir: Path
    cloud: object | None  # pyvista.PolyData with U / U_mag, or None
    caption: str
    available: bool
    n_points: int = 0


def _ensure_cell_u(mesh):
    """Return a mesh with cell-data vector ``U`` (promote from point data if needed)."""
    g = mesh
    if "U" in g.point_data and "U" not in g.cell_data:
        g = g.point_data_to_cell_data()
    if "U" not in g.cell_data:
        raise KeyError("mesh has no U field")
    return g


def build_velocity_cloud(
    mesh,
    *,
    max_points: int = DEFAULT_MAX_CLOUD,
    z_half_span_m: float = DEFAULT_Z_HALF_SPAN_M,
    scale_m_to_mm: bool = True,
):
    """Cell-center subsample with ``U`` / ``U_mag``; points optionally in mm.

    Aggressive axial clip + stride so Windows UI stays usable on ~1e5-cell meshes.
    """
    import pyvista as pv

    g = _ensure_cell_u(mesh)
    centers = g.cell_centers()
    pts = np.asarray(centers.points, dtype=float)
    u = np.asarray(centers["U"], dtype=float)
    if u.ndim == 1:
        u = u.reshape(-1, 1)
    if u.shape[1] < 3:
        pad = np.zeros((u.shape[0], 3), dtype=float)
        pad[:, : u.shape[1]] = u
        u = pad

    if pts.shape[0] == 0:
        raise ValueError("mesh has no cell centers")

    mask = np.abs(pts[:, 2]) <= float(z_half_span_m)
    idx = np.nonzero(mask)[0]
    if idx.size == 0:
        idx = np.arange(pts.shape[0])

    max_points = max(1, int(max_points))
    if idx.size > max_points:
        step = int(np.ceil(idx.size / max_points))
        idx = idx[::step]
    if idx.size > max_points:
        idx = idx[:max_points]

    out_pts = pts[idx]
    if scale_m_to_mm:
        out_pts = out_pts * M_TO_MM
    u_sub = u[idx]
    mag = np.linalg.norm(u_sub, axis=1)

    cloud = pv.PolyData(out_pts)
    cloud["U"] = u_sub
    cloud["U_mag"] = mag
    return cloud


def schematic_axial_flow_cloud(
    *,
    hub_radius_mm: float,
    tip_radius_mm: float,
    z_span_mm: float = 40.0,
    u_axial_ms: float = 3.0,
    n_radial: int = 4,
    n_theta: int = 16,
    n_axial: int = 5,
):
    """Build a non-CFD axial through-flow sample cloud for stock / no-case previews.

    Flow is +Z (outlet), matching the cockpit midplane convention (FRONT −Z → OUTLET +Z).
    Points and arrow lengths use the same units as CFD glyphs (points in mm, ``U`` in m/s).
    """
    import pyvista as pv

    hub_r = max(1.0, float(hub_radius_mm))
    tip_r = max(hub_r + 1.0, float(tip_radius_mm))
    z_half = 0.5 * max(8.0, float(z_span_mm))
    n_radial = max(1, int(n_radial))
    n_theta = max(4, int(n_theta))
    n_axial = max(1, int(n_axial))

    rs = np.linspace(hub_r + 0.5, tip_r - 0.5, n_radial)
    thetas = np.linspace(0.0, 2.0 * np.pi, n_theta, endpoint=False)
    zs = np.linspace(-z_half, z_half, n_axial)
    pts = []
    for r in rs:
        for th in thetas:
            for z in zs:
                pts.append((r * np.cos(th), r * np.sin(th), z))
    pts_a = np.asarray(pts, dtype=float)
    u = np.zeros_like(pts_a)
    u[:, 2] = float(u_axial_ms)
    cloud = pv.PolyData(pts_a)
    cloud["U"] = u
    cloud["U_mag"] = np.full(pts_a.shape[0], float(u_axial_ms), dtype=float)
    return cloud


def make_glyph_arrows(
    cloud,
    *,
    stride: int = DEFAULT_STRIDE,
    factor: float = DEFAULT_FACTOR,
    max_arrows: int = DEFAULT_MAX_ARROWS,
):
    """Build arrow glyphs from a velocity cloud (already in plotter units)."""
    import pyvista as pv

    if cloud is None or cloud.n_points == 0:
        return None
    if "U" not in cloud.point_data and "U" not in cloud.array_names:
        raise KeyError("cloud has no U field")

    stride = max(1, int(stride))
    max_arrows = max(1, int(max_arrows))
    src = cloud
    if stride > 1 or cloud.n_points > max_arrows:
        idx = np.arange(0, cloud.n_points, stride)
        if idx.size > max_arrows:
            step = int(np.ceil(idx.size / max_arrows))
            idx = idx[::step]
        src = cloud.extract_points(idx, include_cells=False)
        # extract_points may drop arrays on some PyVista versions — reattach if needed
        if "U" not in src.point_data:
            src = pv.PolyData(cloud.points[idx])
            src["U"] = np.asarray(cloud["U"])[idx]
            src["U_mag"] = np.asarray(cloud["U_mag"])[idx]

    if "U_mag" not in src.point_data:
        u = np.asarray(src["U"], dtype=float)
        src["U_mag"] = np.linalg.norm(u, axis=1) if u.ndim > 1 else np.abs(u)

    arrows = src.glyph(
        orient="U",
        scale="U_mag",
        factor=float(factor),
        geom=pv.Arrow(),
    )
    return arrows if arrows.n_points > 0 else None


def ensure_velocity_glyphs(
    case_dir: str | Path | None,
    *,
    runner_factory=None,
    image_ok=None,
    mesh=None,
    max_points: int = DEFAULT_MAX_CLOUD,
    z_half_span_m: float = DEFAULT_Z_HALF_SPAN_M,
) -> VelocityGlyphs:
    """Load / subsample velocity cloud for a case. Fail-soft — never raises."""
    unavailable = VelocityGlyphs(
        case_dir=Path(case_dir) if case_dir else Path("."),
        cloud=None,
        caption="Velocity arrows not available for this design",
        available=False,
        n_points=0,
    )
    if case_dir is None:
        return unavailable
    case_dir = Path(case_dir)
    if not case_dir.is_dir():
        return unavailable

    try:
        if mesh is None:
            if not case_has_flow_fields(case_dir):
                return unavailable
            if not ensure_reconstructed(
                case_dir, runner_factory=runner_factory, image_ok=image_ok,
            ):
                return unavailable
            from fansim.acoustics.case import read_case

            mesh = read_case(case_dir)

        cloud = build_velocity_cloud(
            mesh,
            max_points=max_points,
            z_half_span_m=z_half_span_m,
            scale_m_to_mm=True,
        )
        n = int(cloud.n_points)
        if n <= 0:
            return unavailable
        return VelocityGlyphs(
            case_dir=case_dir,
            cloud=cloud,
            caption=f"{n} velocity sample points (subsampled near impeller)",
            available=True,
            n_points=n,
        )
    except Exception:  # noqa: BLE001 — viz must never break Assess
        return unavailable
