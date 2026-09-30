"""CROR relative noise proxies (roadmap §4.2) — ranking only, not mic-calibrated."""

from __future__ import annotations

import math

import numpy as np

from fansim.cror.geometry import CrorParams
from fansim.propeller.bemt import analyze
from fansim.propeller.noise import estimate_prop_noise


def estimate_cror_noise(params: CrorParams, rpm: float) -> dict:
    """Relative dual-rotor noise: combine front/rear tip-speed proxies (energy sum)."""
    front_perf = analyze(params.front, rpm=rpm)
    rear_perf = analyze(params.rear, rpm=rpm)
    nf = estimate_prop_noise(params.front, rpm, front_perf)
    nr = estimate_prop_noise(params.rear, rpm, rear_perf)
    # Incoherent sum of linear intensities from relative dB scores.
    i_f = 10.0 ** (float(nf["rel_dba"]) / 10.0)
    i_r = 10.0 ** (float(nr["rel_dba"]) / 10.0)
    rel = 10.0 * math.log10(i_f + i_r)
    # Rear stagger is signed for opposite spin; BEMT CT sign follows that convention.
    # Noise ranking uses |thrust| (delivery magnitude), not the signed prop convention.
    return {
        "rel_dba": round(rel, 1),
        "front_rel_dba": nf["rel_dba"],
        "rear_rel_dba": nr["rel_dba"],
        "front_bpf_hz": nf["bpf_hz"],
        "rear_bpf_hz": nr["bpf_hz"],
        "tip_mach_front": nf["tip_mach"],
        "tip_mach_rear": nr["tip_mach"],
        "thrust_g": abs(front_perf.thrust_g) + abs(rear_perf.thrust_g),
        "analogy": "cror_tip_speed_proxy",
    }


def cror_fwh_from_proxy(params: CrorParams, rpm: float, *, r_obs: float = 1.0) -> dict:
    """Synthetic dual-BPF FW-H: sum front+rear Fz tones at each rotor BPF."""
    from fansim.acoustics.fwh import noise_from_compact_force

    front_perf = analyze(params.front, rpm=rpm)
    rear_perf = analyze(params.rear, rpm=rpm)
    Tf = max(abs(float(front_perf.thrust_n)), 1e-6)
    Tr = max(abs(float(rear_perf.thrust_n)), 1e-6)
    n_f = int(params.front.n_blades)
    n_r = int(params.rear.n_blades)
    omega_rev = float(rpm) / 60.0
    bpf_f = n_f * omega_rev
    bpf_r = n_r * omega_rev
    n_revs, spr = 8, 256  # fs = rpm/60*spr; keep Nyquist above FW-H 2500 Hz cutoff at ~2k RPM
    n = n_revs * spr
    t = np.arange(n, dtype=float) / (omega_rev * spr)
    load_frac = 0.12
    fz = (
        Tf + load_frac * Tf * np.sin(2.0 * math.pi * bpf_f * t)
        + Tr + load_frac * Tr * np.sin(2.0 * math.pi * bpf_r * t)
    )
    F = np.column_stack([np.zeros(n), np.zeros(n), fz])
    # Use front blade count for tone metric helpers; stamp both BPFs.
    out = noise_from_compact_force(
        t, F, n_blades=n_f, rpm=float(rpm), r_obs=float(r_obs),
    )
    out["analogy"] = "fwh_cror_synthetic"
    out["bpf_front_hz"] = round(bpf_f, 1)
    out["bpf_rear_hz"] = round(bpf_r, 1)
    out["thrust_n_front"] = round(Tf, 4)
    out["thrust_n_rear"] = round(Tr, 4)
    return out
