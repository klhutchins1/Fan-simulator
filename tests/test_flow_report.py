"""Unit tests for fansim.cfd.flow_report (synthetic fields with known answers)."""
from __future__ import annotations

import numpy as np
import pytest

from fansim.cfd.flow_report import (
    FlowMetrics, FlowReportUnavailable, FlowSamples, compute_metrics, exit_slab_mask,
)

HUB, TIP = 0.02, 0.055


def _annulus(n_r=20, n_th=72, zs=(-0.0099, 0.0099)):
    """Cells on an annulus at the inlet (z<0) and exit (z>0) slab planes (0.18*TIP = 0.0099)."""
    rs = np.linspace(HUB + 0.0005, TIP - 0.0005, n_r)
    th = np.linspace(-np.pi, np.pi, n_th, endpoint=False)
    R, T, Z = np.meshgrid(rs, th, np.asarray(zs), indexing="ij")
    pts = np.column_stack([(R * np.cos(T)).ravel(), (R * np.sin(T)).ravel(), Z.ravel()])
    return pts


def _samples(pts, u, p=None, w=None, k=None, omega=None):
    n = pts.shape[0]
    return FlowSamples(pts=pts, u=u, p=np.zeros(n) if p is None else p,
                       w=np.ones(n) if w is None else w, k=k, omega=omega)


def test_uniform_forward_flow():
    pts = _annulus()
    u = np.tile([0.0, 0.0, 3.0], (pts.shape[0], 1))
    m = compute_metrics(_samples(pts, u), hub_r=HUB, tip_r=TIP, z_fan=0.0)
    assert m.backflow_frac == 0.0
    assert m.net_reversed is False
    assert m.dead_frac == 0.0
    assert m.swirl_frac == pytest.approx(0.0, abs=1e-12)
    assert m.tip_band_uz_ratio == pytest.approx(1.0)
    assert m.mean_uz_exit == pytest.approx(3.0)
    assert m.noise_swl_db is None  # no k/omega supplied


