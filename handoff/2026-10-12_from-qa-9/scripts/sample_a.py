"""QA r9 Task A sample (PREREG_R9 a0260c0, seed 9009). Writes a_sample.jsonl."""
import gzip, json, random, sys
SRC = "/workspace/fansim/repo-r7/handoff/2026-10-11_from-qa-7/stress/inputs.jsonl.gz"
D = [json.loads(l) for l in gzip.open(SRC)]; D = [d for d in D if not d.get("sample_error")]
rng = random.Random(9009)
shr = lambda d: float(d["flat"].get("shroud_thick_mm") or 0) > 0
feat = lambda d: any(float(v or 0) for v in (d.get("features") or {}).values())
used = set(); out = []
def take(pool, n, group):
    pool = [d for d in pool if d["id"] not in used]; pick = rng.sample(pool, min(n, len(pool)))
    for d in pick:
        used.add(d["id"]); e = json.loads(json.dumps(d)); e["group"] = group; out.append(e)
    return pick
take([d for d in D if d["stratum"] == "CTL"], 5, "CTL")
take([d for d in D if d["stratum"] == "S8"], 10, "S8")
take([d for d in D if shr(d) and d["stratum"] not in ("S8", "CTL")], 15, "shrouded")
take([d for d in D if feat(d) and not shr(d) and d["stratum"] not in ("S8", "CTL")], 15, "featured")
base = [d for d in D if not shr(d) and not feat(d) and d["stratum"] in ("S1", "S2", "S3", "S4", "S5", "S6")]
for g, n in (("notched", 15), ("winglet", 15), ("tip_round", 15), ("uneven", 10), ("plain", 50)):
    for d in take(base, n, g):
        e = out[-1] if False else next(x for x in out if x["id"] == d["id"]); f = e["flat"]
        if g == "notched": f["notched_tips"] = True
        if g == "winglet":
            while True:
                f["winglet_sweep"] = rng.uniform(0, 10); f["winglet_lean"] = rng.uniform(0, 18)
                if max(f["winglet_sweep"], f["winglet_lean"]) >= 2: break
            f["winglet_span"] = 0.85
        if g == "tip_round": f["tip_round"] = rng.uniform(0.3, 1.0); f["tip_round_start"] = 0.80
        if g == "uneven": f["spacing_spread"] = rng.uniform(0.15, 0.6); f["spacing_seed"] = rng.randint(1, 999)
strata = {d["stratum"] for d in out}; missing = {"S1","S2","S3","S4","S5","S6","S7"} - strata
assert not missing, missing
sys.path.insert(0, "/workspace/fansim/repo-r9")
from fansim.fan_spec import get_fan_spec, mount_min_hub_radius
mmin = mount_min_hub_radius(get_fan_spec("a12x25"))
for i, e in enumerate(out): e["a_idx"] = i; e["seq"] = i; e["kind_C"] = e["stratum"] == "CTL"; e["kind_R"] = e["kind_T"] = False
elig = [e for e in out if e["stratum"] != "CTL" and (mmin is None or e["flat"]["hub_radius"] >= mmin)]
for e in rng.sample(elig, min(25, len(elig))): e["kind_C"] = True
with open(sys.argv[1], "w") as fh:
    for e in out: fh.write(json.dumps(e) + "\n")
from collections import Counter
print(len(out), Counter(e["group"] for e in out), Counter(e["stratum"] for e in out), "C:", sum(e["kind_C"] for e in out), "eligible", len(elig), "mmin", mmin)
