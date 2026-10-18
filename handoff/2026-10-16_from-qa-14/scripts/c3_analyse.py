"""QA r14 C3 analysis (PREREG_R14 586bbe9): PASS iff 0 readable stations outside chord 3 % / net camber 0.005 / stagger 1.5 deg."""
import json, sys
R = [json.loads(l) for l in open(sys.argv[1])]
ok = [r for r in R if "stations" in r]; err = [r for r in R if "stations" not in r]
st = [dict(s, i=r["i"], hang=r["hang"]) for r in ok for s in r["stations"]]
read = [s for s in st if s.get("chord_m") is not None]
bad = [s for s in read if abs(s["chord_err"]) > 0.03 or abs(s["camber_gap_net"]) > 0.005 or abs(s["stagger_err"]) > 1.5]
out = {"n_designs": len(R), "n_built": len(ok), "build_errors": [(r["i"], r.get("err", "")[:160]) for r in err],
       "n_stations": len(st), "n_readable": len(read), "unreadable": [(s["i"], s["k"]) for s in st if s.get("chord_m") is None],
       "n_none_total": sum(r.get("n_none", 0) for r in ok),
       "max_abs": {"chord_err": max(abs(s["chord_err"]) for s in read), "camber_gap_net": max(abs(s["camber_gap_net"]) for s in read),
                   "stagger_err": max(abs(s["stagger_err"]) for s in read)},
       "n_hanging_designs": sum(1 for r in ok if r["hang"] > 0),
       "outside": [{k: s[k] for k in ("i", "k", "r_frac", "chord_err", "camber_gap_net", "stagger_err", "hang")} for s in bad]}
out["PASS"] = not bad
json.dump(out, open(sys.argv[2], "w"), indent=1)
print(json.dumps({k: v for k, v in out.items() if k != "outside"}), "\nOUTSIDE", out["outside"])
