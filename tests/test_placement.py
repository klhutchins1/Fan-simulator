from copy import deepcopy

from fansim.cockpit.placement import (
    fit_envelope,
    measure_flat,
    nominal_fits_spec,
    placed_child_record,
    preview_changes,
    scale_to_hub,
)
from fansim.fan_spec import get_fan_spec
from fansim.optimize.search_space import blade_from_flat


def _base(**kw):
    d = dict(
        n_blades=9,
        stagger_root=26,
        stagger_mid=26,
        stagger_tip=22,
        chord_root=34,
        chord_mid=44,
        chord_tip=38,
        sweep_mid=3,
        sweep_tip=5,
        max_camber=0.05,
        camber_pos=0.4,
        lean_mid=14,
        lean_tip=26,
        le_sweep_mid=0,
        le_sweep_tip=0,
        skew_mid=0,
        skew_tip=0,
        winglet_span=0.85,
        winglet_sweep=0,
        winglet_lean=0,
        hub_radius=16.5,
        tip_radius=59.0,
        hub_height=0,
        hub_profile="cylinder",
        hub_nose=0,
        thickness_root=0.08,
        thickness_mid=0.05,
        thickness_tip=0.03,
    )
    d.update(kw)
    return d


def test_fit_envelope_raises_hub_to_measured_cup():
    spec = get_fan_spec("a12x25")
    r = fit_envelope(_base(), spec)
    assert r.flat["hub_radius"] >= 19.825
    assert r.flat["hub_radius"] != 16.5
    assert any(c.field == "hub_radius" for c in r.changes)


def test_fit_envelope_records_change_when_hub_radius_missing():
    spec = get_fan_spec("a12x25")
    src = _base()
    del src["hub_radius"]
    r = fit_envelope(src, spec)
    hub_changes = [c for c in r.changes if c.field == "hub_radius"]
    assert len(hub_changes) == 1
    assert hub_changes[0].before == 0.0
    assert hub_changes[0].after >= 19.825


def test_fit_envelope_shrinks_tip_inside_110mm_frame():
    spec = get_fan_spec("a12x25")
    r = fit_envelope(_base(), spec)
    bp = blade_from_flat(r.flat)
    from fansim.cockpit.placement import blade_max_dia

    assert blade_max_dia(bp) <= spec.tip_dia_mm[1] + 0.01


def test_scale_halves_chords_not_stagger():
    spec = get_fan_spec("a12x25")
    src = _base(tip_radius=110.0, chord_root=40, chord_mid=40, chord_tip=40, stagger_mid=30)
    # scale_to_hub uses target tip ~ 110/2 - 2 = 53; s ≈ 53/110
    r = scale_to_hub(src, spec)
    assert r.flat["stagger_mid"] == 30
    assert r.flat["chord_root"] < 40
    assert r.flat["n_blades"] == 9


def test_scale_refuses_nonpositive_tip():
    spec = get_fan_spec("a12x25")
    r = scale_to_hub(_base(tip_radius=0.0), spec)
    assert r.flat["tip_radius"] == 0.0
    assert r.fit_status == "unplaced"
    assert "tip radius" in r.leftover.lower()


def test_scale_defaults_missing_tip_radius():
    spec = get_fan_spec("a12x25")
    src = _base()
    del src["tip_radius"]
    target_tip = spec.tip_dia_mm[1] / 2.0 - 2.0
    r = scale_to_hub(src, spec)
    assert r.flat["tip_radius"] > 0.0
    assert r.fit_status != "unplaced"
    assert abs(r.flat["tip_radius"] - target_tip) < 2.0


def test_preview_lists_changes():
    spec = get_fan_spec("a12x25")
    r = fit_envelope(_base(), spec)
    text = preview_changes(r.changes)
    assert "hub_radius" in text
    assert "CFD will be stale" in text


