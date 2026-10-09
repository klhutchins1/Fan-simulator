"""QA r4 request 6, step 1: export Stock / 9504 through the cockpit path.
prepare_export_flat(fit_frame=True, fit_hub=True) -> python -m fansim.cockpit._export_worker (do_export,
also_mirror=True). Usage: python export_run.py <stock|9504> <outdir>"""
import json, subprocess, sys, time
from dataclasses import asdict
from pathlib import Path

from fansim.cockpit.placement import prepare_export_flat
from fansim.fan_spec import fan_spec_to_dict, get_fan_spec
from fansim.geometry.features import Features
from fansim.optimize.search_space import stock_blade_flat

which, outdir = sys.argv[1], Path(sys.argv[2]).resolve()
outdir.mkdir(parents=True, exist_ok=True)
spec = get_fan_spec("a12x25")
if which == "stock":
    flat = stock_blade_flat("a12x25")
else:
    flat = json.load(open("/workspace/fansim/repo-r3/handoff/2026-10-09_from-qa-2/screen_r3/designs/"
                          "ref_prev04_T06559_bem_9504.flat.json"))
feats = Features()
fitted, changes = prepare_export_flat(flat, spec, fit_frame=True, features=feats, fit_hub=True)
out = outdir / f"{which}.stl"
job = {"flat": fitted, "features": asdict(feats), "out": str(out), "spec": fan_spec_to_dict(spec),
       "also_mirror": True, "result": str(outdir / f"{which}.export.json")}
(outdir / "job.json").write_text(json.dumps(job, default=float))
t = time.time()
rc = subprocess.call([sys.executable, "-m", "fansim.cockpit._export_worker", str(outdir / "job.json")],
                     stdout=open(outdir / "worker.log", "w"), stderr=subprocess.STDOUT)
info = {"which": which, "rc": rc, "wall_s": round(time.time() - t, 1),
        "changes": [str(c) for c in changes],
        "fitted": {k: fitted.get(k) for k in ("n_blades", "tip_radius", "hub_radius", "hub_height")}}
(outdir / "run.json").write_text(json.dumps(info, indent=1, default=str))
print(json.dumps(info, default=str))
