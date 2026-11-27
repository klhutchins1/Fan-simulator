"""RV-3 Module 6 unit tests for ``fansim/optimize/search_space.py``.

Covers every non-model bug fixed in the RV-3 audit plus key bounds, handedness,
wrap-constraint geometry, serialization round-trip, and reproducibility invariants.
"""

from __future__ import annotations

import dataclasses

import optuna
import pytest

from fansim.cfd.domain import OPTIMIZER_TIP_GAP_MM
from fansim.geometry.blade import (
    SHROUD_DEFAULT_MM,
    BladeParams,
    RadialStation,
    open_tip_rmax_mm,
)
from fansim.geometry.features import features_from_flat
from fansim.optimize.search_space import (
    BOUNDS,
    EXTENDED,
    FLAT_STATION_SLOT_R,
    FLAT_STATION_SLOTS,
    FLAT_STATIONS,
    GUIDED,
    GUIDED_LC,
    OPEN,
    SICKLE_BOUNDS,
    STATOR_BOUNDS,
    TIP_CAP_CLEARANCE_MM,
    WINGLET,
    blade_from_flat,
    blade_to_flat,
    outline_blade_flat,
    stock_blade_flat,
    suggest_params,
    tip_radius_cap_mm,
)
from fansim.optimize.trial_attrs import with_shroud_attr

optuna.logging.set_verbosity(optuna.logging.WARNING)


def _stations(chord_tip: float = 20.0, lean_tip: float = 10.0, lean_mid: float = 0.0):
    return [
        RadialStation(0.0, 18.0, 35.0, thickness=0.10, lean_deg=0.0),
        RadialStation(0.5, 22.0, 32.0, thickness=0.08, lean_deg=lean_mid),
        RadialStation(1.0, chord_tip, 24.0, thickness=0.06, lean_deg=lean_tip),
    ]


# ---------------------------------------------------------------------------
# 1. tip_radius_cap_mm & clearance constant (F5, F6, F7, F8)
# ---------------------------------------------------------------------------


def test_tip_cap_clearance_is_single_sourced_from_cfd_domain():
    assert TIP_CAP_CLEARANCE_MM == OPTIMIZER_TIP_GAP_MM


def test_tip_radius_cap_does_not_double_subtract_shroud():
    """Shroud ring must reduce tip_radius by 1*shroud, not 2*shroud."""
    frame_half = 55.0
    st = _stations(chord_tip=24.0, lean_tip=20.0)
    open_cap = tip_radius_cap_mm(st, 21.5, frame_half, shroud_mm=0.0)
    ring_cap = tip_radius_cap_mm(st, 21.5, frame_half, shroud_mm=SHROUD_DEFAULT_MM)

    assert open_cap == pytest.approx(frame_half - TIP_CAP_CLEARANCE_MM, abs=1e-9)
    assert ring_cap == pytest.approx(
        frame_half - TIP_CAP_CLEARANCE_MM - SHROUD_DEFAULT_MM, abs=1e-9
    )
    assert open_cap - ring_cap == pytest.approx(SHROUD_DEFAULT_MM, abs=1e-9)

    probe = BladeParams(
        hub_radius=21.5, tip_radius=ring_cap, stations=st, section_wrap="cylinder"
    )
    assert open_tip_rmax_mm(probe) + SHROUD_DEFAULT_MM <= frame_half - TIP_CAP_CLEARANCE_MM + 1e-9


def test_tip_radius_cap_wrapped_untrimmed_has_no_spurious_float_step():
    """1e-14 hypot rounding on wrapped cylinders must not trigger a -0.15 mm shrink step."""
    frame_half = 55.0
    st = _stations(chord_tip=34.0, lean_tip=35.0, lean_mid=15.0)
    cap = tip_radius_cap_mm(
        st, 21.5, frame_half, shroud_mm=0.0, cylindrical_tip=False, section_wrap="cylinder"
    )
    assert cap == pytest.approx(frame_half - TIP_CAP_CLEARANCE_MM, abs=1e-9)


