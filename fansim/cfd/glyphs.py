"""Stage-2 duct velocity glyphs for the Fan cockpit 3-D plotter.

After reconstruct (shared readiness with midplane), load the internal mesh ``U``
field, subsample cell centers near the impeller, scale meters→millimeters to match
the impeller STL, and build arrow glyphs for overlay in the same PyVista plotter.

Process-local cloud cache (§22.1) + on-disk ``.vtp`` under ``cockpit_viz/`` (§22.9):
reselecting / restarting must not re-``read_case`` the ~0.5–1M-cell OpenFOAM grid.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from fansim.cfd.midplane import case_has_flow_fields, ensure_reconstructed

_log = logging.getLogger(__name__)

# OpenFOAM cases are SI meters; cockpit impeller STL is millimeters.
M_TO_MM = 1.0e3
# Keep arrows near the rotor — the screening duct is long in Z.
DEFAULT_Z_HALF_SPAN_M = 0.05
DEFAULT_MAX_CLOUD = 2000
DEFAULT_STRIDE = 1
DEFAULT_MAX_ARROWS = 700
DEFAULT_FACTOR = 2.0  # |U| [m/s] * factor ≈ arrow length in mm
# Tip |U| spikes (~20+ m/s) blow glyph scale vs bulk (~3 m/s). Cap length at p95 (§15.3).
GLYPH_MAG_PERCENTILE = 95.0

_VIZ_SUBDIR = Path("postProcessing") / "cockpit_viz"
_GLYPH_VTP = "velocity_cloud_v1.vtp"
_GLYPH_META = "velocity_cloud_v1.meta.json"

# (resolved case path, field fingerprint, max_points, z_half_span) → VelocityGlyphs
_GLYPH_CACHE: dict[tuple[str, str, int, float], VelocityGlyphs] = {}


@dataclass(frozen=True)
class VelocityGlyphs:
    """Subsampled velocity point cloud (mm) ready to glyph in the cockpit."""

    case_dir: Path
    cloud: object | None  # pyvista.PolyData with U / U_mag, or None
    caption: str
    available: bool
    n_points: int = 0


def clear_glyph_cache() -> None:
    """Drop the process-local glyph cloud cache (tests / after field rewrite)."""
    _GLYPH_CACHE.clear()


def glyph_artifact_paths(case_dir: str | Path) -> tuple[Path, Path]:
    """``(vtp, meta.json)`` under ``postProcessing/cockpit_viz/`` (§22.9)."""
    root = Path(case_dir) / _VIZ_SUBDIR
    return root / _GLYPH_VTP, root / _GLYPH_META


def _latest_nonzero_time_dir(case_dir: Path) -> Path | None:
    times: list[Path] = []
    for p in case_dir.iterdir():
        if not p.is_dir():
            continue
        name = p.name
        if not name.replace(".", "", 1).isdigit():
            continue
        try:
            if float(name) > 0.0:
                times.append(p)
        except ValueError:
            continue
    if not times:
        return None
    return max(times, key=lambda p: float(p.name))


def case_field_fingerprint(case_dir: str | Path) -> str:
    """Stable fingerprint of the latest reconstructed field set (mtime of ``U``)."""
    case_dir = Path(case_dir)
    if not case_dir.is_dir():
        return "none"
    latest = _latest_nonzero_time_dir(case_dir)
    if latest is None:
        return "none"
    u = latest / "U"
    try:
        mt = u.stat().st_mtime_ns if u.is_file() else latest.stat().st_mtime_ns
    except OSError:
        return f"{latest.name}:missing"
    return f"{latest.name}:{mt}"


def _cache_key(
    case_dir: Path, max_points: int, z_half_span_m: float,
) -> tuple[str, str, int, float]:
    return (
        str(case_dir.resolve()),
        case_field_fingerprint(case_dir),
        int(max_points),
        float(z_half_span_m),
    )


def _load_disk_glyphs(
    case_dir: Path,
    *,
    max_points: int,
    z_half_span_m: float,
) -> VelocityGlyphs | None:
    """Load ``velocity_cloud_v1.vtp`` when meta fingerprint matches (§22.9)."""
    vtp, meta_path = glyph_artifact_paths(case_dir)
    if not vtp.is_file() or not meta_path.is_file():
        return None
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(meta, dict):
        return None
    if str(meta.get("fingerprint", "")) != case_field_fingerprint(case_dir):
        return None
    if int(meta.get("max_points", -1)) != int(max_points):
        return None
    if abs(float(meta.get("z_half_span_m", -1.0)) - float(z_half_span_m)) > 1e-12:
        return None
    try:
        import pyvista as pv

        cloud = pv.read(str(vtp))
        if cloud.n_points <= 0 or "U" not in cloud.point_data:
            return None
        if "U_mag" not in cloud.point_data:
            u = np.asarray(cloud["U"], dtype=float)
            cloud["U_mag"] = np.linalg.norm(u, axis=1) if u.ndim > 1 else np.abs(u)
        n = int(cloud.n_points)
        return VelocityGlyphs(
            case_dir=case_dir,
            cloud=cloud,
            caption=f"{n} velocity sample points (cached)",
            available=True,
            n_points=n,
        )
    except Exception as exc:  # noqa: BLE001
        _log.debug("load disk glyphs %s: %s: %s", vtp, type(exc).__name__, exc)
        return None


def _save_disk_glyphs(
    case_dir: Path,
    art: VelocityGlyphs,
    *,
    max_points: int,
    z_half_span_m: float,
) -> None:
    """Write glyph cloud + fingerprint meta (fail-soft)."""
    if not art.available or art.cloud is None:
        return
    vtp, meta_path = glyph_artifact_paths(case_dir)
    try:
        vtp.parent.mkdir(parents=True, exist_ok=True)
        art.cloud.save(str(vtp))
        meta = {
            "fingerprint": case_field_fingerprint(case_dir),
            "max_points": int(max_points),
            "z_half_span_m": float(z_half_span_m),
            "n_points": int(art.n_points),
        }
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        _log.debug("save disk glyphs %s: %s: %s", vtp, type(exc).__name__, exc)


def peek_cached_velocity_glyphs(
    case_dir: str | Path | None,
    *,
    max_points: int = DEFAULT_MAX_CLOUD,
    z_half_span_m: float = DEFAULT_Z_HALF_SPAN_M,
) -> VelocityGlyphs | None:
    """Return a cached glyph cloud without reading the OpenFOAM mesh, or None on miss.

    Checks process memory first, then on-disk ``.vtp`` (§22.1 / §22.9).
    """
    if case_dir is None:
        return None
    case_dir = Path(case_dir)
    if not case_dir.is_dir():
        return None
    key = _cache_key(case_dir, max_points, z_half_span_m)
    hit = _GLYPH_CACHE.get(key)
    if hit is not None:
        return hit
    disk = _load_disk_glyphs(
        case_dir, max_points=max_points, z_half_span_m=z_half_span_m,
    )
    if disk is not None:
        _GLYPH_CACHE[key] = disk
    return disk


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

    As-built preview: open intake +Z, exhaust past the motor at −Z (user-confirmed real fan;
    Audit #1). CFD field glyphs are in the duct frame and come from the solve, not this cloud.
    Units: points mm, ``U`` m/s.
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
    u_ax = abs(float(u_axial_ms))
    u[:, 2] = -u_ax  # −Z: air enters open +Z intake and exits past the motor at −Z
    cloud = pv.PolyData(pts_a)
    cloud["U"] = u
    cloud["U_mag"] = np.full(pts_a.shape[0], u_ax, dtype=float)
    return cloud


def make_glyph_arrows(
    cloud,
    *,
    stride: int = DEFAULT_STRIDE,
    factor: float = DEFAULT_FACTOR,
    max_arrows: int = DEFAULT_MAX_ARROWS,
    mag_percentile: float = GLYPH_MAG_PERCENTILE,
):
    """Build arrow glyphs from a velocity cloud (already in plotter units).

    Orientation uses true ``U``; arrow *length* scales with ``U_mag`` capped at the
    given percentile so tip spikes cannot dominate the Design 3-D view (§15.3).
    """
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

    mag = np.asarray(src["U_mag"], dtype=float)
    pct = float(np.clip(mag_percentile, 50.0, 100.0))
    if mag.size and pct < 100.0:
        cap = float(np.percentile(mag, pct))
        if cap > 0.0:
            src["U_glyph_scale"] = np.minimum(mag, cap)
            scale_key = "U_glyph_scale"
        else:
            scale_key = "U_mag"
    else:
        scale_key = "U_mag"

    arrows = src.glyph(
        orient="U",
        scale=scale_key,
        factor=float(factor),
        geom=pv.Arrow(),
    )
    return arrows if arrows.n_points > 0 else None


def cfd_cloud_to_as_built(cloud, orientation: str):
    """Map a velocity cloud from the CFD (solve) frame back to the as-built preview frame.

    The axial CFD copy of the rotor may be rotated 180 deg about X relative to the as-built
    part (``fansim.cfd.orientation.AXIAL_CFD_ORIENTATION``). Drawing the solve's velocity
    cloud directly onto the as-built preview mesh is wrong when that orientation is
    ``"flipped"``: points and vectors must be mapped through the same 180 deg-about-X
    rotation the STL went through (``fansim.cfd.orientation.flip_about_x``), i.e. negate the
    y and z components of both. ``"as_built"`` is the identity (returns ``cloud`` unchanged).
    ``U_mag`` is a magnitude and is unaffected either way.
    """
    from fansim.cfd.orientation import ORIENTATIONS

    if orientation not in ORIENTATIONS:
        raise ValueError(f"orientation must be one of {ORIENTATIONS}, got {orientation!r}")
    if orientation == "as_built":
        return cloud
    import pyvista as pv

    pts = np.array(cloud.points, dtype=float)
    pts[:, 1] *= -1.0
    pts[:, 2] *= -1.0
    u = np.array(cloud["U"], dtype=float)
    u[:, 1] *= -1.0
    u[:, 2] *= -1.0
    out = pv.PolyData(pts)
    out["U"] = u
    out["U_mag"] = np.array(cloud["U_mag"])
    return out


def ensure_velocity_glyphs(
    case_dir: str | Path | None,
    *,
    runner_factory=None,
    image_ok=None,
    mesh=None,
    max_points: int = DEFAULT_MAX_CLOUD,
    z_half_span_m: float = DEFAULT_Z_HALF_SPAN_M,
    use_cache: bool = True,
) -> VelocityGlyphs:
    """Load / subsample velocity cloud for a case. Fail-soft — never raises.

    When ``use_cache`` is True (default), process memory + on-disk ``.vtp`` (§22.1 /
    §22.9) avoid re-reading the OpenFOAM mesh on design reselect / cockpit restart.
    Pass ``mesh=`` to skip ``read_case`` (and still populate both caches).
    """
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

    cache_key: tuple[str, str, int, float] | None = None
    if use_cache:
        cache_key = _cache_key(case_dir, max_points, z_half_span_m)
        hit = peek_cached_velocity_glyphs(
            case_dir, max_points=max_points, z_half_span_m=z_half_span_m,
        )
        if hit is not None:
            return hit

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
        art = VelocityGlyphs(
            case_dir=case_dir,
            cloud=cloud,
            caption=f"{n} velocity sample points (subsampled near impeller)",
            available=True,
            n_points=n,
        )
        if cache_key is not None:
            _GLYPH_CACHE[cache_key] = art
            _save_disk_glyphs(
                case_dir, art, max_points=max_points, z_half_span_m=z_half_span_m,
            )
        return art
    except Exception:  # noqa: BLE001 — viz must never break Assess
        return unavailable
