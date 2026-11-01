"""R23 B: BEM pq_curve shutoff for K3 (no CFD). Run from repo-r23 with its .venv; writes JSON to argv[1]."""
import json, sys, time
from pathlib import Path
t0 = time.monotonic()
from fansim.fan_bem import pq_curve
from fansim.geometry.config import load_blade_params
from fansim.optimize.search_space import stock_blade_flat, blade_from_flat
from fansim.optimize import system_curve as sc
out = {}
cases = {
    "a12x25_stock": blade_from_flat(stock_blade_flat("a12x25")),
    "lt120_validation_params": load_blade_params(Path("validation/reference/lt120/params.json")),
    "lt120_benchmark_params": load_blade_params(Path("docs/qa/benchmarks/lt120/fansim_params.json")),
}
for name, p in cases.items():
    rpm = 2000.0
    row = {"rpm": rpm}
    for model in ("euler", "axial_force"):
        c = pq_curve(p, rpm, pressure_model=model)
        row[model] = {"shutoff_dp_pa": round(float(c.shutoff_dp_pa), 3),
                      "free_delivery_cfm": None if c.free_delivery_cfm is None else round(float(c.free_delivery_cfm), 2)}
    try:
        row["bem_screen_cfm"] = sc.bem_screen_cfm(p, rpm)  # may need different signature
    except Exception as e:
        row["bem_screen_cfm"] = f"n/a ({type(e).__name__})"
    out[name] = row
out["fan01"] = "n/a: STL-only case, no BladeParams for pq_curve"
out["elapsed_s"] = round(time.monotonic() - t0, 1)
Path(sys.argv[1]).write_text(json.dumps(out, indent=1, default=str))
print(json.dumps(out, default=str))
