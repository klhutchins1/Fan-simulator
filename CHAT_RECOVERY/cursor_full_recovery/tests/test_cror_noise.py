"""CROR relative noise + synthetic dual-BPF FW-H."""

from __future__ import annotations

from fansim.cror.geometry import CrorParams
from fansim.cror.noise import cror_fwh_from_proxy, estimate_cror_noise
from fansim.cror.optimize import thin_cror_for_frame


def test_estimate_cror_noise():
    p = thin_cror_for_frame(CrorParams(), max_depth_mm=25.0)
    n = estimate_cror_noise(p, rpm=2000.0)
    assert n["analogy"] == "cror_tip_speed_proxy"
    assert n["rel_dba"] >= max(n["front_rel_dba"], n["rear_rel_dba"]) - 1e-6
    assert n["thrust_g"] > 0


def test_cror_fwh_synthetic():
    p = thin_cror_for_frame(CrorParams(), max_depth_mm=25.0)
    out = cror_fwh_from_proxy(p, rpm=2000.0)
    assert out["analogy"] == "fwh_cror_synthetic"
    assert "noise_dba_band" in out
    assert out["bpf_front_hz"] > 0 and out["bpf_rear_hz"] > 0
