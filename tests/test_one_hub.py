"""R1.7 / QA-44: validate, score and export share one hub, grown below the blades."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from fansim.fan_spec import get_fan_spec
from fansim.geometry.blade import _hub_axial_range
from fansim.geometry.features import Features
from fansim.manufacturability.print_export import mount_hub_params
from fansim.optimize.search_space import blade_from_flat

R16 = Path(__file__).resolve().parents[1] / "handoff/2026-10-17_from-qa-16-hang/data/p1_designed.jsonl"


def _r16(design_id: str):
    for line in R16.open(encoding="utf-8"):
        row = json.loads(line)
        if row["id"] == design_id:
            return blade_from_flat(row["flat"], Features())
    raise KeyError(design_id)


def test_short_hub_grows_below_the_blades():
    """All of Δh sits below the blades; the intake (top) face stays put."""
    mount = get_fan_spec("a12x25").motor_mount
    p = _r16("S2_0000")
    z0, z1 = _hub_axial_range(p)
    have = z1 - z0
    assert have < 15.0
    grown, note = mount_hub_params(p, mount)
    x0, x1 = _hub_axial_range(grown)
    assert x1 - x0 == pytest.approx(15.0, abs=1e-6)
    assert x1 == pytest.approx(z1, abs=1e-6)
    assert (z0 - x0) == pytest.approx(15.0 - have, abs=1e-6)
    assert "hub" in note


def test_already_tall_hub_is_unchanged():
    mount = get_fan_spec("a12x25").motor_mount
    p = _r16("S1_0001")
    z0, z1 = _hub_axial_range(p)
    assert z1 - z0 >= 15.0
    same, note = mount_hub_params(p, mount)
    assert same is p and note == ""


def test_validate_cfd_and_export_share_one_hub(tmp_path, monkeypatch):
    """QA-44: the hub validate/score/export see is the same object bounds."""
    from fansim.optimize import objectives as obj

    p = _r16("S2_0000")
    mount = get_fan_spec("a12x25").motor_mount
    export_hub = _hub_axial_range(mount_hub_params(p, mount)[0])
    seen: dict[str, tuple[float, float]] = {}
    real_validate = obj.validate_blade_params

    def wrap_validate(params):
        seen["validate"] = _hub_axial_range(params)
        real_validate(params)

    def capture_build(params):
        seen["cfd"] = _hub_axial_range(params)
        raise AssertionError("stop before CAD")

    class _Ok:
        ok = True
        printable = True
        reason = ""
        tip_deflection_mm = 0.0
        beam_aspect = 1.0
        beam_regime_ok = True
        f1_hz = 100.0
        bpf_hz = 300.0
        margin = 1.0

    monkeypatch.setattr(obj, "validate_blade_params", wrap_validate)
    monkeypatch.setattr(obj, "build_impeller", capture_build)
    monkeypatch.setattr(obj, "export_stl", capture_build)
    monkeypatch.setattr(obj, "check_printability", lambda *_a, **_k: _Ok())
    monkeypatch.setattr(obj, "centrifugal_root_stress", lambda *_a, **_k: _Ok())
    monkeypatch.setattr(obj, "root_bending_stress", lambda *_a, **_k: _Ok())
    monkeypatch.setattr(obj, "flutter_report", lambda *_a, **_k: _Ok())
    monkeypatch.setattr(obj, "remaining_tip_gap_mm", lambda *_a, **_k: 1.0)
    monkeypatch.setattr(obj, "deflection_report", lambda *_a, **_k: _Ok())
    obj.evaluate_candidate(p, workdir=tmp_path, exploit_guard=False)
    assert seen["validate"] == pytest.approx(export_hub, abs=1e-6)
    assert seen["cfd"] == pytest.approx(export_hub, abs=1e-6)


def test_prepare_export_flat_grows_hub_below_the_blades():
    from fansim.cockpit.placement import prepare_export_flat
    from fansim.optimize.search_space import blade_to_flat

    spec = get_fan_spec("a12x25")
    p0 = _r16("S2_0000")
    z0, z1 = _hub_axial_range(p0)
    assert z1 - z0 < 15.0
    src = blade_to_flat(p0)
    flat, _changes = prepare_export_flat(src, spec, fit_frame=False, fit_hub=True)
    p1 = blade_from_flat(flat, Features())
    x0, x1 = _hub_axial_range(p1)
    assert x1 - x0 >= 15.0 - 1e-6
    assert x1 == pytest.approx(z1, abs=1e-5)


def test_auto_hub_cfd_scores_are_stale():
    """Old saved designs scored the auto hub; do not migrate them."""
    from fansim.cfd.metrics import CFD_VERSION
    from fansim.cockpit.data import cfd_is_stale

    assert CFD_VERSION >= 6
    assert cfd_is_stale(5)
