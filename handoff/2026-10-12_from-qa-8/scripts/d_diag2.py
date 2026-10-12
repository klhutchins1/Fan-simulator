import json, dataclasses, trimesh
from fansim.geometry.config import blade_params_from_dict
from fansim.geometry import chord_realisation as C, build_impeller, export_stl
from fansim.geometry.blade import build_blade_solid
from fansim.validation.section_compare import measure_sections
p = blade_params_from_dict(json.load(open("docs/qa/benchmarks/lt120/fansim_params.json")))
q = C.prepare_loft_chords(p)
export_stl(build_blade_solid(q, _chord_realized=True, _trim_tip=False), "/tmp/lt_blade.stl")
export_stl(build_blade_solid(q, _chord_realized=True, _trim_tip=True), "/tmp/lt_blade_trim.stl")
fr = (0.632, 0.755, 0.942)
for f in ("/tmp/lt_blade.stl", "/tmp/lt_blade_trim.stl", "/tmp/qa8d_lt120_measured.stl"):
    m = trimesh.load(f); print(f, "z range", m.bounds[:, 2].round(2))
    for r in measure_sections(f, fr, tip_radius_mm=p.tip_radius):
        print("  ", r["r_frac"], round(r.get("chord_mm", 0), 2), "axial", round(r.get("axial_extent_mm", 0), 2), "n", r["n_blades"])
