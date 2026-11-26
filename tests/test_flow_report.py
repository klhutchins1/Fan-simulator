"""Unit tests for fansim.cfd.flow_report (synthetic fields with known answers)."""
from __future__ import annotations

import numpy as np
import pytest

from fansim.cfd.flow_report import (
    FlowMetrics,
    FlowReportUnavailable,
    FlowSamples,
    compute_metrics,
    exit_slab_mask,
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


# --- QA round 7 Task G follow-ups (roadmap 27.3) ---------------------------------------------

def _area_weights(pts):
    return np.hypot(pts[:, 0], pts[:, 1])  # uniform r/theta grid: cell area grows with r


def test_mean_push_is_area_weighted_over_the_annulus():
    pts = _annulus()
    u = np.tile([0.0, 0.0, 3.0], (pts.shape[0], 1))
    p = np.where(pts[:, 2] > 0, 10.0, 0.0)
    m = compute_metrics(_samples(pts, u, p=p, w=_area_weights(pts)), hub_r=HUB, tip_r=TIP, z_fan=0.0)
    assert m.mean_dp0_pa == pytest.approx(12.0)


def test_swirl_radial_equilibrium_tilts_bands_but_not_the_mean():
    """QA r7 G: swirl alone moves static pressure hub->tip (dp/dr = Uth^2/r), adding no axial work.
    The bands tilt; the area-weighted mean push must stay ~0 (Kimball 2026-10-12: judge on the mean)."""
    pts = _annulus()
    r = np.hypot(pts[:, 0], pts[:, 1])
    w = _area_weights(pts)
    ex = pts[:, 2] > 0
    uth = np.where(ex, 4.0, 0.0)
    u = np.column_stack([-pts[:, 1] / r * uth, pts[:, 0] / r * uth, np.full(len(r), 3.0)])
    lnr = np.log(r)
    shift = 16.0 * (lnr - np.sum(lnr[ex] * w[ex]) / np.sum(w[ex]))  # Uth^2 ln r, zero area mean
    p = np.where(ex, shift, 0.0)
    m = compute_metrics(_samples(pts, u, p=p, w=w), hub_r=HUB, tip_r=TIP, z_fan=0.0)
    assert m.band_dp0_pa[0] < -3.0 and m.band_dp0_pa[4] > 3.0
    assert m.mean_dp0_pa == pytest.approx(0.0, abs=1e-6)


def test_noise_level_matches_proudman_closed_form():
    from fansim.acoustics.proxies import ALPHA_PROUDMAN, C0_AIR, CMU, RHO_AIR

    pts = _annulus()
    u = np.tile([0.0, 0.0, 3.0], (pts.shape[0], 1))
    k, om, vol = 0.5, 2000.0, 1e-9
    n = pts.shape[0]
    m = compute_metrics(_samples(pts, u, k=np.full(n, k), omega=np.full(n, om), w=np.full(n, vol)),
                        hub_r=HUB, tip_r=TIP, z_fan=0.0)
    power = n * ALPHA_PROUDMAN * RHO_AIR * (CMU * k * om) * (np.sqrt(2 * k) / C0_AIR) ** 5 * vol
    assert m.noise_swl_db == pytest.approx(10 * np.log10(power / 1e-12), abs=1e-9)


def test_swirl_share_ignores_spin_sign_and_mixes_correctly():
    pts = _annulus()
    r = np.hypot(pts[:, 0], pts[:, 1])
    for sign in (1.0, -1.0):
        u = np.column_stack([-pts[:, 1] / r * 4.0 * sign, pts[:, 0] / r * 4.0 * sign,
                             np.full(len(r), 3.0)])
        m = compute_metrics(_samples(pts, u), hub_r=HUB, tip_r=TIP, z_fan=0.0)
        assert m.swirl_frac == pytest.approx(0.64)


def test_zero_exit_flow_records_why_values_are_missing():
    pts = _annulus()
    u = np.zeros((pts.shape[0], 3))
    m = compute_metrics(_samples(pts, u), hub_r=HUB, tip_r=TIP, z_fan=0.0)
    assert np.isnan(m.swirl_frac) and np.isnan(m.tip_band_uz_ratio) and np.isnan(m.dead_frac)
    assert "swirl_frac" in m.missing and "tip_band_uz_ratio" in m.missing and "dead_frac" in m.missing


def test_balanced_forward_and_backflow_zero_mean_marks_dead_frac_missing():
    """When mean_uz == 0 from opposing flows, 0.10*|mean_uz| == 0 is undefined, not 0 % dead."""
    pts = _annulus()
    u = np.zeros((pts.shape[0], 3))
    ex = np.flatnonzero(pts[:, 2] > 0)
    u[ex[: len(ex) // 2], 2] = 3.0
    u[ex[len(ex) // 2 :], 2] = -3.0
    m = compute_metrics(_samples(pts, u), hub_r=HUB, tip_r=TIP, z_fan=0.0)
    assert m.mean_uz_exit == pytest.approx(0.0, abs=1e-12)
    assert np.isnan(m.dead_frac) and "dead_frac" in m.missing


def test_zero_volume_tip_or_band_records_missing():
    pts = _annulus()
    r = np.hypot(pts[:, 0], pts[:, 1])
    frac = (r - HUB) / (TIP - HUB)
    u = np.tile([0.0, 0.0, 3.0], (pts.shape[0], 1))
    w = np.ones(pts.shape[0])
    # Zero out cell volumes in the outer 10% tip strip and in the inner band (band 0).
    w[(pts[:, 2] > 0) & (frac >= 0.9)] = 0.0
    w[(pts[:, 2] > 0) & (frac < 0.2)] = 0.0
    m = compute_metrics(_samples(pts, u, w=w), hub_r=HUB, tip_r=TIP, z_fan=0.0)
    assert np.isnan(m.tip_band_uz_ratio) and "tip_band_uz_ratio" in m.missing
    assert np.isnan(m.band_dp0_pa[0]) and "band_dp0_pa[0]" in m.missing


def test_zero_weights_are_unavailable_not_nan():
    pts = _annulus()
    u = np.tile([0.0, 0.0, 3.0], (pts.shape[0], 1))
    with pytest.raises(FlowReportUnavailable):
        compute_metrics(_samples(pts, u, w=np.zeros(pts.shape[0])), hub_r=HUB, tip_r=TIP, z_fan=0.0)


def test_empty_band_on_a_coarse_mesh_is_missing_with_reason():
    pts = _annulus()
    r = np.hypot(pts[:, 0], pts[:, 1])
    keep = (r - HUB) / (TIP - HUB) < 0.8  # no cells in the outer fifth
    pts = pts[keep]
    u = np.tile([0.0, 0.0, 3.0], (pts.shape[0], 1))
    m = compute_metrics(_samples(pts, u), hub_r=HUB, tip_r=TIP, z_fan=0.0)
    assert np.isnan(m.band_dp0_pa[4]) and "band_dp0_pa[4]" in m.missing


def test_to_dict_is_strict_json_and_round_trips_missing_values():
    import json

    m = FlowMetrics(0.1, False, [1.0, float("nan"), 3.0, 4.0, 5.0], float("nan"), 0.05, 0.9, None, 2.5,
                    mean_dp0_pa=3.2, missing={"swirl_frac": "no exit flow"})
    text = json.dumps(m.to_dict(), allow_nan=False)
    back = FlowMetrics.from_dict(json.loads(text))
    assert np.isnan(back.swirl_frac) and np.isnan(back.band_dp0_pa[1])
    assert back.band_dp0_pa[0] == 1.0 and back.mean_dp0_pa == 3.2
    assert back.missing == {"swirl_frac": "no exit flow"}


# --- 27.3e: planes follow the blade row (audit 2026-10-17-push-row-planes) ---------------------------

def test_slab_centres_sit_outside_the_blade_row():
    from fansim.cfd.flow_report import PLANE_GAP_FRAC, slab_centres, slab_half_width
    h = slab_half_width(TIP)
    z_in, z_ex = slab_centres(tip_r=TIP, z_fan=0.0, blade_z=(-0.0164, 0.0042))
    assert z_in == pytest.approx(-0.0164 - PLANE_GAP_FRAC * TIP - h)
    assert z_ex == pytest.approx(0.0042 + PLANE_GAP_FRAC * TIP + h)
    assert z_in + h < -0.0164 and z_ex - h > 0.0042        # F2: slabs never touch the blade


def test_slab_centres_without_blade_extent_are_the_old_fixed_planes():
    from fansim.cfd.flow_report import PLANE_Z_FRAC, slab_centres
    assert slab_centres(tip_r=TIP, z_fan=0.0, blade_z=None) == pytest.approx(
        (-PLANE_Z_FRAC * TIP, PLANE_Z_FRAC * TIP))


def test_push_is_measured_at_the_blade_relative_planes():
    """A blade row shifted toward the inlet: the old inlet plane would sit inside it."""
    from fansim.cfd.flow_report import slab_centres
    z_in, z_ex = slab_centres(tip_r=TIP, z_fan=0.0, blade_z=(-0.020, -0.004))
    pts = _annulus(zs=(z_in, -0.0099, 0.0099, z_ex))
    z = pts[:, 2]
    u = np.tile([0.0, 0.0, 3.0], (pts.shape[0], 1))
    # kinematic p: 0 upstream, 5 behind the row, 50 at the old fixed planes (inside / far from the row)
    p = np.where(np.isclose(z, z_in), 0.0, np.where(np.isclose(z, z_ex), 5.0, 50.0))
    m = compute_metrics(_samples(pts, u, p=p), hub_r=HUB, tip_r=TIP, z_fan=0.0, blade_z=(-0.020, -0.004))
    from fansim.physics.air import RHO_AMCA
    assert m.mean_dp0_pa == pytest.approx(RHO_AMCA * 5.0)
    assert "planes" not in m.missing


def test_missing_blade_extent_is_reported():
    pts = _annulus()
    u = np.tile([0.0, 0.0, 3.0], (pts.shape[0], 1))
    m = compute_metrics(_samples(pts, u), hub_r=HUB, tip_r=TIP, z_fan=0.0)
    assert "planes" in m.missing


def test_blade_z_extent_from_stl(tmp_path):
    import trimesh

    from fansim.cfd.flow_report_case import blade_z_extent
    hub = trimesh.creation.cylinder(radius=20.0, height=30.0)                 # hub, mm, z -15..15
    blade = trimesh.creation.box(extents=(10.0, 4.0, 12.0))                    # blade, mm, z -6..6
    blade.apply_translation((40.0, 0.0, -2.0))                                 # r ~35-45 mm, z -8..4
    (tmp_path / "impeller_cfd.stl").write_bytes(trimesh.util.concatenate([hub, blade]).export(file_type="stl"))
    lo, hi = blade_z_extent(tmp_path, hub_r=0.020)
    assert lo == pytest.approx(-0.008) and hi == pytest.approx(0.004)        # the hub's -15..15 is ignored
    assert blade_z_extent(tmp_path / "nope", hub_r=0.020) is None