def test_nominal_fits_spec_rejects_oversized_tip():
    spec = get_fan_spec("a12x25")
    assert not nominal_fits_spec(_base(hub_radius=21.5, tip_radius=59.0), spec)
    r = fit_envelope(_base(), spec)
    assert r.fit_status == "fits"
    assert nominal_fits_spec(r.flat, spec)


def test_nominal_fits_spec_rejects_over_depth():
    spec = get_fan_spec("a12x25")
    flat = _base(
        hub_radius=21.0,
        tip_radius=52.0,  # old proxy: (2*tip + 4) <= 110 => would pass tip gate
        chord_root=22,
        chord_mid=22,
        chord_tip=20,
        stagger_mid=55,
        stagger_tip=55,
        sweep_mid=35,
        sweep_tip=45,
        le_sweep_mid=20,
        le_sweep_tip=25,
    )
    assert (2.0 * float(flat["tip_radius"]) + 4.0) <= spec.tip_dia_mm[1]
    m = measure_flat(flat)
    assert m is not None
    tip_dia, depth, _hub = m
    assert tip_dia <= spec.tip_dia_mm[1]
    assert depth > spec.depth_mm[1]
    assert not nominal_fits_spec(flat, spec)


def test_parent_flat_unchanged():
    spec = get_fan_spec("a12x25")
    original = _base()
    snapshot = deepcopy(original)
    fit_envelope(original, spec)
    assert original == snapshot


def test_placed_child_record_keeps_parent_id_and_stale_cfd():
    spec = get_fan_spec("a12x25")
    parent = _base()
    rec = placed_child_record(parent, spec, op="fit_envelope", parent_id="opt_run1_t9038", hub_key="a12x25")
    assert rec["parent_id"] == "opt_run1_t9038"
    assert rec["place_op"] == "fit_envelope"
    assert rec["cfd_stale"] is True
    assert rec["placed_on"] == "a12x25"
    assert rec["flat"]["hub_radius"] >= 19.825
    assert parent["hub_radius"] == 16.5


def test_scale_does_not_change_shroud_height_frac():
    spec = get_fan_spec("a12x25")
    src = _base(tip_radius=110.0, shroud_thick_mm=1.6, shroud_height_frac=0.3)
    r = scale_to_hub(src, spec)
    assert r.flat["shroud_height_frac"] == 0.3


def test_prepare_export_flat_off_leaves_oversize_untouched():
    from fansim.cockpit.placement import prepare_export_flat

    spec = get_fan_spec("a12x25")
    src = _base(tip_radius=59.0)
    snap = deepcopy(src)
    flat, changes = prepare_export_flat(src, spec, fit_frame=False)
    assert changes == []
    assert flat["tip_radius"] == 59.0
    assert src == snap
    assert flat is not src


def test_prepare_export_flat_on_shrinks_oversize_tip():
    from fansim.cfd.domain import OPTIMIZER_TIP_GAP_MM, remaining_tip_gap_mm
    from fansim.cockpit.placement import prepare_export_flat

    spec = get_fan_spec("a12x25")
    src = _base(tip_radius=59.0)
    snap = deepcopy(src)
    flat, changes = prepare_export_flat(src, spec, fit_frame=True)
    assert src == snap
    assert any(c.field == "tip_radius" for c in changes)
    assert flat["tip_radius"] < 59.0
    bp = blade_from_flat(flat)
    assert remaining_tip_gap_mm(bp, spec.tip_dia_mm[1]) >= OPTIMIZER_TIP_GAP_MM


def test_prepare_export_flat_on_does_not_grow_legal_tip():
    from fansim.cockpit.placement import prepare_export_flat

    spec = get_fan_spec("a12x25")
    src = _base(hub_radius=21.5, tip_radius=48.0, lean_mid=0, lean_tip=0, chord_tip=22)
    flat, _changes = prepare_export_flat(src, spec, fit_frame=True)
    assert flat["tip_radius"] <= src["tip_radius"]


