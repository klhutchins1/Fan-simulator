"""QA r10b Task B sample (PREREG_R10 26aa359, seed 10010). Writes b_sample.jsonl."""
import gzip, json, random, sys
SRC = "/workspace/fansim/repo-r7/handoff/2026-10-11_from-qa-7/stress/inputs.jsonl.gz"
D = [json.loads(l) for l in gzip.open(SRC)]; D = [d for d in D if not d.get("sample_error")]
rng = random.Random(10010)
shr = lambda d: float(d["flat"].get("shroud_thick_mm") or 0) > 0
feat = lambda d: any(float(v or 0) for v in (d.get("features") or {}).values())
used = set(); out = []
def add(d, group):
    used.add(d["id"]); e = json.loads(json.dumps(d)); e["group"] = group; out.append(e); return e
def take(pool, n, group):
    pool = [d for d in pool if d["id"] not in used]; return [add(d, group) for d in rng.sample(pool, min(n, len(pool)))]
take([d for d in D if d["stratum"] == "CTL"], 5, "CTL")
fpool = [d for d in D if feat(d) and not shr(d) and d["stratum"] not in ("S8", "CTL")]
add(next(d for d in fpool if d["id"] == "S5_0167"), "featured"); take(fpool, 4, "featured")
take([d for d in D if d["stratum"] == "S8"], 5, "near_bounds")
take([d for d in D if shr(d) and d["stratum"] not in ("S8", "CTL")], 5, "shrouded")
base = [d for d in D if not shr(d) and not feat(d) and d["stratum"] in ("S1", "S2", "S3", "S4", "S5", "S6")]
for g in ("notched", "winglet", "tip_round", "uneven", "plain"):
    for e in take(base, 4, g):
        f = e["flat"]
        if g == "notched": f["notched_tips"] = True
        if g == "winglet":
            while True:
                f["winglet_sweep"] = rng.uniform(0, 10); f["winglet_lean"] = rng.uniform(0, 18)
                if max(f["winglet_sweep"], f["winglet_lean"]) >= 2: break
            f["winglet_span"] = 0.85
        if g == "tip_round": f["tip_round"] = rng.uniform(0.3, 1.0); f["tip_round_start"] = 0.80
        if g == "uneven": f["spacing_spread"] = rng.uniform(0.15, 0.6); f["spacing_seed"] = rng.randint(1, 999)
from fansim.fan_spec import get_fan_spec, mount_min_hub_radius
mmin = mount_min_hub_radius(get_fan_spec("a12x25"))
for i, e in enumerate(out): e["a_idx"] = i; e["seq"] = i; e["kind_C"] = e["stratum"] == "CTL"
elig = [e for e in out if e["stratum"] != "CTL" and (mmin is None or e["flat"]["hub_radius"] >= mmin)]
for e in rng.sample(elig, min(5, len(elig))): e["kind_C"] = True
with open(sys.argv[1], "w") as fh:
    for e in out: fh.write(json.dumps(e) + "\n")
from collections import Counter
print(len(out), Counter(e["group"] for e in out), Counter(e["stratum"] for e in out), "C:", sum(e["kind_C"] for e in out), "eligible", len(elig))
