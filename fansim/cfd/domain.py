# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Test-rig flow domain around the impeller (AMCA/ISO-style ducted fan setup).

All CFD works in SI meters; the impeller design is authored in millimeters, so this module
also carries the mm->m scale used when placing the STL into an OpenFOAM case.

Layout (axis = Z, flow +Z):

    inlet ──[ L_in ]──┤ impeller (MRF zone) ├──[ L_out ]── outlet
                      duct radius = tip + tip_gap

The MRF (Multiple Reference Frame) zone is a cylinder spanning the impeller axially and
enclosing the full duct cross-section; cells inside it get the rotational source term.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from fansim.geometry.blade import BladeParams

MM_TO_M = 1.0e-3


@dataclass
class TestRig:
    """Ducted-fan CFD domain, in SI meters, plus the single operating point.

    Attributes are meters / m·s⁻¹ / rad·s⁻¹ unless noted.
    """

    duct_radius: float
    tip_gap: float
    inlet_length: float
    outlet_length: float
    impeller_z_min: float
    impeller_z_max: float
    mrf_z_min: float
    mrf_z_max: float
    rpm: float
    inlet_velocity: float  # uniform axial inlet velocity that sets the operating flow
    spin: int = -1  # rotation sign about +z; -1 makes this blade handedness pump +z (flow)

    @property
    def omega_rad_s(self) -> float:
        """Unsigned rotation rate (rad/s), for power = torque * omega."""
        return self.rpm * 2.0 * math.pi / 60.0

    @property
    def omega_signed(self) -> float:
        """Signed rotation rate applied in the MRF zone (sets which way the rotor pumps)."""
        return self.spin * self.omega_rad_s

    @property
    def domain_z_min(self) -> float:
        return self.impeller_z_min - self.inlet_length

    @property
    def domain_z_max(self) -> float:
        return self.impeller_z_max + self.outlet_length

    @property
    def frontal_area(self) -> float:
        """Duct cross-sectional area (m²) used to convert velocity <-> volume flow.

        The Phase-1 skeleton uses a *square* box duct of side ``2*duct_radius`` (robust
        blockMesh), so this is a square area. Phase-2 fidelity switches to a circular duct.
        """
        return (2.0 * self.duct_radius) ** 2

    @property
    def inlet_flow_m3s(self) -> float:
        return self.inlet_velocity * self.frontal_area

    @property
    def inlet_flow_cfm(self) -> float:
        return self.inlet_flow_m3s * 2118.88

    @property
    def tip_speed(self) -> float:
        """Blade tip speed (m/s)."""
        return self.omega_rad_s * (self.duct_radius - self.tip_gap)


def rig_for_impeller(
    params: BladeParams,
    tip_gap_mm: float = 1.0,
    inlet_diameters: float = 2.0,
    outlet_diameters: float = 4.0,
    axial_margin_mm: float = 1.5,
    mrf_margin_mm: float = 2.0,
    inlet_velocity: float = 2.0,
) -> TestRig:
    """Build a TestRig sized to an impeller.

    Args:
        params: The impeller design.
        tip_gap_mm: Radial clearance between blade tip and duct wall (printed parts need
            more than the ~0.05 mm Noctua stock; default 1 mm is a realistic printed value).
        inlet_diameters / outlet_diameters: Duct lengths as multiples of duct diameter.
        axial_margin_mm: Assumed blade half-extent margin about z=0 when the STL axial span
            is not yet known (refined later from the actual mesh bounds).
        mrf_margin_mm: Axial padding of the MRF zone beyond the impeller extent.
        inlet_velocity: Uniform inlet axial velocity (m/s) defining the operating point.
    """
    tip_r_m = params.tip_radius * MM_TO_M
    tip_gap_m = tip_gap_mm * MM_TO_M
    duct_r = tip_r_m + tip_gap_m

    # Approximate impeller axial extent about z=0 from the station sweep spread + margin.
    sweeps = [s.sweep for s in params.stations]
    z_lo = (min(sweeps) - params.hub_axial_margin - axial_margin_mm) * MM_TO_M
    z_hi = (max(sweeps) + params.hub_axial_margin + axial_margin_mm) * MM_TO_M

    diameter = 2.0 * duct_r
    return TestRig(
        duct_radius=duct_r,
        tip_gap=tip_gap_m,
        inlet_length=inlet_diameters * diameter,
        outlet_length=outlet_diameters * diameter,
        impeller_z_min=z_lo,
        impeller_z_max=z_hi,
        mrf_z_min=z_lo - mrf_margin_mm * MM_TO_M,
        mrf_z_max=z_hi + mrf_margin_mm * MM_TO_M,
        rpm=params.rpm,
        inlet_velocity=inlet_velocity,
    )
