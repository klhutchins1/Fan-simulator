"""QA r26 A (PREREG_R26 00ed802): QA-66 behaviour probes. Library calls only; verify_fn is a fake (no CFD, no Docker);
image_available is monkeypatched. Usage: python a_qa66_probe.py out.json  (run with repo-r26 venv, cwd repo-r26)."""
import json, sys, tempfile
from pathlib import Path
import fansim.cfd.runner as runner
from fansim.optimize import surrogate_search as ss
from fansim.catalog import build_catalog

R = {}
calls = {"synthetic": 0}
_real = ss.synthetic_label
def counting(p):
    calls["synthetic"] += 1
    return _real(p)
ss.synthetic_label = counting
runner.image_available = lambda: True

def fake_cfd(params, workdir):  # stands in for CFD; deterministic, not synthetic_label
    Path(workdir).mkdir(parents=True, exist_ok=True)
    c = 40.0 + float(params.get("chord_tip", 14.0))
    return True, {"cfm_free": c, "cfm_load": 0.6 * c, "efficiency": 0.3}, "fake-cfd"

def catalog(tmp, n, with_k=False):
    runs = tmp / "runs"; d = runs / "opt_s"; d.mkdir(parents=True)
    rows = []
    for i in range(n):
        r = {"trial": i + 1, "cfm_free": float(40 + i), "cfm_load": 30.0,
             "params": {"n_blades": 7, "stagger_root": 40.0, "stagger_mid": 40.0, "stagger_tip": 40.0,
                        "chord_root": 18.0, "chord_mid": 18.0, "chord_tip": 14.0 + i, "sweep_mid": 0.0, "sweep_tip": 0.0,
                        "lean_mid": 0.0, "lean_tip": 0.0, "max_camber": 0.04, "hub_radius": 21.5, "tip_radius": 50.0}}
        if with_k: r["k"] = 0.01
        rows.append(r)
    (d / "pareto.json").write_text(json.dumps(rows))
    db = tmp / "cat.db"; build_catalog(runs_dir=runs, store_dir=tmp / "none", db=db); return db

def run(tag, **kw):
    calls["synthetic"] = 0
    tmp = Path(tempfile.mkdtemp(prefix=f"r26_{tag}_"))
    db = kw.pop("ncat", None)
    if db is not None: db = catalog(tmp, db, kw.pop("with_k", False))
    out = tmp / "sg"; rec = {"tag": tag}
    try:
        res = ss.run_surrogate_guided(out_dir=out, n_doe=8, n_nsga=12, top_k=2, n_rounds=1, space="guided", seed=4,
                                      catalog_db=db, **kw)
        rec.update(ok=True, n_train=len(res.X), notes=res.notes, labels=res.labels, priors=res.priors)
    except Exception as e:
        rec.update(ok=False, err=f"{type(e).__name__}: {e}")
    rec["synthetic_label_calls"] = calls["synthetic"]
    j = out / "surrogate_guided.json"
    rec["json_written"] = j.exists()
    if j.exists():
        d = json.loads(j.read_text()); rec["json_labels"] = d.get("labels"); rec["json_priors"] = d.get("priors")
    rec["out_dir_created"] = out.exists()
    stubs = list(out.rglob("stub_result.json")) if out.exists() else []
    rec["stub_result_files"] = len(stubs)
    if stubs: rec["stub_result_labels"] = json.loads(stubs[0].read_text()).get("labels")
    R[tag] = rec

# rule 1 positive path: verify_cfd + 8-row catalog + (fake) CFD verifies -> no synthetic DoE
run("r1_verifycfd_cat8", verify_cfd=True, verify_fn=fake_cfd, ncat=8)
# rule 5 on disk: same run's JSON priors; and a catalog with k present (cfm_load should NOT be a prior)
run("r5_verifycfd_cat8_withk", verify_cfd=True, verify_fn=fake_cfd, ncat=8, with_k=True)
# rule 4: 7-row and missing catalog under verify_cfd -> refuse before search
run("r4_verifycfd_cat7", verify_cfd=True, verify_fn=fake_cfd, ncat=7)
run("r4_verifycfd_nocat", verify_cfd=True, verify_fn=fake_cfd)
# rule 4 without injected verify_fn, docker 'present' (patched): make_cfd_verify_fn only builds a closure; must refuse on catalog
run("r4_verifycfd_nocat_realverify", verify_cfd=True)
# rule 3: stub path on disk, real stub_verify (writes stub_result.json)
run("r3_stub_labels", stub_labels=True, ncat=8)
json.dump(R, open(sys.argv[1], "w"), indent=1, default=str)
for k, v in R.items():
    print(k, {x: v.get(x) for x in ("ok", "err", "synthetic_label_calls", "labels", "json_labels", "json_priors", "stub_result_files", "stub_result_labels", "n_train", "out_dir_created")})
