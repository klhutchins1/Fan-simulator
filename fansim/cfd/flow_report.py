"""Plain-language flow report: measurements on the saved loaded-point CFD field (roadmap §24).

Pure numpy on cell samples. The exit/inlet slabs match ``fansim.cfd.spanwise`` (z_fan +- 0.18 r_tip).
Flow runs inlet -Z -> outlet +Z in the CFD frame, so forward is Uz > 0. Weights are cell volumes.
Spec: docs/superpowers/specs/2026-10-10-flow-report-card-design.md
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from fansim.acoustics.proxies import epsilon_from_komega, proudman_power_density, sound_power_level
from fansim.cfd.spanwise import cylindrical_velocity
from fansim.physics.air import RHO_AMCA

FLOW_REPORT_VERSION = 2  # v2: push excludes swirl energy (audit 2026-10-10-flow-report-checks)
N_BANDS = 5
PLANE_Z_FRAC = 0.18           # same plane as fansim.cfd.spanwise._PLANE_Z_FRAC
DEAD_FRAC_OF_MEAN = 0.10      # |Uz| below this share of the mean exit Uz counts as dead air
TIP_BAND_FRAC = 0.10          # outer share of the span for the tip-leakage ratio
NOISE_Z_FRAC = 1.5            # rotor region for the noise total: |z - z_fan| <= 1.5 r_tip
NOISE_R_FRAC = 1.2            # ... and r <= 1.2 r_tip


class FlowReportUnavailable(Exception):
    """The field cannot support the report (e.g. no cells on the exit plane)."""


@dataclass
class FlowSamples:
    pts: np.ndarray
    u: np.ndarray
    p: np.ndarray
    w: np.ndarray
    k: np.ndarray | None = None
    omega: np.ndarray | None = None


@dataclass
class FlowMetrics:
    backflow_frac: float
    net_reversed: bool
    band_dp0_pa: list[float]
    swirl_frac: float
    dead_frac: float
    tip_band_uz_ratio: float
    noise_swl_db: float | None
    mean_uz_exit: float

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> FlowMetrics:
        return cls(**{k: d[k] for k in cls.__dataclass_fields__})


def _half_dz(tip_r: float) -> float:
    return max(0.04 * float(tip_r), 0.002)


def _annulus(pts, hub_r, tip_r):
    r = np.hypot(pts[:, 0], pts[:, 1])
    return (r >= hub_r) & (r <= tip_r)


def exit_slab_mask(pts, *, hub_r, tip_r, z_fan):
    z0 = float(z_fan) + PLANE_Z_FRAC * float(tip_r)
    return _annulus(pts, hub_r, tip_r) & (np.abs(pts[:, 2] - z0) <= _half_dz(tip_r))


def inlet_slab_mask(pts, *, hub_r, tip_r, z_fan):
    z0 = float(z_fan) - PLANE_Z_FRAC * float(tip_r)
    return _annulus(pts, hub_r, tip_r) & (np.abs(pts[:, 2] - z0) <= _half_dz(tip_r))


def _wmean(a, w) -> float:
    sw = float(np.sum(w))
    return float(np.sum(a * w) / sw) if sw > 0 else float("nan")


def noise_density(k, omega) -> np.ndarray:
    """Proudman acoustic power density [W/m^3] from k-omega fields."""
    return proudman_power_density(k, epsilon_from_komega(k, omega))


def _band_index(r, hub_r, tip_r):
    frac = (r - hub_r) / max(tip_r - hub_r, 1e-12)
    return np.clip((frac * N_BANDS).astype(int), 0, N_BANDS - 1)


def compute_metrics(s: FlowSamples, *, hub_r: float, tip_r: float, z_fan: float) -> FlowMetrics:
    pts, u, p, w = s.pts, s.u, np.asarray(s.p, float), np.asarray(s.w, float)
    ex = exit_slab_mask(pts, hub_r=hub_r, tip_r=tip_r, z_fan=z_fan)
    inn = inlet_slab_mask(pts, hub_r=hub_r, tip_r=tip_r, z_fan=z_fan)
    if not np.any(ex):
        raise FlowReportUnavailable("no cells on the exit plane")
    r, uz, uth = cylindrical_velocity(pts, u)
    we = w[ex]
    uz_e, uth_e, r_e = uz[ex], uth[ex], r[ex]

    mean_uz = _wmean(uz_e, we)
    backflow = _wmean((uz_e < 0).astype(float), we)
    denom = float(np.sum(we * (uz_e ** 2 + uth_e ** 2)))
    swirl = float(np.sum(we * uth_e ** 2) / denom) if denom > 0 else float("nan")
    dead_lim = DEAD_FRAC_OF_MEAN * abs(mean_uz)
    dead = _wmean((np.abs(uz_e) < dead_lim).astype(float), we)

    frac_e = (r_e - hub_r) / max(tip_r - hub_r, 1e-12)
    tip_sel = frac_e >= 1.0 - TIP_BAND_FRAC
    tip_ratio = (_wmean(uz_e[tip_sel], we[tip_sel]) / mean_uz
                 if np.any(tip_sel) and mean_uz != 0 else float("nan"))

    # Useful push: static + forward dynamic pressure. Swirl energy is the separate 'wasted spin'
    # row; counting it here made a swirly fan (Stock) look stronger than a better one (t9005).
    p0 = p + 0.5 * uz * uz
    b_ex = _band_index(r_e, hub_r, tip_r)
    b_in = _band_index(r[inn], hub_r, tip_r)
    p0_e, w_in, p0_in = p0[ex], w[inn], p0[inn]
    bands = []
    for i in range(N_BANDS):
        se, si = b_ex == i, b_in == i
        if not np.any(se) or not np.any(si):
            bands.append(float("nan"))
            continue
        bands.append(RHO_AMCA * (_wmean(p0_e[se], we[se]) - _wmean(p0_in[si], w_in[si])))

    swl = None
    if s.k is not None and s.omega is not None:
        rot = (np.abs(pts[:, 2] - z_fan) <= NOISE_Z_FRAC * tip_r) & (r <= NOISE_R_FRAC * tip_r)
        power = float(np.sum(noise_density(s.k[rot], s.omega[rot]) * w[rot]))
        swl = float(sound_power_level(power)) if power > 0 else None

    return FlowMetrics(
        backflow_frac=float(backflow), net_reversed=bool(mean_uz < 0), band_dp0_pa=bands,
        swirl_frac=swirl, dead_frac=float(dead), tip_band_uz_ratio=float(tip_ratio),
        noise_swl_db=swl, mean_uz_exit=float(mean_uz))
