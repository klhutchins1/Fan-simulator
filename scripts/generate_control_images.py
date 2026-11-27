"""Generate a min-vs-max illustration for each cockpit slider (for hover tooltips).

For every control we build the geometry at the slider's MIN and MAX (all other params at defaults)
and render the two side by side as SHADED SOLIDS (pyvista, off-screen) so it reads like a real fan.
Spatial controls (blade count, wrap, sweep, hub, chord, spacing) render the whole impeller; subtle
airfoil controls (camber, thickness, camber position, LE curve, features) render a zoomed single
blade so the change is visible. Output: docs/control_images/<model>.png, used by the cockpit tooltips.

Usage:
  uv run python scripts/generate_control_images.py              # all CONTROLS
  uv run python scripts/generate_control_images.py e_tip_round  # only named models
"""
import os
import sys
import tempfile
from pathlib import Path

import cadquery as cq
import numpy as np
import pyvista as pv

from fansim.geometry import build_impeller, export_stl
from fansim.geometry.blade import build_blade_solid, with_screen_loft
from fansim.geometry.features import Features
from fansim.optimize.search_space import blade_from_flat

pv.OFF_SCREEN = True
OUT = Path("docs/control_images")
DEFAULT = {
    "n_blades": 7, "stagger_root": 26, "stagger_mid": 26, "stagger_tip": 22,
    "chord_root": 34, "chord_mid": 44, "chord_tip": 38, "max_camber": 0.05,
    "camber_root": 0.05, "camber_mid": 0.05, "camber_tip": 0.05,
    "sweep_mid": 3, "sweep_tip": 5, "lean_mid": 14, "lean_tip": 26,
    "hub_radius": 21.5, "tip_radius": 56.5, "hub_height": 18.0,
    "thickness_root": 0.10, "thickness_mid": 0.08, "thickness_tip": 0.06,
    "camber_pos": 0.4, "spacing_spread": 0.0, "spacing_seed": 0,
    "section_family": "naca", "span_interp": "linear",
    "cylindrical_tip": True, "le_thick_scale": 1.0, "te_thick_scale": 1.0,
    "blade_hub_z": 0.0,
}

