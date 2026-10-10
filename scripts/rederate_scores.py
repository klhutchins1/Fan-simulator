"""Motor-efficiency change: check (M1-M3) and apply the re-derate of saved scores.

    .venv/Scripts/python.exe scripts/rederate_scores.py --check
    .venv/Scripts/python.exe scripts/rederate_scores.py --apply      # after --check passes

Pre-registration: docs/validation/audits/2026-10-10-motor-efficiency.md
"""

from __future__ import annotations

import argparse
import glob
import json
import re
import shutil
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fansim.optimize.rederate import derate_factor, rederate_scale, rescore_from_raw  # noqa: E402

TARGET_RPM = 2000.0
B_OLD = 12.0 * 0.14 * 0.40
B_NEW = 12.0 * 0.14 * 0.50
B_HIGH = 12.0 * 0.14 * 0.65
NEW_EFF = 0.50
TOL = 1e-3
OUT = ROOT / "docs" / "validation" / "audits" / "2026-10-10-motor-efficiency.json"


def _j(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _load_pa(raw: dict, case: Path) -> float | None:
    dj = case / "design.json"
    if dj.is_file():
        lp = (_j(dj).get("extra") or {}).get("load_pa")
        if lp is not None:
            return float(lp)
    try:
        d = float(raw.get("derate") or 1.0)
        return round(float(raw["p_probe_pa"]) / (d * d) * 2.0) / 2.0
    except (KeyError, TypeError, ValueError):
        return None


def _rel(a: float, b: float) -> float:
    return abs(a - b) / max(abs(b), 1e-9)


def check() -> dict:
    out: dict = {}
    stock = _j(ROOT / "runs/screen_rank_audit/stock_hubclip/full/_eval_result.json")["raw"]
    shaft = max(stock["free"]["shaft_power_w"], stock["load"]["shaft_power_w"])
    out["M1"] = {"stock_shaft_w": shaft, "lambda_new": derate_factor(B_NEW, shaft),
                 "pass": derate_factor(B_NEW, shaft) == 1.0}

    files = sorted(glob.glob(str(ROOT / "runs/*/cockpit_assess/design_*/_eval_result.json"))
                   + glob.glob(str(ROOT / "runs/screen_rank_audit/*/full/_eval_result.json")))
    rows, skipped = [], []
    for f in files:
        case = Path(f).parent
        d = _j(Path(f))
        raw = d.get("raw") or {}
        if not d.get("feasible"):
            skipped.append((case.name, "infeasible"))
            continue
        lp = _load_pa(raw, case)
        if lp is None:
            skipped.append((case.name, "no load_pa"))
            continue
        old = rescore_from_raw(raw, budget_w=B_OLD, target_rpm=TARGET_RPM, load_pa=lp)
        if old is None:
            skipped.append((case.name, "refine_op or missing metrics"))
            continue
        a_err = max(_rel(old[k], float(d[k])) for k in ("cfm_free", "cfm_load", "efficiency"))
        new = rescore_from_raw(raw, budget_w=B_NEW, target_rpm=TARGET_RPM, load_pa=lp)
        s = rederate_scale(old["actual_rpm"], TARGET_RPM, B_OLD, B_NEW)
        b_err = max(_rel(old["cfm_free"] * s, new["cfm_free"]), _rel(old["cfm_load"] * s, new["cfm_load"]),
                    _rel(old["efficiency"], new["efficiency"]))
        rows.append({"case": str(case.relative_to(ROOT)), "a_err": a_err, "b_err": b_err,
                     "lambda_old": old["derate"], "lambda_new": new["derate"],
                     "saved": {k: d[k] for k in ("cfm_free", "cfm_load", "efficiency")}})
    fails_a = [r for r in rows if r["a_err"] > TOL]
    fails_b = [r for r in rows if r["b_err"] > TOL]
    out["M2"] = {"n": len(rows), "skipped": skipped, "fail_a": fails_a, "fail_b": fails_b,
                 "pass": bool(rows) and not fails_a and not fails_b}

    # M3: load-CFM rank at 0.40 / 0.50 / 0.65 over the current-scored cockpit designs.
    designs = []
    for f in sorted(glob.glob(str(ROOT / "runs/*/cockpit_assess/design_*/design.json"))):
        dj = _j(Path(f))
        ex = dj.get("extra") or {}
        if not dj.get("feasible") or ex.get("refine_op") or ex.get("fan_model", "a12x25") != "a12x25":
            continue
        rpm = float(ex.get("actual_rpm") or TARGET_RPM)
        load = float(dj["objectives"]["cfm_load"])
        designs.append((dj["trial"], f, load, rpm))
    ranks = {}
    for name, b in (("0.40", B_OLD), ("0.50", B_NEW), ("0.65", B_HIGH)):
        vals = {(t, f): load * rederate_scale(rpm, TARGET_RPM, B_OLD, b) for t, f, load, rpm in designs}
        ranks[name] = [k for k, _ in sorted(vals.items(), key=lambda kv: -kv[1])]
    flips = {}
    for other in ("0.50", "0.65"):
        pos = {k: i for i, k in enumerate(ranks[other])}
        base = ranks["0.40"]
        flips[other] = [(a[0], b[0]) for i, a in enumerate(base) for b in base[i + 1:] if pos[a] > pos[b]]
    out["M3"] = {"n": len(designs), "flips": flips, "top10_0.50": [k[0] for k in ranks["0.50"][:10]]}
    return out


def _scale_design_json(f: Path) -> tuple[str, float] | None:
    dj = _j(f)
    ex = dj.setdefault("extra", {})
    if ex.get("motor_eff") == NEW_EFF or not dj.get("feasible"):
        return None
    if ex.get("fan_model", "a12x25") != "a12x25":
        return None
    rpm = float(ex.get("actual_rpm") or TARGET_RPM)
    s = rederate_scale(rpm, TARGET_RPM, B_OLD, B_NEW)
    if ex.get("refine_op") and s != 1.0:
        ex["motor_model_stale"] = True  # extra CFD at the old derated point: needs re-run
    else:
        obj = dj["objectives"]
        obj["cfm_free"] = float(obj["cfm_free"]) * s
        obj["cfm_load"] = float(obj["cfm_load"]) * s
        ex["actual_rpm"] = round(min(TARGET_RPM, rpm * s))
    ex["motor_eff"] = NEW_EFF
    f.write_text(json.dumps(dj, indent=2), encoding="utf-8")
    return dj["trial"], s


_LIMIT = re.compile(r"motor-limited: (\d+) RPM")


def _scale_studies(log: list) -> None:
    for db in sorted(glob.glob(str(ROOT / "runs/*/study.db"))):
        shutil.copyfile(db, db + ".bak_motor_eff")
        con = sqlite3.connect(db)
        try:
            for tid, number in con.execute("select trial_id, number from trials where state='COMPLETE'"):
                attrs = dict(con.execute(
                    "select key, value_json from trial_user_attributes where trial_id=?", (tid,)))
                if json.loads(attrs.get("motor_eff", "null") or "null") == NEW_EFF:
                    continue
                if not json.loads(attrs.get("feasible", "false")):
                    continue
                m = _LIMIT.search(json.loads(attrs.get("reason", '""')) or "")
                rpm = float(m.group(1)) if m else TARGET_RPM
                s = rederate_scale(rpm, TARGET_RPM, B_OLD, B_NEW)
                # objectives 0 and 1 are free / load CFM (fansim.optimize.objectives.OBJECTIVE_NAMES)
                con.execute("update trial_values set value = value * ? where trial_id=? and objective in (0, 1)",
                            (s, tid))
                con.execute("insert or replace into trial_user_attributes (trial_id, key, value_json) "
                            "values (?, 'motor_eff', ?)", (tid, json.dumps(NEW_EFF)))
                log.append((Path(db).parent.name, number, s, bool(m)))
            con.commit()
        finally:
            con.close()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(argv)
    if a.check:
        res = check()
        OUT.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
        print("M1", res["M1"])
        print("M2 n", res["M2"]["n"], "pass", res["M2"]["pass"], "fail_a", len(res["M2"]["fail_a"]),
              "fail_b", len(res["M2"]["fail_b"]), "skipped", len(res["M2"]["skipped"]))
        print("M3 n", res["M3"]["n"], "flips@0.50", len(res["M3"]["flips"]["0.50"]),
              "flips@0.65", len(res["M3"]["flips"]["0.65"]))
    if a.apply:
        changed = [r for f in sorted(glob.glob(str(ROOT / "runs/*/cockpit_assess/design_*/design.json")))
                   if (r := _scale_design_json(Path(f))) is not None]
        study_log: list = []
        _scale_studies(study_log)
        print(f"design.json rederated: {len(changed)} (changed: {sum(1 for _, s in changed if s != 1.0)})")
        print(f"study trials rederated: {len(study_log)} (changed: {sum(1 for r in study_log if r[2] != 1.0)})")
        for r in changed:
            if r[1] != 1.0:
                print(f"  design {r[0]}: x{r[1]:.4f}")
        for r in study_log:
            if r[2] != 1.0:
                print(f"  {r[0]} trial {r[1]}: x{r[2]:.4f} ({'from note' if r[3] else 'assumed >=0.995'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
