"""Cheap aeroacoustic noise proxies from RANS fields (screening tier).

The GPU LBM control-volume dipole (scripts/evaluate_noise.py) is accurate but expensive (~2.5 min
each), so it is finalist-only. These proxies estimate noise from a steady RANS solution that already
exists for every candidate -- effectively free -- so noise can screen the whole search. See
docs/bibliography.md sections 1-2 (Proudman 1952, Curle 1955).
"""

from fansim.acoustics.farfield import (
    a_weighting_db,
    blade_pass_frequency,
    noise_from_cv_force,
)
from fansim.acoustics.loading import (
    calibrate as calibrate_loading_proxy,
)
from fansim.acoustics.loading import (
    loading_noise_proxy,
    loading_proxy_from_rans,
    loading_proxy_operating,
)
from fansim.acoustics.proxies import (
    curle_dpdt_estimate,
    curle_surface_swl,
    epsilon_from_komega,
    proudman_power_density,
    proudman_swl,
    sound_power_level,
    turbulent_mach,
)
from fansim.acoustics.tonal import (
    blade_passing_modes,
    peak_tone_amplitude,
    peak_tone_reduction_db,
    tonal_peak_ratio,
)

__all__ = [
    "a_weighting_db",
    "blade_pass_frequency",
    # tonal analysis from spacing pattern (compute-free)
    "blade_passing_modes",
    "calibrate_loading_proxy",
    "curle_dpdt_estimate",
    "curle_surface_swl",
    # RANS proxies (screening tier)
    "epsilon_from_komega",
    # calibrated cheap LOADING-noise proxy (better than Proudman for dipole/loading noise)
    "loading_noise_proxy",
    "loading_proxy_from_rans",
    "loading_proxy_operating",
    # LBM far-field reduction (finalist tier)
    "noise_from_cv_force",
    "peak_tone_amplitude",
    "peak_tone_reduction_db",
    "proudman_power_density",
    "proudman_swl",
    "sound_power_level",
    "tonal_peak_ratio",
    "turbulent_mach",
]
