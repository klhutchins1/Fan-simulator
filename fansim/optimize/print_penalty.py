"""Sim→print knockdown: report printed CFM/eta from smooth-wall RANS (roadmap §7.6)."""

from __future__ import annotations

PRINT_K_CFM = 0.95    # printed free/load CFM / smooth-wall CFM
PRINT_K_ETA = 0.92    # printed efficiency / smooth-wall efficiency (thin tip)
PRINT_K_ETA_THICK = 0.96  # thick-tip milder η knockdown (robustness lever)
PRINT_T_THIN = 0.04   # tip thickness ≤ this → full η knockdown
PRINT_T_THICK = 0.10  # tip thickness ≥ this → thick η knockdown


def print_k_eta_for_thickness(tip_thickness: float | None) -> float:
    """Lerp η knockdown: thin tips keep 0.92; thick tips ease toward 0.96."""
    if tip_thickness is None:
        return PRINT_K_ETA
    t = float(tip_thickness)
    if t <= PRINT_T_THIN:
        return PRINT_K_ETA
    if t >= PRINT_T_THICK:
        return PRINT_K_ETA_THICK
    frac = (t - PRINT_T_THIN) / (PRINT_T_THICK - PRINT_T_THIN)
    return PRINT_K_ETA + frac * (PRINT_K_ETA_THICK - PRINT_K_ETA)


def tip_section_thickness(params) -> float:
    """Tip-station thickness fraction (chord units) from ``BladeParams.stations``."""
    st = max(params.stations, key=lambda s: float(s.r_frac))
    return float(st.thickness)


def apply_print_penalty(
    cfm_free: float,
    cfm_load: float,
    efficiency: float,
    enabled: bool = True,
    tip_thickness: float | None = None,
    tip_deflection_mm: float | None = None,
    tip_gap_mm: float | None = None,
) -> tuple[float, float, float, dict]:
    """Scale reported objectives. Returns (cfm_free, cfm_load, efficiency, raw stamps).

    Optional ``tip_thickness`` lerps η (roadmap §7.6 stage 2). Optional tip deflection vs gap
    multiplies an FSI factor into CFM (stage 1 leftover).
    """
    if not enabled:
        return float(cfm_free), float(cfm_load), float(efficiency), {}

    k_eta = print_k_eta_for_thickness(tip_thickness)
    k_cfm = PRINT_K_CFM
    k_fsi = 1.0
    stamps: dict = {
        "cfm_free_cfd": float(cfm_free),
        "cfm_load_cfd": float(cfm_load),
        "efficiency_cfd": float(efficiency),
        "print_k_cfm": k_cfm,
        "print_k_eta": k_eta,
    }
    if tip_thickness is not None:
        stamps["print_tip_thickness"] = float(tip_thickness)

    if tip_deflection_mm is not None and tip_gap_mm is not None and float(tip_gap_mm) > 0.0:
        gap_frac = min(float(tip_deflection_mm) / float(tip_gap_mm), 1.0)
        k_fsi = max(0.90, 1.0 - 0.5 * gap_frac)
        k_cfm = PRINT_K_CFM * k_fsi
        stamps["print_k_fsi"] = k_fsi
        stamps["print_k_cfm"] = k_cfm
        stamps["tip_deflection_mm"] = float(tip_deflection_mm)
        stamps["deflection_gap_frac"] = gap_frac

    return (
        float(cfm_free) * k_cfm,
        float(cfm_load) * k_cfm,
        float(efficiency) * k_eta,
        stamps,
    )
