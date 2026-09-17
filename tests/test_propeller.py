# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Propeller geometry (fansim/propeller) — pitch-driven twist, watertight, shaft bore."""

from __future__ import annotations

from pathlib import Path

from fansim.prop_spec import get_prop_spec
from fansim.propeller import build_prop, prop_blade_params


def test_prop_twist_is_steep_root_shallow_tip():
    p = prop_blade_params(get_prop_spec("fpv_5inch"))
    root, mid, tip = (s.stagger_deg for s in sorted(p.stations, key=lambda s: s.r_frac))
    assert root > mid > tip                 # propeller twist: high angle at hub, low at tip
    assert root > 50 and tip < 30           # sane magnitudes for a 5x4.3


def test_prop_dimensions_from_spec():
    spec = get_prop_spec("fpv_5inch")
    p = prop_blade_params(spec)
    assert p.n_blades == spec.n_blades
    assert abs(p.tip_radius - spec.diameter_mm / 2) < 0.1     # tip radius = dia/2
    assert abs(2 * p.hub_radius - spec.shaft.hub_dia_mm) < 0.1  # small shaft-mount hub


def test_higher_pitch_gives_more_tip_angle():
    # a 3-inch (pitch ratio 1.0) has a higher tip angle than a 7-inch (pitch ratio ~0.57)
    tip3 = prop_blade_params(get_prop_spec("cine_3inch")).stations[-1].stagger_deg
    tip7 = prop_blade_params(get_prop_spec("longrange_7inch")).stations[-1].stagger_deg
    assert tip3 > tip7


def test_build_prop_watertight_with_bore(tmp_path):
    r = build_prop(get_prop_spec("fpv_5inch"), tmp_path / "p.stl", bore=True)
    assert r.ok and r.n_bodies == 1
    solid = build_prop(get_prop_spec("fpv_5inch"), tmp_path / "solid.stl", bore=False)
    assert r.volume_mm3 < solid.volume_mm3      # the shaft bore removed material


def test_build_prop_preview_writes_stl_and_volume_sidecar(tmp_path):
    import json

    from fansim.propeller.geometry import build_prop_preview

    out = tmp_path / "preview.stl"
    path = build_prop_preview(get_prop_spec("fpv_5inch"), out)
    assert path.exists() and path.stat().st_size > 0
    meta = Path(str(out) + ".meta.json")
    assert meta.exists()
    assert json.loads(meta.read_text())["volume_mm3"] > 0


def test_prop_cockpit_analyze_uses_preview_path():
    text = Path("fansim/cockpit/prop_tab.py").read_text(encoding="utf-8")
    assert "build_prop_preview" in text
    # Export still uses the fused printable path.
    assert "lambda: build_prop(" in text or "build_prop(spec, out" in text