def test_tip_radius_cap_planar_shroud_respects_bulge_and_single_shroud():
    """Planar untrimmed tips with shroud subtract shroud once plus actual bulge."""
    frame_half = 55.0
    st = _stations(chord_tip=36.0, lean_tip=40.0, lean_mid=20.0)
    cap = tip_radius_cap_mm(
        st,
        21.5,
        frame_half,
        shroud_mm=SHROUD_DEFAULT_MM,
        cylindrical_tip=False,
        section_wrap="planar",
    )
    probe = BladeParams(
        hub_radius=21.5,
        tip_radius=cap,
        stations=st,
        cylindrical_tip=False,
        section_wrap="planar",
    )
    built = open_tip_rmax_mm(probe) + SHROUD_DEFAULT_MM
    assert built <= frame_half - TIP_CAP_CLEARANCE_MM + 1e-9
    # Must not over-shrink by an extra full shroud thickness.
    assert built >= frame_half - TIP_CAP_CLEARANCE_MM - 0.5


def test_tip_radius_cap_rejects_invalid_inputs():
    st = _stations()
    with pytest.raises(ValueError, match="shroud"):
        tip_radius_cap_mm(st, 21.5, 55.0, shroud_mm=-1.0)
    with pytest.raises(ValueError, match="frame_half"):
        tip_radius_cap_mm(st, 21.5, 0.0)
    with pytest.raises(ValueError, match="hub_radius"):
        tip_radius_cap_mm(st, -1.0, 55.0)
    with pytest.raises(ValueError, match="stations"):
        tip_radius_cap_mm([], 21.5, 55.0)
    with pytest.raises(ValueError, match="span"):
        tip_radius_cap_mm(st, 25.0, 25.0)


def test_tip_radius_cap_small_frame_never_exceeds_frame():
    """Small frames (< 20 mm) must never clamp upward to 20 mm past frame_half_mm."""
    st = _stations(chord_tip=14.0, lean_tip=25.0)
    cap = tip_radius_cap_mm(
        st, 6.0, 18.0, shroud_mm=0.0, cylindrical_tip=False, section_wrap="planar"
    )
    assert 6.0 < cap < 18.0 - TIP_CAP_CLEARANCE_MM


# ---------------------------------------------------------------------------
# 2. suggest_params validation, shroud stamping, cap interaction (F2, F3, F4)
# ---------------------------------------------------------------------------


def test_suggest_params_stamps_shroud_thick_attr_for_replay():
    study = optuna.create_study(sampler=optuna.samplers.RandomSampler(seed=7))
    t = study.ask()
    bp = suggest_params(
        t,
        space="guided",
        with_shroud=True,
        with_winglet=True,
        with_spacing=True,
        with_extended=True,
        with_features=True,
        frame_half_mm=55.0,
    )
    assert t.user_attrs["shroud_thick_mm"] == pytest.approx(SHROUD_DEFAULT_MM)

    flat = with_shroud_attr(t)
    rebuilt = blade_from_flat(flat, features_from_flat(flat))
    assert rebuilt.shroud_thick_mm == pytest.approx(bp.shroud_thick_mm)
    assert rebuilt.shroud_height_frac == pytest.approx(bp.shroud_height_frac)
    assert rebuilt.tip_radius == pytest.approx(bp.tip_radius)
    assert rebuilt.hub_radius == pytest.approx(bp.hub_radius)
    assert rebuilt.blade_angles_deg == bp.blade_angles_deg
    assert rebuilt.features == bp.features
    assert [dataclasses.asdict(s) for s in rebuilt.stations] == [
        dataclasses.asdict(s) for s in bp.stations
    ]


def test_suggest_params_respects_both_frame_half_and_max_tip_radius():
    study = optuna.create_study(sampler=optuna.samplers.RandomSampler(seed=3))
    for _ in range(10):
        t = study.ask()
        bp = suggest_params(t, frame_half_mm=55.0, max_tip_radius=51.0)
        assert bp.hub_radius < bp.tip_radius <= 51.0 + 1e-9
        study.tell(t, 0.0)


def test_suggest_params_small_frame_keeps_tip_above_hub():
    study = optuna.create_study(sampler=optuna.samplers.RandomSampler(seed=5))
    t = study.ask()
    bp = suggest_params(t, hub_radius_range=(21.5, 21.5), frame_half_mm=22.5)
    assert bp.hub_radius < bp.tip_radius <= 22.0 + 1e-9


