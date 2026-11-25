"""Run the pre-registered checks P1-P4 for the builder direction cross-check, attempt 2.

    .venv/Scripts/python.exe scripts/direction_crosscheck_2_check.py

Pre-registration: docs/validation/audits/2026-10-10-direction-crosscheck-2.md. Results go to
docs/validation/audits/2026-10-10-direction-crosscheck-2.json. Builds one STL (P3a), no CFD.
"""

from __future__ import annotations

import csv
import dataclasses
import gzip
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fansim.audit.direction import prove_direction  # noqa: E402
from fansim.cfd.orientation import builder_direction_refusal  # noqa: E402
from fansim.geometry.blade import signed_design_camber  # noqa: E402
from fansim.optimize.search_space import blade_from_flat  # noqa: E402
from fansim.validation.blade_golden import stock_a12x25_params  # noqa: E402

RUNS = ROOT / "runs" / "screen_rank_audit"
CSV = ROOT / "handoff" / "2026-10-09_to-qa-2" / "cfd_designs.csv"
STRESS = ROOT / "handoff" / "2026-10-09_from-qa-5" / "stress" / "designs.jsonl.gz"
OUT = ROOT / "docs" / "validation" / "audits" / "2026-10-10-direction-crosscheck-2.json"


def _check(stl: Path, camber: float | None, mesh=None) -> dict:
    proof = prove_direction(mesh if mesh is not None else trimesh.load(str(stl), force="mesh"))
    why = builder_direction_refusal(proof, camber)
    return {"verdict": proof.verdict, "omega": proof.omega_sign, "pump": proof.pump_sign,
            "chirality": proof.chirality, "design_camber": camber, "refused": why is not None,
            "why": why}


def _stl_in(run_dir: Path) -> Path | None:
    for cand in (run_dir / "impeller.stl", run_dir / "full" / "impeller.stl",
                 run_dir / "quick_load" / "impeller.stl"):
        if cand.is_file():
            return cand
    return None


def p1() -> dict:
    out: dict = {}
    stock_cam = signed_design_camber(stock_a12x25_params())
    out["stock"] = _check(RUNS / "stock" / "full" / "impeller.stl", stock_cam)
    with CSV.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["design_id"] == "stock" or not row["flat"]:
                continue
            stl = _stl_in(ROOT / row["source"].replace("\\", "/"))
            if stl is None:
                out[row["design_id"]] = {"missing": row["source"]}
                continue
            out[row["design_id"]] = _check(stl, signed_design_camber(blade_from_flat(json.loads(row["flat"]))))
    for d in sorted(RUNS.glob("r3_96*")):
        job = d / "quick_load" / "_job.json"
        stl = d / "quick_load" / "impeller.stl"
        if not (job.is_file() and stl.is_file()):
            out[d.name] = {"missing": str(d)}
            continue
        flat = json.loads(job.read_text(encoding="utf-8"))["flat"]
        out[d.name] = _check(stl, signed_design_camber(blade_from_flat(flat)))
    return out


def p2(p1_out: dict) -> dict:
    sources = {"stock": (RUNS / "stock" / "full" / "impeller.stl", p1_out["stock"]["design_camber"]),
               "t9005": (_stl_in(RUNS / "t9005"), p1_out.get("t9005", {}).get("design_camber")),
               "bem_9504": (_stl_in(RUNS / "bem_9504"), p1_out.get("bem_9504", {}).get("design_camber")),
               "9605": (RUNS / "r3_9605" / "quick_load" / "impeller.stl",
                        p1_out["r3_9605"]["design_camber"])}
    out = {}
    for name, (stl, cam) in sources.items():
        for axis, m in (("x", np.diag([-1.0, 1, 1, 1])), ("y", np.diag([1.0, -1, 1, 1]))):
            mesh = trimesh.load(str(stl), force="mesh")
            mesh.apply_transform(m)  # trimesh re-winds faces for a reflection
            out[f"{name}_{axis}"] = _check(stl, cam, mesh=mesh)
    return out


