"""Cantilever first-bending vs blade-passing frequency (cheap resonance gate).

Treat the blade as a uniform rectangular cantilever of mid-span chord × thickness. This is not
flutter derivatives or FEA — it only catches TPU / extreme RPM / long-span pathologies.

Wide plates (span/chord ≲ :data:`~fansim.structural.deflection.BEAM_ASPECT_MIN`) stamp
``beam_regime_ok=False`` without failing the resonance gate alone (§19.18).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from fansim.geometry.blade import BladeParams
from fansim.manufacturability.materials import MATERIALS
from fansim.structural.deflection import (
    BEAM_ASPECT_MIN,
    _fdm_e_factor,
    _validate_radii,
    beam_aspect_ratio,
)
from fansim.structural.stress import MM_TO_M

CANTILEVER_LAMBDA = 1.875104
MIN_F1_OVER_BPF = 1.2


@dataclass
class FlutterReport:
    ok: bool
    f1_hz: float
    rpm_hz: float
    bpf_hz: float
    margin: float
    reason: str = ""
    beam_aspect: float = float("inf")
    beam_regime_ok: bool = True


def _mid_station(params: BladeParams):
    if not params.stations:
        raise ValueError("BladeParams.stations must not be empty")
    return min(params.stations, key=lambda s: abs(float(s.r_frac) - 0.5))


def first_bending_hz(params: BladeParams, material: str = "PETG") -> float:
    mat = MATERIALS[material]
    hub, tip = _validate_radii(params)
    span_m = max(tip - hub, 1.0) * MM_TO_M
    st = _mid_station(params)
    chord_raw = float(st.chord)
    thick_raw = float(st.thickness)
    if not (math.isfinite(chord_raw) and math.isfinite(thick_raw)):
        raise ValueError(
            f"station chord and thickness must be finite, got chord={st.chord!r}, thickness={st.thickness!r}"
        )
    chord_m = max(chord_raw, 1e-3) * MM_TO_M
    thick_m = max(thick_raw, 1e-4) * chord_m
    area = chord_m * thick_m
    inertia = chord_m * thick_m ** 3 / 12.0
    mu = mat.density_kg_m3 * area
    e = mat.youngs_modulus_gpa * 1e9 * _fdm_e_factor(material)
    return float(
        (CANTILEVER_LAMBDA ** 2) / (2.0 * math.pi) * math.sqrt(e * inertia / (mu * span_m ** 4))
    )


def max_blades_for_margin(
    f1_hz: float,
    rpm: float,
    *,
    min_margin: float = MIN_F1_OVER_BPF,
) -> int:
    """Largest blade count that still clears ``f1 / BPF ≥ min_margin`` at ``rpm``."""
    f1 = float(f1_hz)
    rpm_f = float(rpm)
    margin_f = float(min_margin)
    if not (math.isfinite(f1) and math.isfinite(rpm_f)):
        raise ValueError(f"f1_hz and rpm must be finite, got f1_hz={f1_hz!r}, rpm={rpm!r}")
    if not (math.isfinite(margin_f) and margin_f > 0.0):
        raise ValueError(f"min_margin must be finite and > 0, got {min_margin!r}")
    if rpm_f <= 0.0 or f1 <= 0.0:
        return 0
    max_bpf = f1 / margin_f
    return max(0, math.floor(max_bpf * 60.0 / rpm_f))


def resonance_user_message(
    *,
    f1_hz: float,
    bpf_hz: float,
    margin: float,
    min_margin: float,
    material: str,
    n_blades: int,
    rpm: float,
) -> str:
    """Plain-language reject text for Assess / Optimize / CLI."""
    need_f1 = float(bpf_hz) * float(min_margin)
    max_n = max_blades_for_margin(f1_hz, rpm, min_margin=min_margin)
    if max_n >= 2 and max_n < int(n_blades):
        blade_fix = f"drop Blades to <={max_n}"
    elif max_n < 2:
        blade_fix = "use fewer blades and/or a much stiffer / shorter blade"
    else:
        blade_fix = "keep this blade count only if you stiffen the blade a lot"

    return (
        f"blade vibration risk ({material}): the blade's natural bend frequency "
        f"({f1_hz:.0f} Hz) is too close to the blade-pass tone "
        f"(BPF {bpf_hz:.0f} Hz = {n_blades} blades x {rpm:.0f} RPM). "
        f"Need bend >= {min_margin:.1f}x BPF (>= {need_f1:.0f} Hz); yours is only "
        f"{margin:.2f}x. Fix: {blade_fix}, or raise Thickness mid (stiffer), "
        f"or shorten Tip radius (shorter span)."
    )


def flutter_report(
    params: BladeParams,
    material: str = "PETG",
    min_margin: float = MIN_F1_OVER_BPF,
) -> FlutterReport:
    rpm = float(params.rpm)
    n_blades = int(params.n_blades)
    margin_f = float(min_margin)
    if not (math.isfinite(rpm) and rpm >= 0.0):
        raise ValueError(f"rpm must be finite and >= 0, got {params.rpm!r}")
    if n_blades < 0:
        raise ValueError(f"n_blades must be >= 0, got {params.n_blades!r}")
    if not (math.isfinite(margin_f) and margin_f > 0.0):
        raise ValueError(f"min_margin must be finite and > 0, got {min_margin!r}")
    f1 = first_bending_hz(params, material)
    rpm_hz = rpm / 60.0
    bpf = n_blades * rpm_hz
    margin = float(f1 / bpf) if bpf > 1e-9 else float("inf")
    ok = margin >= margin_f
    aspect = beam_aspect_ratio(params, station="mid")
    regime = aspect >= BEAM_ASPECT_MIN
    reason = ""
    if not ok:
        reason = resonance_user_message(
            f1_hz=f1,
            bpf_hz=bpf,
            margin=margin,
            min_margin=margin_f,
            material=material,
            n_blades=n_blades,
            rpm=rpm,
        )
    elif not regime:
        reason = (
            f"WARN beam regime: mid span/chord={aspect:.2f} < {BEAM_ASPECT_MIN} "
            f"(wide plate; f1 is order-of-magnitude only — §19.18)"
        )
    return FlutterReport(ok, f1, rpm_hz, bpf, margin, reason, aspect, regime)
