"""Task C (round 7): lt120 geometry.json -> BladeParams, build one fused STL, cut cylinders, compare with the table.
Usage: python lt120_to_params.py <geometry.json> <out_params.json> <out_stl> <out_compare.json>
Station radius mapping uses the BUILDER's span: r_frac = (r - r0)/(tip - r0), r0 = hub_radius - root_embed
(fansim/geometry/blade.py lofts from hub - root_embed). With hub 25 mm and the default root_embed 2 mm, r0 = 23.0 mm =
table row 1, so all 10 rows map inside [0, 1] with no clamping."""
import json, sys, dataclasses
from fansim.geometry.blade import BladeParams, RadialStation
from fansim.geometry import build_impeller, export_stl
from fansim.validation.section_compare import measure_sections
g = json.load(open(sys.argv[1])); v = lambda d: d["value"]
hub, tip = v(g["hub_radius_mm"]), v(g["tip_radius_mm"])
p = BladeParams(n_blades=v(g["n_blades"]), hub_radius=hub, tip_radius=tip, rpm=v(g["rpm"]), section_family="naca")
r0 = hub - p.root_embed
rows = [dict(r=v(s["r_mm"]), chord=v(s["chord_mm"]), stagger=v(s["stagger_deg"]), camber=v(s["max_camber"]),
             cpos=v(s["camber_pos"]), t=v(s["thickness"])) for s in g["stations"]]
p.stations = [RadialStation(r_frac=round((x["r"] - r0) / (tip - r0), 6), chord=x["chord"], stagger_deg=x["stagger"],
                            thickness=x["t"], max_camber=x["camber"], camber_pos=x["cpos"]) for x in rows]
json.dump(dataclasses.asdict(p), open(sys.argv[2], "w"), indent=1)
# Measurement build: TWO blades (validator minimum) on the hub (same sections, ~2/7 of the fuse memory; the box is shared with a memory-heavy job).
export_stl(build_impeller(dataclasses.replace(p, n_blades=2)), sys.argv[3])
meas_rows = [x for x in rows if x["r"] > hub]          # 23.0 mm row is inside the hub
built = measure_sections(sys.argv[3], tuple(x["r"] / tip for x in meas_rows), tip_radius_mm=tip)
out = []
for x, b in zip(meas_rows, built):
    if b["n_blades"] == 0:
        out.append({"r_mm": x["r"], "n_blades": 0}); continue
    tc = b["max_thickness_mm"] / b["chord_mm"]
    out.append({"r_mm": x["r"], "n_blades": b["n_blades"], "omega_sign": b.get("omega_sign"),
                "chord": [x["chord"], round(b["chord_mm"], 3), round(100 * (b["chord_mm"] - x["chord"]) / x["chord"], 2)],
                "stagger": [x["stagger"], round(b["stagger_deg"], 3), round(b["stagger_deg"] - x["stagger"], 3)],
                "camber": [x["camber"], round(b["camber_ratio"], 4), round(b["camber_ratio"] - x["camber"], 4)],
                "camber_pos": [x["cpos"], round(b["camber_pos"], 3)],
                "t_c": [x["t"], round(tc, 4), round(100 * (tc - x["t"]) / x["t"], 1)]})
json.dump(out, open(sys.argv[4], "w"), indent=1)
for o in out: print(o)