def p3() -> dict:
    from fansim.geometry import blade as blade_mod
    from fansim.geometry import build_impeller, export_stl

    stock = stock_a12x25_params()
    neg = dataclasses.replace(stock, stations=[dataclasses.replace(s, max_camber=-s.max_camber)
                                               for s in stock.stations])
    try:
        blade_mod.validate_blade_params(neg)
        p3b = {"refused": False}
    except ValueError as exc:
        p3b = {"refused": True, "why": str(exc)}
    from fansim.optimize.search_space import BOUNDS
    p3b["bounds_non_negative"] = all(b["max_camber"][0] >= 0.0 for b in BOUNDS.values())
    # P3a needs the backwards geometry, which the validator now refuses: build it with the check off.
    real = blade_mod.validate_blade_params
    blade_mod.validate_blade_params = lambda p: None
    try:
        stl = export_stl(build_impeller(neg), Path(tempfile.mkdtemp()) / "stock_negcamber.stl")
    finally:
        blade_mod.validate_blade_params = real
    p3a = _check(stl, signed_design_camber(stock))
    return {"P3a": p3a, "P3b": p3b}


def p4() -> dict:
    rows = []
    with gzip.open(STRESS, "rt", encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            m = r.get("meas") or {}
            k5 = m.get("K5") or {}
            if k5.get("verdict") is None:
                continue
            mc = (m.get("inputs") or {}).get("max_camber")
            mc = max(mc, key=abs) if isinstance(mc, list) else mc
            om, pu = k5.get("omega"), k5.get("pump")

            class _P:  # recorded proof; chirality = omega*pump (the proof's own cross-check identity)
                verdict = k5["verdict"]
                omega_sign, pump_sign = om, pu
                chirality = None if om is None else om * pu
                note = k5.get("note", "")

            old = (k5["verdict"] == "CONCLUSIVE" and (om, pu) != (1, -1))
            new = builder_direction_refusal(_P, mc) is not None
            rows.append({"id": r["id"], "old_refused": old, "new_refused": new, "camber": mc})
    return {"n": len(rows), "old_refused": [r["id"] for r in rows if r["old_refused"]],
            "new_refused": [r["id"] for r in rows if r["new_refused"]],
            "newly_refused": [r["id"] for r in rows if r["new_refused"] and not r["old_refused"]]}


def main() -> int:
    res = {"P1": p1()}
    res["P2"] = p2(res["P1"])
    res.update(p3())
    res["P4"] = p4()
    OUT.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    p1r = res["P1"]
    missing = [k for k, v in p1r.items() if "missing" in v]
    refused = [k for k, v in p1r.items() if v.get("refused")]
    print(f"P1 n={len(p1r) - len(missing)} missing={missing} refused={refused} -> "
          f"{'PASS' if not refused and not missing else 'FAIL'}")
    not_caught = [k for k, v in res["P2"].items() if not v["refused"]]
    print(f"P2 mirrors={len(res['P2'])} not caught={not_caught} -> {'PASS' if not not_caught else 'FAIL'}")
    print(f"P3a {res['P3a']['verdict']} ({res['P3a']['omega']},{res['P3a']['pump']}) refused="
          f"{res['P3a']['refused']} -> {'PASS' if res['P3a']['refused'] else 'FAIL'}")
    ok3b = res["P3b"]["refused"] and res["P3b"]["bounds_non_negative"]
    print(f"P3b validator refused={res['P3b']['refused']} bounds>=0={res['P3b']['bounds_non_negative']} -> "
          f"{'PASS' if ok3b else 'FAIL'}")
    p4r = res["P4"]
    print(f"P4 n={p4r['n']} old refused={len(p4r['old_refused'])} new refused={p4r['new_refused']} "
          f"newly={p4r['newly_refused']} -> {'PASS' if not p4r['new_refused'] else 'FAIL'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
