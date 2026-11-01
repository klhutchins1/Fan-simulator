"""Render Optimize stamps that change STATIONARY parts (not the rotor) in the repo generator's style.

scripts/generate_control_images.py can only build the impeller/blade (_mesh -> build_impeller /
build_blade_solid), so --stator, --stator-stack and --stepped-inlet are drawn here with the same
pyvista off-screen settings (460x250, white bg, '#3b82f6' smooth shading, isometric, upper caption).
Stationary part = blue; rotor shown light grey for context. Geometry comes from the repo's own builders:
fansim.cfd.frame.build_frame_solid, fansim.cfd.stator.build_stator_solid, fansim.cfd.casing.build_casing_solid.
"""
import os, tempfile
from pathlib import Path
import cadquery as cq
import pyvista as pv
from fansim.geometry import build_impeller, export_stl
from fansim.geometry.blade import BladeParams
from fansim.cfd.domain import rig_for_impeller
from fansim.cfd.frame import build_frame_solid, stack_frame_z_start_mm
from fansim.cfd.stator import build_stator_solid
from fansim.cfd.casing import build_casing_solid

pv.OFF_SCREEN = True
OUT = Path("/workspace/fansim/qa_tooltips/img")
params = BladeParams()
rig = rig_for_impeller(params, tip_gap_mm=0.5)


def _pv(solid):
    tmp = Path(tempfile.mkdtemp()) / "m.stl"
    cq.exporters.export(cq.Workplane(obj=solid), str(tmp))
    return pv.read(str(tmp))


tmp = Path(tempfile.mkdtemp()) / "rotor.stl"
export_stl(build_impeller(params), tmp)
rotor = pv.read(str(tmp))
frame = _pv(build_frame_solid(params, rig))
stator = _pv(build_stator_solid(params, rig))
stack = [_pv(build_stator_solid(params, rig)),
         _pv(build_frame_solid(params, rig, z_start_mm=stack_frame_z_start_mm(rig)))]
casing = _pv(build_casing_solid(rig)).clip(normal="x", origin=(0, 0, 0))
casing_st = _pv(build_casing_solid(rig, stepped=True)).clip(normal="x", origin=(0, 0, 0))


def two(name, left, right, ltxt, rtxt, rotor_ctx=True, view="iso"):
    p = pv.Plotter(off_screen=True, shape=(1, 2), window_size=(460, 250), border=False)
    p.background_color = "white"
    for col, (meshes, txt) in enumerate([(left, ltxt), (right, rtxt)]):
        p.subplot(0, col)
        if rotor_ctx:
            p.add_mesh(rotor, color="#d1d5db", smooth_shading=True, opacity=0.6)
        for m in (meshes if isinstance(meshes, list) else [meshes]):
            p.add_mesh(m, color="#3b82f6", smooth_shading=True)
        p.add_text(txt, font_size=9, color="black", position="upper_edge")
        if view == "side":
            p.view_yz()
        else:
            p.view_isometric()
        p.camera.zoom(1.3)
    p.screenshot(str(OUT / f"{name}.png"))
    p.close()
    print(f"  {name}.png")


two("opt_stator", frame, stator, "off = 4-strut frame", f"on = stator vanes")
two("opt_stator_stack", frame, stack, "off = 4-strut frame", "on = stator + frame")
two("opt_stepped", casing, casing_st, "off = plain bore", "on = stepped inlet (+1.2 mm, 6 mm)",
    rotor_ctx=True, view="side")
os._exit(0)
