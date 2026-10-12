"""Rate / K5-map / timing tables from designs.jsonl (A4). Usage: python make_tables.py designs.jsonl > tables.md"""
import json, sys, collections, statistics as st
R = [json.loads(l) for l in open(sys.argv[1])]
K = ["K1", "K2", "K3", "K4", "K5", "K6", "K7", "K8", "K9", "K10", "K11"]
S = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "CTL"]
print("### Rate table (fail / tested; N/A, SKIPPED and INCONCLUSIVE are not 'tested'; K5 INCONCLUSIVE in brackets)\n")
print("| stratum | n | " + " | ".join(K) + " |"); print("|" + "---|" * (len(K) + 2))
tot = collections.defaultdict(lambda: [0, 0, 0])
for s in S + ["all"]:
    rs = [r for r in R if s == "all" or r["stratum"] == s]
    cells = []
    for k in K:
        v = [r["checks"].get(k) for r in rs if r["checks"].get(k) in ("PASS", "FAIL", "INCONCLUSIVE")]
        f = v.count("FAIL"); n = sum(x in ("PASS", "FAIL") for x in v); inc = v.count("INCONCLUSIVE")
        if k == "K5":
            n += inc
        cells.append("—" if not n else (f"{f}/{n}" + (f" ({inc})" if k == "K5" else "")))
    print(f"| {s} | {len(rs)} | " + " | ".join(cells) + " |")
print("\n### K5 map: FAIL / INCONCLUSIVE / tested, by max_camber × lean_tip\n")
cb = [(0, .01), (.01, .02), (.02, .04), (.04, 1)]; lb = [(0, 10), (10, 20), (20, 30), (30, 90)]
print("| max_camber \\ lean_tip | " + " | ".join(f"{a}–{b}°" if b < 90 else f"≥{a}°" for a, b in lb) + " |"); print("|---|" + "---|" * len(lb))
for a, b in cb:
    row = []
    for c, d in lb:
        v = [r["checks"]["K5"] for r in R if r["checks"].get("K5") and r["meas"].get("inputs")
             and a <= (r["meas"]["inputs"]["max_camber"] or 0) < b and c <= r["meas"]["inputs"]["lean"][-1] < d]
        row.append(f"{v.count('FAIL')} / {v.count('INCONCLUSIVE')} / {len(v)}" if v else "—")
    print(f"| {a}–{b if b < 1 else '0.06'} | " + " | ".join(row) + " |")
print("\n### Time and memory per build kind (suspend-flagged builds excluded from times)\n")
print("| kind | n | n suspend-flagged | median wall s | median monotonic s | median child CPU s | max peak RSS MB | median peak MB |")
print("|---|---|---|---|---|---|---|---|")
agg = collections.defaultdict(list)
for r in R:
    for k, b in r["builds"].items():
        if b.get("s") is not None:
            agg[k].append(b)
for k in ["P", "R", "C", "T16gb", "T6gb"]:
    v = agg.get(k, [])
    if not v:
        continue
    ok = [b for b in v if not b.get("suspect_suspend") and b["s"] < 1000]
    med = lambda f: round(st.median([b[f] for b in ok if b.get(f) is not None]), 1) if [b for b in ok if b.get(f) is not None] else "—"
    print(f"| {k} | {len(v)} | {sum(1 for b in v if b.get('suspect_suspend'))} | {med('s')} | {med('mono_s')} | {med('child_cpu_s')} | {max(b.get('peak_mb', 0) for b in v)} | {round(st.median(b.get('peak_mb', 0) for b in v))} |")
sk = sum(1 for r in R if r["builds"].get("T16gb", {}).get("outcome") == "SKIPPED_MEM")
print(f"\nT16gb SKIPPED_MEM: {sk}. K8 byte-identical across tiers: {sum(1 for r in R if r['meas'].get('K8_byte_identical'))}/{sum(1 for r in R if 'K8' in r['checks'])}.")
