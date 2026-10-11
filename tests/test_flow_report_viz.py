from __future__ import annotations

import numpy as np
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
