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

    calls = []

    def fake_build_case(case_dir, stl, rig, **kw):
        calls.append({"stl": stl, "rig": rig, "kw": kw})
        if len(calls) < 2:
            # First call is the initial mesh build; let it "succeed" so evaluate_candidate
            # proceeds to solve_at's build_case (the second call) without touching Docker.
            return case_dir
        # Second call is solve_at's (the per-operating-point rebuild). Stop here -- this is
        # the call a stale/rebound stl or rig0 between the two sites would go undetected by
        # if we only ever inspected the first call.
        raise _Stop

    monkeypatch.setattr(objectives, "build_case", fake_build_case)
    # run_mesh would otherwise shell out to Docker between the two build_case calls.
    monkeypatch.setattr(objectives, "run_mesh", lambda runner: None)

    params = load_blade_params("config/problems/a12x25_reference.yaml")
    result = objectives.evaluate_candidate(params, workdir=tmp_path)
    assert not result.feasible
    # NOTE: this depends on the exact wording of evaluate_candidate's except-Exception handlers.
    # The first build_case now succeeds, so the _Stop raised by the SECOND call is caught by the
    # solve-path handler, which reports "solve failed: {type(exc).__name__}" (no `str(exc)`) --
    # unlike the mesh-path handler's "mesh failed: {type(exc).__name__}: {exc}". Either wording
    # contains the exception's class name, "_Stop".
    assert "_Stop" in (result.reason or "")
    assert len(calls) >= 2

    as_built = trimesh.load(str(tmp_path / "impeller.stl"))
    for call in calls[:2]:
        stl = call["stl"]
        assert stl.name == "impeller_cfd.stl"
        cfd = trimesh.load(str(stl))
        # Flipped about X: the z-range is mirrored.
        assert cfd.bounds[0, 2] == pytest.approx(-as_built.bounds[1, 2], abs=1e-6)
        assert cfd.bounds[1, 2] == pytest.approx(-as_built.bounds[0, 2], abs=1e-6)
        rig = call["rig"]
        assert rig.spin == -1
        assert rig.mrf_z_min <= cfd.bounds[0, 2] * MM_TO_M
        assert rig.mrf_z_max >= cfd.bounds[1, 2] * MM_TO_M
        frame = call["kw"].get("frame_stl_mm")
        if frame is not None:
            assert trimesh.load(str(frame)).bounds[0, 2] >= cfd.bounds[1, 2] - 1e-6

    # A rebind of stl/rig0 between the mesh build and solve_at would show up here: both calls
    # must share the same oriented STL path and an identically-fitted MRF zone.
    first_rig, second_rig = calls[0]["rig"], calls[1]["rig"]
    assert calls[0]["stl"] == calls[1]["stl"]
    assert second_rig.mrf_z_min == pytest.approx(first_rig.mrf_z_min, abs=1e-12)
    assert second_rig.mrf_z_max == pytest.approx(first_rig.mrf_z_max, abs=1e-12)
