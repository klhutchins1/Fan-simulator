import json, dataclasses
from fansim.geometry.config import blade_params_from_dict
from fansim.geometry import build_impeller, export_stl
from fansim.validation.blade_golden import stock_a12x25_params
from fansim.validation.section_compare import measure_sections
lt = blade_params_from_dict(json.load(open("docs/qa/benchmarks/lt120/fansim_params.json")))
st = stock_a12x25_params()
for nm, p in (("stock", st), ("lt120", lt)):
    print(nm, "lean", [round(s.lean_deg, 1) for s in p.stations], "sweep", [round(s.sweep, 1) for s in p.stations], "skew", [round(s.skew, 1) for s in p.stations], "le_sweep", [round(s.le_sweep,1) for s in p.stations], "le_skew", [round(s.le_skew,1) for s in p.stations])
def var(p, **kw): return dataclasses.replace(p, stations=[dataclasses.replace(s, **kw) for s in p.stations])
for tag, p in (("loft", st), ("loft,lean0", var(st, lean_deg=0.0)), ("loft,sweep0", var(st, sweep=0.0, le_sweep=0.0)),
               ("loft,lean0+sweep0", var(st, lean_deg=0.0, sweep=0.0, le_sweep=0.0, skew=0.0, le_skew=0.0))):
    q = dataclasses.replace(p, chord_basis="loft", n_blades=2, blade_angles_deg=None, clip_below_hub=False)
    export_stl(build_impeller(q), "/tmp/st_var.stl")
    r0 = q.hub_radius - q.root_embed; span = q.tip_radius - r0
    fr = tuple(min((r0 + span * s.r_frac) / q.tip_radius, 0.99) for s in q.stations[1:])
    out = []
    for s, r in zip(q.stations[1:], measure_sections("/tmp/st_var.stl", fr, tip_radius_mm=q.tip_radius)):
        out.append(f'{r["r_mm"]:.0f}:{100*(r.get("chord_mm",0)/s.chord-1):+.0f}%/{r.get("camber_ratio",0):.3f}')
    print(tag, " ".join(out))
