"""Diagnostic for Task C: same lt120 params, one builder flag changed. Usage: python lt120_variant.py <params.json> key=value ..."""
import json, sys, dataclasses
from fansim.geometry.config import blade_params_from_dict
from fansim.geometry import build_impeller, export_stl
from fansim.validation.section_compare import measure_sections
d = json.load(open(sys.argv[1]))
for kv in sys.argv[2:]:
    k, v = kv.split("="); d[k] = json.loads(v)
d["n_blades"] = 2
p = blade_params_from_dict(d)
export_stl(build_impeller(p), "/tmp/lt120_var.stl")
R = [26.7, 37.9, 45.3, 56.5]; tab = {26.7: (21.2, .04, .18), 37.9: (28.9, .04, .12), 45.3: (34.2, .04, .08), 56.5: (41.6, .04, .06)}
for r, b in zip(R, measure_sections("/tmp/lt120_var.stl", tuple(x / p.tip_radius for x in R), tip_radius_mm=p.tip_radius)):
    c, cam, t = tab[r]
    print(r, "chord %.1f%%" % (100 * (b["chord_mm"] - c) / c), "camber %.4f" % b["camber_ratio"], "stagger %.2f" % b["stagger_deg"], "t/c %.4f" % (b["max_thickness_mm"] / b["chord_mm"]))
