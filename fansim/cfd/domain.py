"""Test-rig flow domain around the impeller (AMCA/ISO-style ducted fan setup).

All CFD works in SI meters; the impeller design is authored in millimeters, so this module
also carries the mm->m scale used when placing the STL into an OpenFOAM case.

Layout (axis = Z, flow **+Z**):

    inlet (−Z) ──[ L_in ]──┤ impeller (MRF zone) ├──[ L_out ]── outlet (+Z)
                           duct radius = tip + tip_gap

The duct flows +Z at ``spin=-1``. As built, the rotor is designed to turn CCW seen from +Z
(``omega_z = +1``) and pump **−Z**; the CFD copy is rotated 180° about X by
``fansim.cfd.orientation`` (``AXIAL_CFD_ORIENTATION``), so ``spin=-1`` on the *oriented* copy
solves for the as-built rotation. See
``docs/validation/audits/2026-09-25-audit-01-flow-direction.md`` for the evidence.

Hub/motor: volume-flow from velocity uses the **annulus** (duct − hub). The solid hub in the
STL already blocks the core in CFD; schematic glyphs stay outside the hub too.

Geometry authoring still places the motor cup on the −Z face and the hub nose toward +Z —
that is the print/mount convention; duct inlet is the −Z end so flow hits the LE first.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from fansim.cfd.metrics import CFM_PER_M3S
from fansim.geometry.blade import BladeParams, open_tip_rmax_mm

MM_TO_M = 1.0e-3

# Minimum radial leftover (mm) between the BUILT impeller tip and the frame ID. Below this the CFD
# gate refuses the design (ring-to-frame-gap spec 2026-09-02). Ported here on 2026-09-12 recovery.
OPTIMIZER_TIP_GAP_MM = 0.5


def _built_tip_radius_mm(params: BladeParams) -> float:
    """Built outer radius (mm): the tip bulges past nominal tip_radius, plus any shroud ring."""
    return open_tip_rmax_mm(params) + float(getattr(params, "shroud_thick_mm", 0.0) or 0.0)


def remaining_tip_gap_mm(params: BladeParams, casing_id_mm: float) -> float:
    """Radial leftover (mm) from the built tip to the frame ID -- the quantity the optimizer/cockpit
    CFD gap gate checks: ``casing_id/2 - built_r``. Negative/overlap means the impeller is too big."""
    return float(casing_id_mm) / 2.0 - _built_tip_radius_mm(params)


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
    inlet_velocity: float  # uniform |axial| inlet speed (m/s); signed U_z is +this
    spin: int = -1  # oriented-CFD-copy spin; pumps +Z on the copy fansim.cfd.orientation flips
    hub_radius: float = 0.0  # m; excluded from flow_area (motor blocks the core)

    @property
    def omega_rad_s(self) -> float:
        """Unsigned rotation rate (rad/s), for power = torque * omega."""
        return self.rpm * 2.0 * math.pi / 60.0

    @property
    def omega_signed(self) -> float:
        """Signed rotation rate applied in the MRF zone (sets which way the rotor pumps)."""
        return self.spin * self.omega_rad_s

    @property
    def flow_sign(self) -> int:
        """Axial velocity sign: +1 (inlet −Z → outlet +Z), matching blade LE on low-Z."""
        return 1

    @property
    def u_axial(self) -> float:
        """Signed axial freestream / inlet BC velocity (m/s)."""
        return float(self.flow_sign) * abs(float(self.inlet_velocity))

    @property
    def domain_z_min(self) -> float:
        """Inlet end (−Z)."""
        return self.impeller_z_min - self.inlet_length

    @property
    def domain_z_max(self) -> float:
        """Outlet end (+Z)."""
        return self.impeller_z_max + self.outlet_length

    @property
    def frontal_area(self) -> float:
        """Full duct disk πR² (legacy name). Prefer :attr:`flow_area` for CFM from velocity."""
        return math.pi * self.duct_radius ** 2

    @property
    def flow_area(self) -> float:
        """Annulus area (m²): duct minus hub — motor blocks the core."""
        r_duct = float(self.duct_radius)
        r_hub = min(max(float(self.hub_radius), 0.0), r_duct * 0.95)
        return math.pi * (r_duct ** 2 - r_hub ** 2)

    @property
    def inlet_flow_m3s(self) -> float:
        return abs(self.inlet_velocity) * self.flow_area

    @property
    def inlet_flow_cfm(self) -> float:
        return self.inlet_flow_m3s * CFM_PER_M3S

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
    casing_id_mm: float | None = None,
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
        inlet_velocity: Uniform inlet |axial| speed (m/s); BC uses +Z.
    """
    tip_gap_m = tip_gap_mm * MM_TO_M
    if casing_id_mm is not None:
        # Pin the duct to the spec frame ID (ring-to-frame-gap): duct = frame/2, and the caller
        # passes the leftover (remaining_tip_gap_mm) as tip_gap_mm so tip_speed uses the built radius.
        duct_r = (float(casing_id_mm) / 2.0) * MM_TO_M
    else:
        # No spec: grow the duct around the BUILT tip envelope (bulge + shroud) plus the gap.
        duct_r = _built_tip_radius_mm(params) * MM_TO_M + tip_gap_m

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
        hub_radius=float(params.hub_radius) * MM_TO_M,
    )
