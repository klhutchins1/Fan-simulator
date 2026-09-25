"""evaluate_candidate meshes the CFD-oriented rotor with a rig fitted to it (Audit #1 fix)."""

from __future__ import annotations

import pytest
import trimesh

from fansim.cfd.domain import MM_TO_M

pytestmark = pytest.mark.slow  # builds the Stock impeller with CadQuery


class _Stop(Exception):
    pass


def test_build_case_gets_flipped_rotor_and_fitted_rig(tmp_path, monkeypatch):
    from fansim.geometry.config import load_blade_params
    from fansim.optimize import objectives

    seen = {}

    def fake_build_case(case_dir, stl, rig, **kw):
        seen["stl"], seen["rig"], seen["kw"] = stl, rig, kw
        raise _Stop

    monkeypatch.setattr(objectives, "build_case", fake_build_case)
    params = load_blade_params("config/problems/a12x25_reference.yaml")
    # evaluate_candidate's meshing step wraps build_case in a broad `except Exception`, converting
    # any failure (including our _Stop probe) into an infeasible ObjectiveResult rather than letting
    # it propagate. What matters here is that build_case was actually called and with what args, so
    # inspect `seen` (populated before the raise) and the infeasible reason instead of pytest.raises.
    result = objectives.evaluate_candidate(params, workdir=tmp_path)
    assert not result.feasible
    assert "_Stop" in (result.reason or "")
    assert "stl" in seen

    stl = seen["stl"]
    assert stl.name == "impeller_cfd.stl"
    as_built = trimesh.load(str(tmp_path / "impeller.stl"))
    cfd = trimesh.load(str(stl))
    # Flipped about X: the z-range is mirrored.
    assert cfd.bounds[0, 2] == pytest.approx(-as_built.bounds[1, 2], abs=1e-6)
    assert cfd.bounds[1, 2] == pytest.approx(-as_built.bounds[0, 2], abs=1e-6)
    rig = seen["rig"]
    assert rig.spin == -1
    assert rig.mrf_z_min <= cfd.bounds[0, 2] * MM_TO_M
    assert rig.mrf_z_max >= cfd.bounds[1, 2] * MM_TO_M
    frame = seen["kw"].get("frame_stl_mm")
    if frame is not None:
        assert trimesh.load(str(frame)).bounds[0, 2] >= cfd.bounds[1, 2] - 1e-6
