"""Pictures for the flow report card: fan-face map, push bars, spin and noise side views (§24)."""

from __future__ import annotations

import ctypes
import ctypes.util
from pathlib import Path

import numpy as np


def __getattr__(name: str):
    if name == "pv":
        import pyvista as pv

        globals()["pv"] = pv
        return pv
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

from fansim.cfd.flow_report import (
    DEAD_FRAC_OF_MEAN,
    FlowMetrics,
    noise_density,
    slab_centres,
)
from fansim.cfd.flow_report_case import blade_z_extent, case_geometry
from fansim.cfd.midplane import _RENDER_LOCK, robust_clim, rotor_outline, slice_volume_for_viz

PICTURES = ("face", "push", "spin", "noise")
WINDOW = (640, 480)


def _cells(mesh):
    g = mesh if "U" in mesh.cell_data else mesh.point_data_to_cell_data()
    return g


def _with_derived(mesh, case_dir):
    g = _cells(mesh).copy()
    c = np.asarray(g.cell_centers().points)
    u = np.asarray(g.cell_data["U"], float)
    r = np.hypot(c[:, 0], c[:, 1]) + 1e-12
    uth = (-u[:, 0] * c[:, 1] + u[:, 1] * c[:, 0]) / r
    g.cell_data["Uz"] = u[:, 2]
    g.cell_data["spin"] = np.abs(uth) / (np.linalg.norm(u, axis=1) + 1e-12)
    if "k" in g.cell_data and "omega" in g.cell_data:
        g.cell_data["noise"] = np.log10(noise_density(g.cell_data["k"], g.cell_data["omega"]) + 1e-30)
    return g


def picture_scales(case_dir, *, mesh) -> dict:
    g = _with_derived(mesh, case_dir)
    sc = {"uz": robust_clim(g.cell_data["Uz"], symmetric=True),
          "spin": (0.0, robust_clim(g.cell_data["spin"])[1])}
    sc["noise"] = robust_clim(g.cell_data["noise"]) if "noise" in g.cell_data else (0.0, 1.0)
    return sc


def _osmesa_available() -> bool:
    """Return True if libOSMesa can be loaded by VTK's OSMesa backend."""
    names = [n for n in (ctypes.util.find_library("OSMesa"), "libOSMesa.so.8", "libOSMesa.so") if n]
    for name in names:
        try:
            ctypes.CDLL(name)
            return True
        except OSError:
            continue
    return False


def _plotter():
    import pyvista as pv

    pl = pv.Plotter(off_screen=True, window_size=list(WINDOW))
    if type(pl.render_window).__name__ == "vtkOSOpenGLRenderWindow" and not _osmesa_available():
        # VTK 9.6 on headless Linux without X11, working EGL, or libOSMesa still returns an
        # uninitialized vtkOSOpenGLRenderWindow whose Render() dereferences null GL pointers
        # (SIGSEGV). Fail cleanly before Render() so callers keep verdicts and tests report an error.
        pl.close()
        raise RuntimeError(
            "No usable OpenGL backend for off-screen VTK rendering: VTK fell back to "
            "vtkOSOpenGLRenderWindow without libOSMesa. Set DISPLAY (e.g. run under xvfb-run) "
            "or provide a working EGL driver."
        )
    pl.background_color = "white"
    return pl


def _face(g, case_dir, hub_r, tip_r, z_fan, scales, metrics, path):
    z0 = slab_centres(tip_r=tip_r, z_fan=z_fan, blade_z=blade_z_extent(case_dir, hub_r=hub_r))[1]  # 27.3e
    # Same cutter as midplane (§22.4): drop/bypass OpenFOAM polyhedra so vtkCutter does not
    # flood the cockpit log with "non-manifold triangulation" on every Results bake.
    slc = slice_volume_for_viz(g, (0.0, 0.0, 1.0), (0.0, 0.0, z0))
    pts = slc.cell_centers().points if slc.n_cells else np.zeros((0, 3))
    rr = np.hypot(pts[:, 0], pts[:, 1])
    slc = slc.extract_cells(np.flatnonzero((rr >= hub_r) & (rr <= tip_r))) if slc.n_cells else slc
    with _RENDER_LOCK:
        pl = _plotter()
        try:
            pl.add_mesh(slc.cell_data_to_point_data(), scalars="Uz", cmap="Blues", lighting=False,
                        clim=[0.0, scales["uz"][1]], show_scalar_bar=True,
                        scalar_bar_args={"title": "forward speed (m/s)"})
            uz = np.asarray(slc.cell_data["Uz"]) if slc.n_cells else np.zeros(0)
            back = slc.extract_cells(np.flatnonzero(uz < 0)) if uz.size else None
            if back is not None and back.n_cells:
                pl.add_mesh(back, color="red")
            mean = metrics.mean_uz_exit if metrics else (float(np.mean(uz)) if uz.size else 0.0)
            dead = slc.extract_cells(np.flatnonzero(np.abs(uz) < DEAD_FRAC_OF_MEAN * abs(mean))) if uz.size else None
            if dead is not None and dead.n_cells:
                pl.add_mesh(dead, color="gray")
            ol = rotor_outline(case_dir, (0, 0, 1), (0, 0, z_fan))
            if ol is not None:
                pl.add_mesh(ol, color="black", line_width=1)
            pl.view_xy()
            pl.camera.parallel_projection = True
            pl.reset_camera()
            pl.screenshot(str(path))
        finally:
            pl.close()
    return path