def test_ten_percent_backflow():
    pts = _annulus()
    u = np.tile([0.0, 0.0, 3.0], (pts.shape[0], 1))
    exit_idx = np.flatnonzero(pts[:, 2] > 0)
    u[exit_idx[: len(exit_idx) // 10], 2] = -1.0
    m = compute_metrics(_samples(pts, u), hub_r=HUB, tip_r=TIP, z_fan=0.0)
    assert m.backflow_frac == pytest.approx(0.10, abs=0.005)
    assert m.net_reversed is False


def test_net_reversed():
    pts = _annulus()
    u = np.tile([0.0, 0.0, -2.0], (pts.shape[0], 1))
    m = compute_metrics(_samples(pts, u), hub_r=HUB, tip_r=TIP, z_fan=0.0)
    assert m.net_reversed is True
    assert m.backflow_frac == pytest.approx(1.0)


def test_pure_swirl_fraction_is_one():
    pts = _annulus()
    r = np.hypot(pts[:, 0], pts[:, 1])
    u = np.column_stack([-pts[:, 1] / r * 4.0, pts[:, 0] / r * 4.0, np.full(len(r), 1e-9)])
    m = compute_metrics(_samples(pts, u), hub_r=HUB, tip_r=TIP, z_fan=0.0)
    assert m.swirl_frac == pytest.approx(1.0, abs=1e-6)


def test_band_rise_in_pa():
    pts = _annulus()
    u = np.tile([0.0, 0.0, 3.0], (pts.shape[0], 1))
    p = np.where(pts[:, 2] > 0, 10.0, 0.0)  # kinematic rise of 10 m2/s2 everywhere
    m = compute_metrics(_samples(pts, u, p=p), hub_r=HUB, tip_r=TIP, z_fan=0.0)
    assert len(m.band_dp0_pa) == 5
    assert all(v == pytest.approx(12.0) for v in m.band_dp0_pa)  # rho 1.2 * 10


def test_bands_use_own_radii():
    hub2, tip2 = 0.025, 0.05
    rs = np.linspace(hub2 + 0.0005, tip2 - 0.0005, 20)
    th = np.linspace(-np.pi, np.pi, 72, endpoint=False)
    R, T, Z = np.meshgrid(rs, th, np.asarray([-0.009, 0.009]), indexing="ij")
    pts = np.column_stack([(R * np.cos(T)).ravel(), (R * np.sin(T)).ravel(), Z.ravel()])
    u = np.tile([0.0, 0.0, 3.0], (pts.shape[0], 1))
    frac = (np.hypot(pts[:, 0], pts[:, 1]) - hub2) / (tip2 - hub2)
    p = np.where(pts[:, 2] > 0, 10.0 * (frac >= 0.8), 0.0)  # rise only in the outer fifth
    m = compute_metrics(_samples(pts, u, p=p), hub_r=hub2, tip_r=tip2, z_fan=0.0)
    assert m.band_dp0_pa[:4] == pytest.approx([0, 0, 0, 0], abs=1e-9)
    assert m.band_dp0_pa[4] == pytest.approx(12.0)


def test_dead_fraction_and_tip_ratio():
    pts = _annulus()
    r = np.hypot(pts[:, 0], pts[:, 1])
    frac = (r - HUB) / (TIP - HUB)
    uz = np.where(frac > 0.9, 0.05, 3.0)  # outer 10 % nearly still
    u = np.column_stack([np.zeros_like(uz), np.zeros_like(uz), uz])
    m = compute_metrics(_samples(pts, u), hub_r=HUB, tip_r=TIP, z_fan=0.0)
    assert m.dead_frac == pytest.approx(0.10, abs=0.03)
    assert m.tip_band_uz_ratio < 0.1


def test_volume_weighting():
    pts = _annulus()
    u = np.tile([0.0, 0.0, 3.0], (pts.shape[0], 1))
    exit_idx = np.flatnonzero(pts[:, 2] > 0)
    back = exit_idx[: len(exit_idx) // 10]
    u[back, 2] = -1.0
    w = np.ones(pts.shape[0])
    w[back] = 9.0  # 10 % of cells holding half the exit volume
    m = compute_metrics(_samples(pts, u, w=w), hub_r=HUB, tip_r=TIP, z_fan=0.0)
    assert m.backflow_frac == pytest.approx(0.5, abs=0.02)


def test_noise_present_when_k_omega_given():
    pts = _annulus()
    u = np.tile([0.0, 0.0, 3.0], (pts.shape[0], 1))
    k = np.full(pts.shape[0], 0.5)
    om = np.full(pts.shape[0], 2000.0)
    m = compute_metrics(_samples(pts, u, k=k, omega=om, w=np.full(pts.shape[0], 1e-9)),
                        hub_r=HUB, tip_r=TIP, z_fan=0.0)
    assert m.noise_swl_db is not None and np.isfinite(m.noise_swl_db)


def test_empty_slab_raises():
    pts = _annulus(zs=(-0.04, 0.04))  # nothing near +-0.0099
    u = np.tile([0.0, 0.0, 3.0], (pts.shape[0], 1))
    with pytest.raises(FlowReportUnavailable):
        compute_metrics(_samples(pts, u), hub_r=HUB, tip_r=TIP, z_fan=0.0)


def test_metrics_roundtrip_dict():
    m = FlowMetrics(0.1, False, [1, 2, 3, 4, 5], 0.2, 0.05, 0.9, 61.0, 2.5)
    assert FlowMetrics.from_dict(m.to_dict()) == m


def test_exit_slab_mask_excludes_hub_and_outside():
    pts = np.array([[0.01, 0, 0.0099], [0.03, 0, 0.0099], [0.06, 0, 0.0099], [0.03, 0, 0.03]])
    assert exit_slab_mask(pts, hub_r=HUB, tip_r=TIP, z_fan=0.0).tolist() == [False, True, False, False]


def test_band_rise_excludes_swirl_energy():
    """Swirl leaving the fan is the 'wasted spin' row; it must not count as push (§24, F-check ruling)."""
    pts = _annulus()
    r = np.hypot(pts[:, 0], pts[:, 1])
    swirl = np.where(pts[:, 2] > 0, 4.0, 0.0)  # spin added only downstream
    u = np.column_stack([-pts[:, 1] / r * swirl, pts[:, 0] / r * swirl, np.full(len(r), 3.0)])
    m = compute_metrics(_samples(pts, u), hub_r=HUB, tip_r=TIP, z_fan=0.0)
    assert m.band_dp0_pa == pytest.approx([0.0] * 5, abs=1e-9)
