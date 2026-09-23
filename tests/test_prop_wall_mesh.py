"""Wall thickness, layout, and hover figure of merit for the obj_2 diagnostic."""

from __future__ import annotations

import pytest
import trimesh

from fansim.propeller.wall_mesh import (
    figure_of_merit,
    mesh_for_wall,
    min_wall_mm,
    wall_resolved,
    wall_sample,
)


def _slab():
    mesh = trimesh.creation.box(extents=(20.0, 20.0, 2.0))
    return mesh.subdivide()


def test_thin_slab_percentile_is_about_2mm():
    sample = wall_sample(_slab())
    assert sample["n_hits"] >= 20
    assert sample["min_wall_mm"] == pytest.approx(2.0, abs=0.15)
    assert sample["abs_min_mm"] <= sample["min_wall_mm"] + 1e-6
    assert min_wall_mm(_slab()) == pytest.approx(sample["min_wall_mm"], abs=1e-6)


def test_too_few_hits_raises():
    mesh = trimesh.creation.box(extents=(20.0, 20.0, 2.0))
    with pytest.raises(RuntimeError, match="20"):
        wall_sample(mesh)


def test_slab_is_axial_and_not_outward():
    sample = wall_sample(_slab())
    assert sample["layout"] == "axial"
    assert sample["faces_outward"] is False
    assert sample["mean_abs_nz"] > sample["mean_abs_nr"]


def test_tall_cylinder_is_radial_and_outward():
    mesh = trimesh.creation.cylinder(radius=5.0, height=30.0, sections=24)
    sample = wall_sample(mesh)
    assert sample["layout"] == "radial"
    assert sample["faces_outward"] is True
    assert sample["mean_abs_nr"] > sample["mean_abs_nz"]


def test_figure_of_merit_matches_smoke_density():
    fm = figure_of_merit(9.1980953, 2034.2277232229224, 45.38854474432168 / 1000.0)
    assert fm == pytest.approx(0.111245, rel=1e-4)


def test_figure_of_merit_zero_when_power_or_thrust_missing():
    assert figure_of_merit(0.0, 10.0, 0.05) == 0.0
    assert figure_of_merit(1.0, 0.0, 0.05) == 0.0


def test_wall_resolved_three_cell_rule():
    # 0.005 m / 2**4 = 0.3125 mm. Needs min wall >= 0.9375 mm.
    assert wall_resolved(0.005, 4, 1.0) is True
    assert wall_resolved(0.005, 4, 0.5) is False


def test_mesh_for_wall_enables_layers():
    mesh = mesh_for_wall(0.005, 2.0)
    assert mesh.base_cell == 0.005
    assert mesh.add_layers is True
    assert mesh.n_surface_layers == 3
    assert mesh.surf_max == 3
    assert mesh.surf_min == 2