# (model, label, key, min, max, mode[, base_overrides]).
# mode 'fan' = whole impeller, 'blade' = one zoomed blade.
# key forms:
#   str flat key
#   ("feat", amp_key, count_key, count[, extra_feat])  — vary amp; count on when amp>0
#   ("feat_n", feat_fixed: dict, count_key)            — vary count; amp/other dims fixed
CONTROLS = [
    ("e_n_blades", "Blades", "n_blades", 5, 11, "fan"),
    ("e_camber", "Camber / scoop", "max_camber", 0.0, 0.15, "blade"),
    ("e_camber_root", "Camber / scoop — root", "camber_root", 0.0, 0.15, "blade"),
    ("e_camber_mid", "Camber / scoop — mid", "camber_mid", 0.0, 0.15, "blade"),
    ("e_camber_tip", "Camber / scoop — tip", "camber_tip", 0.0, 0.15, "blade"),
    ("e_stagger_root", "Stagger / pitch — root", "stagger_root", 15, 55, "fan"),
    ("e_stagger_mid", "Stagger / pitch — mid", "stagger_mid", 15, 55, "fan"),
    ("e_stagger_tip", "Stagger / pitch — tip", "stagger_tip", 15, 55, "fan"),
    ("e_chord_root", "Chord — root", "chord_root", 14, 50, "fan"),
    ("e_chord_mid", "Chord — mid", "chord_mid", 14, 60, "fan"),
    ("e_chord_tip", "Chord — tip", "chord_tip", 14, 70, "fan"),
    ("e_lean_mid", "Wrap — mid", "lean_mid", 0, 30, "fan"),
    ("e_lean_tip", "Wrap — tip", "lean_tip", 0, 45, "fan"),
    ("e_sweep_mid", "Sweep — mid", "sweep_mid", -10, 20, "blade"),
    ("e_sweep_tip", "Sweep — tip", "sweep_tip", -8, 25, "blade"),
    ("e_le_mid", "LE curve — mid", "le_sweep_mid", -12, 12, "blade"),
    ("e_le_tip", "LE curve — tip", "le_sweep_tip", -12, 12, "blade"),
    ("e_le_skew_mid", "Sickle — mid", "le_skew_mid", 0, 12, "fan",
     {"lean_tip": 10.0, "cylindrical_tip": False}),
    ("e_le_skew_tip", "Sickle — tip", "le_skew_tip", 0, 15, "fan",
     {"lean_tip": 10.0, "cylindrical_tip": False}),
    ("e_hub_radius", "Hub radius", "hub_radius", 15, 35, "fan"),
    ("e_tip_radius", "Tip radius / length", "tip_radius", 45, 59, "fan"),
    ("e_skew_mid", "Skew mid", "skew_mid", -20, 20, "fan"),
    ("e_skew_tip", "Skew tip", "skew_tip", -25, 25, "fan"),
    ("e_winglet_sweep", "Winglet sweep", "winglet_sweep", 0, 15, "fan"),
    ("e_winglet_lean", "Winglet lean", "winglet_lean", 0, 30, "fan"),
    ("e_winglet_span", "Winglet start", "winglet_span", 0.6, 0.95, "fan",
     {"winglet_sweep": 10.0, "winglet_lean": 20.0}),
    ("e_tip_round", "Tip round", "tip_round", 0.0, 1.0, "fan"),
    ("e_tip_start", "Tip round start", "tip_round_start", 0.5, 0.92, "fan",
     {"tip_round": 0.85}),
    ("e_cylindrical_tip", "Cylindrical tip", "cylindrical_tip", 0, 1, "fan",
     {"lean_tip": 40.0, "chord_tip": 40.0, "stagger_tip": 28.0}),
    ("e_shroud_thick", "Shroud thickness", "shroud_thick_mm", 0.0, 3.0, "fan"),
    ("e_shroud_height", "Shroud height", "shroud_height_frac", 0.2, 1.0, "fan",
     {"shroud_thick_mm": 1.6}),
    ("e_hub_height", "Hub height", "hub_height", 6, 30, "fan"),
    ("e_blade_hub_z", "Blade on hub", "blade_hub_z", -5, 5, "fan",
     {"hub_height": 24.0}),
    ("e_blade_z", "Blade Z (plate)", "blade_z", -8, 8, "fan",
     {"section_family": "plate", "hub_height": 36.0, "thick_mm": 2.0}),
    ("e_le_face_root", "Front edge — root", "le_face_root", 0.0, 1.0, "blade",
     {"section_family": "plate", "thick_mm": 2.0, "te_face_root": 1.0}),
    ("e_le_face_mid", "Front edge — mid", "le_face_mid", 0.0, 1.0, "blade",
     {"section_family": "plate", "thick_mm": 2.0, "te_face_mid": 1.0}),
    ("e_le_face_tip", "Front edge — tip", "le_face_tip", 0.0, 1.0, "blade",
     {"section_family": "plate", "thick_mm": 2.0, "te_face_tip": 1.0}),
    ("e_te_face_root", "Back edge — root", "te_face_root", 0.0, 1.0, "blade",
     {"section_family": "plate", "thick_mm": 2.0, "le_face_root": 1.0}),
    ("e_te_face_mid", "Back edge — mid", "te_face_mid", 0.0, 1.0, "blade",
     {"section_family": "plate", "thick_mm": 2.0, "le_face_mid": 1.0}),
    ("e_te_face_tip", "Back edge — tip", "te_face_tip", 0.0, 1.0, "blade",
     {"section_family": "plate", "thick_mm": 2.0, "le_face_tip": 1.0}),
    ("e_hub_nose", "Hub nose", "hub_nose", 0.0, 15.0, "fan",
     {"hub_profile": "cone", "hub_height": 18.0}),
    ("e_camber_pos", "Camber position", "camber_pos", 0.2, 0.6, "blade"),
    ("e_thick_root", "Thickness — root", "thickness_root", 0.03, 0.15, "blade"),
    ("e_thick_mid", "Thickness — mid", "thickness_mid", 0.03, 0.15, "blade"),
    ("e_thick_tip", "Thickness — tip", "thickness_tip", 0.03, 0.15, "blade"),
    ("e_thick_mm", "Wall thickness", "thick_mm", 0.8, 4.0, "blade",
     {"section_family": "plate"}),
    ("e_thick_mode", "Thickness span", "thick_mode", "tapered", "uniform", "blade"),
    ("e_le_thick", "LE thick scale", "le_thick_scale", 0.5, 2.0, "blade",
     {"section_family": "naca", "thickness_mid": 0.08}),
    ("e_te_thick", "TE thick / roundness", "te_thick_scale", 0.15, 2.0, "blade",
     {"section_family": "plate", "thickness_mid": 0.10, "max_camber": 0.0,
      "camber_root": 0.0, "camber_mid": 0.0, "camber_tip": 0.0}),
    ("e_section_family", "Section family", "section_family", "naca", "plate", "blade",
     {"thickness_root": 0.08, "thickness_mid": 0.08, "thickness_tip": 0.08}),
    ("e_tip_notched", "Tip TE notches", "notched_tips", 0, 1, "fan",
     {"lean_tip": 20.0, "chord_tip": 40.0, "cylindrical_tip": True}),
    ("e_tip_notch_depth", "Tip notch depth", "tip_notch_depth_mm", 0.5, 3.0, "fan",
     {"notched_tips": True, "lean_tip": 20.0, "chord_tip": 40.0}),
    ("e_smooth_span", "Smooth span", "span_interp", "linear", "pchip", "fan",
     {"lean_mid": 8.0, "lean_tip": 35.0, "sweep_mid": 2.0, "sweep_tip": 10.0}),
    ("e_spacing", "Uneven spacing", "spacing_spread", 0.0, 0.6, "fan"),
    ("e_tub_amp", "Tubercle amp", ("feat", "tubercle_amp", "tubercle_waves", 5), 0.0, 0.10, "blade"),
    ("e_tub_waves", "Tubercle waves", ("feat_n", {"tubercle_amp": 0.08}, "tubercle_waves"), 2, 8, "blade"),
    ("e_ser_amp", "Serration amp", ("feat", "serration_amp", "serration_waves", 7), 0.0, 0.06, "blade"),
    ("e_ser_waves", "Serration teeth", ("feat_n", {"serration_amp": 0.05}, "serration_waves"), 3, 12, "blade"),
    ("e_dim_amp", "Dimple depth", ("feat", "dimple_amp", "dimple_rows", 4, {"dimple_cols": 4}),
     0.0, 0.35, "blade"),
    ("e_dim_rows", "Dimple rows",
     ("feat_n", {"dimple_amp": 0.25, "dimple_cols": 4}, "dimple_rows"), 1, 6, "blade"),
    ("e_dim_cols", "Dimple cols",
     ("feat_n", {"dimple_amp": 0.25, "dimple_rows": 4}, "dimple_cols"), 1, 6, "blade"),
]


