from __future__ import annotations

from types import SimpleNamespace

from fansim.cockpit import fan_flow_report as ffr


def _d(**kw):
    base = {"stl_path": "", "extra": {}, "has_model": False, "trial": 1}
    base.update(kw)
    return SimpleNamespace(**base)


def test_message_never_assessed():
    assert ffr.card_message(_d()) == (
        "No flow simulation for this design yet. Run Assess to see how the air moves.")


def test_message_stale():
    d = _d(has_model=True, stl_path="x/impeller.stl",
           extra={"cfd_stale": True, "stale_reason": "old solver"})
    assert ffr.card_message(d) == "These results are out of date (old solver). Re-run Assess."


def test_message_ok_when_case_exists(tmp_path):
    (tmp_path / "500").mkdir()
    d = _d(has_model=True, stl_path=str(tmp_path / "impeller.stl"))
    assert ffr.card_message(d) is None


def test_report_without_reference(tmp_path, monkeypatch):
    from fansim.cfd.flow_report import FlowMetrics
    m = FlowMetrics(0.05, False, [1, 2, 3, 4, 5], 0.2, 0.05, 0.8, 60.0, 2.5)
    monkeypatch.setattr(ffr, "load_or_compute_metrics", lambda cd, **k: m)
    monkeypatch.setattr(ffr, "_pictures", lambda *a, **k: {})
    out = ffr.build_report(tmp_path, None)
    assert out["flow_overall"].startswith("No Stock comparison")
    assert "Stock hasn't been tested this way" in out["flow_msg"]
    assert len(out["flow_rows"]) == 5


def test_stale_token_not_applied():
    state = SimpleNamespace(selected_trial=2, flow_rows=["old"])
    applied = ffr._apply_if_current(state, token=1, payload={"flow_rows": ["new"]})
    assert applied is False and state.flow_rows == ["old"]
    assert ffr._apply_if_current(state, token=2, payload={"flow_rows": ["new"]}) is True
    assert state.flow_rows == ["new"]
