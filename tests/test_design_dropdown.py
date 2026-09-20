"""design_dropdown_items — the shared archetype previous-runs dropdown builder (§17.1)."""

from __future__ import annotations

from fansim.cockpit.data import design_dropdown_items


def test_trial_valued_items():
    rows = [
        {"trial": 5, "objectives": {"cfm_free": 40.0, "cfm_load": 22.0, "efficiency": 8.1}},
        {"trial": 9001, "objectives": {"cfm_free": 51.2}, "extra": {"cfd_stale": True}},
    ]
    items = design_dropdown_items(rows)
    assert items[0]["value"] == 5
    assert "#5" in items[0]["title"] and "free 40.0" in items[0]["title"]
    assert items[1]["value"] == 9001
    assert "⧗" in items[1]["title"]  # stale marker


def test_index_valued_items():
    rows = [{"trial": 3, "objectives": {"fm": 0.72}}, {"trial": 7, "objectives": {}}]
    items = design_dropdown_items(rows, by_index=True)
    assert [it["value"] for it in items] == [0, 1]  # list index, not trial
    assert "FM 0.7" in items[0]["title"]


def test_empty_and_missing_trial():
    assert design_dropdown_items([]) == []
    assert design_dropdown_items(None) == []
    items = design_dropdown_items([{"objectives": {}}])  # no trial → falls back to index head
    assert items[0]["value"] == 0 and items[0]["title"].startswith("#0")
