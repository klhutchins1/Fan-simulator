"""Stage-1 duct airflow midplane slices for the Fan cockpit.

After Assess (or when selecting a Results design whose case still has fields),
reconstruct the latest time if needed, slice the internal mesh on the Y=0
meridional plane (axis = Z), and write off-screen PNGs for ``|U|`` and ``p``.

Stage-2 interactive velocity glyphs live in ``fansim.cfd.glyphs`` (same
reconstruct readiness). Streamlines / Mixed-Volute reuse — see roadmap.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import threading

import numpy as np

# Meridional cut through the duct axis (Z). Flow is +Z: inlet (−Z) → outlet (+Z).
_MIDPLANE_NORMAL = (0.0, 1.0, 0.0)
_VIZ_SUBDIR = Path("postProcessing") / "cockpit_viz"
# v8: |U| color scale is the 95th-percentile through-flow, not the tip-speed spike.
_U_NAME = "U_midplane_v8.png"
_P_NAME = "p_midplane_v7.png"
# Scroll layout (volute): full Y=0 section, camera up=+Z so +X outlet is screen-right.
_U_NAME_SCROLL = "U_midplane_scroll_v1.png"
_P_NAME_SCROLL = "p_midplane_scroll_v1.png"
# Off-screen Plotter + matplotlib mathtext is not thread-safe (Windows hard crash).
_RENDER_LOCK = threading.Lock()

_LAYOUTS = ("axial", "scroll")

# VTK_POLYHEDRON — snappyHexMesh leaves these; vtkCutter WARNs and slows (§22.4).
_VTK_POLYHEDRON = 42


def _mesh_has_polyhedra(mesh) -> bool:
    try:
        types = np.asarray(mesh.celltypes)
        return bool(np.any(types == _VTK_POLYHEDRON))
    except Exception:  # noqa: BLE001
        return False


def slice_volume_for_viz(mesh, normal, origin):
    """Slice a volume field for cockpit PNGs without polyhedron cutter spam (§22.4).

    Hex/tet/wedge meshes use PyVista ``slice`` (fast, exact). When polyhedra are
    present, drop those cells before cutting when a usable majority remains; otherwise
    fall back to a cell-center plane band + ``delaunay_2d`` so VTK never contours
    non-manifold polyhedra.
    """
    origin = tuple(float(x) for x in origin)
    normal = tuple(float(x) for x in normal)

    if not _mesh_has_polyhedra(mesh):
        return mesh.slice(normal=normal, origin=origin)

    try:
        types = np.asarray(mesh.celltypes)
        keep = types != _VTK_POLYHEDRON
        n_keep = int(np.count_nonzero(keep))
        if n_keep >= max(1000, int(0.55 * types.size)):
            subset = mesh.extract_cells(keep)
            if subset.n_cells > 0:
                return subset.slice(normal=normal, origin=origin)
    except Exception:  # noqa: BLE001 — fall through to center band
        pass

    return _slice_cell_center_band(mesh, normal, origin)


def _slice_cell_center_band(mesh, normal, origin):
    """PolyData near the plane from cell centers (no vtkCutter on polyhedra)."""
    import pyvista as pv

    n = np.asarray(normal, dtype=float)
    n = n / max(float(np.linalg.norm(n)), 1e-12)
    o = np.asarray(origin, dtype=float)
    try:
        centers = mesh.cell_centers()
    except Exception:  # noqa: BLE001
        return mesh.slice(normal=tuple(n), origin=tuple(o))

    pts = np.asarray(centers.points, dtype=float)
    if pts.size == 0:
        return pv.PolyData()
    dist = (pts - o) @ n
    # Band ~1–2 typical near-impeller cell sizes (screening base_cell ~6 mm → 0.006 m).
    b = mesh.bounds
    char = max(
        abs(float(b[1]) - float(b[0])),
        abs(float(b[3]) - float(b[2])),
        abs(float(b[5]) - float(b[4])),
        0.05,
    )
    band = max(0.002, min(0.008, 0.02 * char))
    mask = np.abs(dist) <= band
    if not np.any(mask):
        # Widen once so sparse meshes still yield a surface.
        mask = np.abs(dist) <= max(band * 3.0, 0.01)
    if not np.any(mask):
        return pv.PolyData()

    idx = np.nonzero(mask)[0]
    cloud = centers.extract_points(idx, include_cells=False)
    # Re-attach cell arrays vtk may have dropped.
    for name in list(centers.array_names):
        if name not in cloud.array_names and name in centers.point_data:
            try:
                cloud[name] = np.asarray(centers[name])[idx]
            except Exception:  # noqa: BLE001
                pass
    try:
        # Project onto the cut plane then triangulate for a fillable surface.
        proj = cloud.points - np.outer((cloud.points - o) @ n, n)
        flat = pv.PolyData(proj)
        for name in cloud.point_data.keys():
            flat[name] = cloud[name]
        surf = flat.delaunay_2d()
        if surf.n_cells > 0:
            return surf
    except Exception:  # noqa: BLE001
        pass
    return cloud


@dataclass(frozen=True)
class MidplaneArtifacts:
    """Paths to cached midplane PNGs (may be missing if unavailable)."""

    case_dir: Path
    u_png: Path | None
    p_png: Path | None
    caption: str
    available: bool

    @property
    def primary_png(self) -> Path | None:
        return self.u_png or self.p_png


def _is_time_dir(name: str) -> bool:
    try:
        float(name)
        return True
    except ValueError:
        return False


def has_reconstructed_fields(case_dir: str | Path) -> bool:
    """True when a non-zero reconstructed time dir contains ``U`` (and preferably ``p``)."""
    case_dir = Path(case_dir)
    if not case_dir.is_dir():
        return False
    best: float | None = None
    best_dir: Path | None = None
    for p in case_dir.iterdir():
        if not p.is_dir() or not _is_time_dir(p.name):
            continue
        t = float(p.name)
        if t <= 0.0:
            continue
        if best is None or t > best:
            best, best_dir = t, p
    if best_dir is None:
        return False
    return (best_dir / "U").is_file()


def has_decomposed_fields(case_dir: str | Path) -> bool:
    """True when any ``processor*/<t>/U`` exists with ``t > 0``."""
    case_dir = Path(case_dir)
    if not case_dir.is_dir():
        return False
    for proc in case_dir.glob("processor*"):
        if not proc.is_dir():
            continue
        for child in proc.iterdir():
            if not child.is_dir() or not _is_time_dir(child.name):
                continue
            if float(child.name) <= 0.0:
                continue
            if (child / "U").is_file():
                return True
    return False


def case_has_flow_fields(case_dir: str | Path) -> bool:
    """Reconstructed or decomposed volume fields present on disk."""
    return has_reconstructed_fields(case_dir) or has_decomposed_fields(case_dir)


def artifact_paths(case_dir: str | Path, *, layout: str = "axial") -> tuple[Path, Path]:
    """Canonical cache locations under ``postProcessing/cockpit_viz/``."""
    root = Path(case_dir) / _VIZ_SUBDIR
    if layout == "scroll":
        return root / _U_NAME_SCROLL, root / _P_NAME_SCROLL
    return root / _U_NAME, root / _P_NAME


def find_cached_midplane(
    case_dir: str | Path, *, layout: str = "axial",
) -> MidplaneArtifacts | None:
    """Return artifacts if both (or at least one) midplane PNGs already exist."""
    case_dir = Path(case_dir)
    u_png, p_png = artifact_paths(case_dir, layout=layout)
    u = u_png if u_png.is_file() else None
    p = p_png if p_png.is_file() else None
    if u is None and p is None:
        return None
    if layout == "scroll":
        cap = (
            "Umag scroll section — OUTLET RIGHT (+X), INLET UP (+Z)"
            if u
            else "pressure scroll section — OUTLET RIGHT (+X), INLET UP (+Z)"
        )
    else:
        cap = (
            "Umag midplane — FRONT LEFT -> OUTLET RIGHT (wake-biased)"
            if u
            else "pressure midplane — FRONT LEFT -> OUTLET RIGHT (wake-biased)"
        )
    return MidplaneArtifacts(
        case_dir=case_dir,
        u_png=u,
        p_png=p,
        caption=cap,
        available=True,
    )


def ensure_reconstructed(
    case_dir: str | Path,
    *,
    runner_factory=None,
    image_ok=None,
) -> bool:
    """Run ``reconstructPar -latestTime`` when only decomposed fields exist.

    Returns True if reconstructed fields are available afterward. Never raises —
    Docker-down / prune / command failure → False.
    """
    case_dir = Path(case_dir)
    if has_reconstructed_fields(case_dir):
        return True
    if not has_decomposed_fields(case_dir):
        return False
    try:
        from fansim.cfd.runner import OpenFOAMRunner, image_available

        check = image_ok if image_ok is not None else image_available
        if not check():
            return False
        factory = runner_factory or OpenFOAMRunner
        runner = factory(case_dir)
        result = runner.run("reconstructPar -latestTime", check=False)
        return bool(result.ok) and has_reconstructed_fields(case_dir)
    except Exception:  # noqa: BLE001 — viz must never break Assess
        return False


def _grid_with_umag(grid):
    """Attach cell-data ``U_mag`` from vector ``U`` (point or cell data)."""
    g = grid
    if "U" in g.point_data and "U" not in g.cell_data:
        g = g.point_data_to_cell_data()
    if "U" not in g.cell_data and "U" not in g.point_data:
        raise KeyError("mesh has no U field")
    src = g.cell_data if "U" in g.cell_data else g.point_data
    u = np.asarray(src["U"], dtype=float)
    if u.ndim == 1:
        mag = np.abs(u)
    else:
        mag = np.linalg.norm(u, axis=1)
    if "U" in g.cell_data:
        g.cell_data["U_mag"] = mag
    else:
        g.point_data["U_mag"] = mag
    return g


def _grid_with_uaxial(grid):
    """Attach ``U_axial`` = the Z (fan-axis) component of ``U``.

    Signed: +Z is the delivery direction (inlet −Z → outlet +Z), so **negative U_axial
    is reverse flow** — exactly the recirculation that shows up when the fan stalls at a
    hose it can't hold. Rendered with a diverging colormap so reverse regions stand out.
    """
    g = grid
    if "U" in g.point_data and "U" not in g.cell_data:
        g = g.point_data_to_cell_data()
    if "U" not in g.cell_data and "U" not in g.point_data:
        raise KeyError("mesh has no U field")
    src = g.cell_data if "U" in g.cell_data else g.point_data
    u = np.asarray(src["U"], dtype=float)
    if u.ndim == 1:  # already scalar (an axial-only field)
        uz = u
    else:
        uz = u[:, 2]
    if "U" in g.cell_data:
        g.cell_data["U_axial"] = uz
    else:
        g.point_data["U_axial"] = uz
    return g


def throughflow_umag_clim(values) -> tuple[float, float]:
    """Color scale for |U| from the through-flow, not the tip-speed spike.

    The 95th percentile matches the streamline clamp. A floor of 0.5 m/s keeps a
    quiet slice from collapsing to a black bar.
    """
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return (0.0, 0.5)
    hi = float(np.percentile(arr, 95.0))
    return (0.0, max(hi, 0.5))


def render_midplane_pngs(
    case_dir: str | Path,
    *,
    mesh=None,
    window_size: tuple[int, int] = (1600, 480),
    layout: str = "axial",
) -> MidplaneArtifacts:
    """Slice internal mesh on Y=0 and write ``|U|`` + ``p`` PNGs.

    ``layout="axial"`` (default): impeller-anchored crop biased to the +Z wake;
    look from +Y with up=+X so −Z is left (FRONT) and +Z is right (OUTLET).

    ``layout="scroll"``: keep the full Y=0 section (no tip-radius crop); look from
    +Y with up=+Z so +X is right (volute OUTLET) and +Z is up (INLET). Used by the
    Volute tab — the axial crop was cutting the Archimedean scroll to a thin strip.

    ``mesh`` may be injected for tests (PyVista UnstructuredGrid-like). When
    omitted, loads via ``fansim.acoustics.case.read_case`` (requires reconstruct).
    """
    import pyvista as pv

    if layout not in _LAYOUTS:
        raise ValueError(f"unknown midplane layout {layout!r}; known: {_LAYOUTS}")

    case_dir = Path(case_dir)
    out_u, out_p = artifact_paths(case_dir, layout=layout)
    out_u.parent.mkdir(parents=True, exist_ok=True)

    if mesh is None:
        from fansim.acoustics.case import read_case

        mesh = read_case(case_dir)

    mesh = _grid_with_umag(mesh)
    origin = tuple(float(x) for x in mesh.center)
    slc = slice_volume_for_viz(mesh, _MIDPLANE_NORMAL, origin)
    if slc.n_points == 0:
        return MidplaneArtifacts(
            case_dir=case_dir, u_png=None, p_png=None,
            caption="Airflow not available for this design", available=False,
        )

    b = slc.bounds
    z0, z1 = float(b[4]), float(b[5])
    x0, x1 = float(b[0]), float(b[1])
    xc = 0.5 * (x0 + x1)
    zc = 0.0 if (z0 < 0.0 < z1) else 0.5 * (z0 + z1)

    if layout == "axial":
        # Impeller-anchored crop (rig places the rotor near Z=0). Bias +Z: short approach,
        # long wake — uniform inlet green is boring; the jet develops behind the blades.
        r_tip = max(abs(x0), abs(x1), abs(x0 - xc), abs(x1 - xc), 0.03)
        z_in = max(1.1 * r_tip, 0.04)   # −Z (FRONT) — just enough to see the LE entry
        z_out = max(4.0 * r_tip, 0.10)  # +Z (OUTLET) — hub wake + tip jets
        z_look = zc + 0.5 * (z_out - z_in)  # frame mid of the asymmetric window
        x_keep = 1.08 * r_tip
        try:
            slc = slc.clip_box(
                [
                    xc - x_keep, xc + x_keep,
                    float(b[2]) - 0.01, float(b[3]) + 0.01,
                    zc - z_in, zc + z_out,
                ],
                invert=False,
            )
        except Exception:  # noqa: BLE001 — keep full slice if clip fails
            pass
        if slc.n_points == 0:
            return MidplaneArtifacts(
                case_dir=case_dir, u_png=None, p_png=None,
                caption="Airflow not available for this design", available=False,
            )
        cam_focal = (float(xc), float(origin[1]), float(z_look))
        view_up = (1.0, 0.0, 0.0)
        left_label, right_label = "FRONT (inlet)", "OUTLET (flow ->)"
        title_u, title_p = "Umag midplane (m/s)", "pressure midplane (m2/s2)"
        cap_u = "Umag midplane — FRONT LEFT -> OUTLET RIGHT (wake-biased)"
        cap_p = "pressure midplane — FRONT LEFT -> OUTLET RIGHT (wake-biased)"
    else:
        # Full scroll section — outlet stub lives at +X beyond tip radius.
        cam_focal = (float(xc), float(origin[1]), float(zc))
        view_up = (0.0, 0.0, 1.0)
        left_label, right_label = "scroll / eye", "OUTLET (+X)"
        title_u, title_p = "Umag scroll section (m/s)", "pressure scroll section (m2/s2)"
        cap_u = "Umag scroll section — OUTLET RIGHT (+X), INLET UP (+Z)"
        cap_p = "pressure scroll section — OUTLET RIGHT (+X), INLET UP (+Z)"

    u_written = p_written = None

    def _shot(scalars: str, title: str, path: Path) -> Path | None:
        if scalars not in slc.array_names and scalars not in (
            list(slc.cell_data.keys()) + list(slc.point_data.keys())
        ):
            if scalars not in slc.cell_data and scalars not in slc.point_data:
                return None
        # Serialize: concurrent off-screen Plotters + vtkMatplotlibMathTextUtilities
        # hard-crash the interpreter on Windows (selecting designs while midplane builds).
        with _RENDER_LOCK:
            pl = pv.Plotter(off_screen=True, window_size=list(window_size))
            try:
                pl.background_color = "white"
                mesh_kw = {}
                if scalars == "U_mag":
                    src = slc.point_data if "U_mag" in slc.point_data else slc.cell_data
                    mesh_kw["clim"] = list(throughflow_umag_clim(src["U_mag"]))
                pl.add_mesh(
                    slc, scalars=scalars, cmap="turbo", show_edges=False,
                    scalar_bar_args={
                        "title": title,
                        "n_labels": 5,
                        "fmt": "%.2f",
                        "title_font_size": 12,
                        "label_font_size": 10,
                        "width": 0.12,
                        "height": 0.55,
                        "position_x": 0.86,
                        "position_y": 0.2,
                    },
                    **mesh_kw,
                )
                bb = slc.bounds
                xspan = max(abs(float(bb[1]) - float(bb[0])), 1e-6)
                zspan = max(abs(float(bb[5]) - float(bb[4])), 1e-6)
                if layout == "scroll":
                    # Fit both X (outlet) and Z (inlet) extents in the viewport.
                    half = 0.55 * max(xspan, zspan)
                else:
                    half = 0.55 * xspan  # fit duct diameter in viewport height → wide Z panorama
                dist = 3.0 * max(half, 0.1)
                fx, fy, fz = cam_focal
                pl.camera_position = [
                    (fx, fy + dist, fz),
                    (fx, fy, fz),
                    view_up,
                ]
                pl.camera.parallel_projection = True
                pl.camera.parallel_scale = half
                # ASCII only — ``|U|`` / arrows go through matplotlib mathtext and can crash VTK.
                pl.add_text(title, font_size=11, color="black", position="upper_edge")
                pl.add_text(
                    left_label, font_size=11, color="black", position="lower_left",
                )
                pl.add_text(
                    right_label, font_size=11, color="black", position="lower_right",
                )
                pl.screenshot(str(path))
            finally:
                pl.close()
        return path if path.is_file() else None

    try:
        u_written = _shot("U_mag", title_u, out_u)
    except Exception:  # noqa: BLE001
        u_written = None
    try:
        if "p" in slc.cell_data or "p" in slc.point_data or "p" in slc.array_names:
            p_written = _shot("p", title_p, out_p)
    except Exception:  # noqa: BLE001
        p_written = None

    ok = u_written is not None or p_written is not None
    cap = (
        cap_u
        if u_written
        else (cap_p if p_written else "Airflow not available for this design")
    )
    return MidplaneArtifacts(
        case_dir=case_dir,
        u_png=u_written,
        p_png=p_written,
        caption=cap,
        available=ok,
    )


_UAXIAL_NAME = "U_axial_slice_v1.png"


@dataclass(frozen=True)
class AxialSliceArtifact:
    """Path to the cached axial-velocity (Uz) cut-plane PNG (may be missing)."""

    case_dir: Path
    png: Path | None
    caption: str
    available: bool


def axial_artifact_path(case_dir: str | Path) -> Path:
    """Canonical cache location for the axial-Uz slice PNG."""
    return Path(case_dir) / _VIZ_SUBDIR / _UAXIAL_NAME


def render_axial_uz_png(
    case_dir: str | Path,
    *,
    mesh=None,
    window_size: tuple[int, int] = (960, 900),
    clim: tuple[float, float] | None = None,
) -> AxialSliceArtifact:
    """Slice the volume on a Z-normal plane at the impeller and render axial velocity ``Uz``.

    A STAR-CCM+-style "Velocity[k]" cut-plane: look down the fan axis at the rotor face,
    color by the axial velocity component with a **diverging** colormap centered on zero, so
    forward delivery (+Z) and reverse/recirculating flow (−Z) read as opposite colors. The
    reverse (cool) regions are the recirculation that grows as the fan approaches stall.

    ``mesh`` may be injected for tests (a PyVista grid with a vector ``U``). Otherwise the
    reconstructed case is read via ``fansim.acoustics.case.read_case``. ``clim`` overrides the
    auto symmetric range (98th-percentile of |Uz|, floor 0.5 m/s).
    """
    import pyvista as pv

    case_dir = Path(case_dir)
    out = axial_artifact_path(case_dir)
    out.parent.mkdir(parents=True, exist_ok=True)

    if mesh is None:
        from fansim.acoustics.case import read_case

        mesh = read_case(case_dir)

    mesh = _grid_with_uaxial(mesh)
    # Rig places the rotor near Z=0; slice there when it is inside the mesh, else at the center.
    b = mesh.bounds
    z0, z1 = float(b[4]), float(b[5])
    cx, cy = float(mesh.center[0]), float(mesh.center[1])
    z_cut = 0.0 if z0 < 0.0 < z1 else 0.5 * (z0 + z1)
    slc = slice_volume_for_viz(mesh, (0.0, 0.0, 1.0), (cx, cy, z_cut))
    if slc.n_points == 0:
        return AxialSliceArtifact(
            case_dir=case_dir, png=None,
            caption="Axial-velocity slice not available for this design", available=False,
        )

    src = slc.cell_data if "U_axial" in slc.cell_data else slc.point_data
    vals = np.asarray(src["U_axial"], dtype=float)
    if clim is None:
        lim = float(np.percentile(np.abs(vals), 98.0)) if vals.size else 1.0
        lim = max(lim, 0.5)
        clim = (-lim, lim)

    # Fit the disc (X–Y extent of the slice) in the viewport.
    xspan = max(float(b[1]) - float(b[0]), 1e-6)
    yspan = max(float(b[3]) - float(b[2]), 1e-6)
    half = 0.55 * max(xspan, yspan)

    with _RENDER_LOCK:
        pl = pv.Plotter(off_screen=True, window_size=list(window_size))
        try:
            pl.background_color = "white"
            # coolwarm_r: delivery (+Z, positive) → blue, reverse (−Z, negative) → red — matches
            # the STAR-CCM+ Velocity[k] convention (blue positive) and flags reverse in alert red.
            pl.add_mesh(
                slc, scalars="U_axial", cmap="coolwarm_r", clim=list(clim),
                show_edges=False, smooth_shading=False,
                scalar_bar_args={
                    "title": "axial Uz (m/s)",
                    "n_labels": 5,
                    "fmt": "%.1f",
                    "title_font_size": 12,
                    "label_font_size": 10,
                    "width": 0.12,
                    "height": 0.55,
                    "position_x": 0.86,
                    "position_y": 0.2,
                },
            )
            # Look down the axis from +Z toward −Z (fan face on), up = +Y.
            dist = 3.0 * max(half, 0.05)
            pl.camera_position = [
                (cx, cy, z_cut + dist),
                (cx, cy, z_cut),
                (0.0, 1.0, 0.0),
            ]
            pl.camera.parallel_projection = True
            pl.camera.parallel_scale = half
            pl.add_text("axial velocity Uz (m/s)", font_size=11, color="black",
                        position="upper_edge")
            pl.add_text("blue = delivery (+Z)   red = reverse (-Z)", font_size=10,
                        color="black", position="lower_left")
            pl.screenshot(str(out))
        finally:
            pl.close()

    if not out.is_file():
        return AxialSliceArtifact(
            case_dir=case_dir, png=None,
            caption="Axial-velocity slice not available for this design", available=False,
        )
    return AxialSliceArtifact(
        case_dir=case_dir, png=out,
        caption="axial Uz cut-plane — blue = delivery (+Z), red = reverse flow",
        available=True,
    )


_STREAM_NAME = "streamlines_v1.png"


@dataclass(frozen=True)
class StreamlineArtifact:
    """Path to the cached streamline PNG (may be missing)."""

    case_dir: Path
    png: Path | None
    caption: str
    available: bool


def streamline_artifact_path(case_dir: str | Path) -> Path:
    """Canonical cache location for the streamline PNG."""
    return Path(case_dir) / _VIZ_SUBDIR / _STREAM_NAME


def render_streamlines_png(
    case_dir: str | Path,
    *,
    mesh=None,
    window_size: tuple[int, int] = (1000, 1000),
    n_seed: int = 24,
    clim: tuple[float, float] | None = None,
) -> StreamlineArtifact:
    """Seed a disc upstream of the rotor and trace streamlines colored by ``|U|``.

    A STAR-CCM+-style hero shot: streamlines enter along the axis, accelerate through the
    blade rows (warm colors), and fan out into the wake. Seeds a disc of ~tip radius just
    inside the −Z (inlet) side and integrates both directions so the approach and the wake
    both show. The impeller STL, if present in the case, is drawn as a light-grey body for
    context. Fail-soft; ``mesh`` may be injected for tests.

    Defaults lean cheap for cockpit first-open (§22.8): ``n_seed=24``, capped integration
    steps. Raise ``n_seed`` for publication stills.
    """
    import pyvista as pv

    case_dir = Path(case_dir)
    out = streamline_artifact_path(case_dir)
    out.parent.mkdir(parents=True, exist_ok=True)

    if mesh is None:
        from fansim.acoustics.case import read_case

        mesh = read_case(case_dir)

    # Streamline integration interpolates POINT data along the lines, so U (and the U_mag
    # used for coloring) must live on points — else the traced tubes carry no scalar.
    if "U" not in mesh.point_data:
        mesh = mesh.cell_data_to_point_data()
    if "U" not in mesh.point_data:
        return StreamlineArtifact(
            case_dir=case_dir, png=None,
            caption="Streamlines not available for this design", available=False,
        )
    uvec = np.asarray(mesh.point_data["U"], dtype=float)
    mesh.point_data["U_mag"] = (
        np.linalg.norm(uvec, axis=1) if uvec.ndim > 1 else np.abs(uvec))

    b = mesh.bounds
    cx, cy = float(mesh.center[0]), float(mesh.center[1])
    z0, z1 = float(b[4]), float(b[5])
    r_tip = 0.5 * max(float(b[1]) - float(b[0]), float(b[3]) - float(b[2]))
    z_fan = 0.0 if z0 < 0.0 < z1 else 0.5 * (z0 + z1)
    # Keep a wide radial window so lines are free to SPIRAL outward (a tight radial clip
    # truncates the swirl into short arcs), and a long wake so the corkscrew develops.
    zlo = max(z0, z_fan - 1.0 * r_tip)
    zhi = min(z1, z_fan + 10.0 * r_tip)
    try:
        focused = mesh.clip_box(
            [cx - 5.0 * r_tip, cx + 5.0 * r_tip,
             cy - 5.0 * r_tip, cy + 5.0 * r_tip, zlo, zhi],
            invert=False,
        )
        if focused.n_points > 0:
            mesh = focused
    except Exception:  # noqa: BLE001 — keep full mesh if clip fails
        pass

    r_seed = max(0.95 * r_tip, 1e-4)
    # Seed the wake DOWNSTREAM of the blades, not upstream: an upstream line integrated forward
    # dies the instant it hits a blade surface (the 9 blades fill the annulus) and reads as a
    # short dash. Seeding past the trailing edges lets the swirling wake trace long spirals.
    z_seed = min(zhi - 0.1 * r_tip, z_fan + 1.5 * r_tip)
    seed = pv.Disc(center=(cx, cy, z_seed), normal=(0.0, 0.0, 1.0),
                   inner=0.15 * r_tip, outer=r_seed, r_res=1, c_res=max(8, n_seed))
    try:
        streams = mesh.streamlines_from_source(
            seed, vectors="U", integration_direction="forward",
            max_steps=4000, initial_step_length=0.25, max_step_length=1.2,
            terminal_speed=1e-8,
        )
    except Exception:  # noqa: BLE001
        streams = None
    if streams is None or streams.n_points == 0:
        return StreamlineArtifact(
            case_dir=case_dir, png=None,
            caption="Streamlines not available for this design", available=False,
        )

    src = streams.point_data if "U_mag" in streams.point_data else streams.cell_data
    vals = np.asarray(src.get("U_mag", []), dtype=float)
    if clim is None:
        # Scale to the through-flow, not the blade-tip speed. The 95th percentile spans the wake
        # jet; clamp into [2, 8] m/s so mid-range lines show color instead of saturating warm.
        hi = float(np.percentile(vals, 95.0)) if vals.size else 5.0
        hi = min(max(hi, 2.0), 8.0)
        clim = (0.0, hi)
    tubes = streams.tube(radius=0.006 * r_tip)

    with _RENDER_LOCK:
        pl = pv.Plotter(off_screen=True, window_size=list(window_size))
        try:
            pl.background_color = "white"
            pl.add_mesh(
                tubes, scalars="U_mag", cmap="turbo", clim=list(clim),
                show_scalar_bar=True,
                scalar_bar_args={
                    "title": "Velocity |U| (m/s)",
                    "n_labels": 5, "fmt": "%.1f",
                    "title_font_size": 12, "label_font_size": 10,
                    "width": 0.12, "height": 0.55, "position_x": 0.86, "position_y": 0.2,
                },
            )
            # Impeller STL context omitted in cockpit stills (§22.8) — wake tubes carry the story.
            # Look down the axis from DOWNSTREAM (slightly off-axis) back at the rotor: the wake
            # swirl then reads as a corkscrew. A side view would flatten it into straight lines.
            pl.camera_position = [
                (cx + 0.5 * r_tip, cy + 0.4 * r_tip, zhi + 3.0 * r_tip),
                (cx, cy, z_fan),
                (0.0, 1.0, 0.0),
            ]
            pl.reset_camera()
            pl.camera.zoom(1.9)  # fill the frame — reset_camera fits the wide clip / stray lines
            pl.add_text("streamlines — |U| through the rotor", font_size=11,
                        color="black", position="upper_edge")
            pl.screenshot(str(out))
        finally:
            pl.close()

    if not out.is_file():
        return StreamlineArtifact(
            case_dir=case_dir, png=None,
            caption="Streamlines not available for this design", available=False,
        )
    return StreamlineArtifact(
        case_dir=case_dir, png=out,
        caption="streamlines colored by |U| — inlet (−Z) → wake (+Z)", available=True,
    )


def ensure_streamlines_artifact(
    case_dir: str | Path | None,
    *,
    runner_factory=None,
    image_ok=None,
    mesh=None,
    force: bool = False,
) -> StreamlineArtifact:
    """Find or build the streamline PNG for a case (fail-soft, mirrors midplane)."""
    unavailable = StreamlineArtifact(
        case_dir=Path(case_dir) if case_dir else Path("."),
        png=None, caption="Streamlines not available for this design", available=False,
    )
    if case_dir is None:
        return unavailable
    case_dir = Path(case_dir)
    if not case_dir.is_dir():
        return unavailable

    if not force:
        cached = streamline_artifact_path(case_dir)
        if cached.is_file():
            return StreamlineArtifact(
                case_dir=case_dir, png=cached,
                caption="streamlines colored by |U| — inlet (−Z) → wake (+Z)",
                available=True,
            )

    if mesh is None:
        if not case_has_flow_fields(case_dir):
            return unavailable
        if not ensure_reconstructed(case_dir, runner_factory=runner_factory, image_ok=image_ok):
            return unavailable

    try:
        return render_streamlines_png(case_dir, mesh=mesh)
    except Exception:  # noqa: BLE001 — viz must never break Assess
        return unavailable


def ensure_axial_uz_artifact(
    case_dir: str | Path | None,
    *,
    runner_factory=None,
    image_ok=None,
    mesh=None,
    force: bool = False,
) -> AxialSliceArtifact:
    """Find or build the axial-Uz slice PNG for a case (fail-soft, mirrors midplane)."""
    unavailable = AxialSliceArtifact(
        case_dir=Path(case_dir) if case_dir else Path("."),
        png=None,
        caption="Axial-velocity slice not available for this design",
        available=False,
    )
    if case_dir is None:
        return unavailable
    case_dir = Path(case_dir)
    if not case_dir.is_dir():
        return unavailable

    if not force:
        cached = axial_artifact_path(case_dir)
        if cached.is_file():
            return AxialSliceArtifact(
                case_dir=case_dir, png=cached,
                caption="axial Uz cut-plane — blue = delivery (+Z), red = reverse flow",
                available=True,
            )

    if mesh is None:
        if not case_has_flow_fields(case_dir):
            return unavailable
        if not ensure_reconstructed(case_dir, runner_factory=runner_factory, image_ok=image_ok):
            return unavailable

    try:
        return render_axial_uz_png(case_dir, mesh=mesh)
    except Exception:  # noqa: BLE001 — viz must never break Assess
        return unavailable


def ensure_midplane_artifacts(
    case_dir: str | Path | None,
    *,
    runner_factory=None,
    image_ok=None,
    mesh=None,
    force: bool = False,
    layout: str = "axial",
) -> MidplaneArtifacts:
    """Find or build midplane PNGs for a case directory.

    Fail-soft: missing case / no fields / Docker down / render error →
    ``available=False`` and caption ``Airflow not available for this design``.
    """
    unavailable = MidplaneArtifacts(
        case_dir=Path(case_dir) if case_dir else Path("."),
        u_png=None,
        p_png=None,
        caption="Airflow not available for this design",
        available=False,
    )
    if case_dir is None:
        return unavailable
    case_dir = Path(case_dir)
    if not case_dir.is_dir():
        return unavailable

    if not force:
        cached = find_cached_midplane(case_dir, layout=layout)
        if cached is not None and cached.u_png is not None:
            return cached

    if mesh is None:
        if not case_has_flow_fields(case_dir):
            return unavailable
        if not ensure_reconstructed(case_dir, runner_factory=runner_factory, image_ok=image_ok):
            return unavailable

    try:
        return render_midplane_pngs(case_dir, mesh=mesh, layout=layout)
    except Exception:  # noqa: BLE001
        return unavailable
