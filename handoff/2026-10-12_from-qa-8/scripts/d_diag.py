import json, os, dataclasses
from fansim.geometry.config import blade_params_from_dict
from fansim.geometry import chord_realisation as C
p = blade_params_from_dict(json.load(open("docs/qa/benchmarks/lt120/fansim_params.json")))
print("cache dir", C._cache_dir())
loft = C.loft_chords_for_measured_targets(p)
print("loft", [round(x,2) for x in loft])
print("fracs", [None if f is None else round(f,3) for f in C._station_measure_fracs(p)])
m = C.measure_station_chords(C.with_loft_chords(p, loft))
print("single-blade untrimmed measured", [None if x is None else round(x,2) for x in m])
print("targets", [s.chord for s in p.stations])