def test_prepare_export_flat_off_leaves_oversize_untouched():
    from fansim.cockpit.placement import prepare_export_flat

    spec = get_fan_spec("a12x25")
    src = _base(tip_radius=59.0)
    snap = deepcopy(src)
    flat, changes = prepare_export_flat(src, spec, fit_frame=False)
    assert changes == []
    assert flat["tip_radius"] == 59.0
    assert src == snap
    assert flat is not src


def test_prepare_export_flat_on_shrinks_oversize_tip():
    from fansim.cfd.domain import OPTIMIZER_TIP_GAP_MM, remaining_tip_gap_mm
    from fansim.cockpit.placement import prepare_export_flat

    spec = get_fan_spec("a12x25")
    src = _base(tip_radius=59.0)
    snap = deepcopy(src)
    flat, changes = prepare_export_flat(src, spec, fit_frame=True)
    assert src == snap
    assert any(c.field == "tip_radius" for c in changes)
    assert flat["tip_radius"] < 59.0
    bp = blade_from_flat(flat)
    assert remaining_tip_gap_mm(bp, spec.tip_dia_mm[1]) >= OPTIMIZER_TIP_GAP_MM


def test_prepare_export_flat_on_does_not_grow_legal_tip():
    from fansim.cockpit.placement import prepare_export_flat

    spec = get_fan_spec("a12x25")
    src = _base(hub_radius=21.5, tip_radius=48.0, lean_mid=0, lean_tip=0, chord_tip=22)
    flat, _changes = prepare_export_flat(src, spec, fit_frame=True)
    assert flat["tip_radius"] <= src["tip_radius"]


def test_features_from_flat_roundtrips_bio_keys():
    from fansim.geometry.features import Features, features_from_flat

    f = features_from_flat({
        "tubercle_amp": 0.08, "tubercle_waves": 6,
        "serration_amp": 0.04, "serration_waves": 8,
        "n_blades": 9,  # ignored
    })
    assert f == Features(tubercle_amp=0.08, tubercle_waves=6,
                         serration_amp=0.04, serration_waves=8)
    assert features_from_flat({}).active is False


def test_measure_flat_uses_bio_features_from_flat():
    """With cylindrical_tip off, blank Features under-reads tip OD vs featured Preview."""
    from fansim.cockpit.placement import blade_max_dia, blade_z_extent
    from fansim.geometry.features import Features

    flat = _base(
        hub_radius=21.5, tip_radius=52.0, cylindrical_tip=False,
        tubercle_amp=0.1, tubercle_waves=6,
        serration_amp=0.05, serration_waves=8,
    )
    feat = Features(tubercle_amp=0.1, tubercle_waves=6,
                    serration_amp=0.05, serration_waves=8)
    dia_blank = blade_max_dia(blade_from_flat(flat, Features()))
    dia_feat = blade_max_dia(blade_from_flat(flat, feat))
    assert dia_feat - dia_blank > 1.0  # features enlarge the built tip

    m = measure_flat(flat)
    assert m is not None
    tip_dia, depth, _hub = m
    assert abs(tip_dia - dia_feat) < 1e-6
    assert abs(depth - blade_z_extent(blade_from_flat(flat, feat))) < 1e-6
    assert abs(tip_dia - dia_blank) > 1.0


def test_cylindrical_tip_caps_bio_feature_od():
    """Default cylindrical tip trims feature overshoot — measure/Fit see tip_radius, not bulge."""
    from fansim.cockpit.placement import blade_max_dia
    from fansim.geometry.features import Features

    flat = _base(
        hub_radius=21.5, tip_radius=52.0,  # cylindrical_tip default True via blade_from_flat
        tubercle_amp=0.1, tubercle_waves=6,
        serration_amp=0.05, serration_waves=8,
    )
    feat = Features(tubercle_amp=0.1, tubercle_waves=6,
                    serration_amp=0.05, serration_waves=8)
    dia_blank = blade_max_dia(blade_from_flat(flat, Features()))
    dia_feat = blade_max_dia(blade_from_flat(flat, feat))
    assert abs(dia_feat - dia_blank) < 0.05  # both capped at ~2*tip_radius
    assert abs(dia_feat - 2.0 * 52.0) < 0.05


