"""QA r14 Task A1 analysis (PREREG_R14 586bbe9). Usage: python analyse_b.py b_results.jsonl b_analysis.json"""
import gzip, json, sys
from fansim.resources import fuse_remaining_estimate_gb
rs = [json.loads(l) for l in open(sys.argv[1])]
r9 = [json.loads(l)["id"] for l in gzip.open("/workspace/fansim/repo-r9/handoff/2026-10-12_from-qa-9/data/e_results.jsonl.gz")]
rows = []
for r in rs:
    row = {"id": r["id"], "kind": r["kind"], "outcome": r["outcome"], "n_blades": r["n_blades"]}
    calls = [e for e in r["events"] if e["ev"] == "call"]; c = calls[0] if calls else None
    ex = next((e for e in r["events"] if e["ev"] == "exit" and c and e["pid"] == c["pid"]), None)
    if r["outcome"] == "OK" and c and ex:
        rem = (ex["VmHWM"] - c["VmRSS"]) * 1024
        ask = 1.15 * fuse_remaining_estimate_gb(c["n_faces"], shrouded=c["shrouded"], n_blade_faces=c["n_blade_faces"]) * 1024**3
        row.update(n_faces=c["n_faces"], shrouded=c["shrouded"], n_blade_faces=c["n_blade_faces"], n_calls=len(calls),
                   rss_call_gb=round(c["VmRSS"] / 1048576, 3), hwm_exit_gb=round(ex["VmHWM"] / 1048576, 3),
                   remaining_gb=round(rem / 1024**3, 3), ask_gb=round(ask / 1024**3, 3), ratio=round(rem / ask, 3), ok=rem <= ask,
                   bf_eq_total_minus4=(c["n_blade_faces"] == c["n_faces"] - 4) if c["shrouded"] else None)
    elif r["outcome"] == "OK":
        row["no_pair"] = True
    else:
        row["err"] = r.get("err")
    rows.append(row)
ok = [x for x in rows if "ok" in x]
A = {"n": len(rows), "ids_match_r9": [x["id"] for x in rows] == r9, "n_paired_ok": len(ok),
     "n_fail": sum(not x["ok"] for x in ok), "max_ratio": max(x["ratio"] for x in ok) if ok else None,
     "no_pair": [x["id"] for x in rows if x.get("no_pair")], "not_ok": [x["id"] for x in rows if x["outcome"] != "OK"],
     "PASS": bool(ok) and all(x["ok"] for x in ok), "rows": rows}
json.dump(A, open(sys.argv[2], "w"), indent=1)
print({k: v for k, v in A.items() if k != "rows"})
for x in rows: print(x["id"], x["kind"], x.get("n_faces"), x.get("remaining_gb"), x.get("ask_gb"), x.get("ratio"), x.get("bf_eq_total_minus4"))