def _unpack(row):
    model, label, key, lo, hi, mode, *rest = row
    base = rest[0] if rest else {}
    return model, label, key, lo, hi, mode, base


def _params(key, value, base=None):
    flat = dict(DEFAULT)
    if base:
        flat.update(base)
    feat = Features()
    if isinstance(key, tuple):
        kind = key[0]
        if kind == "feat":
            _, amp_key, count_key, count, *extra = key
            kw = {amp_key: value, count_key: (count if value > 0 else 0)}
            if extra:
                kw.update(extra[0])
                if value <= 0:
                    for k in list(kw):
                        if k.endswith(("_waves", "_rows", "_cols")):
                            kw[k] = 0
            feat = Features(**kw)
        elif kind == "feat_n":
            _, fixed, count_key = key
            kw = dict(fixed)
            kw[count_key] = int(value)
            feat = Features(**kw)
        else:
            raise ValueError(f"unknown feature key kind: {kind!r}")
    elif key == "thick_mm":
        from fansim.geometry.blade import uniform_thickness_tc

        mm = float(value)
        th = uniform_thickness_tc(mm, flat["chord_root"], flat["chord_mid"], flat["chord_tip"])
        flat["thick_mode"] = "uniform"
        flat["thick_mm"] = mm
        flat["thickness_root"], flat["thickness_mid"], flat["thickness_tip"] = th
        flat.setdefault("section_family", "plate")
    elif key == "thick_mode":
        from fansim.geometry.blade import uniform_thickness_tc

        mode = str(value)
        flat["thick_mode"] = mode
        if mode == "uniform":
            th = uniform_thickness_tc(
                2.4, flat["chord_root"], flat["chord_mid"], flat["chord_tip"],
            )
            flat["thick_mm"] = 2.4
            flat["thickness_root"], flat["thickness_mid"], flat["thickness_tip"] = th
        else:
            flat["thickness_root"] = 0.12
            flat["thickness_mid"] = 0.08
            flat["thickness_tip"] = 0.03
    elif key == "cylindrical_tip":
        flat["cylindrical_tip"] = bool(int(value)) if not isinstance(value, bool) else bool(value)
    elif key == "notched_tips":
        on = bool(int(value)) if not isinstance(value, bool) else bool(value)
        flat["notched_tips"] = on
        flat["tip_notch_count"] = 3 if on else 0
        flat["tip_notch_depth_mm"] = 1.5 if on else 0.0
    elif key == "tip_notch_depth_mm":
        flat["notched_tips"] = True
        flat["tip_notch_count"] = 3
        flat["tip_notch_depth_mm"] = float(value)
    elif key == "section_family":
        flat["section_family"] = str(value)
    elif key == "span_interp":
        flat["span_interp"] = str(value)
    else:
        flat[key] = value
    return blade_from_flat(flat, feat)


