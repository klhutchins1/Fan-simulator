from __future__ import annotations

from pathlib import Path

import pytest


def test_spin_hint_from_name():
    from fansim.propeller.stl_import import spin_hint_from_name

    assert spin_hint_from_name("obj_1_CCW impeller.stl") == -1
    assert spin_hint_from_name("obj_3_CW_impeller.stl") == 1
    assert spin_hint_from_name("obj_2_CCW.stl") == -1
    assert spin_hint_from_name("mystery.stl") is None


def test_prepare_prop_stl_centers_and_fixes_normals(tmp_path):
    import numpy as np
    import trimesh

    from fansim.propeller.stl_import import measure_prop_stl, prepare_prop_stl

    # Off-origin box with inverted normals (negative volume).
    mesh = trimesh.creation.box(extents=(40.0, 40.0, 10.0))
    mesh.apply_translation([200.0, 150.0, 30.0])
    mesh.invert()
    assert float(mesh.volume) < 0.0
    src = tmp_path / "raw.stl"
    mesh.export(str(src))

    dst = tmp_path / "prepared.stl"
    prepare_prop_stl(src, dst)
    out = trimesh.load(str(dst), force="mesh")
    assert float(out.volume) > 0.0
    assert abs(float(out.vertices[:, 0].mean())) < 1e-3
    assert abs(float(out.vertices[:, 1].mean())) < 1e-3
    assert abs(0.5 * (float(out.bounds[0, 2]) + float(out.bounds[1, 2]))) < 1e-3

    metrics = measure_prop_stl(dst)
    assert metrics.tip_radius_mm == pytest.approx(
        float(np.percentile(np.linalg.norm(out.vertices[:, :2], axis=1), 99.5)),
        rel=1e-6,
    )
    assert metrics.watertight is True
    assert metrics.volume_mm3 > 0.0


def test_evaluate_prop_cfd_external_stl_skips_bemt(tmp_path, monkeypatch):
    import trimesh

    from fansim.propeller import cfd as prop_cfd
    from fansim.prop_spec import get_prop_spec

    mesh = trimesh.creation.cylinder(radius=30.0, height=12.0, sections=32)
    mesh.apply_translation([100.0, 80.0, 5.0])
    src = tmp_path / "impeller.stl"
    mesh.export(str(src))

    work = tmp_path / "case"
    calls = {"mesh": 0, "solve": 0}

    def fake_mesh(*_a, **_k):
        calls["mesh"] += 1

    def fake_solve(*_a, **_k):
        calls["solve"] += 1
        fo = work / "postProcessing" / "forces" / "10"
        fo.mkdir(parents=True)
        (fo / "force.dat").write_text("#\n10  (0 0 2.0) (0 0 2) (0 0 0)\n", encoding="utf-8")
        (fo / "moment.dat").write_text("#\n10  (0 0 -0.1) (0 0 -0.1) (0 0 0)\n", encoding="utf-8")

    monkeypatch.setattr(prop_cfd, "run_mesh", fake_mesh)
    monkeypatch.setattr(prop_cfd, "run_solve_prop", fake_solve)

    import fansim.cfd.runner as runner_mod

    monkeypatch.setattr(
        runner_mod,
        "OpenFOAMRunner",
        lambda workdir: type("R", (), {"run": staticmethod(lambda *a, **k: None)})(),
    )

    out = prop_cfd.evaluate_prop_cfd(
        get_prop_spec("cine_3inch"),
        work,
        rpm=20000.0,
        iters=10,
        procs=1,
        base_cell=0.02,
        stl_mm=src,
        bemt_floor_g=1e9,  # would skip if BEMT ran
        direction="manual",  # plain test cylinder has no blades to prove direction from
    )
    assert out.get("skipped") is not True
    assert out["bemt_thrust_g"] is None
    assert out["stl"] == str(src)
    assert out["tip_radius_mm"] == pytest.approx(30.0, rel=0.05)
    assert calls["mesh"] == 1 and calls["solve"] == 1


def test_cli_evaluate_prop_cfd_declares_stl():
    from tests._cli_parsers import load_build_parser

    ap = load_build_parser("evaluate_prop_cfd.py")()
    args = ap.parse_args(["--stl", "foo.stl", "--dry-run"])
    assert args.stl == Path("foo.stl")
    assert args.no_prepare_stl is False
