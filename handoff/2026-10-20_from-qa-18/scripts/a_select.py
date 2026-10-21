"""QA r18 A selection (PREREG_R18): deterministic from existing r17 data. Usage: python a_select.py <p1.jsonl> <r17 c300_built.jsonl>"""
import json, random, sys
P = {json.loads(l)["id"]: json.loads(l) for l in open(sys.argv[1])}
Bt = {json.loads(l)["id"]: json.loads(l) for l in open(sys.argv[2])}
ok = sorted(i for i in Bt if "error" not in Bt[i]); h = lambda i: Bt[i]["h_bx"]
feat = [i for i in ok if P[i]["features_active"]]; nf = [i for i in ok if not P[i]["features_active"]]
rng = random.Random(18001)
sel = ["S2_0269", "S5_0207"]
f2 = sorted((i for i in feat if i != "S5_0207"), key=lambda i: abs(h(i) - 2.0))[:2]; sel += f2
sel.append(rng.choice([i for i in feat if i not in sel]))
sel.append(max((i for i in nf if h(i) < 2.0), key=h)); sel.append(min((i for i in nf if h(i) > 2.0), key=h))
for lo, hi in ((0.0, 1.0), (1.0, 1.8), (2.5, 1e9)):
    sel.append(rng.choice([i for i in nf if lo < h(i) <= hi and i not in sel]))
assert len(set(sel)) == 10
print(json.dumps([{"id": i, "features": bool(P[i]["features_active"]), "r17_h_bx": Bt.get(i, {}).get("h_bx")} for i in sel]))
