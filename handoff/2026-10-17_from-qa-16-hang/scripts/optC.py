"""QA r16 hang (PREREG 52eca5f) Option C: coupled slider limits. Closed form from A1:
  M_k = (c_k/2) sin(beta_k) - sweep_k - (c_root/2) sin(beta_root) - 1.5   for k = mid, tip   (designed margin at station k)
Built hang ~ k_amp * designed hang (A-1, k_amp = 1.75), so 'built <= 2 mm' becomes max(M_mid, M_tip) <= 2 / 1.75.
C-closed uses the station formula; C-exact uses the validator's own section-point margin s_d <= 2/1.75.
Usage: python optC.py <p1.jsonl> <p2.jsonl> <out.json>"""
import json, math, sys
import numpy as np

K = 1.75; LIM = 2.0 / K


def M(f):
    X = {k: 0.5 * f[f"chord_{k}"] * math.sin(math.radians(f[f"stagger_{k}"])) - float(f.get(f"sweep_{k}", 0.0) or 0.0)
         for k in ("root", "mid", "tip")}
    return max(X["mid"], X["tip"]) - X["root"] - 1.5


def main(p1, p2, out):
    P1 = [json.loads(l) for l in open(p1)]; G = [r for r in P1 if r["src"] == "guided"]
    Q = {json.loads(l)["id"]: json.loads(l) for l in open(p2)}
    res = {"limit_designed_mm": LIM}
    for name, keep in (("C-closed", lambda r: M(r["flat"]) <= LIM), ("C-exact", lambda r: r["s_d"] <= LIM),
                       ("today (designed <= 2)", lambda r: r["s_d"] <= 2.0)):
        kept = [r for r in G if keep(r)]
        sm_all = [r["flat"]["stagger_mid"] for r in G]; sm_kept = [r["flat"]["stagger_mid"] for r in kept]
        rows = [r for r in P1 if r["id"] in Q and "h_b" in Q[r["id"]]]
        over = [r for r in rows if Q[r["id"]]["h_b"] > 2.0]; under = [r for r in rows if Q[r["id"]]["h_b"] <= 2.0]
        hi = [r for r in G if r["flat"]["stagger_mid"] >= 44.0]
        res[name] = dict(guided_removed_frac=1 - len(kept) / len(G),
                         P2_misses_built_over2_kept=sum(keep(r) for r in over), P2_n_over2=len(over),
                         P2_false_cuts_built_le2_removed=sum(not keep(r) for r in under), P2_n_le2=len(under),
                         stagger_mid_quartiles_all=np.percentile(sm_all, [25, 50, 75]).round(2).tolist(),
                         stagger_mid_quartiles_kept=np.percentile(sm_kept, [25, 50, 75]).round(2).tolist(),
                         high_stagger_mid_ge44_removed_frac=1 - sum(keep(r) for r in hi) / max(1, len(hi)))
        print(name, res[name])
    json.dump(res, open(out, "w"), indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:])
