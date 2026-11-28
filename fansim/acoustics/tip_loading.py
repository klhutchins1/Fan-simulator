"""Mesh-robust relative noise hint from tip speed and airflow (roadmap 27.3c).

Proudman SWL on the Assess mesh moved ~36 dB on the same Stock fan (27.3b). This ranking number
uses only U_tip and free-air CFM, so it cannot see near-blade turbulence or pressure loading ΔP.
Not calibrated dB(A), and never judged in ``flow_verdicts`` (``NOISE_JUDGED = False``, R0.4):
- At fixed geometry (CFM ∝ U_tip), ``55 log10(U_tip) + 10 log10(CFM)`` scales as U_tip^6.5 rather
  than pure U^5–U^6 dipole scaling and omits ΔP (cf. Madison/Graham specific sound power; #125).
- At fixed RPM and tip diameter, U_tip is constant so the hint reduces to ``const + 10 log10(CFM)``,
  strictly ordering higher-CFM designs louder regardless of loading or stall.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

DIPOLE_EXPONENT = 55.0  # middle of the 50–60 Ffowcs Williams / Lighthill dipole scale


def tip_speed_ms(rpm: float, tip_radius_mm: float) -> float:
    rpm_f = float(rpm)
    r_mm = float(tip_radius_mm)
    if not (math.isfinite(rpm_f) and rpm_f >= 0.0):
        raise ValueError(f"rpm must be finite and >= 0, got {rpm!r}")
    if not (math.isfinite(r_mm) and r_mm >= 0.0):
        raise ValueError(f"tip_radius_mm must be finite and >= 0, got {tip_radius_mm!r}")
    return (rpm_f * 2.0 * math.pi / 60.0) * (r_mm / 1000.0)


def tip_loading_swl_db(tip_speed_ms_: float, cfm_free: float) -> float:
    """Relative ranking SWL [dB-ish]. Lower is quieter. Compare designs, don't claim a mic."""
    u = float(tip_speed_ms_)
    cfm = float(cfm_free)
    if not (math.isfinite(u) and math.isfinite(cfm)):
        raise ValueError(
            f"tip_speed_ms_ and cfm_free must be finite, got {tip_speed_ms_!r}, {cfm_free!r}"
        )
    return (
        DIPOLE_EXPONENT * math.log10(max(u, 1.0))
        + 10.0 * math.log10(max(cfm, 0.1))
    )


def noise_hint_from_case(case_dir) -> float | None:
    """L from a saved Assess case, or None if CFM / geometry is missing."""
    case_dir = Path(case_dir)
    try:
        raw = json.loads((case_dir / "_eval_result.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    cfm = raw.get("cfm_free")
    if cfm is None:
        return None
    rpm = raw.get("actual_rpm")
    if rpm is None:
        rpm = (raw.get("raw") or {}).get("actual_rpm")
    from fansim.cfd.spanwise import load_case_radii_omega

    try:
        _hub, tip_m, omega = load_case_radii_omega(case_dir)
        if rpm is None:
            rpm = abs(float(omega)) * 60.0 / (2.0 * math.pi)
        return tip_loading_swl_db(tip_speed_ms(float(rpm), float(tip_m) * 1000.0), float(cfm))
    except (OSError, TypeError, ValueError):
        return None
