"""QA r10b Task C.3 (PREREG_R10 26aa359): evaluate_candidate on two refused designs, CFD stubbed as in
tests/test_objectives_orientation.py (build_case/run_mesh monkeypatched; calls counted)."""
import gzip, json, sys, tempfile, time
from fansim.geometry.features import Features
from fansim.optimize.search_space import blade_from_flat
from fansim.optimize import objectives
X = {json.loads(l)["id"]: json.loads(l) for l in gzip.open("/workspace/fansim/repo-r7/handoff/2026-10-11_from-qa-7/stress/inputs.jsonl.gz")}
calls = []
objectives.build_case = lambda *a, **k: calls.append("build_case") or (_ for _ in ()).throw(RuntimeError("stub build_case reached"))
objectives.run_mesh = lambda *a, **k: calls.append("run_mesh")
out = []
for did in sys.argv[1:]:
    x = X[did]; p = blade_from_flat(dict(x["flat"], section_wrap="cylinder"), Features(**(x.get("features") or {})))
    n0 = len(calls); t0 = time.monotonic()
    with tempfile.TemporaryDirectory() as td:
        r = objectives.evaluate_candidate(p, workdir=td)
    out.append({"id": did, "feasible": r.feasible, "reason": r.reason, "stub_calls": calls[n0:], "s": round(time.monotonic() - t0, 1)})
    print(json.dumps(out[-1]), flush=True)