def test_fit_envelope_ignores_feature_overshoot_when_cylindrical():
    """Product rule: with trim on, Fit tip_radius matches blank vs featured (cut caps OD)."""
    from fansim.geometry.features import Features

    spec = get_fan_spec("a12x25")
    flat = _base(hub_radius=21.5, tip_radius=54.0)  # cylindrical default on
    feat = Features(tubercle_amp=0.1, tubercle_waves=6,
                    serration_amp=0.05, serration_waves=8)
    r0 = fit_envelope(flat, spec, features=Features())
    r1 = fit_envelope(flat, spec, features=feat)
    assert abs(float(r1.flat["tip_radius"]) - float(r0.flat["tip_radius"])) < 1e-9


def test_fit_envelope_accounts_for_bio_features():
    """Fit must shrink tip enough for featured OD when cylindrical trim is off."""
    from fansim.cfd.domain import OPTIMIZER_TIP_GAP_MM, remaining_tip_gap_mm
    from fansim.geometry.features import Features

    spec = get_fan_spec("a12x25")
    feat = Features(tubercle_amp=0.1, tubercle_waves=6,
                    serration_amp=0.05, serration_waves=8)
    flat = _base(
        hub_radius=21.5, tip_radius=54.0, cylindrical_tip=False,
        tubercle_amp=0.1, tubercle_waves=6,
        serration_amp=0.05, serration_waves=8,
    )
    r_blank = fit_envelope(flat, spec, features=Features())
    r_feat = fit_envelope(flat, spec)  # pulls features from flat
    assert r_feat.flat["tip_radius"] < r_blank.flat["tip_radius"]
    bp = blade_from_flat(r_feat.flat, feat)
    assert remaining_tip_gap_mm(bp, spec.tip_dia_mm[1]) >= OPTIMIZER_TIP_GAP_MM
    assert r_feat.fit_status == "fits"


def test_fit_envelope_explicit_features_override_flat():
    from fansim.geometry.features import Features

    spec = get_fan_spec("a12x25")
    flat = _base(hub_radius=21.5, tip_radius=54.0, cylindrical_tip=False)  # no feature keys
    feat = Features(tubercle_amp=0.1, tubercle_waves=6,
                    serration_amp=0.05, serration_waves=8)
    r0 = fit_envelope(flat, spec, features=Features())
    r1 = fit_envelope(flat, spec, features=feat)
    assert r1.flat["tip_radius"] < r0.flat["tip_radius"]


def test_fit_envelope_preserves_sickle_and_notch_keys():
    from fansim.geometry.blade import NOTCH_COUNT, NOTCH_DEPTH_MM

    spec = get_fan_spec("a12x25")
    flat = _base(hub_radius=21.5, tip_radius=54.0, sickle_mm=3.0,
                 tip_notch_count=3, tip_notch_depth_mm=1.2)
    r = fit_envelope(flat, spec)
    # Fit only mutates envelope fields; sickle/notch keys stay on the flat.
    assert r.flat.get("sickle_mm") == 3.0
    assert r.flat.get("tip_notch_count") == 3
    assert r.flat.get("tip_notch_depth_mm") == 1.2
    bp = blade_from_flat(r.flat)
    # apply_notched_tips stamps the fixed recipe (count/depth), sickle stamps le_skew
    assert bp.tip_notch_count == NOTCH_COUNT
    assert bp.tip_notch_depth_mm == NOTCH_DEPTH_MM
    assert any(abs(float(st.le_skew)) > 0 for st in bp.stations)


