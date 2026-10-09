"""Round-3 (6): BEM screen re-run in axial-force mode with max_camber up to 0.10.
Reuses /workspace/fansim/screen/bem_screen.py unchanged (same guards, score, load, Sobol 4096 + TPE 2500,
seed 0); only (a) pq_curve/operating_point get pressure_model="axial_force" and (b) the guided
max_camber bound is widened 0.06 -> 0.10. Run from repo_research (axial patch applied, e48a32d)."""
import functools, os, sys
from pathlib import Path
sys.path.insert(0, os.getcwd()); sys.path.insert(0, "/workspace/fansim/screen")
import fansim.fan_bem as FB
from fansim.optimize import search_space as SS
import bem_screen as S
S.pq_curve = functools.partial(FB.pq_curve, pressure_model="axial_force")
S.operating_point = functools.partial(FB.operating_point, pressure_model="axial_force")
lo, hi = SS.BOUNDS[S.SPACE]["max_camber"]
SS.BOUNDS[S.SPACE]["max_camber"] = (lo, 0.10)
assert S.BOUNDS[S.SPACE]["max_camber"] == (lo, 0.10)
print("max_camber bounds", SS.BOUNDS[S.SPACE]["max_camber"], "pressure_model axial_force", flush=True)
S.run(Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]))
