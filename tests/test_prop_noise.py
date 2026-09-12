# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Propeller noise proxy (fansim/propeller/noise.py) — relative-ranking sanity."""

from __future__ import annotations

from fansim.prop_spec import get_prop_spec
from fansim.propeller import prop_blade_params
from fansim.propeller.bemt import analyze
from fansim.propeller.noise import estimate_prop_noise


def _noise(spec, rpm):
    p = prop_blade_params(spec)
    return estimate_prop_noise(p, rpm, analyze(p, rpm=rpm))


def test_louder_at_higher_rpm():
    spec = get_prop_spec("fpv_5inch")
    lo = _noise(spec, 12000)
    hi = _noise(spec, 30000)
    assert hi["rel_dba"] > lo["rel_dba"]           # faster tip = louder
    assert hi["tip_mach"] > lo["tip_mach"]
    assert hi["bpf_hz"] > lo["bpf_hz"]


def test_reports_tip_mach_and_bpf():
    n = _noise(get_prop_spec("fpv_5inch"), 30000)
    assert 0.2 < n["tip_mach"] < 0.9              # 5-inch @ 30k is transonic-ish tip
    assert n["bpf_hz"] > 0 and n["tip_speed_ms"] > 0


def test_more_blades_lower_loading_term():
    # at the same thrust, more blades spread the load -> quieter loading term (=> not louder overall)
    import dataclasses
    spec = get_prop_spec("fpv_5inch")
    n3 = _noise(dataclasses.replace(spec, n_blades=2), 20000)
    n4 = _noise(dataclasses.replace(spec, n_blades=4), 20000)
    assert n4["rel_dba"] <= n3["rel_dba"] + 0.1    # more blades never louder on this proxy