def _fmt_extreme(v) -> str:
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return f"{v:g}"
    return str(v)


def _mesh(key, value, mode, base=None):
    p = _params(key, value, base)
    tmp = Path(tempfile.mkdtemp()) / "m.stl"
    if mode == "blade":
        cq.exporters.export(cq.Workplane(obj=build_blade_solid(p)), str(tmp))
    else:
        export_stl(build_impeller(p), tmp)
    return pv.read(str(tmp))


def _cq_to_pv(shape, tol: float = 0.12) -> pv.PolyData:
    verts, tris = shape.tessellate(tol)
    pts = np.array([[v.x, v.y, v.z] for v in verts], dtype=np.float64)
    faces = np.hstack(
        [np.full((len(tris), 1), 3, dtype=np.int64), np.asarray(tris, dtype=np.int64)]
    ).ravel()
    return pv.PolyData(pts, faces)


def _trimesh_to_pv(tm) -> pv.PolyData:
    faces = np.hstack(
        [np.full((len(tm.faces), 1), 3, dtype=np.int64), np.asarray(tm.faces, dtype=np.int64)]
    ).ravel()
    return pv.PolyData(np.asarray(tm.vertices, dtype=np.float64), faces)


def _rotate_pv_z(mesh: pv.PolyData, deg: float) -> pv.PolyData:
    return mesh.rotate_z(deg, inplace=False)


# --- Multi-tab controls (Prop / Mixed / Volute / CROR; Issue #100) ---------------------------
# Each entry: (model, label, key, lo, hi, view, unit, shared_scale)
# view: "iso" | "top_tilt" | "side_tilt" | "rear_iso" | "volute_cut" | "volute_tongue"
PROP_CONTROLS = [
    ("p_n_blades", "Prop blades", "n_blades", 2, 4, "top_tilt", "", False),
    ("p_pitch", "Prop pitch", "pitch_in", 1.5, 8.0, "side_tilt", " in", False),
    ("p_chord_root", "Prop chord root", "chord_root", 0.08, 0.30, "top_tilt", " xR", False),
    ("p_chord_mid", "Prop chord mid", "chord_mid", 0.10, 0.32, "top_tilt", " xR", False),
    ("p_chord_tip", "Prop chord tip", "chord_tip", 0.04, 0.18, "top_tilt", " xR", False),
    ("p_sweep_tip", "Prop sweep tip", "sweep_tip", -2.0, 14.0, "side_tilt", " mm", True),
    ("p_tip_round", "Prop tip round", "tip_round", 0.0, 1.0, "top_tilt", "", False),
]

MIXED_CONTROLS = [
    ("mf_n_blades", "Mixed blades", "n_blades", 5, 13, "iso", "", False),
    ("mf_r_eye", "Mixed eye hub R", "r_eye_mm", 12.0, 24.0, "iso", " mm", True),
    ("mf_r_back", "Mixed back hub R", "r_back_mm", 21.5, 35.0, "rear_iso", " mm", True),
    ("mf_r_tip", "Mixed tip R", "r_tip_mm", 48.0, 54.5, "iso", " mm", True),
    ("mf_z_span", "Mixed Z span", "z_span_mm", 12.0, 22.0, "side_tilt", " mm", True),
    ("mf_chord_tip", "Mixed chord tip", "chord_tip", 14.0, 28.0, "iso", " mm", False),
    ("mf_stagger", "Mixed stagger mid", "stagger_deg", 20.0, 50.0, "iso", " deg", False),
]