def test_features_from_flat_roundtrips_bio_keys():
    from fansim.geometry.features import Features, features_from_flat

    f = features_from_flat({
        "tubercle_amp": 0.08, "tubercle_waves": 6,
        "serration_amp": 0.04, "serration_waves": 8,
        "n_blades": 9,  # ignored
    })
    assert f == Features(tubercle_amp=0.08, tubercle_waves=6,
                         serration_amp=0.04, serration_waves=8)
    assert features_from_flat({}).active is False


def test_measure_flat_uses_bio_features_from_flat():
    """Blank Features under-reads tip OD / depth vs Preview's featured geometry."""
    from fansim.cockpit.placement import blade_max_dia, blade_z_extent
    from fansim.geometry.features import Features

    flat = _base(
        hub_radius=21.5, tip_radius=52.0,
        tubercle_amp=0.1, tubercle_waves=6,
        serration_amp=0.05, serration_waves=8,
    )
    feat = Features(tubercle_amp=0.1, tubercle_waves=6,
                    serration_amp=0.05, serration_waves=8)
    dia_blank = blade_max_dia(blade_from_flat(flat, Features()))
    dia_feat = blade_max_dia(blade_from_flat(flat, feat))
    assert dia_feat - dia_blank > 1.0  # features enlarge the built tip

    m = measure_flat(flat)
    assert m is not None
    tip_dia, depth, _hub = m
    assert abs(tip_dia - dia_feat) < 1e-6
    assert abs(depth - blade_z_extent(blade_from_flat(flat, feat))) < 1e-6
    assert abs(tip_dia - dia_blank) > 1.0


def test_fit_envelope_accounts_for_bio_features():
    """Fit must shrink tip enough for featured OD, not the smooth under-read."""
    from fansim.cfd.domain import OPTIMIZER_TIP_GAP_MM, remaining_tip_gap_mm
    from fansim.geometry.features import Features

    spec = get_fan_spec("a12x25")
    feat = Features(tubercle_amp=0.1, tubercle_waves=6,
                    serration_amp=0.05, serration_waves=8)
    flat = _base(
        hub_radius=21.5, tip_radius=54.0,
        tubercle_amp=0.1, tubercle_waves=6,
        serration_amp=0.05, serration_waves=8,
    )
    r_blank = fit_envelope(flat, spec, features=Features())
    r_feat = fit_envelope(flat, spec)  # pulls features from flat
    assert r_feat.flat["tip_radius"] < r_blank.flat["tip_radius"]
    bp = blade_from_flat(r_feat.flat, feat)
    assert remaining_tip_gap_mm(bp, spec.tip_dia_mm[1]) >= OPTIMIZER_TIP_GAP_MM
    assert r_feat.fit_status == "fits"


def test_fit_envelope_explicit_features_override_flat():
    from fansim.geometry.features import Features

    spec = get_fan_spec("a12x25")
    flat = _base(hub_radius=21.5, tip_radius=54.0)  # no feature keys
    feat = Features(tubercle_amp=0.1, tubercle_waves=6,
                    serration_amp=0.05, serration_waves=8)
    r0 = fit_envelope(flat, spec, features=Features())
    r1 = fit_envelope(flat, spec, features=feat)
    assert r1.flat["tip_radius"] < r0.flat["tip_radius"]


def test_fit_envelope_preserves_sickle_and_notch_keys():
    spec = get_fan_spec("a12x25")
    flat = _base(hub_radius=21.5, tip_radius=54.0, sickle_mm=3.0,
                 tip_notch_count=3, tip_notch_depth_mm=1.2)
    r = fit_envelope(flat, spec)
    assert r.flat.get("sickle_mm") == 3.0
    assert r.flat.get("tip_notch_count") == 3
    assert r.flat.get("tip_notch_depth_mm") == 1.2
    bp = blade_from_flat(r.flat)
    assert bp.tip_notch_count == 3
    assert float(getattr(bp, "stations")[0].__dict__.get("le_skew", 0) or 0) >= 0  # sickle applied path ok
    # sickle stamps le_skew on stations; rebuild should keep tip_notch
    assert bp.tip_notch_depth_mm == 1.2
