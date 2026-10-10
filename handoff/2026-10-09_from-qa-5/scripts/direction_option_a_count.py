"""Task B Q1: apply direction option (a) to Task A's K5/K6 records (no builds; reads the stress map).
Usage: python direction_option_a_count.py <stress_records.jsonl|.jsonl.gz|.csv> [--camber-min 0.02]
Field names (rename via --map k=v if Task A used others):
  design_id, k5_verdict, k5_omega, k5_pump, k5_chirality, k6_verdict, k6_omega,
  design camber: max over |camber_root|, |camber_mid|, |camber_tip|, |max_camber| present in the record
  (signed value at that station kept for the sign test).
Rules compared (builder convention omega +1, pump -1, chirality -1):
  current : refuse if CONCLUSIVE and (omega, pump) != (+1, -1)
  option a: refuse if CONCLUSIVE and chirality != -1                                  (mirror)
            or CONCLUSIVE and |design camber| >= camber_min and split != expected for sign(camber)
"""
import argparse, csv, gzip, json, sys
from collections import Counter
ap = argparse.ArgumentParser(); ap.add_argument("path"); ap.add_argument("--camber-min", type=float, default=0.02)
ap.add_argument("--map", action="append", default=[]); a = ap.parse_args()
M = dict(kv.split("=", 1) for kv in a.map)
g = lambda r, k, d=None: r.get(M.get(k, k), d)
op = gzip.open if a.path.endswith(".gz") else open
with op(a.path, "rt") as fh:
    rows = list(csv.DictReader(fh)) if a.path.rstrip(".gz").endswith(".csv") else [json.loads(l) for l in fh if l.strip()]
num = lambda x: None if x in (None, "", "None") else float(x)
def design_camber(r):
    vals = [num(g(r, k)) for k in ("camber_root", "camber_mid", "camber_tip", "max_camber")]
    vals = [v for v in vals if v is not None]
    return max(vals, key=abs) if vals else None
C = Counter(); ex = {}
for r in rows:
    v = g(r, "k5_verdict")
    if v != "CONCLUSIVE":
        C["k5_not_conclusive"] += 1; continue
    om, pu, ch = int(num(g(r, "k5_omega"))), int(num(g(r, "k5_pump"))), int(num(g(r, "k5_chirality")))
    cam = design_camber(r)
    cur = (om, pu) != (1, -1)
    mirror_like = ch != -1
    exp_split = (1, -1) if (cam is None or cam >= 0) else (-1, 1)
    opt = mirror_like or (cam is not None and abs(cam) >= a.camber_min and (om, pu) != exp_split)
    key = ("cur_refuse" if cur else "cur_pass") + "/" + ("a_refuse" if opt else "a_pass")
    C[key] += 1
    if cur and not opt: C["removed_false_refusals"] += 1
    if cur and opt:
        C["remaining_refusals_" + ("chirality" if mirror_like else f"split_camber>={a.camber_min}")] += 1
    if not cur and opt: C["new_refusals_under_a"] += 1
    ex.setdefault(key, g(r, "design_id"))
    k6 = g(r, "k6_verdict")
    if k6 == "CONCLUSIVE":
        C["k6_conclusive_mirrors"] += 1
        # the mirrored part: chirality flips by construction of the proof; option (a) refuses on chirality
        if int(num(g(r, "k6_omega"))) == -om: C["k6_omega_flipped"] += 1
        if g(r, "k6_chirality") not in (None, ""):
            C["k6_caught_by_option_a (mirrored chirality != -1)"] += int(int(num(g(r, "k6_chirality"))) != -1)
        else:
            C["k6_chirality_missing"] += 1
print(json.dumps({"n": len(rows), **C, "examples": ex}, indent=1))
