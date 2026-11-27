"""Prop spin/sign + datasheet thrust comparison (roadmap §4.3).

Drone convention: report **positive** static thrust in grams. The prop is oriented (via
``fansim.propeller.direction``) so its designed rotation pushes air toward +Z, so the fluid
force on it is Fz < 0 and thrust = -Fz. A wrong sign is reported (``thrust_sign_ok``), never
hidden by flipping spin. Magnitude is then compared to ``PropSpec.ref_thrust_g`` with RPM²
affinity scaling.
"""

from __future__ import annotations

from typing import Any


def affinity_thrust_g(ref_thrust_g: float, ref_rpm: float, rpm: float) -> float:
    """Scale datasheet static thrust to ``rpm`` via T ∝ n²."""
    ref = float(ref_rpm)
    if ref <= 0.0:
        return float(ref_thrust_g)
    return float(ref_thrust_g) * (float(rpm) / ref) ** 2


def affinity_power_w(ref_power_w: float, ref_rpm: float, rpm: float) -> float:
    """Scale datasheet shaft power via P ∝ n³."""
    ref = float(ref_rpm)
    if ref <= 0.0:
        return float(ref_power_w)
    return float(ref_power_w) * (float(rpm) / ref) ** 3


def normalize_metrics_sign(metrics: dict[str, Any], *, spin: int) -> dict[str, Any]:
    """Report thrust along the designed pumping direction; flag (never flip) a wrong sign.

    The prop is oriented so its designed rotation pushes air toward +Z (fansim.propeller.direction),
    so the fluid force on it is Fz < 0 and thrust = -Fz. A positive Fz means the prop pushed air the
    wrong way: that is reported, not hidden by flipping spin.
    """
    out = dict(metrics)
    raw = float(out.get("thrust_n", 0.0))
    out["thrust_n_raw"] = raw
    out["spin"] = int(spin)
    out["thrust_n"] = -raw
    out["thrust_g"] = -raw / 9.80665 * 1000.0
    out["thrust_sign_ok"] = raw < 0.0
    if raw >= 0.0:
        out["thrust_sign_error"] = (
            f"Fz={raw:+.4g} N pushes the prop toward -Z: air went the wrong way for spin {int(spin):+d}")
    return out


def flag_direction_suspect(result: dict[str, Any]) -> dict[str, Any]:
    """Flag a prop CFD result whose direction could not be confirmed AND whose thrust sign is wrong.

    ``direction_crosscheck`` (see :func:`fansim.propeller.direction.resolve_prop_direction`) is
    None for a manual override, or a dict with ``"verdict"`` in ``{"CONCLUSIVE", "INCONCLUSIVE"}``
    for the mesh-only geometry proof run as a cross-check on builder geometry. A CONCLUSIVE
    cross-check that disagreed with the builder convention would already have raised (see
    ``resolve_prop_direction``), so a wrong thrust sign together with a CONCLUSIVE cross-check is
    something else (e.g. a genuinely draggy high-advance-ratio point), not a suspect direction.

    But an INCONCLUSIVE cross-check combined with a wrong CFD thrust sign (``thrust_sign_ok`` is
    False) means neither independent check confirmed this design spins/pumps the way it's
    supposed to -- that combination is flagged as ``direction_suspect`` with an explanatory
    ``direction_warning``, so a silently backwards prop doesn't slide through unnoticed.
    """
    out = dict(result)
    crosscheck = out.get("direction_crosscheck")
    inconclusive = isinstance(crosscheck, dict) and crosscheck.get("verdict") == "INCONCLUSIVE"
    if inconclusive and out.get("thrust_sign_ok") is False:
        out["direction_suspect"] = True
        out["direction_warning"] = (
            "direction cross-check was INCONCLUSIVE and the CFD thrust sign is wrong -- this "
            "design may be spinning/oriented backwards; verify the geometry before trusting "
            "this result"
        )
    return out


def datasheet_compare(
    *,
    thrust_g: float,
    power_w: float | None = None,
    rpm: float,
    spec,
) -> dict[str, Any]:
    """Compare a result to ``spec.ref_*`` at affinity-scaled RPM. Honest ratios only."""
    ref_t = getattr(spec, "ref_thrust_g", None)
    ref_rpm = getattr(spec, "ref_rpm", None) or getattr(spec, "rpm_max", None)
    ref_p = getattr(spec, "ref_power_w", None)
    out: dict[str, Any] = {
        "rpm": float(rpm),
        "thrust_g": float(thrust_g),
        "ref_thrust_g": None if ref_t is None else float(ref_t),
        "ref_rpm": None if ref_rpm is None else float(ref_rpm),
        "thrust_ref_scaled_g": None,
        "thrust_ratio": None,
        "power_w": None if power_w is None else float(power_w),
        "power_ref_scaled_w": None,
        "power_ratio": None,
        "within_2x": None,
    }
    if ref_t is not None and ref_rpm is not None:
        scaled = affinity_thrust_g(float(ref_t), float(ref_rpm), float(rpm))
        out["thrust_ref_scaled_g"] = scaled
        ratio = float(thrust_g) / scaled if scaled > 0 else None
        out["thrust_ratio"] = ratio
        out["within_2x"] = bool(ratio is not None and 0.5 <= ratio <= 2.0)
    if power_w is not None and ref_p is not None and ref_rpm is not None:
        p_scaled = affinity_power_w(float(ref_p), float(ref_rpm), float(rpm))
        out["power_ref_scaled_w"] = p_scaled
        out["power_ratio"] = float(power_w) / p_scaled if p_scaled > 0 else None
    return out


def bemt_datasheet_report(spec, *, rpm: float | None = None) -> dict[str, Any]:
    """Instant BEMT vs datasheet at ``rpm`` (default ``ref_rpm`` or ``rpm_max``)."""
    from fansim.propeller.bemt import analyze
    from fansim.propeller.geometry import prop_blade_params

    rpm_f = float(
        rpm
        if rpm is not None
        else (getattr(spec, "ref_rpm", None) or spec.rpm_max)
    )
    perf = analyze(prop_blade_params(spec), rpm=rpm_f)
    cmp_ = datasheet_compare(
        thrust_g=perf.thrust_g, power_w=perf.power_w, rpm=rpm_f, spec=spec,
    )
    return {
        "source": "bemt",
        "rpm": rpm_f,
        "thrust_g": perf.thrust_g,
        "power_w": perf.power_w,
        "figure_of_merit": perf.figure_of_merit,
        "datasheet": cmp_,
    }
