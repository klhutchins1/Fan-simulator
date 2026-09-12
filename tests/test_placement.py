# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
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