def side_view_box(tip_r: float, z_fan: float) -> tuple[float, ...]:
    """Crop for side views: the fan plus 4 tip radii of wake, not the whole duct."""
    r = 1.2 * tip_r
    return (-r, r, -r, r, z_fan - 1.5 * tip_r, z_fan + 4.0 * tip_r)


def side_view_camera(tip_r: float, z_fan: float):
    """Look from +Y with up +X, like the midplane: inlet (-Z) LEFT, outlet RIGHT."""
    return ((0.0, 6.0 * tip_r, z_fan), (0.0, 0.0, z_fan), (1.0, 0.0, 0.0))


def _side(g, case_dir, field, cmap, clim, title, path, z_fan, tip_r, highlight_pct=None):
    slc = slice_volume_for_viz(g, (0.0, 1.0, 0.0), (0.0, 0.0, z_fan))
    try:
        slc = slc.clip_box(list(side_view_box(tip_r, z_fan)), invert=False)
    except Exception:  # noqa: BLE001, S110 - keep the full slice
        pass
    with _RENDER_LOCK:
        pl = _plotter()
        try:
            pl.add_mesh(slc.cell_data_to_point_data(), scalars=field, cmap=cmap, clim=list(clim), lighting=False,
                        scalar_bar_args={"title": title})
            if highlight_pct is not None and slc.n_cells:
                v = np.asarray(slc.cell_data[field])
                hot = slc.extract_cells(np.flatnonzero(v >= np.percentile(v, highlight_pct)))
                if hot.n_cells:
                    pl.add_mesh(hot, color="orangered")
            ol = rotor_outline(case_dir, (0, 1, 0), (0, 0, z_fan))
            if ol is not None:
                pl.add_mesh(ol, color="black", line_width=2)
            pl.camera_position = list(side_view_camera(tip_r, z_fan))
            pl.add_text("FRONT (inlet)", font_size=10, color="black", position="lower_left")
            pl.add_text("OUTLET (flow ->)", font_size=10, color="black", position="upper_right")
            pl.camera.parallel_projection = True
            pl.reset_camera()
            pl.screenshot(str(path))
        finally:
            pl.close()
    return path


def _push(bands, stock_bands, path):
    """Push bars under the shared pyplot lock (pyplot is not thread-safe; spanwise plots run too)."""
    from fansim.cfd.spanwise import _PLOT_LOCK

    with _PLOT_LOCK:
        return _push_unlocked(bands, stock_bands, path)


def _push_unlocked(bands, stock_bands, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    names = ["hub", "inner", "middle", "outer", "tip"]
    x = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(6.4, 3.2), dpi=100)
    ax.bar(x - 0.2, bands, 0.4, label="this design", color="#1f77b4")
    if stock_bands is not None:
        ax.bar(x + 0.2, stock_bands, 0.4, label="Stock", color="#c8a400")
    ax.set_xticks(x, names)
    ax.set_ylabel("pressure added (Pa)")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def render_report_pictures(case_dir, *, mesh, scales=None, out_dir=None, stock_bands=None,
                           metrics: FlowMetrics | None = None) -> dict[str, Path]:
    case_dir = Path(case_dir)
    out_dir = Path(out_dir or case_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    hub_r, tip_r, z_fan = case_geometry(case_dir, mesh)
    g = _with_derived(mesh, case_dir)
    sc = scales or picture_scales(case_dir, mesh=mesh)
    out: dict[str, Path] = {}
    out["face"] = _face(g, case_dir, hub_r, tip_r, z_fan, sc, metrics, out_dir / "flow_face.png")
    bands = metrics.band_dp0_pa if metrics else [0.0] * 5
    out["push"] = _push(bands, stock_bands, out_dir / "flow_push.png")
    out["spin"] = _side(g, case_dir, "spin", "Purples", sc["spin"], "share of speed that is spin",
                        out_dir / "flow_spin.png", z_fan, tip_r)
    if "noise" in g.cell_data:
        out["noise"] = _side(g, case_dir, "noise", "Greys", sc["noise"], "turbulence noise (log, relative)",
                             out_dir / "flow_noise.png", z_fan, tip_r, highlight_pct=95.0)
    return out
