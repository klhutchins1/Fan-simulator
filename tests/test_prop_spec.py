# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Drone-propeller specs + registry (fansim/prop_spec.py)."""

from __future__ import annotations

from fansim.prop_spec import (
    PropShaftMount,
    PropSpec,
    get_prop_spec,
    prop_spec_from_dict,
    prop_spec_names,
    prop_spec_to_dict,
)


def test_registry_has_common_sizes():
    names = prop_spec_names()
    for k in ("fpv_5inch", "cine_3inch", "longrange_7inch", "micro_2inch"):
        assert k in names
    p = get_prop_spec("fpv_5inch")
    assert p.diameter_in == 5.0 and p.n_blades == 3 and p.shaft.shaft_dia_mm == 5.0


def test_geometry_conversions():
    p = get_prop_spec("fpv_5inch")
    assert abs(p.diameter_mm - 127.0) < 0.1        # 5 in = 127 mm
    assert abs(p.pitch_ratio - 4.3 / 5.0) < 1e-6


def test_tip_mach_flags_compressibility():
    # every FPV prop at full throttle should exceed the ~0.3 incompressible threshold — the whole
    # reason the fan's incompressible MRF assumption can't be reused for props.
    for k in prop_spec_names():
        assert get_prop_spec(k).tip_mach() > 0.3
    # a 5-inch at 30k RPM is well into compressible territory
    assert get_prop_spec("fpv_5inch").tip_mach() > 0.5


def test_efficiency_metric():
    p = get_prop_spec("fpv_5inch")
    assert p.ref_efficiency_g_per_w == round(1850.0 / 650.0, 2)   # g/W, the prop efficiency metric


def test_roundtrip_with_nested_shaft():
    p = get_prop_spec("longrange_7inch")
    back = prop_spec_from_dict(prop_spec_to_dict(p))
    assert isinstance(back.shaft, PropShaftMount)
    assert back.shaft.shaft_dia_mm == 5.0 and back.diameter_in == 7.0
