"""Mesh-robust relative noise hint from tip speed and airflow (roadmap 27.3c).

Proudman SWL on the Assess mesh moved ~36 dB on the same Stock fan (27.3b). This ranking number
uses only U_tip and free-air CFM, so it cannot see near-blade turbulence. Not calibrated dB(A).
"""

from __future__ import annotations

import json
import math
from pathlib import Path

DIPOLE_EXPONENT = 55.0  # middle of the 50–60 Ffowcs Williams / Lighthill dipole scale


def tip_speed_ms(rpm: float, tip_radius_mm: float) -> float:
    return (float(rpm) * 2.0 * math.pi / 60.0) * (float(tip_radius_mm) / 1000.0)


def tip_loading_swl_db(tip_speed_ms_: float, cfm_free: float) -> float:
    """Relative ranking SWL [dB-ish]. Lower is quieter. Compare designs, don't claim a mic."""
    return (
        DIPOLE_EXPONENT * math.log10(max(float(tip_speed_ms_), 1.0))
        + 10.0 * math.log10(max(float(cfm_free), 0.1))
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

    _hub, tip_m, omega = load_case_radii_omega(case_dir)
    if rpm is None:
        rpm = abs(float(omega)) * 60.0 / (2.0 * math.pi)
    try:
        return tip_loading_swl_db(tip_speed_ms(float(rpm), float(tip_m) * 1000.0), float(cfm))
    except (TypeError, ValueError):
        return None
