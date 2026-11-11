"""r28: one print-ready export for timing/peak-RSS (run under /usr/bin/time -v). Usage: e_one_export.py <out.stl> <code|-> """
import json, resource, sys, time
from fansim.geometry.config import load_blade_params
from fansim.fan_spec import get_fan_spec
from fansim.manufacturability.print_export import export_print_ready
p = load_blade_params("config/problems/a12x25_reference.yaml"); mount = get_fan_spec("a12x25").motor_mount
code = None if sys.argv[2] == "-" else sys.argv[2]
t0 = time.monotonic(); rep = export_print_ready(p, sys.argv[1], mount=mount, print_id=code, also_step=bool(int(__import__("os").environ.get("STEP", "0"))))
print(json.dumps({"code": code, "s": round(time.monotonic() - t0, 1), "watertight": rep.watertight, "volume": rep.volume_mm3,
                  "bodies": rep.n_bodies, "maxrss_gb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6, 2)}))
