"""QA r26 A follow-up probe (QA-68): run_optimization.main() with --surrogate-guided --verify-cfd and a catalog with
no rows, image_available monkeypatched True (no Docker present, nothing launched). Expect: clean 'return 2'.
The real verify closure is replaced by one that aborts if called. Usage: python a_qa68_cli_probe.py <repo> out.json"""
import importlib.util, json, sys, tempfile, traceback
from pathlib import Path
repo, OUT = Path(sys.argv[1]), sys.argv[2]
spec = importlib.util.spec_from_file_location("run_opt", repo / "scripts/run_optimization.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
import fansim.cfd.runner as runner, fansim.optimize.surrogate_search as ss
m.image_available = lambda: True; runner.image_available = lambda: True
_real = ss.make_cfd_verify_fn
def guarded(*a, **k):
    _real(*a, **k)  # factory only builds a closure; the closure is never returned
    def fn(*a, **k): raise SystemExit("ABORT: a CFD verify was called")
    return fn
ss.make_cfd_verify_fn = guarded
tmp = Path(tempfile.mkdtemp(prefix="r26_qa68_")); out = tmp / "opt"
R = {}
for name, db in (("no_catalog_file", tmp / "missing.db"),):
    sys.argv = ["run_optimization.py", "--surrogate-guided", "--verify-cfd", "--out", str(out), "--surrogate-db", str(db)]
    try:
        R[name] = {"returned": m.main()}
    except SystemExit as e:
        R[name] = {"SystemExit": str(e)}
    except Exception as e:
        R[name] = {"uncaught": type(e).__name__, "msg": str(e)[:200], "tb_last": traceback.format_exc().strip().splitlines()[-3:]}
    R[name]["out_dir_created"] = out.exists()
json.dump(R, open(OUT, "w"), indent=1, ensure_ascii=False); print(json.dumps(R, indent=1, ensure_ascii=False))
