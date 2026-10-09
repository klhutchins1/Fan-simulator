"""Benchmark cases + runner shared by the lead prototypes."""
import copy, json, os, sys
from pathlib import Path
sys.path.insert(0, os.getcwd())
from fansim.geometry.config import load_blade_params
from fansim.geometry.blade import BladeParams
from fansim.optimize.search_space import blade_from_flat

SCR = Path("/workspace/fansim/screen/designs")


def cases():
    stock = load_blade_params("config/problems/a12x25_reference.yaml")
    out = {"stock7": stock}
    for f in sorted(SCR.glob("0[1-6]_*.flat.json")):
        out[f.name.split(".")[0]] = blade_from_flat(json.loads(f.read_text()))
    def restag(v):
        p = copy.deepcopy(stock)
        for s in p.stations: s.stagger_deg = v
        return p
    out["paddle89"] = restag(89.0)
    out["rev-45"] = restag(-45.0)
    out["rev-60"] = restag(-60.0)
    out["zero_blades"] = BladeParams(n_blades=0)
    return out
