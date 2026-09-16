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
from fansim.acoustics.proxies import (
    curle_dpdt_estimate,
    curle_surface_swl,
    epsilon_from_komega,
    proudman_power_density,
    proudman_swl,
    sound_power_level,
    turbulent_mach,
)
from fansim.acoustics.loading import (
    calibrate as calibrate_loading_proxy,
    loading_noise_proxy,
    loading_proxy_from_rans,
)
from fansim.acoustics.tonal import (
    blade_passing_modes,
    peak_tone_amplitude,
    peak_tone_reduction_db,
    tonal_peak_ratio,
)

__all__ = [
    # RANS proxies (screening tier)
    "epsilon_from_komega",
    "turbulent_mach",
    "proudman_power_density",
    "proudman_swl",
    "curle_surface_swl",
    "curle_dpdt_estimate",
    "sound_power_level",
    # LBM far-field reduction (finalist tier)
    "noise_from_cv_force",
    "a_weighting_db",
    "blade_pass_frequency",
    # tonal analysis from spacing pattern (compute-free)
    "blade_passing_modes",
    "peak_tone_amplitude",
    "tonal_peak_ratio",
    "peak_tone_reduction_db",
    # calibrated cheap LOADING-noise proxy (better than Proudman for dipole/loading noise)
    "loading_noise_proxy",
    "loading_proxy_from_rans",
    "calibrate_loading_proxy",
]