def test_suggest_params_rejects_invalid_inputs():
    study = optuna.create_study(sampler=optuna.samplers.RandomSampler(seed=1))
    with pytest.raises(KeyError, match="unknown search space"):
        suggest_params(study.ask(), space="nonexistent")
    with pytest.raises(ValueError, match="hub_radius_range"):
        suggest_params(study.ask(), hub_radius_range=(-2.0, 20.0))
    with pytest.raises(ValueError, match="hub_radius_range"):
        suggest_params(study.ask(), hub_radius_range=(25.0, 20.0))
    with pytest.raises(ValueError, match="frame_half_mm"):
        suggest_params(study.ask(), frame_half_mm=0.0)
    with pytest.raises(ValueError, match="max_tip_radius"):
        suggest_params(study.ask(), max_tip_radius=-5.0)
    with pytest.raises(ValueError, match="hub_radius"):
        suggest_params(study.ask(), hub_radius_range=(25.0, 25.0), max_tip_radius=24.0)


def test_suggest_params_seeded_reproducibility():
    def run_once():
        study = optuna.create_study(sampler=optuna.samplers.RandomSampler(seed=123))
        out = []
        for _ in range(5):
            t = study.ask()
            bp = suggest_params(
                t,
                space="open",
                with_features=True,
                with_spacing=True,
                with_extended=True,
                with_winglet=True,
                with_shroud=True,
                frame_half_mm=55.0,
            )
            out.append((t.params, bp.blade_angles_deg, [dataclasses.asdict(s) for s in bp.stations]))
            study.tell(t, 0.0)
        return out

    assert run_once() == run_once()


# ---------------------------------------------------------------------------
# 3. blade_to_flat / blade_from_flat serialization & edge cases (F1, F9-F15)
# ---------------------------------------------------------------------------


def test_blade_to_flat_preserves_zero_thick_scales_and_shroud_height():
    """Explicit 0.0 must not be clobbered to 1.0 by `or 1.0`."""
    bp = BladeParams(
        section_family="plate",
        le_thick_scale=0.0,
        te_thick_scale=0.0,
        shroud_thick_mm=SHROUD_DEFAULT_MM,
        shroud_height_frac=0.0,
    )
    flat = blade_to_flat(bp)
    assert flat["le_thick_scale"] == 0.0
    assert flat["te_thick_scale"] == 0.0
    assert flat["shroud_height_frac"] == 0.0

    rebuilt = blade_from_flat(flat)
    assert rebuilt.le_thick_scale == 0.0
    assert rebuilt.te_thick_scale == 0.0
    assert rebuilt.shroud_height_frac == 0.0


def test_blade_to_flat_preserves_three_station_root_le_offsets_and_camber_pos():
    bp = BladeParams(
        n_blades=7,
        stations=[
            RadialStation(0.0, 22.0, 30.0, camber_pos=0.35, le_sweep=1.5, le_skew=2.0),
            RadialStation(0.5, 28.0, 28.0, camber_pos=0.42),
            RadialStation(1.0, 32.0, 22.0, camber_pos=0.48),
        ],
    )
    flat = blade_to_flat(bp)
    assert FLAT_STATIONS in flat
    rebuilt = blade_from_flat(flat)
    assert [s.le_sweep for s in rebuilt.stations] == pytest.approx([1.5, 0.0, 0.0])
    assert [s.le_skew for s in rebuilt.stations] == pytest.approx([2.0, 0.0, 0.0])
    assert [s.camber_pos for s in rebuilt.stations] == pytest.approx([0.35, 0.42, 0.48])


def test_blade_to_flat_thick_mode_checks_full_span_not_just_adjacent():
    """Root=2.00, mid=2.015, tip=2.03 has adjacent diffs < 0.02 but total span 0.03 >= 0.02."""
    bp = BladeParams(
        stations=[
            RadialStation(0.0, 20.0, 30.0, thickness=2.00 / 20.0),
            RadialStation(0.5, 20.0, 28.0, thickness=2.015 / 20.0),
            RadialStation(1.0, 20.0, 22.0, thickness=2.03 / 20.0),
        ]
    )
    assert blade_to_flat(bp)["thick_mode"] == "tapered"


