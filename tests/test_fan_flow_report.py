from __future__ import annotations

from pathlib import Path
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


def test_scored_case_dir_follows_refreshed_score(tmp_path):
    """A refreshed design's score came from extra.case_dir (relative to runs/), not its own folder."""
    from fansim.cockpit.data import scored_case_dir
    design_dir = tmp_path / "runs" / "opt_run1" / "cockpit_assess" / "design_9005"
    design_dir.mkdir(parents=True)
    (tmp_path / "runs" / "screen_rank_audit" / "t9005" / "full").mkdir(parents=True)
    stl = design_dir / "impeller.stl"
    d = _d(has_model=True, stl_path=str(stl), extra={"case_dir": "screen_rank_audit/t9005/full"})
    assert scored_case_dir(d) == tmp_path / "runs" / "screen_rank_audit" / "t9005" / "full"
    assert scored_case_dir(_d(has_model=True, stl_path=str(stl))) == design_dir
    missing = _d(has_model=True, stl_path=str(stl), extra={"case_dir": "gone/full"})
    assert scored_case_dir(missing) == design_dir  # fall back when the recorded run was pruned


def test_card_has_a_message_before_any_design_is_picked():
    """First load shows the reference (never assessed); the card must not be blank."""
    from fansim.cockpit import fan_core

    class _State(SimpleNamespace):
        def change(self, *a, **k):
            return lambda f: f

    session = SimpleNamespace(state=_State())
    fan_core.apply_state_defaults(session)
    assert session.state.flow_msg == ffr.MSG_NONE


def test_pictures_are_rendered_once_per_run(tmp_path, monkeypatch):
    """Spec: pictures are made once per design and reused; re-opening is instant."""
    calls = []

    def fake(case_dir, metrics, *, scales=None, stock_bands=None, out_dir=None):
        calls.append(case_dir)
        out = Path(out_dir or case_dir) / "flow_face.png"
        out.write_bytes(b"png")
        return {"face": out}

    monkeypatch.setattr(ffr, "_pictures", fake)
    a = ffr._pictures_cached(tmp_path, None, key="v2|500|ref")
    b = ffr._pictures_cached(tmp_path, None, key="v2|500|ref")
    assert a == b and len(calls) == 1
    ffr._pictures_cached(tmp_path, None, key="v2|750|ref")  # newer CFD time: re-render
    assert len(calls) == 2
    (tmp_path / "flow_face.png").unlink()
    ffr._pictures_cached(tmp_path, None, key="v2|750|ref")  # file gone: re-render
    assert len(calls) == 3
