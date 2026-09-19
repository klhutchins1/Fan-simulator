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
# v7: wake-biased crop + VTK-safe labels (no ``|U|`` mathtext) + render lock.
_U_NAME = "U_midplane_v7.png"
_P_NAME = "p_midplane_v7.png"
# Off-screen Plotter + matplotlib mathtext is not thread-safe (Windows hard crash).
_RENDER_LOCK = threading.Lock()


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


def artifact_paths(case_dir: str | Path) -> tuple[Path, Path]:
    """Canonical cache locations under ``postProcessing/cockpit_viz/``."""
    root = Path(case_dir) / _VIZ_SUBDIR
    return root / _U_NAME, root / _P_NAME


def find_cached_midplane(case_dir: str | Path) -> MidplaneArtifacts | None:
    """Return artifacts if both (or at least one) midplane PNGs already exist."""
    case_dir = Path(case_dir)
    u_png, p_png = artifact_paths(case_dir)
    u = u_png if u_png.is_file() else None
    p = p_png if p_png.is_file() else None
    if u is None and p is None:
        return None
    return MidplaneArtifacts(
        case_dir=case_dir,
        u_png=u,
        p_png=p,
        caption=(
            "Umag midplane — FRONT LEFT -> OUTLET RIGHT (wake-biased)"
            if u
            else "pressure midplane — FRONT LEFT -> OUTLET RIGHT (wake-biased)"
        ),
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


def render_midplane_pngs(
    case_dir: str | Path,
    *,
    mesh=None,
    window_size: tuple[int, int] = (1600, 480),
) -> MidplaneArtifacts:
    """Slice internal mesh on Y=0 and write ``|U|`` + ``p`` PNGs.

    Orientation (v3+): look from **+Y** with +X up so world **−Z is left** (FRONT /
    inlet) and **+Z is right** (OUTLET). VTK's view-right is ``ViewUp × ViewPlaneNormal``;
    looking from −Y accidentally mirrored that, which v2 got wrong.

    v6 keeps the crop impeller-anchored but biases it downstream: short FRONT
    approach, long OUTLET wake (the interesting jet / hub dead-zone develops
    behind the blades). Camera aims at the window mid so the PNG isn't
    left-padded with empty inlet.

    ``mesh`` may be injected for tests (PyVista UnstructuredGrid-like). When
    omitted, loads via ``fansim.acoustics.case.read_case`` (requires reconstruct).
    """
    import pyvista as pv

    case_dir = Path(case_dir)
    out_u, out_p = artifact_paths(case_dir)
    out_u.parent.mkdir(parents=True, exist_ok=True)

    if mesh is None:
        from fansim.acoustics.case import read_case

        mesh = read_case(case_dir)

    mesh = _grid_with_umag(mesh)
    origin = tuple(float(x) for x in mesh.center)
    slc = mesh.slice(normal=_MIDPLANE_NORMAL, origin=origin)
    if slc.n_points == 0:
        return MidplaneArtifacts(
            case_dir=case_dir, u_png=None, p_png=None,
            caption="Airflow not available for this design", available=False,
        )

    # Impeller-anchored crop (rig places the rotor near Z=0). Bias +Z: short approach,
    # long wake — uniform inlet green is boring; the jet develops behind the blades.
    b = slc.bounds
    z0, z1 = float(b[4]), float(b[5])
    x0, x1 = float(b[0]), float(b[1])
    xc = 0.5 * (x0 + x1)
    zc = 0.0 if (z0 < 0.0 < z1) else 0.5 * (z0 + z1)
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
                )
                # Look from +Y, up = +X → screen-right = +Z (OUTLET), screen-left = −Z (FRONT).
                bb = slc.bounds
                xspan = max(abs(float(bb[1]) - float(bb[0])), 1e-6)
                half = 0.55 * xspan  # fit duct diameter in viewport height → wide Z panorama
                dist = 3.0 * max(half, 0.1)
                pl.camera_position = [
                    (float(xc), float(origin[1]) + dist, float(z_look)),
                    (float(xc), float(origin[1]), float(z_look)),
                    (1.0, 0.0, 0.0),
                ]
                pl.camera.parallel_projection = True
                pl.camera.parallel_scale = half
                # ASCII only — ``|U|`` / arrows go through matplotlib mathtext and can crash VTK.
                pl.add_text(title, font_size=11, color="black", position="upper_edge")
                pl.add_text(
                    "FRONT (inlet)", font_size=11, color="black", position="lower_left",
                )
                pl.add_text(
                    "OUTLET (flow ->)", font_size=11, color="black", position="lower_right",
                )
                pl.screenshot(str(path))
            finally:
                pl.close()
        return path if path.is_file() else None

    try:
        u_written = _shot("U_mag", "Umag midplane (m/s)", out_u)
    except Exception:  # noqa: BLE001
        u_written = None
    try:
        if "p" in slc.cell_data or "p" in slc.point_data or "p" in slc.array_names:
            p_written = _shot("p", "pressure midplane (m2/s2)", out_p)
    except Exception:  # noqa: BLE001
        p_written = None

    ok = u_written is not None or p_written is not None
    cap = (
        "Umag midplane — FRONT LEFT -> OUTLET RIGHT (wake-biased)"
        if u_written
        else (
            "pressure midplane — FRONT LEFT -> OUTLET RIGHT (wake-biased)"
            if p_written
            else "Airflow not available for this design"
        )
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
    z_cut = 0.0 if z0 < 0.0 < z1 else 0.5 * (z0 + z1)
    cx, cy = float(mesh.center[0]), float(mesh.center[1])
    slc = mesh.slice(normal=(0.0, 0.0, 1.0), origin=(cx, cy, z_cut))
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
    window_size: tuple[int, int] = (1280, 800),
    n_seed: int = 240,
    clim: tuple[float, float] | None = None,
) -> StreamlineArtifact:
    """Seed a disc upstream of the rotor and trace streamlines colored by ``|U|``.

    A STAR-CCM+-style hero shot: streamlines enter along the axis, accelerate through the
    blade rows (warm colors), and fan out into the wake. Seeds a disc of ~tip radius just
    inside the −Z (inlet) side and integrates both directions so the approach and the wake
    both show. The impeller STL, if present in the case, is drawn as a light-grey body for
    context. Fail-soft; ``mesh`` may be injected for tests.
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
    r_seed = max(0.85 * r_tip, 1e-4)
    span = max(z1 - z0, 1e-4)
    z_seed = z0 + 0.15 * span  # just inside the inlet (−Z) side

    seed = pv.Disc(center=(cx, cy, z_seed), normal=(0.0, 0.0, 1.0),
                   inner=0.04 * r_tip, outer=r_seed, r_res=1, c_res=max(8, n_seed))
    try:
        streams = mesh.streamlines_from_source(
            seed, vectors="U", integration_direction="both",
            max_steps=4000, initial_step_length=0.2, max_step_length=1.0,
            terminal_speed=1e-6,
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
        # Scale to the through-flow, not the blade-tip speed: the 85th percentile keeps the
        # freestream lines colored (tip outliers just saturate warm).
        hi = float(np.percentile(vals, 85.0)) if vals.size else 5.0
        clim = (0.0, max(hi, 0.5))
    tubes = streams.tube(radius=0.004 * r_tip)

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
            stl = case_dir / "impeller.stl"
            if stl.is_file():
                try:
                    body = pv.read(str(stl))
                    # The snappy STL is in mm; the OpenFOAM mesh is in m. Scale it down when it
                    # dwarfs the flow domain, else skip (a mis-scaled body swamps the scene).
                    bl = body.length
                    if bl > 5.0 * max(r_tip, 1e-6):
                        body = body.scale(0.001, inplace=False)
                    if body.length <= 5.0 * max(r_tip, 1e-6):
                        pl.add_mesh(body, color="lightgrey", opacity=0.35,
                                    show_scalar_bar=False)
                except Exception:  # noqa: BLE001 — context body is optional
                    pass
            # Three-quarter view: off the +Z/outlet quarter, looking back at the rotor.
            diag = 2.4 * max(r_tip, 0.05)
            pl.camera_position = [
                (cx + diag, cy + 0.7 * diag, z1 + 0.8 * diag),
                (cx, cy, 0.5 * (z0 + z1)),
                (0.0, 1.0, 0.0),
            ]
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
        cached = find_cached_midplane(case_dir)
        if cached is not None and cached.u_png is not None:
            return cached

    if mesh is None:
        if not case_has_flow_fields(case_dir):
            return unavailable
        if not ensure_reconstructed(case_dir, runner_factory=runner_factory, image_ok=image_ok):
            return unavailable

    try:
        return render_midplane_pngs(case_dir, mesh=mesh)
    except Exception:  # noqa: BLE001
        return unavailable
