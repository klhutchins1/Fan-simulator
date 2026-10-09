"""Approximate mixed-flow screening via an axial BEM adapter (roadmap §4.1).

Maps ``MixedFlowParams`` onto a synthetic ``BladeParams`` so the existing axial
``pq_curve`` / ``bem_screen_cfm`` path can cheaply reject hopeless designs before CFD.
This is an axial stand-in for a diagonal machine — stamp ``bem_adapter=axial`` and do
not claim calibrated mixed-flow CFM.
"""

from __future__ import annotations

from fansim.centrifugal.geometry import MixedFlowParams, _loft_tip_radius_mm
from fansim.geometry.blade import BladeParams, RadialStation


def mixed_to_blade_params(params: MixedFlowParams) -> BladeParams:
    """Synthetic axial blade with the mixed-flow annulus / section recipe."""
    tip = float(_loft_tip_radius_mm(params))
    stations = [
        RadialStation(
            r_frac=rf,
            chord=float(params.chord_mm),
            stagger_deg=float(params.stagger_deg),
            thickness=float(params.thickness),
            max_camber=float(params.max_camber),
            camber_pos=float(params.camber_pos),
        )
        for rf in (0.0, 0.5, 1.0)
    ]
    return BladeParams(
        n_blades=int(params.n_blades),
        hub_radius=float(params.r_back_mm),
        tip_radius=tip,
        stations=stations,
    )


def mixed_bem_screen_cfm(
    params: MixedFlowParams,
    rpm: float,
    load_pa: float,
    tip_gap_mm: float,
) -> tuple[float, float]:
    """(BEM free-delivery CFM, BEM system-curve op CFM) via the axial adapter."""
    from fansim.optimize.system_curve import bem_screen_cfm

    return bem_screen_cfm(
        mixed_to_blade_params(params), rpm, load_pa, tip_gap_mm, stator=False)
