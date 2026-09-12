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