def test_blade_from_flat_handles_explicit_none_optional_fields():
    flat = {
        "n_blades": 7,
        "chord_root": 22.0,
        "chord_mid": 28.0,
        "chord_tip": 32.0,
        "stagger_root": 30.0,
        "stagger_mid": 28.0,
        "stagger_tip": 22.0,
        "sweep_mid": 1.0,
        "sweep_tip": 2.0,
        "max_camber": 0.04,
        "camber_root": None,
        "camber_mid": None,
        "camber_tip": None,
        "camber_pos": None,
        "thickness_root": None,
        "thickness_mid": None,
        "thickness_tip": None,
        "skew_mid": None,
        "skew_tip": None,
        "lean_mid": None,
        "lean_tip": None,
        "le_sweep_root": None,
        "le_sweep_mid": None,
        "le_sweep_tip": None,
        "le_skew_root": None,
        "le_skew_mid": None,
        "le_skew_tip": None,
        "hub_radius": None,
        "tip_radius": None,
        "hub_height": None,
        "hub_nose": None,
        "blade_z": None,
        "blade_z_mm": -1.25,
        "blade_hub_z": None,
        "blade_hub_z_mm": 0.75,
        "shroud_thick_mm": None,
        "shroud_height_frac": None,
        "le_thick_scale": None,
        "te_thick_scale": None,
        "n_span": None,
        "n_chord": None,
        "cylindrical_tip": None,
        "sickle_mm": None,
        "winglet_sweep": None,
        "winglet_lean": None,
        "tip_round": None,
        "spacing_spread": None,
        "spacing_seed": None,
    }
    bp = blade_from_flat(flat)
    assert bp.hub_radius == BladeParams.hub_radius
    assert bp.tip_radius == BladeParams.tip_radius
    assert bp.blade_z_mm == pytest.approx(-1.25)
    assert bp.blade_hub_z_mm == pytest.approx(0.75)
    assert [s.max_camber for s in bp.stations] == pytest.approx([0.04, 0.04, 0.04])
    assert bp.blade_angles_deg is None


def test_blade_from_flat_spacing_seed_none_and_negative():
    base = blade_to_flat(BladeParams())
    bp = blade_from_flat({**base, "spacing_spread": 0.25, "spacing_seed": None})
    bp0 = blade_from_flat({**base, "spacing_spread": 0.25, "spacing_seed": 0})
    assert bp.blade_angles_deg == bp0.blade_angles_deg

    with pytest.raises(ValueError, match="spacing_seed"):
        blade_from_flat({**base, "spacing_spread": 0.25, "spacing_seed": -1})


def test_stations_from_payload_uses_true_station_defaults_for_te_le_face():
    """Legacy FLAT_STATIONS dicts without te_face/le_face must default to 1.0, not 0.0."""
    flat = stock_blade_flat("a12x25")
    legacy_stations = [
        {k: v for k, v in s.items() if k not in ("te_face", "le_face")}
        for s in flat[FLAT_STATIONS]
    ]
    edited = {**flat, FLAT_STATIONS: legacy_stations, "te_face_tip": 0.5}
    bp = blade_from_flat(edited)
    assert bp.stations[-1].te_face == pytest.approx(0.5)
    assert bp.stations[0].te_face == pytest.approx(1.0)


def test_stations_from_payload_rejects_unsorted_slot_r():
    flat = stock_blade_flat("a12x25")
    bad = {**flat, FLAT_STATION_SLOT_R: [1.0, 0.5, 0.0]}
    with pytest.raises(ValueError, match=FLAT_STATION_SLOT_R):
        blade_from_flat(bad)


def test_blade_from_flat_full_payload_does_not_require_legacy_slot_keys():
    flat = stock_blade_flat("a12x25")
    minimal = {
        "n_blades": flat["n_blades"],
        FLAT_STATIONS: flat[FLAT_STATIONS],
        FLAT_STATION_SLOTS: flat[FLAT_STATION_SLOTS],
        FLAT_STATION_SLOT_R: flat[FLAT_STATION_SLOT_R],
    }
    bp = blade_from_flat(minimal)
    assert len(bp.stations) == 7


# ---------------------------------------------------------------------------
# 4. Bounds & recipe invariants
# ---------------------------------------------------------------------------


