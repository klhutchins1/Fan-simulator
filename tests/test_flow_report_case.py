from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import pyvista as pv

from fansim.cfd import flow_report_case as frc
from fansim.cfd.flow_report import FLOW_REPORT_VERSION, FlowReportUnavailable


def _grid(uz=3.0):
    """Small structured annulus-ish block around z=0 with cell U/p/k/omega."""
    # z spacing 2.5 mm so cell centres (±0.00875, ±0.01125) fall inside the ±0.0098 ± 0.0022 slabs
    g = pv.ImageData(dimensions=(23, 23, 17), spacing=(0.005, 0.005, 0.0025),
                     origin=(-0.055, -0.055, -0.02)).cast_to_unstructured_grid()
    n = g.n_cells
    g.cell_data["U"] = np.tile([0.0, 0.0, uz], (n, 1))
    g.cell_data["p"] = np.zeros(n)
    g.cell_data["k"] = np.full(n, 0.3)
    g.cell_data["omega"] = np.full(n, 1500.0)
    return g


def _case(tmp_path: Path, *, surf_max=4, p_probe=8.0, derate=1.0, rpm=2000.0, time="500") -> Path:
    c = tmp_path / "case"
    (c / "constant").mkdir(parents=True)
    (c / time).mkdir()
    (c / "constant" / "case_meta.json").write_text(json.dumps({
        "hub_radius_m": 0.0215, "tip_radius_m": 0.0545, "rpm": rpm, "spin": -1,
        "cfd_version": 5, "duct_shape": "ring", "casing": True}))
    (c / "_eval_result.json").write_text(json.dumps({"raw": {
        "surf_max": surf_max, "p_probe_pa": p_probe, "derate": derate}}))
    return c


def test_samples_from_mesh_has_weights_and_turbulence():
    s = frc.samples_from_mesh(_grid())
    assert s.w.shape[0] == s.pts.shape[0] and np.all(s.w > 0)
    assert s.k is not None and s.omega is not None


def test_settings_and_mismatch(tmp_path):
    a = frc.test_settings(_case(tmp_path / "a"))
    assert a["back_pressure_pa"] == 8.0 and a["surf_max"] == 4
    b = frc.test_settings(_case(tmp_path / "b", p_probe=8.0 * 0.9 ** 2, derate=0.9))
    assert frc.first_mismatch(a, b) is None          # derated probe maps back to 8 Pa
    c = frc.test_settings(_case(tmp_path / "c", surf_max=None))
    assert frc.first_mismatch(a, c) == "mesh level not recorded"
    d = frc.test_settings(_case(tmp_path / "d", rpm=2200.0))
    assert "rpm" in frc.first_mismatch(a, d)


def test_compute_and_cache(tmp_path):
    case = _case(tmp_path)
    calls = []

    def loader(cd):
        calls.append(cd)
        return _grid()

    m1 = frc.load_or_compute_metrics(case, loader=loader)
    m2 = frc.load_or_compute_metrics(case, loader=loader)
    assert m1 == m2 and len(calls) == 1
    data = json.loads(frc.report_json_path(case).read_text())
    assert data["version"] == FLOW_REPORT_VERSION and data["time"].startswith("500@")


def test_cache_invalidated_by_version(tmp_path):
    case = _case(tmp_path)
    frc.report_json_path(case).write_text(json.dumps(
        {"version": FLOW_REPORT_VERSION - 1, "time": "500", "metrics": {}}))
    m = frc.load_or_compute_metrics(case, loader=lambda cd: _grid())
    assert m.mean_uz_exit == pytest.approx(3.0)
    (case / "750").mkdir()  # a newer CFD time also invalidates
    m2 = frc.load_or_compute_metrics(case, loader=lambda cd: _grid(uz=2.0))
    assert m2.mean_uz_exit == pytest.approx(2.0)


def test_no_fields_raises(tmp_path):
    with pytest.raises(FlowReportUnavailable):
        frc.load_or_compute_metrics(_case(tmp_path), loader=lambda cd: None)


def test_reference_missing_returns_none(tmp_path, monkeypatch):
    from fansim.cockpit import flow_reference as fr
    monkeypatch.setattr(fr, "REFERENCE_FILE", tmp_path / "ref.json")
    assert fr.get_reference() is None
    case = _case(tmp_path)
    fr.set_reference(case)
    assert fr.get_reference() == case.resolve()
    import shutil
    shutil.rmtree(case)
    assert fr.get_reference() is None  # deleted reference reads as missing


def test_mesh_level_read_from_snappy_dict_when_not_stamped(tmp_path):
    """Runs before 2026-10-09 didn't stamp surf_max; the case's own mesh settings still state it."""
    case = _case(tmp_path, surf_max=None)
    (case / "system").mkdir()
    (case / "system" / "snappyHexMeshDict").write_text(
        "refinementSurfaces\n{\n    impeller { level (3 4); patchInfo { type wall; } }\n"
        "    frame { level (3 4); patchInfo { type wall; } }\n}\n")
    assert frc.test_settings(case)["surf_max"] == 4
    bare = _case(tmp_path / "bare", surf_max=None)
    assert frc.test_settings(bare)["surf_max"] is None


def test_rerun_at_same_time_invalidates_cache(tmp_path):
    """Review: steady runs end at the same time; a re-Assess into the same folder must not reuse."""
    import os
    case = _case(tmp_path)
    frc.load_or_compute_metrics(case, loader=lambda cd: _grid())
    t = case / "500"
    os.utime(t, (t.stat().st_atime + 100, t.stat().st_mtime + 100))
    m = frc.load_or_compute_metrics(case, loader=lambda cd: _grid(uz=2.0))
    assert m.mean_uz_exit == pytest.approx(2.0)
