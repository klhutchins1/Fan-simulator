"""QA r17 C300 analytic shares. Usage: python c300_analytic.py <p1.jsonl> <p2.jsonl> <out.jsonl>"""
import json, sys, gzip
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import p2_built as P2
from c_common import rules
R7 = {}
for l in gzip.open(P2.R7):
    x = json.loads(l); R7[x["id"]] = l
_orig = gzip.open
class _G:  # serve params_of's R7 scan from memory (same records)
    def __init__(self, rid): self.l = [R7[rid]]
    def __iter__(self): return iter(self.l)
P1 = {json.loads(l)["id"]: json.loads(l) for l in open(sys.argv[1])}
P2r = [json.loads(l) for l in open(sys.argv[2])]
with open(sys.argv[3], "w") as fh:
    for k, b in enumerate(P2r):
        r = P1[b["id"]]
        if r["src"] == "r7": gzip.open = lambda *a, rid=r["id"], **kw: _G(rid)
        p = P2.params_of(r); gzip.open = _orig
        out = dict(id=r["id"], src=r["src"], h_b_auto=b.get("h_b"), h_d_r16=r["h_d"], **rules(p))
        fh.write(json.dumps(out) + "\n")
print("DONE", len(P2r))
