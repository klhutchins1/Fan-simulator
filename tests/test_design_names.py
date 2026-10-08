"""Short stable Results names (F<n>) and dropdown titles."""

import json

from fansim.cockpit.design_names import (
    assign_display_names,
    design_key,
    dropdown_title,
    shape_summary,
    short_date,
)
from fansim.optimize.design import Design


def _d(trial, *, completed="", stale=False, source=None, run="opt_run1", orig=None, **params):
    extra = {"completed": completed, "cfd_stale": stale, "source_run": run}
    if source:
        extra["source"] = source
    if orig is not None:
        extra["orig_trial"] = orig
    return Design(trial=trial, params={"n_blades": 9, **params},
                  objectives={"cfm_free": 50.24, "cfm_load": 41.43, "efficiency": 19.72},
                  feasible=True, is_pareto=False, stl_path=None, extra=extra)


def test_names_are_assigned_oldest_first_and_stay_put(tmp_path):
    reg = tmp_path / "design_names.json"
    new, old = _d(9001, completed="2026-10-01 09:00"), _d(9000, completed="2026-09-13 21:00")
    assign_display_names([new, old], reg)
    assert (old.extra["display_name"], new.extra["display_name"]) == ("F1", "F2")
    # reload: same names, and a newcomer gets the next number
    again = [_d(9001, completed="2026-10-01 09:00"), _d(9000, completed="2026-09-13 21:00"),
             _d(9002, completed="2026-10-07 14:00")]
    assign_display_names(again, reg)
    assert [d.extra["display_name"] for d in again] == ["F2", "F1", "F3"]
    assert json.loads(reg.read_text())["next"] == 4


def test_key_survives_rekeyed_trial_ids():
    a = _d(9000, run="opt_run1")
    b = _d(9017, run="opt_run1", orig=9000)  # re-keyed after a cross-run collision
    assert design_key(a) == design_key(b) == "assess:opt_run1:9000"
    opt = _d(20004, source="cockpit_opt", run="cockpit_opt_20261001-100133", orig=4)
    assert design_key(opt) == "opt:cockpit_opt_20261001-100133:4"
    assert design_key(_d(3), "opt_run1") == "study:opt_run1:3"


def test_shape_summary_lists_switched_on_features():
    assert shape_summary({"n_blades": 9}) == "9 blades"
    assert shape_summary({"n_blades": 7.0, "tubercle_amp": 0.05, "serration_amp": 0.0,
                          "dimple_amp": 0.2}) == "7 blades, tubercles, dimples"
    assert shape_summary({}) == "custom"


def test_dropdown_title_current_and_stale():
    d = _d(9014, completed="2026-09-30 20:27")
    d.extra["display_name"] = "F12"
    assert dropdown_title(d, tag="  ✪") == (
        "F12  ✪ · 9 blades · Assess Sep 30 · free 50.2 · load 41.4 · η 19.7")
    s = _d(9005, completed="2026-09-15 10:00", stale=True)
    s.extra["display_name"] = "F4"
    assert dropdown_title(s) == "⧗ F4 · 9 blades · Assess Sep 15 · needs re-run (old solver)"
    opt = _d(20004, source="cockpit_opt")
    assert "Optimizer" in dropdown_title(opt) and dropdown_title(opt).startswith("#20004")


def test_short_date():
    assert short_date("2026-09-30 20:27") == "Sep 30"
    assert short_date("") == ""


def test_loader_follows_case_dir_of_a_refreshed_design(tmp_path):
    from fansim.cockpit.fan_helpers import _load_assessed_designs

    runs = tmp_path / "runs"
    dd = runs / "opt_run1" / "cockpit_assess" / "design_9005"
    dd.mkdir(parents=True)
    (dd / "impeller.stl").write_text("old")
    new_case = runs / "screen_rank_audit" / "t9005" / "full"
    new_case.mkdir(parents=True)
    (new_case / "impeller.stl").write_text("new")
    (dd / "design.json").write_text(json.dumps({
        "trial": 9005, "params": {"n_blades": 9},
        "objectives": {"cfm_free": 50.0, "cfm_load": 40.0, "efficiency": 20.0},
        "extra": {"cfd_version": 5, "case_dir": "screen_rank_audit/t9005/full"}}))
    (d,) = _load_assessed_designs([runs / "opt_run1" / "cockpit_assess"])
    assert d.stl_path == new_case / "impeller.stl" and d.extra["cfd_stale"] is False
