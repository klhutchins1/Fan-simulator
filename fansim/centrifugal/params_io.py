"""Serialize MixedFlowParams for cockpit / isolated workers."""

from __future__ import annotations

from fansim.centrifugal.geometry import MixedFlowParams

# Core cockpit knobs + section aero + span planform (§14.3 / §14.3b).
CORE_FLAT_KEYS = (
    "n_blades",
    "r_eye_mm",
    "r_back_mm",
    "r_tip_mm",
    "z_span_mm",
    "chord_mm",
    "stagger_deg",
    "chord_root",
    "chord_tip",
    "stagger_root",
    "stagger_tip",
    "thickness",
    "max_camber",
    "camber_pos",
)


def mixed_params_from_flat(flat: dict | None = None) -> MixedFlowParams:
    """Build ``MixedFlowParams`` from a partial flat dict (defaults fill the rest).

    Legacy flats with only ``chord_mm`` / ``stagger_deg`` broadcast to root/mid/tip.
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

    # Broadcast legacy single chord/stagger onto the span when R/T omitted.
    if "chord_mm" in kw:
        mid = float(kw["chord_mm"])
        kw.setdefault("chord_root", mid)
        kw.setdefault("chord_tip", mid)
    if "stagger_deg" in kw:
        mid_s = float(kw["stagger_deg"])
        kw.setdefault("stagger_root", mid_s)
        kw.setdefault("stagger_tip", mid_s)
    # If only root/tip given without mid, mid stays dataclass default unless chord_mm set.
    if "chord_root" in kw and "chord_tip" in kw and "chord_mm" not in kw:
        kw["chord_mm"] = 0.5 * (float(kw["chord_root"]) + float(kw["chord_tip"]))
    if "stagger_root" in kw and "stagger_tip" in kw and "stagger_deg" not in kw:
        kw["stagger_deg"] = 0.5 * (float(kw["stagger_root"]) + float(kw["stagger_tip"]))

    return MixedFlowParams(**kw)


def mixed_flat_from_params(params: MixedFlowParams) -> dict:
    """Core fields only (for isolated job payloads)."""
    return {k: getattr(params, k) for k in CORE_FLAT_KEYS}
