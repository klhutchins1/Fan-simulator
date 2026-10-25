"""QA r20 A1 (PREREG_R20 2c4380d): write the 4 feature designs' flat + features exactly as r18 built them."""
import gzip, json, sys
R7 = "/workspace/fansim/repo-r7/handoff/2026-10-11_from-qa-7/stress/inputs.jsonl.gz"
IDS = ["S5_0207", "S5_0073", "S5_0112", "S5_0023"]
rows = {}
for l in gzip.open(R7):
    x = json.loads(l)
    if x["id"] in IDS:
        rows[x["id"]] = x
out = {"_source": ("QA r7 stress inputs (grok's own generated designs, qa/r7 inputs.jsonl.gz), as built in grok r18 A: "
                   "blade_from_flat(dict(flat, section_wrap='cylinder'), Features(**features)); flat below already "
                   "carries section_wrap='cylinder'. Built hang at the R1.7 export hub (mount_hub_params, a12x25), "
                   "grok r18 A / r20 A (mm): S5_0207 2.829, S5_0073 2.303, S5_0112 2.626, S5_0023 7.322; all > 2 mm "
                   "so stage 2 refuses all four. Designed hang at that hub: see docs/qa/r18/r18-A-built-hang-reference.csv.")}
for i in IDS:
    x = rows[i]
    out[i] = {"flat": dict(x["flat"], section_wrap="cylinder"), "features": x.get("features") or {}}
json.dump(out, open(sys.argv[1], "w"), indent=1, sort_keys=False)
print({i: sorted(out[i]["features"]) for i in IDS})
