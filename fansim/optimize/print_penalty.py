"""Sim→print knockdown: report printed CFM/eta from smooth-wall RANS (roadmap §7.6)."""

from __future__ import annotations

PRINT_K_CFM = 0.95    # printed free/load CFM / smooth-wall CFM
PRINT_K_ETA = 0.92    # printed efficiency / smooth-wall efficiency


def apply_print_penalty(
    cfm_free: float,
    cfm_load: float,
    efficiency: float,
    enabled: bool = True,
) -> tuple[float, float, float, dict]:
    """Scale reported objectives. Returns (cfm_free, cfm_load, efficiency, raw stamps)."""
    if not enabled:
        return float(cfm_free), float(cfm_load), float(efficiency), {}
    stamps = {
        "cfm_free_cfd": float(cfm_free),
        "cfm_load_cfd": float(cfm_load),
        "efficiency_cfd": float(efficiency),
        "print_k_cfm": PRINT_K_CFM,
        "print_k_eta": PRINT_K_ETA,
    }
    return (
        float(cfm_free) * PRINT_K_CFM,
        float(cfm_load) * PRINT_K_CFM,
        float(efficiency) * PRINT_K_ETA,
        stamps,
    )


# --- spliced from transcript edit-history (recovery 2026-09-12) ---
PRINT_K_ETA_THICK = 0.96  # thick-tip milder η knockdown (robustness lever)


# --- spliced print_k_eta_for_thickness (recovery) ---
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


# --- spliced tip_section_thickness (recovery) ---
def tip_section_thickness(params) -> float:
    """Tip-station thickness fraction (chord units) from ``BladeParams.stations``."""
    st = max(params.stations, key=lambda s: float(s.r_frac))
    return float(st.thickness)
