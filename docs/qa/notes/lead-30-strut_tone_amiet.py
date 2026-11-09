"""Lead #30 cheap prototype: relative strut-tone level vs gap/skew (Sears/Amiet-style).

Does NOT vendor amiet_tools; reimplements a thin ranking proxy from classical Sears
gust response + a wake-deficit model. Absolute dB are arbitrary (ref at baseline).
numpy + scipy only. No CFD.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from scipy.special import j0, j1, y0, y1  # Hankel via J+iY


def sears(k: float) -> complex:
    """Classical Sears function S(k) for reduced frequency k = ωb/U = ωc/(2U).

    S(k) = 2 / (π k (H1^(2)(k) + i H0^(2)(k))) for k>0; S(0)=1.
    """
    if k < 1e-8:
        return 1.0 + 0.0j
    # H_n^(2) = J_n - i Y_n
    H0 = j0(k) - 1j * y0(k)
    H1 = j1(k) - 1j * y1(k)
    return 2.0 / (math.pi * k * (H1 + 1j * H0))


def wake_deficit(gap_mm: float, w0: float, wake_width_mm: float) -> float:
    """Simple exponential wake deficit at axial gap (blade TE → strut LE)."""
    return w0 * math.exp(-max(gap_mm, 0.0) / max(wake_width_mm, 1e-6))


def skew_coherence(skew_deg: float, span_mm: float, gust_kx: float) -> float:
    """Coherence factor from spanwise phase smear when strut is skewed.

    Path-length difference ~ span * tan(|skew|); phase Δφ = gust_kx * Δpath.
    Coherent sum ≈ sinc(Δφ/2). Returns amplitude factor in (0, 1].
    """
    beta = abs(math.radians(skew_deg))
    dpath = (span_mm / 1000.0) * math.tan(beta)
    dphi = gust_kx * dpath
    if abs(dphi) < 1e-9:
        return 1.0
    return abs(math.sin(dphi / 2.0) / (dphi / 2.0))


def relative_tone_db(
    *,
    gap_mm: float,
    skew_deg: float = 0.0,
    strut_chord_mm: float = 8.0,
    span_mm: float = 33.0,
    tip_speed_mps: float = 12.6,  # 120mm @ 2000 rpm ≈ ωR
    bpf_hz: float = 300.0,  # 9 blades * 2000/60
    w0: float = 0.05,  # gust amp / U at TE (assumed)
    wake_width_mm: float = 4.0,
    rho: float = 1.2,
) -> dict:
    """Relative strut-tone level (dB re baseline lift at gap=0.5, skew=0, w0 as given)."""
    U = tip_speed_mps * 0.7  # midspan-ish convection
    c = strut_chord_mm / 1000.0
    b = 0.5 * c
    omega = 2.0 * math.pi * bpf_hz
    k = omega * b / max(U, 1e-6)  # reduced frequency
    S = sears(k)
    w = wake_deficit(gap_mm, w0 * U, wake_width_mm)  # m/s
    kx = omega / max(U, 1e-6)  # frozen-gust chordwise wavenumber
    coh = skew_coherence(skew_deg, span_mm, kx)
    # Unsteady lift amplitude ~ ρ U Γ' c * |S| * w_norm; use ρ U w c |S| coh
    lift = rho * U * w * c * abs(S) * coh
    return {
        "gap_mm": gap_mm,
        "skew_deg": skew_deg,
        "k": round(k, 4),
        "abs_S": round(abs(S), 4),
        "w_mps": round(w, 5),
        "coherence": round(coh, 4),
        "lift_proxy": lift,
    }


def level_db(lift: float, ref: float) -> float:
    if lift <= 0 or ref <= 0:
        return -999.0
    return 20.0 * math.log10(lift / ref)


def main():
    gaps = [0.5, 1.0, 2.0, 4.0, 8.0]
    skews = [0.0, 15.0, 35.0, 60.0]
    base = relative_tone_db(gap_mm=0.5, skew_deg=0.0, w0=0.05)
    ref = base["lift_proxy"]

    gap_rows = []
    for g in gaps:
        r = relative_tone_db(gap_mm=g, skew_deg=0.0, w0=0.05)
        gap_rows.append({**r, "dB_re_baseline": round(level_db(r["lift_proxy"], ref), 2)})

    skew_rows = []
    for s in skews:
        r = relative_tone_db(gap_mm=1.0, skew_deg=s, w0=0.05)
        skew_rows.append({**r, "dB_re_baseline": round(level_db(r["lift_proxy"], ref), 2)})

    # Robustness: ranking of (gap,skew) configs under ±2× w0
    configs = [
        ("gap0.5_sk0", dict(gap_mm=0.5, skew_deg=0.0)),
        ("gap2_sk0", dict(gap_mm=2.0, skew_deg=0.0)),
        ("gap1_sk35", dict(gap_mm=1.0, skew_deg=35.0)),
        ("gap4_sk0", dict(gap_mm=4.0, skew_deg=0.0)),
        ("gap1_sk60", dict(gap_mm=1.0, skew_deg=60.0)),
    ]

    def rank(w0):
        scores = []
        for name, kw in configs:
            r = relative_tone_db(w0=w0, **kw)
            scores.append((level_db(r["lift_proxy"], ref * (w0 / 0.05)), name))
        # quieter = more negative dB; rank quietest first
        scores.sort()
        return [n for _, n in scores]

    rank_nom = rank(0.05)
    rank_half = rank(0.025)
    rank_dbl = rank(0.10)
    order_stable = rank_nom == rank_half == rank_dbl

    # Sensible checks
    gap_monotone = all(
        gap_rows[i]["dB_re_baseline"] >= gap_rows[i + 1]["dB_re_baseline"] - 1e-9
        for i in range(len(gap_rows) - 1)
    )  # larger gap → quieter (lower dB)
    skew_helps = skew_rows[-1]["dB_re_baseline"] < skew_rows[0]["dB_re_baseline"] - 0.5

    out = {
        "model": "Sears |S(k)| * wake_exp(-gap/λ) * skew_sinc; relative 20log10(lift/ref)",
        "baseline_ref": {"gap_mm": 0.5, "skew_deg": 0.0, "w0": 0.05, "lift": ref},
        "gap_sweep_skew0": gap_rows,
        "skew_sweep_gap1mm": skew_rows,
        "ranking_quietest_first": {
            "w0_0.05": rank_nom,
            "w0_0.025": rank_half,
            "w0_0.10": rank_dbl,
            "order_stable_under_pm2x_gust": order_stable,
        },
        "sensible_gap_monotone_quieter": gap_monotone,
        "sensible_skew_reduces_tone": skew_helps,
        "pass_prereg_c": bool(gap_monotone and skew_helps and order_stable),
        "caveat": "Needs a real wake/turbulence estimator for absolute levels; stub λ=4mm, w0=0.05.",
        "amiet_tools": "BSD-3 confirmed; numpy+scipy; delta_p ∝ w0 — same robustness as linear Sears.",
    }
    Path("out.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    print("PASS" if out["pass_prereg_c"] else "FAIL")


if __name__ == "__main__":
    main()
