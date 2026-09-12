"""Map WindTurbineParams → shared BladeParams loft (mm) and export STL."""

from __future__ import annotations

from pathlib import Path

from fansim.geometry.blade import BladeParams, RadialStation
from fansim.wind_turbine.params import WindTurbineParams

MM_PER_M = 1000.0


def blade_params_from_wind(params: WindTurbineParams) -> BladeParams:
    """Turbine-ish twist: steeper stagger at the root than at the tip."""
    tip_r_mm = float(params.diameter_m) * MM_PER_M / 2.0
    hub_r_mm = float(params.hub_radius_m) * MM_PER_M
    chord_tip = float(params.chord_tip_frac) * tip_r_mm
    chord_root = chord_tip * 1.6
    chord_mid = chord_tip * 1.25
    # Tip pitch is the scaffold knob; root is coarser (typical HAWT geometric twist).
    tip_stag = float(params.pitch_deg)
    root_stag = tip_stag + 18.0
    mid_stag = tip_stag + 8.0
    stations = [
        RadialStation(0.0, chord_root, root_stag, thickness=0.12, max_camber=0.03),
        RadialStation(0.5, chord_mid, mid_stag, thickness=0.10, max_camber=0.035),
        RadialStation(1.0, chord_tip, tip_stag, thickness=0.08, max_camber=0.03),
    ]
    return BladeParams(
        n_blades=int(params.n_blades),
        hub_radius=hub_r_mm,
        tip_radius=tip_r_mm,
        root_embed=2.0,
        hub_axial_margin=2.0,
        stations=stations,
        n_span=12,
        n_chord=48,
    )


def export_wind_turbine_stl(params: WindTurbineParams, out_path: str | Path) -> Path:
    from fansim.geometry import build_impeller, export_stl

    out_path = Path(out_path)
    export_stl(
        build_impeller(blade_params_from_wind(params)),
        out_path,
        tolerance=0.05,
        angular_tolerance=0.2,
    )
    return out_path
