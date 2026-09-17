"""Mixed-flow axial-BEM adapter screen. No Docker."""

from __future__ import annotations

from pathlib import Path

import pytest

from fansim.centrifugal.bem import mixed_bem_screen_cfm, mixed_to_blade_params
from fansim.centrifugal.geometry import MixedFlowParams, _loft_tip_radius_mm
from fansim.fan_bem import pq_curve


def test_mixed_to_blade_params_maps_core_fields():
    mf = MixedFlowParams()
    bp = mixed_to_blade_params(mf)
    assert bp.n_blades == mf.n_blades
    assert bp.hub_radius == pytest.approx(mf.r_back_mm)
    assert bp.tip_radius == pytest.approx(_loft_tip_radius_mm(mf))
    assert len(bp.stations) == 3
    for st, ch, sg in zip(bp.stations, mf.chord_triplet(), mf.stagger_triplet()):
        assert st.chord == pytest.approx(ch)
        assert st.stagger_deg == pytest.approx(sg)
        assert st.thickness == pytest.approx(mf.thickness)
        assert st.max_camber == pytest.approx(mf.max_camber)


def test_mixed_to_blade_params_honors_span_planform():
    mf = MixedFlowParams(
        chord_root=18.0, chord_mm=22.0, chord_tip=16.0,
        stagger_root=40.0, stagger_deg=35.0, stagger_tip=28.0,
    )
    bp = mixed_to_blade_params(mf)
    assert bp.stations[0].chord == pytest.approx(18.0)
    assert bp.stations[1].chord == pytest.approx(22.0)
    assert bp.stations[2].chord == pytest.approx(16.0)
    assert bp.stations[0].stagger_deg == pytest.approx(40.0)
    assert bp.stations[2].stagger_deg == pytest.approx(28.0)


def test_adapted_pq_curve_finite_free_cfm():
    bp = mixed_to_blade_params(MixedFlowParams())
    c = pq_curve(bp, rpm=2000, tip_gap_mm=0.5)
    assert 20.0 < c.free_delivery_cfm < 120.0


def test_larger_gap_screens_worse_or_equal():
    bp = mixed_to_blade_params(MixedFlowParams())
    tight = pq_curve(bp, rpm=2000, tip_gap_mm=0.5)
    leaky = pq_curve(bp, rpm=2000, tip_gap_mm=2.0)
    assert leaky.free_delivery_cfm <= tight.free_delivery_cfm


def test_mixed_bem_screen_cfm_tuple():
    q0, q_op = mixed_bem_screen_cfm(MixedFlowParams(), 2000.0, 8.0, 0.5)
    assert q0 > 0
    assert 0 < q_op <= q0


def test_evaluate_bem_prescreen_skips_export(tmp_path, monkeypatch):
    from fansim.centrifugal import evaluate as ev
    from fansim.centrifugal.evaluate import evaluate_mixed_flow

    calls = {"export": 0}

    def boom(*_a, **_k):
        calls["export"] += 1
        raise AssertionError("export should not run")

    monkeypatch.setattr(ev, "export_mixed_flow_stl", boom)
    monkeypatch.setattr(
        ev, "mixed_bem_screen_cfm",
        lambda *a, **k: (10.0, 5.0),
    )
    res = evaluate_mixed_flow(
        MixedFlowParams(), tmp_path / "bem", bem_prescreen_cfm=40.0)
    assert res.feasible is False
    assert "bem-prescreen" in res.reason.lower()
    assert res.raw.get("bem_adapter") == "axial"
    assert calls["export"] == 0


def test_cli_mentions_bem_prescreen():
    text = Path("scripts/evaluate_mixed_flow.py").read_text(encoding="utf-8")
    assert "--bem-prescreen" in text
    assert "★" not in text