VOLUTE_CONTROLS = [
    ("volute_n_blades", "Volute blades", "n_blades", 5, 11, "iso", "", False),
    ("volute_r_hub", "Volute hub R", "r_hub_mm", 12.0, 28.0, "iso", " mm", True),
    ("volute_blade_h", "Volute blade height", "blade_height_mm", 12.0, 32.0, "side_tilt", " mm", True),
    ("volute_spiral", "Volute spiral growth", "spiral_growth_mm", 10.0, 40.0, "volute_cut", " mm", True),
    ("volute_tongue_angle", "Volute tongue angle", "tongue_angle_deg", 2.0, 15.0, "volute_tongue", " deg", True),
    ("volute_out_w", "Volute outlet width", "outlet_width_mm", 20.0, 50.0, "volute_cut", " mm", True),
]

CROR_CONTROLS = [
    ("cror_hub_r", "CROR hub R", "hub_radius", 14.0, 28.0, "iso", " mm", True),
    ("cror_tip_r", "CROR tip R", "tip_radius", 45.0, 58.0, "iso", " mm", True),
    ("cror_gap", "CROR axial gap", "axial_gap_mm", 2.0, 12.0, "side_tilt", " mm", True),
    ("cror_f_n", "CROR front blades", "n_front", 5, 11, "iso", "", False),
    ("cror_r_n", "CROR rear blades", "n_rear", 5, 13, "rear_iso", "", False),
    ("cror_f_stagger", "CROR front stagger", "f_stagger", 25.0, 50.0, "iso", " deg", False),
    ("cror_r_stagger", "CROR rear stagger", "r_stagger", 25.0, 50.0, "rear_iso", " deg", False),
]


def _prop_scene(key: str, value) -> list[tuple[pv.PolyData, str]]:
    from dataclasses import replace

    from fansim.prop_spec import get_prop_spec
    from fansim.propeller.params_io import prop_design_defaults, prop_params_from_flat

    spec = get_prop_spec("fpv_5inch")
    flat = prop_design_defaults()
    if key == "n_blades":
        spec = replace(spec, n_blades=int(value))
    elif key == "pitch_in":
        spec = replace(spec, pitch_in=float(value))
    else:
        flat[key] = float(value)
    bp = with_screen_loft(prop_params_from_flat(spec, flat))
    blade = _cq_to_pv(build_blade_solid(bp), tol=0.12)
    z0, z1 = blade.bounds[4] - 1.0, blade.bounds[5] + 1.0
    hub = _cq_to_pv(
        cq.Solid.makeCylinder(
            bp.hub_radius, max(z1 - z0, 4.0), cq.Vector(0, 0, z0), cq.Vector(0, 0, 1)
        ),
        tol=0.15,
    )
    parts = [hub] + [_rotate_pv_z(blade, k * 360.0 / bp.n_blades) for k in range(bp.n_blades)]
    return [(pv.merge(parts), "#3b82f6")]


def _mixed_scene(key: str, value) -> list[tuple[pv.PolyData, str]]:
    from fansim.centrifugal.geometry import MixedFlowParams, build_mixed_flow_preview

    kw = {}
    if key == "n_blades":
        kw[key] = int(value)
    else:
        kw[key] = float(value)
    if key == "r_back_mm":
        kw["r_eye_mm"] = 14.0
    params = MixedFlowParams(**kw)
    tm, _ = build_mixed_flow_preview(params, tol=0.12)
    return [(_trimesh_to_pv(tm), "#3b82f6")]


def _volute_scene(key: str, value, view: str) -> list[tuple[pv.PolyData, str]]:
    from fansim.volute.geometry import (
        VoluteParams,
        build_radial_impeller,
        build_volute_casing,
        volute_enclosure_extents_mm,
        volute_radii_mm,
    )

    kw = {key: int(value) if key == "n_blades" else float(value)}
    params = VoluteParams(**kw)
    imp = _cq_to_pv(build_radial_impeller(params).val(), tol=0.15)
    if view not in ("volute_cut", "volute_tongue"):
        return [(imp, "#3b82f6")]

    casing = build_volute_casing(params).val()
    rad = volute_radii_mm(params)
    ext = volute_enclosure_extents_mm(params)
    # Remove the top roof slab so the Archimedean scroll cavity, cutwater tongue,
    # and discharge outlet throat are unobstructed from above.
    z_cut = rad["z1_mm"] - 0.5
    pad = 5.0
    roof = (
        cq.Workplane("XY")
        .workplane(offset=z_cut)
        .center(0.5 * (ext["xmin"] + ext["xmax"]), 0.5 * (ext["ymin"] + ext["ymax"]))
        .box(
            (ext["xmax"] - ext["xmin"]) + 2 * pad,
            (ext["ymax"] - ext["ymin"]) + 2 * pad,
            (ext["zmax_casing"] - z_cut) + 10.0,
            centered=(True, True, False),
        )
        .val()
    )
    open_casing = _cq_to_pv(casing.cut(roof), tol=0.20)
    return [(open_casing, "#94a3b8"), (imp, "#3b82f6")]


