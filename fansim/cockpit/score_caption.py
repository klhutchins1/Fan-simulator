"""Human-readable Assess/optimizer score provenance (hose, duct, print knockdown)."""

from __future__ import annotations

from fansim.catalog import curve_provenance


def score_caption(extra: dict) -> str:
    """One line: hose / duct / print-k. Omit clauses whose keys are missing."""
    extra = extra or {}
    parts: list[str] = []
    load_pa = extra.get("load_pa")
    preset = extra.get("preset")
    if load_pa is not None:
        if preset and preset != "legacy":
            parts.append(f"hose: {preset} {float(load_pa):g} Pa @ 50 CFM")
        else:
            parts.append(f"hose: {float(load_pa):g} Pa @ 50 CFM")
    duct = extra.get("duct")
    if duct:
        parts.append(f"{duct} duct")
    k_cfm = extra.get("print_k_cfm")
    k_eta = extra.get("print_k_eta")
    if k_cfm is not None and k_eta is not None:
        parts.append(f"printed ×{float(k_cfm):g} / ×{float(k_eta):g}")
    op_cfd = extra.get("op_cfd")
    if op_cfd:
        parts.append(f"op CFD: {op_cfd}")
    if extra.get("beam_regime_ok") is False:
        aspect = extra.get("beam_aspect")
        if aspect is not None:
            parts.append(f"WARN beam aspect {float(aspect):.2f} (plate-like §19.18)")
        else:
            parts.append("WARN beam regime (plate-like §19.18)")
    return " · ".join(parts)


def stamp_score_extra(
    extra: dict, raw: dict | None, *, load_pa: float, preset: str,
    refine_op: bool = False,
) -> dict:
    """Copy curve / duct / print-k stamps plus the hose used for this Assess."""
    extra.update(curve_provenance(raw))
    extra["load_pa"] = float(load_pa)
    extra["preset"] = preset
    extra["refine_op"] = bool(refine_op)
    raw = raw or {}
    if raw.get("duct"):
        extra["duct"] = raw["duct"]
    for key in ("print_k_cfm", "print_k_eta", "surf_max"):
        if raw.get(key) is not None:
            extra[key] = raw[key]
    for key in ("beam_regime_ok", "beam_aspect", "beam_regime_warn", "f1_bpf_margin"):
        if raw.get(key) is not None:
            extra[key] = raw[key]
    if refine_op:
        if raw.get("op_cfd") is not None:
            extra["op_cfd"] = raw["op_cfd"]
        if raw.get("cfm_op_alg") is not None:
            extra["cfm_op_alg"] = raw["cfm_op_alg"]
    else:
        extra.pop("op_cfd", None)
        extra.pop("cfm_op_alg", None)
    return extra
