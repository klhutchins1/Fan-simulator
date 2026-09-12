"""Radial-discharge CFD domain for a volute blower (roadmap §4.1).

Axis = Z (impeller spin). Axial inlet from +Z into the eye; scroll collects and
discharges through the rectangular stub along +X. Extents match the sealed
casing fill (SI metres).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from fansim.cfd.domain import MM_TO_M
from fansim.volute.geometry import VoluteParams, volute_enclosure_extents_mm, volute_radii_mm

DEFAULT_VOLUTE_RPM = 3000.0


@dataclass
class VoluteDomain:
    """Hex box matched to the sealed volute enclosure fill (SI metres)."""

    xmin: float
    xmax: float
    ymin: float
    ymax: float
    zmin: float
    zmax: float
    mrf_z_min: float
    mrf_z_max: float
    mrf_radius: float
    tip_radius: float
    rpm: float
    omega_signed: float
    inlet_velocity: float  # magnitude; case writer applies (0, 0, -U) on +Z inlet
    outlet_area_m2: float
    location_in_mesh: tuple[float, float, float]

    @property
    def omega_rad_s(self) -> float:
        return abs(self.omega_signed)


def domain_for_volute(
    params: VoluteParams,
    *,
    rpm: float = DEFAULT_VOLUTE_RPM,
    spin: int = -1,
    margin_mm: float = 8.0,
    inlet_plenum_mm: float = 28.0,
    outlet_clearance_mm: float = 12.0,
    mrf_margin_mm: float = 2.0,
    inlet_velocity: float = 2.0,
) -> VoluteDomain:
    """Size the volute CFD box from geometry params (mm → m)."""
    rad = volute_radii_mm(params)
    ext = volute_enclosure_extents_mm(
        params,
        margin_mm=margin_mm,
        inlet_plenum_mm=inlet_plenum_mm,
        outlet_clearance_mm=outlet_clearance_mm,
    )

    z0_m = rad["z0_mm"] * MM_TO_M
    z1_m = rad["z1_mm"] * MM_TO_M
    mrf_r = (params.r_tip_mm + 0.5 * params.volute_clearance_mm) * MM_TO_M

    # Fluid sample point inside the scroll channel opposite the tongue (θ=π).
    r_chan = 0.5 * (rad["r_in_mm"] + rad["r_out_tongue_mm"] + 0.5 * params.spiral_growth_mm)
    loc = (
        -r_chan * MM_TO_M,
        0.0,
        0.5 * (z0_m + z1_m),
    )

    outlet_h = max(params.outlet_height_mm - 2.0 * params.volute_wall_mm, 1.0)
    outlet_w = max(params.outlet_width_mm - 2.0 * params.volute_wall_mm, 1.0)
    outlet_area = (outlet_h * outlet_w) * (MM_TO_M ** 2)

    omega = float(rpm) * 2.0 * math.pi / 60.0
    return VoluteDomain(
        xmin=ext["xmin"] * MM_TO_M,
        xmax=ext["xmax"] * MM_TO_M,
        ymin=ext["ymin"] * MM_TO_M,
        ymax=ext["ymax"] * MM_TO_M,
        zmin=ext["zmin"] * MM_TO_M,
        zmax=ext["zmax_domain"] * MM_TO_M,
        mrf_z_min=z0_m - mrf_margin_mm * MM_TO_M,
        mrf_z_max=z1_m + mrf_margin_mm * MM_TO_M,
        mrf_radius=mrf_r,
        tip_radius=params.r_tip_mm * MM_TO_M,
        rpm=float(rpm),
        omega_signed=float(spin) * omega,
        inlet_velocity=float(inlet_velocity),
        outlet_area_m2=outlet_area,
        location_in_mesh=loc,
    )
