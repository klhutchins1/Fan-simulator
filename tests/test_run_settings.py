"""Runs save the settings from when Run was pressed, not when they finish (roadmap 25.11, QA-22..26)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from fansim.cockpit.run_settings import RunSettings, capture, identity_extra, stamp


def _state(**kw):
    base = dict(assess_preset="case", assess_wall_ks=False, assess_refine_op=False,
                assess_material="PETG", fan_model="a12x25", library_parent_id="",
                library_place_op="", selected_trial=9005)
    base.update(kw)
    return SimpleNamespace(**base)


def test_snapshot_is_unaffected_by_later_cockpit_changes():
    st = _state()
    s = capture(st, lambda: "SPEC-A")
    st.assess_preset, st.assess_material, st.fan_model, st.selected_trial = "radiator", "PLA", "delta", 1
    assert (s.preset, s.material, s.fan_model, s.selected_trial, s.spec) == (
        "case", "PETG", "a12x25", 9005, "SPEC-A")
    with pytest.raises(Exception):
        s.preset = "x"  # frozen


def test_load_pa_follows_the_snapshot_preset():
    from fansim.optimize.presets import assess_load
    s = capture(_state(assess_preset="radiator"), lambda: None)
    assert s.load_pa == assess_load("radiator")[0]


def test_identity_extra_uses_the_snapshot():
    s = capture(_state(library_parent_id="P7", library_place_op="scale_hub"), lambda: None)
    ex = identity_extra(s)
    assert ex == {"fan_model": "a12x25", "material": "PETG", "parent_id": "P7",
                  "place_op": "scale_hub", "placed_on": "a12x25", "cfd_stale": False}
    assert "parent_id" not in identity_extra(capture(_state(), lambda: None))


def test_stamp_records_the_snapshot_hose():
    s = capture(_state(assess_preset="heatsink", assess_refine_op=True), lambda: None)
    extra: dict = {}
    stamp(extra, {}, s)
    assert extra["preset"] == "heatsink" and extra["refine_op"] is True
    assert extra["load_pa"] == s.load_pa and "cfd_version" in extra


def test_run_settings_is_a_dataclass_snapshot():
    assert RunSettings.__dataclass_params__.frozen
