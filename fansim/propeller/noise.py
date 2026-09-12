# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""A fast, analytic RELATIVE noise proxy for propellers — the missing axis for thrust-vs-noise.

BEMT gives thrust/efficiency but no noise, so props had nothing to trade against thrust. This adds a
physically-grounded proxy for RANKING props (not a calibrated dB(A)): the dominant driver is TIP SPEED
/ Mach — self-noise scales steeply with tip speed and rises sharply once the tip goes compressible
(~Mach 0.4+, where FPV props live). A blade-LOADING term (thrust per blade) captures tonal loading
noise: more blades spread the load and run quieter per blade. Consistent coefficients make it a valid
RELATIVE metric to compare designs — the same north-star ('relative gains, not absolute') the fan uses.

Honest caveat: this is NOT a calibrated dB(A). For absolute numbers you'd need a CAA/FW-H run (or a
bench mic). It's a monotonic, physically-sensible score for trading thrust against quietness.
"""

from __future__ import annotations

import math

C_SOUND = 343.0   # m/s


def estimate_prop_noise(params, rpm: float, perf, c_sound: float = C_SOUND) -> dict:
    """Relative propeller noise proxy for RANKING. Returns rel_dba (relative, not calibrated), the tip
    Mach, blade-pass frequency, and tip speed. Drivers: tip speed (dominant), compressible tip rise
    past ~M0.4, and thrust-per-blade loading (more blades = quieter tonal)."""
    R = params.tip_radius / 1000.0                     # m
    omega = rpm * 2.0 * math.pi / 60.0                 # rad/s
    tip_speed = omega * R                              # m/s
    mach = tip_speed / c_sound
    thrust_n = max(float(perf.thrust_n), 1e-3)
    load_per_blade = thrust_n / max(int(params.n_blades), 1)

    broadband = 30.0 * math.log10(max(tip_speed, 1.0))          # tip-speed self-noise (steep)
    loading = 10.0 * math.log10(load_per_blade + 1.0)           # tonal loading, per blade
    compress = 45.0 * max(0.0, mach - 0.40) ** 1.3              # compressible tip rise past M0.4
    rel_dba = broadband + loading + compress

    return {
        "rel_dba": round(rel_dba, 1),                  # RELATIVE ranking score, not calibrated dB(A)
        "tip_mach": round(mach, 3),
        "tip_speed_ms": round(tip_speed, 1),
        "bpf_hz": round(int(params.n_blades) * rpm / 60.0, 0),
    }
