"""QA r12 Task B, UNREGISTERED descriptive repeat of the single failing build (S7_0172_twin) x3, same setup as run_b.py."""
import json, os, sys, time
sys.argv = [sys.argv[0], "/dev/null"]
os.environ["FANSIM_MEMORY_TIER"] = "8gb"
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "run_b.py")).read()
src = src.split("OUT = Path(sys.argv[1])")[0]
exec(src)
LOG = "/tmp/qa12b_rep.calls.jsonl"; os.environ["FUSE_CALL_LOG"] = LOG
os.environ["PYTHONPATH"] = "/workspace/fansim/repo-r13/handoff/2026-10-13_to-qa-11/hook_c11" + os.pathsep + os.environ.get("PYTHONPATH", "")
from fansim.geometry.isolated import build_stl_isolated
it = next(i for i in items if i["id"] == "S7_0172_twin")
for k in range(3):
    n0 = sum(1 for _ in open(LOG)) if os.path.exists(LOG) else 0
    build_stl_isolated(it["flat"], it["features"], "/tmp/qa12b_rep.stl", timeout=900.0, preview=False)
    evs = [json.loads(l) for l in list(open(LOG))[n0:]]
    print(json.dumps({"rep": k, "events": evs}), flush=True)
