"""Flat dict ↔ VoluteParams for cockpit / isolated workers."""

from __future__ import annotations

from fansim.volute.geometry import VoluteParams


def volute_params_from_flat(flat: dict) -> VoluteParams:
    """Build ``VoluteParams`` from a JSON-friendly flat dict (missing → defaults)."""
    d = VoluteParams()
    return VoluteParams(
        n_blades=int(flat.get("n_blades", d.n_blades)),
        r_hub_mm=float(flat.get("r_hub_mm", d.r_hub_mm)),
        r_tip_mm=float(flat.get("r_tip_mm", d.r_tip_mm)),
        blade_height_mm=float(flat.get("blade_height_mm", d.blade_height_mm)),
        blade_thick_mm=float(flat.get("blade_thick_mm", d.blade_thick_mm)),
        backplate_thick_mm=float(flat.get("backplate_thick_mm", d.backplate_thick_mm)),
        volute_clearance_mm=float(flat.get("volute_clearance_mm", d.volute_clearance_mm)),
        volute_wall_mm=float(flat.get("volute_wall_mm", d.volute_wall_mm)),
        spiral_growth_mm=float(flat.get("spiral_growth_mm", d.spiral_growth_mm)),
        n_volute_seg=int(flat.get("n_volute_seg", d.n_volute_seg)),
        outlet_width_mm=float(flat.get("outlet_width_mm", d.outlet_width_mm)),
        outlet_length_mm=float(flat.get("outlet_length_mm", d.outlet_length_mm)),
        outlet_height_mm=float(flat.get("outlet_height_mm", d.outlet_height_mm)),
        tongue_angle_deg=float(flat.get("tongue_angle_deg", d.tongue_angle_deg)),
        tongue_tip_clearance_mm=float(
            flat.get("tongue_tip_clearance_mm", d.tongue_tip_clearance_mm)),
        tongue_fillet_mm=float(flat.get("tongue_fillet_mm", d.tongue_fillet_mm)),
    )


def volute_params_to_flat(params: VoluteParams) -> dict:
    return {
        "n_blades": int(params.n_blades),
        "r_hub_mm": float(params.r_hub_mm),
        "r_tip_mm": float(params.r_tip_mm),
        "blade_height_mm": float(params.blade_height_mm),
        "blade_thick_mm": float(params.blade_thick_mm),
        "backplate_thick_mm": float(params.backplate_thick_mm),
        "volute_clearance_mm": float(params.volute_clearance_mm),
        "volute_wall_mm": float(params.volute_wall_mm),
        "spiral_growth_mm": float(params.spiral_growth_mm),
        "n_volute_seg": int(params.n_volute_seg),
        "outlet_width_mm": float(params.outlet_width_mm),
        "outlet_length_mm": float(params.outlet_length_mm),
        "outlet_height_mm": float(params.outlet_height_mm),
        "tongue_angle_deg": float(params.tongue_angle_deg),
        "tongue_tip_clearance_mm": float(params.tongue_tip_clearance_mm),
        "tongue_fillet_mm": float(params.tongue_fillet_mm),
    }
