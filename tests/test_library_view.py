from copy import deepcopy

from fansim.catalog import CatalogEntry
from fansim.cockpit.library_view import (
    HINT_BIG,
    HINT_FITS,
    HINT_NONE,
    apply_library_recipe,
    fit_hint,
    library_list_items,
)
from fansim.fan_spec import get_fan_spec


def test_missing_params_is_no_geometry():
    spec = get_fan_spec("a12x25")
    e = CatalogEntry(design_id="x", run="opt_run1", params={"n_blades": 9})
    assert fit_hint(e, spec) == "no geometry yet"


def test_row_copy_uses_original_size_not_envelope_jargon():
    spec = get_fan_spec("a12x25")
    e = CatalogEntry(
        design_id="opt_run1_t9038",
        run="opt_run1",
        n_blades=9,
        cfm_free=92.4,
        params={"n_blades": 9, "hub_radius": 16.5, "tip_radius": 59.0},
    )
    items = library_list_items([e], spec)
    groups = [i for i in items if i["role"] == "group"]
    rows = [i for i in items if i["role"] == "row"]
    assert groups[0]["title"] == "First unconstrained 120 mm search"
    assert groups[0]["caption"] == "opt_run1"
    assert rows[0]["value"] == "opt_run1_t9038"
    assert rows[0]["title"] == "9 blades · hub 33 mm · tip 118 mm"
    assert "at original size" in rows[0]["subtitle"]
    assert "original envelope" not in rows[0]["title"].lower()
    assert "original envelope" not in rows[0]["subtitle"].lower()
    assert "no geometry yet" in rows[0]["subtitle"]
    assert rows[0]["clickable"] is False


def test_oversized_is_not_titled_as_fits_a12x25():
    spec = get_fan_spec("a12x25")
    e = CatalogEntry(
        design_id="big",
        run="opt_run1",
        cfm_free=92.0,
        params={"n_blades": 9, "hub_radius": 16.5, "tip_radius": 59.0,
                "stagger_root": 26, "stagger_mid": 26, "stagger_tip": 22,
                "chord_root": 34, "chord_mid": 44, "chord_tip": 38,
                "sweep_mid": 3, "sweep_tip": 5, "max_camber": 0.05},
    )
    hint = fit_hint(e, spec)
    assert hint != "fits this hub"
    assert "Fits it" not in hint
    assert hint == "no geometry yet" or ("too big" in hint and "Scale" in hint)


def _base(**kw):
    d = dict(
        n_blades=9, stagger_root=26, stagger_mid=26, stagger_tip=22,
        chord_root=34, chord_mid=44, chord_tip=38,
        sweep_mid=3, sweep_tip=5, max_camber=0.05, camber_pos=0.4,
        lean_mid=14, lean_tip=26, le_sweep_mid=0, le_sweep_tip=0,
        skew_mid=0, skew_tip=0, winglet_span=0.85, winglet_sweep=0, winglet_lean=0,
        hub_radius=16.5, tip_radius=59.0, hub_height=0, hub_profile="cylinder",
        hub_nose=0, thickness_root=0.08, thickness_mid=0.05, thickness_tip=0.03,
    )
    d.update(kw)
    return d


def test_apply_fit_does_not_mutate_parent_or_invent_a_trial():
    spec = get_fan_spec("a12x25")
    parent = _base()
    snap = deepcopy(parent)
    rec = apply_library_recipe(parent, spec, op="fit_envelope", parent_id="opt_run1_t9038")
    assert parent == snap
    assert rec.ok is True
    assert rec.parent_id == "opt_run1_t9038"
    assert rec.place_op == "fit_envelope"
    assert rec.flat is not None
    assert rec.flat["hub_radius"] >= 19.825
    assert not hasattr(rec, "trial")
    assert "trial" not in rec.__dict__


def test_apply_refuses_empty_params():
    spec = get_fan_spec("a12x25")
    rec = apply_library_recipe({"n_blades": 9}, spec, op="fit_envelope", parent_id="x")
    assert rec.ok is False
    assert rec.flat is None
    assert rec.message == "This recipe has no blade numbers to Fit."


def test_apply_scale_unplaced_on_zero_tip():
    spec = get_fan_spec("a12x25")
    rec = apply_library_recipe(_base(tip_radius=0.0), spec, op="scale_to_hub", parent_id="x")
    assert rec.ok is False
    assert rec.flat is None
    assert rec.fit_status == "unplaced"
