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
import pyvista as pv

from fansim.geometry import build_impeller, export_stl
from fansim.geometry.blade import build_blade_solid
from fansim.geometry.features import Features
from fansim.optimize.search_space import blade_from_flat

pv.OFF_SCREEN = True
OUT = Path("docs/control_images")
DEFAULT = dict(n_blades=7, stagger_root=26, stagger_mid=26, stagger_tip=22,
               chord_root=34, chord_mid=44, chord_tip=38, max_camber=0.05,
               camber_root=0.05, camber_mid=0.05, camber_tip=0.05,
               sweep_mid=3, sweep_tip=5, lean_mid=14, lean_tip=26,
               hub_radius=21.5, tip_radius=56.5, hub_height=18.0,
               thickness_root=0.10, thickness_mid=0.08, thickness_tip=0.06,
               camber_pos=0.4, spacing_spread=0.0, spacing_seed=0,
               section_family="naca", span_interp="linear",
               cylindrical_tip=True, le_thick_scale=1.0, te_thick_scale=1.0,
               blade_hub_z=0.0)

# (model, label, key, min, max, mode[, base_overrides]).
# mode 'fan' = whole impeller, 'blade' = one zoomed blade.
# key forms:
#   str flat key
#   ("feat", amp_key, count_key, count[, extra_feat])  — vary amp; count on when amp>0
#   ("feat_n", feat_fixed: dict, count_key)            — vary count; amp/other dims fixed
CONTROLS = [
    ("e_n_blades", "Blades", "n_blades", 5, 11, "fan"),
    ("e_camber", "Camber / scoop", "max_camber", 0.0, 0.12, "blade"),
    ("e_camber_root", "Camber / scoop — root", "camber_root", 0.0, 0.12, "blade"),
    ("e_camber_mid", "Camber / scoop — mid", "camber_mid", 0.0, 0.12, "blade"),
    ("e_camber_tip", "Camber / scoop — tip", "camber_tip", 0.0, 0.12, "blade"),
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
    ("e_hub_radius", "Hub radius", "hub_radius", 15, 30, "fan"),
    ("e_tip_radius", "Tip radius / length", "tip_radius", 45, 59, "fan"),
    ("e_skew_mid", "Skew mid", "skew_mid", -6, 6, "fan"),
    ("e_skew_tip", "Skew tip", "skew_tip", -6, 6, "fan"),
    ("e_winglet_sweep", "Winglet sweep", "winglet_sweep", 0, 12, "fan"),
    ("e_winglet_lean", "Winglet lean", "winglet_lean", 0, 25, "fan"),
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
    ("e_blade_z", "Blade Z (plate)", "blade_z", -4, 4, "fan",
     {"section_family": "plate", "hub_height": 24.0, "thick_mm": 2.0}),
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
    ("e_thick_mm", "Wall thickness", "thick_mm", 1.0, 3.0, "blade",
     {"section_family": "plate"}),
    ("e_thick_mode", "Thickness span", "thick_mode", "tapered", "uniform", "blade"),
    ("e_le_thick", "LE thick scale", "le_thick_scale", 0.5, 2.0, "blade",
     {"section_family": "naca", "thickness_mid": 0.08}),
    ("e_te_thick", "TE thick / roundness", "te_thick_scale", 0.15, 1.0, "blade",
     {"section_family": "plate", "thickness_mid": 0.10, "max_camber": 0.0,
      "camber_root": 0.0, "camber_mid": 0.0, "camber_tip": 0.0}),
    ("e_section_family", "Section family", "section_family", "naca", "plate", "blade",
     {"thickness_root": 0.08, "thickness_mid": 0.08, "thickness_tip": 0.08}),
    ("e_tip_notched", "Tip TE notches", "notched_tips", 0, 1, "fan",
     {"lean_tip": 20.0, "chord_tip": 40.0, "cylindrical_tip": True}),
    ("e_tip_notch_depth", "Tip notch depth", "tip_notch_depth_mm", 0.5, 2.5, "fan",
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


def main(only=None):
    OUT.mkdir(parents=True, exist_ok=True)
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
    (OUT / "_test_shaded.png").unlink(missing_ok=True)
    print(f"-> {OUT}")
    os._exit(0)  # skip OCP/VTK teardown segfault


if __name__ == "__main__":
    main(only=sys.argv[1:] or None)
