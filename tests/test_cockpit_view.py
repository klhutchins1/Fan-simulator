# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
import re
from pathlib import Path

from fansim.catalog import CatalogEntry, results_for_hub
from fansim.cockpit.app import _reject_hint, scatter_figure
from fansim.cockpit.library_view import library_list_items
from fansim.cockpit.data import Design
from fansim.fan_spec import get_fan_spec


def test_reject_hint_explains_frame_gap():
    # the ring-to-frame gate rejects instantly with this reason; the user must get a hint, not silence
    hint = _reject_hint("Noctua NF-A12x25: tip gap 0.10 mm < min 0.50 mm to 110 mm frame")
    assert hint
    assert "fit to frame" in hint.lower()
    assert "clearance" in hint.lower() or "gap" in hint.lower()


def test_reject_hint_frame_gap_not_confused_with_tip_dia():
    # a genuine tip-DIAMETER rejection keeps its own hint (must not be swallowed by the gap branch)
    hint = _reject_hint("tip dia 112 mm > max 110 mm")
    assert "tip diameter" in hint.lower()


def test_results_for_hub_hides_foreign_envelope():
    a12 = CatalogEntry(design_id="ok", hub_models=["a12x25"], cfm_free=54.0, cfm_load=50.0)
    big = CatalogEntry(design_id="big", hub_models=[], cfm_free=92.0, cfm_load=87.0)
    hits = results_for_hub([a12, big], "a12x25")
    assert [h.design_id for h in hits] == ["ok"]
    spec = get_fan_spec("a12x25")
    lib = library_list_items([a12, big], spec)
    assert [it["value"] for it in lib if it.get("role") == "row"] == ["ok", "big"]

