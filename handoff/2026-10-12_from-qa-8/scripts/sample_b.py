"""QA r8 Task B sample (prereg 6b0aedf, seed 20261012). Writes the sample list as JSON lines."""
import gzip, json, random, sys
R7 = "/workspace/fansim/repo-r7/handoff/2026-10-11_from-qa-7"
F = {json.loads(l)["id"] for l in gzip.open(f"{R7}/data/f_results.jsonl.gz")}
S = {json.loads(l)["id"] for l in gzip.open(f"{R7}/stress/run_r7/designs.jsonl.gz")}
I = [json.loads(l) for l in gzip.open(f"{R7}/stress/inputs.jsonl.gz")]
def cam(fl): return abs(max((fl.get(k, 0) for k in ("camber_root", "camber_mid", "camber_tip", "max_camber")), key=abs))
def feat(r): ft = r.get("features") or {}; return any(ft.get(k, 0) for k in ("tubercle_amp", "serration_amp", "dimple_amp"))
cells = {"S3cell": [], "flatlean": [], "ordinary": []}
for r in I:
    if r.get("sample_error") or r["id"] in F or r["id"] in S: continue
    c, lt = cam(r["flat"]), abs(r["flat"].get("lean_tip", 0))
    k = "S3cell" if 0.02 <= c < 0.04 and lt >= 30 else "flatlean" if c < 0.02 and lt >= 20 else "ordinary" if c >= 0.04 else None
    if k: cells[k].append(r)
rng = random.Random(20261012)
plan = {"S3cell": (22, 2), "flatlean": (16, 1), "ordinary": (26, 2)}
out = []
for k, (n, nf) in plan.items():
    pool = cells[k][:]; rng.shuffle(pool)
    pick = [r for r in pool if feat(r)][:nf]
    if k == "ordinary":
        rest = [r for r in pool if r not in pick]; bys = {}
        for r in rest: bys.setdefault(r["stratum"], []).append(r)
        order = sorted(bys); j = 0
        while len(pick) < n:
            s = order[j % len(order)]; j += 1
            if bys[s]: pick.append(bys[s].pop(0))
    else:
        pick += [r for r in pool if r not in pick][: n - len(pick)]
    out += [{"cell_sel": k, "id": r["id"], "featured": feat(r)} for r in pick]
flip = rng.sample([o["id"] for o in out if o["cell_sel"] == "ordinary"], 5)
out += [{"cell_sel": "flipped", "id": i, "featured": False} for i in flip]
out.append({"cell_sel": "extra", "id": "S3_0014", "featured": False})
with open(sys.argv[1], "w") as f:
    for o in out: f.write(json.dumps(o) + "\n")
print(len(out), sum(o["featured"] for o in out), flip)
