"""catalog() fixture copied verbatim from qa_r26/scripts/a_qa66_probe.py."""
import json
from fansim.catalog import build_catalog

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

