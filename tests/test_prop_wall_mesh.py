"""Wall thickness, layout, and hover figure of merit for the obj_2 diagnostic."""

from __future__ import annotations

import json

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


def _fake_solve(work):
    fo = work / "postProcessing" / "forces" / "10"
    fo.mkdir(parents=True)
    (fo / "force.dat").write_text("#\n10  (0 0 2.0) (0 0 2) (0 0 0)\n", encoding="utf-8")
    (fo / "moment.dat").write_text("#\n10  (0 0 -0.1) (0 0 -0.1) (0 0 0)\n", encoding="utf-8")


def test_default_mesh_stays_coarse(tmp_path, monkeypatch):
    import trimesh

    from fansim.prop_spec import get_prop_spec
    from fansim.propeller import cfd as prop_cfd

    mesh = trimesh.creation.cylinder(radius=30.0, height=12.0, sections=32)
    src = tmp_path / "impeller.stl"
    mesh.export(str(src))
    work = tmp_path / "case"

    monkeypatch.setattr(prop_cfd, "run_mesh", lambda *_a, **_k: None)
    monkeypatch.setattr(prop_cfd, "run_solve_prop", lambda *_a, **_k: _fake_solve(work))
    import fansim.cfd.runner as runner_mod

    monkeypatch.setattr(
        runner_mod,
        "OpenFOAMRunner",
        lambda workdir: type("R", (), {"run": staticmethod(lambda *a, **k: None)})(),
    )
    prop_cfd.evaluate_prop_cfd(
        get_prop_spec("cine_3inch"),
        work,
        rpm=20000.0,
        base_cell=0.005,
        stl_mm=src,
        prepare_stl=False,
    )
    text = (work / "system" / "snappyHexMeshDict").read_text(encoding="utf-8")
    assert "addLayers       false;" in text
    assert "level (1 2);" in text


def test_passed_mesh_writes_layers(tmp_path, monkeypatch):
    import trimesh

    from fansim.prop_spec import get_prop_spec
    from fansim.propeller import cfd as prop_cfd
    from fansim.propeller.wall_mesh import mesh_for_wall

    mesh = trimesh.creation.cylinder(radius=30.0, height=12.0, sections=32)
    src = tmp_path / "impeller.stl"
    mesh.export(str(src))
    work = tmp_path / "layered"
    monkeypatch.setattr(prop_cfd, "run_mesh", lambda *_a, **_k: None)
    monkeypatch.setattr(prop_cfd, "run_solve_prop", lambda *_a, **_k: _fake_solve(work))
    import fansim.cfd.runner as runner_mod

    monkeypatch.setattr(
        runner_mod,
        "OpenFOAMRunner",
        lambda workdir: type("R", (), {"run": staticmethod(lambda *a, **k: None)})(),
    )
    prop_cfd.evaluate_prop_cfd(
        get_prop_spec("cine_3inch"),
        work,
        rpm=20000.0,
        stl_mm=src,
        prepare_stl=False,
        mesh=mesh_for_wall(0.005, 2.0),
    )
    text = (work / "system" / "snappyHexMeshDict").read_text(encoding="utf-8")
    assert "addLayers       true;" in text
    assert "nSurfaceLayers 3;" in text
    assert "level (2 3);" in text


def test_cli_defaults():
    from scripts.run_prop_obj2_wall import build_parser

    args = build_parser().parse_args([])
    assert args.stl.name == "obj_2_ccw.stl"
    assert args.rpm == 25257.0
    assert args.spin == -1
    assert args.base_cell == 0.005
    assert args.iters == 400
    assert args.procs == 8


def test_cli_runtime_error_writes_null_and_skips_stamp(tmp_path, monkeypatch):
    import scripts.run_prop_obj2_wall as wall_cli

    stamp = tmp_path / "obj_2_ccw_wall.json"
    monkeypatch.setattr(wall_cli, "STAMP", stamp)
    monkeypatch.setattr(
        wall_cli, "run_case", lambda **_k: (_ for _ in ()).throw(RuntimeError("solve failed"))
    )
    out = tmp_path / "run"
    code = wall_cli.main(["--out", str(out)])
    assert code == 1
    payload = json.loads((out / "result.json").read_text(encoding="utf-8"))
    assert payload["thrust_g"] is None
    assert payload["shaft_power_w"] is None
    assert not stamp.exists()


def test_cli_finite_result_stamps(tmp_path, monkeypatch):
    import scripts.run_prop_obj2_wall as wall_cli

    stamp = tmp_path / "obj_2_ccw_wall.json"
    monkeypatch.setattr(wall_cli, "STAMP", stamp)

    def fake_run_case(**_k):
        return {
            "thrust_n": 9.2,
            "thrust_g": 938.0,
            "shaft_power_w": 2034.0,
            "torque_nm": 0.77,
            "figure_of_merit": 0.11,
            "layout": "axial",
            "faces_outward": False,
            "wall_resolved": False,
            "min_wall_mm": 0.4,
        }

    monkeypatch.setattr(wall_cli, "run_case", fake_run_case)
    out = tmp_path / "run"
    code = wall_cli.main(["--out", str(out), "--stl", str(tmp_path / "missing.stl")])
    assert code == 0
    assert stamp.is_file()
    payload = json.loads(stamp.read_text(encoding="utf-8"))
    assert payload["thrust_g"] == pytest.approx(938.0)
    assert payload["shaft_power_w"] == pytest.approx(2034.0)