def _cror_scene(key: str, value) -> list[tuple[pv.PolyData, str]]:
    from fansim.cror.geometry import cror_axial_layout_mm
    from fansim.cror.params_io import cror_params_from_flat

    flat = {key: int(value) if key in ("n_front", "n_rear") else float(value)}
    params = cror_params_from_flat(flat)
    layout = cror_axial_layout_mm(params)
    front_b = _cq_to_pv(build_blade_solid(with_screen_loft(params.front)), tol=0.15)
    rear_b = _cq_to_pv(build_blade_solid(with_screen_loft(params.rear)), tol=0.15)
    z_rear = layout["z_rear_mm"]
    front_parts = [
        _rotate_pv_z(front_b, k * 360.0 / params.front.n_blades)
        for k in range(params.front.n_blades)
    ]
    rear_parts = [
        _rotate_pv_z(rear_b, k * 360.0 / params.rear.n_blades).translate((0, 0, z_rear), inplace=False)
        for k in range(params.rear.n_blades)
    ]
    z0, z1 = layout["hub_z0_mm"], layout["hub_z1_mm"]
    hub = _cq_to_pv(
        cq.Solid.makeCylinder(
            params.front.hub_radius, abs(z1 - z0), cq.Vector(0, 0, min(z0, z1)), cq.Vector(0, 0, 1)
        ),
        tol=0.18,
    )
    return [
        (hub, "#64748b"),
        (pv.merge(front_parts), "#2563eb"),
        (pv.merge(rear_parts), "#0891b2"),
    ]


def _set_view(p: pv.Plotter, view: str, bounds: tuple[float, ...]) -> None:
    cx = 0.5 * (bounds[0] + bounds[1])
    cy = 0.5 * (bounds[2] + bounds[3])
    cz = 0.5 * (bounds[4] + bounds[5])
    span = max(bounds[1] - bounds[0], bounds[3] - bounds[2], bounds[5] - bounds[4], 10.0)
    dist = 2.05 * span
    if view == "top_tilt":
        p.camera_position = [(cx + 0.35 * dist, cy - 0.50 * dist, cz + 0.95 * dist), (cx, cy, cz), (0, 0, 1)]
    elif view == "side_tilt":
        p.camera_position = [(cx + 0.95 * dist, cy - 0.45 * dist, cz + 0.32 * dist), (cx, cy, cz), (0, 0, 1)]
    elif view == "rear_iso":
        p.camera_position = [(cx + 0.65 * dist, cy - 0.65 * dist, cz - 0.60 * dist), (cx, cy, cz), (0, 0, -1)]
    elif view == "volute_cut":
        p.camera_position = [(cx + 0.15 * dist, cy - 0.30 * dist, cz + 1.15 * dist), (cx, cy, cz), (0, 1, 0)]
    elif view == "volute_tongue":
        # Center directly on the +X cutwater tongue septum (r_in..r_out0 ≈ 53..61 mm, y=0).
        tx, ty = 58.0, 0.0
        zd = 95.0
        p.camera_position = [(tx + 0.04 * zd, ty - 0.12 * zd, cz + 1.05 * zd), (tx, ty, cz), (0, 1, 0)]
    else:
        p.camera_position = [(cx + 0.72 * dist, cy - 0.72 * dist, cz + 0.65 * dist), (cx, cy, cz), (0, 0, 1)]


def _union_bounds(scene: list[tuple[pv.PolyData, str]]) -> tuple[float, float, float, float, float, float]:
    b = [list(m.bounds) for m, _ in scene]
    return (
        min(x[0] for x in b), max(x[1] for x in b),
        min(x[2] for x in b), max(x[3] for x in b),
        min(x[4] for x in b), max(x[5] for x in b),
    )


