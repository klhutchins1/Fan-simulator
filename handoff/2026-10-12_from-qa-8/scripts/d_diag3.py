import json, dataclasses
from fansim.geometry.config import blade_params_from_dict
from fansim.geometry import build_impeller, export_stl
from fansim.validation.section_compare import measure_sections
p = blade_params_from_dict(json.load(open("docs/qa/benchmarks/lt120/fansim_params.json")))
r0 = p.hub_radius - p.root_embed; span = p.tip_radius - r0
fr = tuple(min((r0 + span * s.r_frac) / p.tip_radius, 0.99) for s in p.stations[1:])
for clip in (False,):
    q = dataclasses.replace(p, clip_below_hub=clip, n_blades=2, blade_angles_deg=None)
    export_stl(build_impeller(q), "/tmp/lt_noclip.stl")
    for s, r in zip(p.stations[1:], measure_sections("/tmp/lt_noclip.stl", fr, tip_radius_mm=p.tip_radius)):
        print(clip, round(r["r_mm"], 1), s.chord, round(r["chord_mm"], 2), f'{100*(r["chord_mm"]/s.chord-1):+.1f}%', "cam", round(r["camber_ratio"], 4), "stag", round(r["stagger_deg"], 1))
