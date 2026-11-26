from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import pyvista as pv

from fansim.cfd.flow_report import FlowMetrics
from fansim.cfd.flow_report_viz import PICTURES, picture_scales, render_report_pictures


def _grid():
    g = pv.ImageData(dimensions=(23, 23, 13), spacing=(0.005, 0.005, 0.005),
                     origin=(-0.055, -0.055, -0.03)).cast_to_unstructured_grid()
    n = g.n_cells
    c = g.cell_centers().points
    r = np.hypot(c[:, 0], c[:, 1]) + 1e-9
    g.cell_data["U"] = np.column_stack([-c[:, 1] / r, c[:, 0] / r, np.full(n, 3.0)])
    g.cell_data["p"] = np.zeros(n)
    g.cell_data["k"] = np.full(n, 0.3)
    g.cell_data["omega"] = np.full(n, 1500.0)
    return g


def test_all_pictures_written(tmp_path):
    m = FlowMetrics(0.0, False, [1, 2, 3, 4, 5], 0.1, 0.0, 1.0, 60.0, 3.0)
    out = render_report_pictures(tmp_path, mesh=_grid(), out_dir=tmp_path,
                                 stock_bands=[1, 1, 1, 1, 1], metrics=m)
    assert set(out) == set(PICTURES)
    assert all(p.is_file() and p.stat().st_size > 1000 for p in out.values())


def test_scales_are_reused(tmp_path):
    sc = picture_scales(tmp_path, mesh=_grid())
    assert set(sc) == {"uz", "spin", "noise"}
    out = render_report_pictures(tmp_path, mesh=_grid(), out_dir=tmp_path, scales=sc,
                                 metrics=FlowMetrics(0, False, [1] * 5, 0, 0, 1, None, 3))
    assert "noise" not in out or out["noise"].is_file()


def test_side_view_matches_midplane_orientation_and_crops_to_fan():
    """Side views look from +Y with up +X like the midplane (inlet LEFT), cropped near the fan."""
    from fansim.cfd.flow_report_viz import side_view_box, side_view_camera
    pos, focal, up = side_view_camera(0.05, 0.0)
    assert pos[1] > 0 and tuple(up) == (1.0, 0.0, 0.0) and focal == (0.0, 0.0, 0.0)
    _x0, x1, _y0, _y1, z0, z1 = side_view_box(0.05, 0.0)
    assert (z0, z1) == pytest.approx((-0.075, 0.2)) and x1 == pytest.approx(0.06)


def test_plotter_rejects_uninitialized_osmesa_instead_of_segfaulting(monkeypatch):
    """Headless Linux without X11/EGL/OSMesa must raise RuntimeError, not SIGSEGV in Render()."""
    from fansim.cfd import flow_report_viz as frv

    class vtkOSOpenGLRenderWindow:
        pass

    class vtkXOpenGLRenderWindow:
        pass

    closed = []

    class FakePlotter:
        def __init__(self, rw):
            self.render_window = rw
            self.background_color = None

        def close(self):
            closed.append(self.render_window)

    monkeypatch.setattr(frv, "_osmesa_available", lambda: False)
    monkeypatch.setattr(
        frv.pv, "Plotter", lambda **_kw: FakePlotter(vtkOSOpenGLRenderWindow())
    )
    with pytest.raises(RuntimeError, match="libOSMesa"):
        frv._plotter()
    assert len(closed) == 1

    # Working backends (X11/Xvfb, or OSMesa when libOSMesa is installed) succeed.
    monkeypatch.setattr(
        frv.pv, "Plotter", lambda **_kw: FakePlotter(vtkXOpenGLRenderWindow())
    )
    pl = frv._plotter()
    assert pl.background_color == "white"

    monkeypatch.setattr(frv, "_osmesa_available", lambda: True)
    monkeypatch.setattr(
        frv.pv, "Plotter", lambda **_kw: FakePlotter(vtkOSOpenGLRenderWindow())
    )
    pl2 = frv._plotter()
    assert pl2.background_color == "white"


def test_push_chart_holds_the_shared_matplotlib_lock(tmp_path, monkeypatch):
    """Review: pyplot is not thread-safe; spanwise plots run beside the report in executor threads."""
    from fansim.cfd import flow_report_viz as frv
    from fansim.cfd import spanwise

    seen = []
    real = frv._push_unlocked

    def spy(*a, **k):
        seen.append(spanwise._PLOT_LOCK.locked())
        return real(*a, **k)

    monkeypatch.setattr(frv, "_push_unlocked", spy)
    frv._push([1, 2, 3, 4, 5], None, tmp_path / "p.png")
    assert seen == [True]


def test_report_pictures_use_the_polyhedron_safe_slice():
    """§22.4: Results bake must not vtkCutter OpenFOAM polyhedra (console flood)."""
    src = Path(__file__).resolve().parents[1] / "fansim" / "cfd" / "flow_report_viz.py"
    text = src.read_text(encoding="utf-8")
    assert "slice_volume_for_viz" in text
    assert ".slice(" not in text