def _optimize_png(path: Path) -> None:
    try:
        from PIL import Image
    except ImportError:
        return
    with Image.open(path) as im:
        im.convert("RGB").save(path, format="PNG", optimize=True)


def _render_pair(
    model: str,
    label: str,
    lo,
    hi,
    scene_lo: list[tuple[pv.PolyData, str]],
    scene_hi: list[tuple[pv.PolyData, str]],
    view: str,
    unit: str,
    shared_scale: bool,
) -> None:
    b_lo = _union_bounds(scene_lo)
    b_hi = _union_bounds(scene_hi)
    b_shared = (
        min(b_lo[0], b_hi[0]), max(b_lo[1], b_hi[1]),
        min(b_lo[2], b_hi[2]), max(b_lo[3], b_hi[3]),
        min(b_lo[4], b_hi[4]), max(b_lo[5], b_hi[5]),
    )
    p = pv.Plotter(off_screen=True, shape=(1, 2), window_size=(460, 250), border=False)
    p.background_color = "white"
    for col, (scene, val, bnd) in enumerate([(scene_lo, lo, b_lo), (scene_hi, hi, b_hi)]):
        p.subplot(0, col)
        for mesh, color in scene:
            p.add_mesh(mesh, color=color, smooth_shading=True)
        tag = "min" if col == 0 else "max"
        p.add_text(
            f"{tag} = {_fmt_extreme(val)}{unit}",
            font_size=9,
            color="black",
            position="upper_edge",
        )
        _set_view(p, view, b_shared if shared_scale else bnd)
    out = OUT / f"{model}.png"
    p.screenshot(str(out))
    p.close()
    _optimize_png(out)
    print(f"  {model}.png  ({label}, {out.stat().st_size // 1024} KB)", flush=True)


def _generate_tab_controls(want: set[str] | None) -> None:
    families = [
        (PROP_CONTROLS, lambda k, v, _view: _prop_scene(k, v)),
        (MIXED_CONTROLS, lambda k, v, _view: _mixed_scene(k, v)),
        (VOLUTE_CONTROLS, _volute_scene),
        (CROR_CONTROLS, lambda k, v, _view: _cror_scene(k, v)),
    ]
    for rows, builder in families:
        for model, label, key, lo, hi, view, unit, shared in rows:
            if want is not None and model not in want:
                continue
            try:
                s_lo = builder(key, lo, view)
                s_hi = builder(key, hi, view)
                _render_pair(model, label, lo, hi, s_lo, s_hi, view, unit, shared)
            except Exception as e:  # noqa: BLE001
                print(f"  SKIP {model}: {type(e).__name__}: {e}")


def main(only=None):
    OUT.mkdir(parents=True, exist_ok=True)
    if only and set(only) == {"--other-tabs"}:
        want = {
            r[0]
            for grp in (PROP_CONTROLS, MIXED_CONTROLS, VOLUTE_CONTROLS, CROR_CONTROLS)
            for r in grp
        }
    else:
        want = set(only) if only else None
    for row in CONTROLS:
        model, label, key, lo, hi, mode, base = _unpack(row)
        if want is not None and model not in want:
            continue
        try:
            mlo, mhi = _mesh(key, lo, mode, base), _mesh(key, hi, mode, base)
            p = pv.Plotter(off_screen=True, shape=(1, 2), window_size=(460, 250), border=False)
            p.background_color = "white"
            for col, (m, v) in enumerate([(mlo, lo), (mhi, hi)]):
                p.subplot(0, col)
                p.add_mesh(m, color="#3b82f6", smooth_shading=True)
                tag = "min" if col == 0 else "max"
                p.add_text(f"{tag} = {_fmt_extreme(v)}",
                           font_size=9, color="black", position="upper_edge")
                p.view_isometric()
                p.camera.zoom(1.3)
            p.screenshot(str(OUT / f"{model}.png"))
            p.close()
            print(f"  {model}.png  ({label})")
        except Exception as e:  # noqa: BLE001
            print(f"  SKIP {model}: {type(e).__name__}: {e}")
    _generate_tab_controls(want)
    (OUT / "_test_shaded.png").unlink(missing_ok=True)
    print(f"-> {OUT}")
    os._exit(0)  # skip OCP/VTK teardown segfault


if __name__ == "__main__":
    main(only=sys.argv[1:] or None)