def test_all_bound_dicts_are_well_formed_and_preserve_handedness():
    expected_keys = set(OPEN.keys())
    assert set(GUIDED.keys()) == expected_keys
    assert set(GUIDED_LC.keys()) == expected_keys
    assert set(BOUNDS.keys()) == {"open", "guided", "guided_lc"}

    for name, space in BOUNDS.items():
        for k, (lo, hi) in space.items():
            assert lo < hi, f"{name}.{k}: {lo} >= {hi}"
            if "stagger" in k:
                assert 0.0 < lo < hi < 90.0, f"{name}.{k} out of (0, 90)"
            if k == "max_camber":
                assert lo >= 0.0, f"{name}.{k} allows negative camber"
            if "chord" in k:
                assert lo > 0.0

    for k, (lo, hi) in EXTENDED.items():
        assert 0.0 < lo < hi, f"EXTENDED.{k}: {(lo, hi)}"
    for k, (lo, hi) in WINGLET.items():
        assert 0.0 <= lo < hi, f"WINGLET.{k}: {(lo, hi)}"
    assert 0.0 < SICKLE_BOUNDS[0] < SICKLE_BOUNDS[1]
    assert 0.0 < STATOR_BOUNDS["stator_stagger_deg"][0] < STATOR_BOUNDS["stator_stagger_deg"][1] < 90.0
    assert 1 <= STATOR_BOUNDS["stator_n_extra"][0] < STATOR_BOUNDS["stator_n_extra"][1]


def test_stock_and_outline_flats_round_trip_cleanly():
    for flat in (stock_blade_flat("a12x25"), stock_blade_flat("a12x25_approx"), outline_blade_flat()):
        bp = blade_from_flat(flat)
        assert bp.n_blades == flat["n_blades"]
        assert bp.tip_radius > bp.hub_radius > 0.0
        assert len(bp.stations) >= 3
    with pytest.raises(KeyError, match="no parametric stock geometry"):
        stock_blade_flat("unknown_model")


# ---------------------------------------------------------------------------
# 5. Issue #128: single-sourced OBJECTIVE_NAMES, active-feature tip cap, archetype forwarding
# ---------------------------------------------------------------------------


def test_objective_names_single_sourced_from_objective_keys():
    from fansim.optimize import objective_keys, search_space

    assert search_space.OBJECTIVE_NAMES is objective_keys.OBJECTIVE_NAMES


def test_tip_radius_cap_accounts_for_features_winglet_and_sickle_without_mutating():
    from fansim.geometry.blade import apply_sickle, apply_winglet
    from fansim.geometry.features import Features

    frame_half = 55.0
    st = _stations(chord_tip=34.0, lean_tip=25.0, lean_mid=10.0)
    st_before = [dataclasses.replace(s) for s in st]

    base_cap = tip_radius_cap_mm(
        st, 21.5, frame_half, cylindrical_tip=False, section_wrap="planar"
    )
    feat = Features(tubercle_amp=0.10, tubercle_waves=5)
    feat_cap = tip_radius_cap_mm(
        st, 21.5, frame_half, cylindrical_tip=False, section_wrap="planar", features=feat
    )
    sickle_cap = tip_radius_cap_mm(
        st, 21.5, frame_half, cylindrical_tip=False, section_wrap="planar", sickle_mm=12.0
    )
    wl_cap = tip_radius_cap_mm(
        st,
        21.5,
        frame_half,
        cylindrical_tip=False,
        section_wrap="planar",
        winglet=(6.0, 15.0),
    )

    # Caller's stations list must never be mutated by winglet/sickle probing.
    assert st == st_before
    # Sickle adds tangential LE displacement in planar mode -> must shrink cap further.
    assert sickle_cap < base_cap
    # Every returned cap must keep the actual built envelope inside frame_half - clearance.
    for cap, kw in (
        (feat_cap, {"features": feat}),
        (sickle_cap, {"sickle_mm": 12.0}),
        (wl_cap, {"winglet": (6.0, 15.0)}),
    ):
        probe = BladeParams(
            hub_radius=21.5,
            tip_radius=cap,
            stations=[dataclasses.replace(s) for s in st],
            cylindrical_tip=False,
            section_wrap="planar",
            features=kw.get("features") or Features(),
        )
        if kw.get("winglet") is not None:
            apply_winglet(probe, sweep_add=kw["winglet"][0], lean_add=kw["winglet"][1])
        if kw.get("sickle_mm"):
            apply_sickle(probe, kw["sickle_mm"])
        assert open_tip_rmax_mm(probe) <= frame_half - TIP_CAP_CLEARANCE_MM + 1e-9


def test_axial_fan_archetype_forwards_frame_half_mm():
    from fansim.problem.archetypes import AxialFanArchetype

    arch = AxialFanArchetype()
    study = optuna.create_study(sampler=optuna.samplers.RandomSampler(seed=7))
    trial = study.ask()
    bp = arch.suggest_design(trial, space="guided", frame_half_mm=45.0)
    assert bp.tip_radius <= 45.0 - TIP_CAP_CLEARANCE_MM + 1e-9
