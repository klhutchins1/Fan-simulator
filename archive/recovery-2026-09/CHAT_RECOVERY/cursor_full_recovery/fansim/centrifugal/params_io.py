"""Serialize MixedFlowParams for cockpit / isolated workers."""

from __future__ import annotations

from fansim.centrifugal.geometry import MixedFlowParams

# Core cockpit knobs (camber/thickness stay at dataclass defaults).
CORE_FLAT_KEYS = (
    "n_blades",
    "r_eye_mm",
    "r_back_mm",
    "r_tip_mm",
    "z_span_mm",
    "chord_mm",
    "stagger_deg",
)


def mixed_params_from_flat(flat: dict | None = None) -> MixedFlowParams:
    """Build ``MixedFlowParams`` from a partial flat dict (defaults fill the rest).

    Raises ``ValueError`` from ``MixedFlowParams.__post_init__`` when eye/back/mount
    constraints fail.
    """
    flat = flat or {}
    kw: dict = {}
    for key in CORE_FLAT_KEYS:
        if key not in flat:
            continue
        if key == "n_blades":
            kw[key] = int(flat[key])
        else:
            kw[key] = float(flat[key])
    return MixedFlowParams(**kw)


def mixed_flat_from_params(params: MixedFlowParams) -> dict:
    """Core fields only (for isolated job payloads)."""
    return {k: getattr(params, k) for k in CORE_FLAT_KEYS}
