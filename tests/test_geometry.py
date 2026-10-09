"""Geometry tests: sections are valid and the impeller is a watertight, in-envelope body."""

from __future__ import annotations

import numpy as np
import pytest

from fansim.geometry import BladeParams, build_impeller, export_stl, watertight_report
from fansim.geometry.airfoil import naca4
from fansim.geometry.config import blade_params_from_dict, load_blade_params, save_blade_params


def test_naca4_closed_loop_and_thickness():
    loop = naca4(max_camber=0.02, camber_pos=0.4, thickness=0.12, n_points=50)
    assert loop.ndim == 2 and loop.shape[1] == 2
    assert np.allclose(loop[0], loop[-1]), "airfoil loop must be closed"
    # Max thickness of a NACA 12% section is ~12% of chord.
    assert 0.10 < (loop[:, 1].max() - loop[:, 1].min()) < 0.14


def test_symmetric_airfoil_has_zero_camber_line():
    loop = naca4(max_camber=0.0, camber_pos=0.4, thickness=0.10, n_points=40)
    assert abs(loop[:, 1].max() + loop[:, 1].min()) < 1e-6


@pytest.fixture(scope="module")
def baseline_stl(tmp_path_factory):
    params = BladeParams()
    imp = build_impeller(params)
    out = export_stl(imp, tmp_path_factory.mktemp("geo") / "impeller.stl")
    return params, out


def test_impeller_is_watertight_single_body(baseline_stl):
    _, out = baseline_stl
    rep = watertight_report(out)
    assert rep.ok, f"impeller not print/mesh-ready: {rep}"
    assert rep.watertight
    assert rep.n_bodies == 1
    assert rep.volume_mm3 > 1000.0


def test_impeller_fits_a12x25_envelope(baseline_stl):
    params, out = baseline_stl
    rep = watertight_report(out)
    (xmin, ymin, zmin), (xmax, ymax, zmax) = rep.bounds_mm
    radius = max(abs(xmin), abs(xmax), abs(ymin), abs(ymax))
    assert radius <= 60.0, "impeller must fit inside the 120 mm frame"
    assert (zmax - zmin) <= 25.0, "impeller must fit the 25 mm axial depth"
    assert radius >= params.tip_radius - 1.0  # tip actually reaches out


def test_config_roundtrip(tmp_path):
    params = BladeParams(n_blades=9)
    path = save_blade_params(params, tmp_path / "p.yaml")
    reloaded = load_blade_params(path)
    assert reloaded.n_blades == 9
    assert len(reloaded.stations) == len(params.stations)
    assert reloaded.stations[0].chord == params.stations[0].chord


def test_config_from_project_yaml():
    params = load_blade_params("config/design_space.yaml")
    assert params.n_blades == 7
    assert params.stations[-1].r_frac == 1.0
