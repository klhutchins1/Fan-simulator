"""QA r18 B (PREREG_R18 5df5059): Shigemitsu 2018 velocity triangles, both rotors, hub/mid/tip, conventions P and X."""
import json, math, sys
d, a, t = math.radians, math.degrees, math.tan
Q = 0.55 / 60.0
ROT = {"front": dict(D=(25.0, 31.1, 37.2), s=(18.2, 31.2, 36.0), sig=(1.61, 1.40, 1.22), n=15000.0, Dh=25.0),
       "rear": dict(D=(26.0, 31.1, 37.2), s=(40.6, 40.0, 45.5), sig=(1.03, 1.17, 1.10), n=14000.0, Dh=26.0)}
CHI_LE, CHI_TE = a(math.atan(2 * 0.04 / 0.4)), a(math.atan(2 * 0.04 / 0.6)); THETA = CHI_LE + CHI_TE
ST = ("hub", "mid", "tip")


def cax(rot, k): return k * Q / (math.pi / 4 * ((37.2e-3) ** 2 - (ROT[rot]["Dh"] * 1e-3) ** 2))
def U(rot, D): return math.pi * D * 1e-3 * ROT[rot]["n"] / 60.0
def gam(s, conv): return 90.0 - s if conv == "P" else s


def run(conv, kc=1.0, ks=1.0):
    rows = []; f = ROT["front"]; ca = cax("front", kc)
    # front exit swirl at mid (Carter), free vortex
    g = gam(f["s"][1], conv); b2p = g - CHI_TE
    mc = 0.23 * (2 * 0.4) ** 2 + b2p / 500.0; dev = mc * THETA / math.sqrt(f["sig"][1])
    b2 = b2p + dev; Um = U("front", f["D"][1]); cu_mid = (Um - ca * t(d(b2))) * ks
    for rot in ("front", "rear"):
        R = ROT[rot]; c = cax(rot, kc)
        for j, st in enumerate(ST):
            D = R["D"][j]; u = U(rot, D)
            cu_in = 0.0 if rot == "front" else cu_mid * f["D"][1] / D
            wu = u + cu_in; b1 = a(math.atan(wu / c)); g = gam(R["s"][j], conv)
            rows.append(dict(conv=conv, kc=kc, ks=ks, rotor=rot, station=st, D_mm=D, U=u, c_ax=c, cu_in=cu_in,
                             beta1_axis=b1, gamma_axis=g, i_chord=b1 - g, i_LE=b1 - (g + CHI_LE),
                             ok=abs(b1 - g) <= 15.0))
    return rows, dict(conv=conv, kc=kc, ks=ks, beta2p=b2p, carter_m=mc, dev=dev, beta2=b2, cu2_mid=cu_mid,
                      dP_euler_front_mid=1.2 * Um * cu_mid)


def verdict(rows):
    ok = {(r["rotor"], r["station"]): r["ok"] for r in rows}; n = sum(ok.values())
    mid = ok[("front", "mid")] and ok[("rear", "mid")]
    return n, ("ALL-SIX" if n == 6 else "MID-ONLY" if mid else "MID-FAILS")


def main(out):
    allrows, swirl, summ = [], [], {}
    for kc in (1.0, 0.85, 1.15):
        for ks in (1.0, 0.0, 0.5, 1.5):
            if kc != 1.0 and ks != 1.0: continue
            for conv in ("P", "X"):
                rows, sw = run(conv, kc, ks); allrows += rows; swirl.append(sw)
                summ[f"{conv}_kc{kc}_ks{ks}"] = verdict(rows)
    clear = all(summ[k][0] <= 3 and summ[k.replace("P_", "X_", 1)][0] > summ[k][0] for k in summ if k.startswith("P_"))
    sign = {}
    for conv in ("P", "X"):
        rows, _ = run(conv)
        for rot in ("front", "rear"):
            rr = [r for r in rows if r["rotor"] == rot]
            sign[f"{conv}_{rot}"] = dict(dgamma=rr[2]["gamma_axis"] - rr[0]["gamma_axis"], dbeta1=rr[2]["beta1_axis"] - rr[0]["beta1_axis"])
    res = dict(chi_LE=CHI_LE, chi_TE=CHI_TE, theta=THETA, verdicts=summ, clearly_inconsistent=clear, spanwise=sign,
               swirl=swirl, rows=allrows)
    json.dump(res, open(out, "w"), indent=1)
    for r in allrows:
        if r["kc"] == 1.0 and r["ks"] == 1.0:
            print(r["conv"], r["rotor"], r["station"], "U %.2f cax %.2f cu %.2f b1 %.1f g %.1f i %.1f iLE %.1f" % (
                r["U"], r["c_ax"], r["cu_in"], r["beta1_axis"], r["gamma_axis"], r["i_chord"], r["i_LE"]))
    print(json.dumps(summ)); print("clear", clear); print(json.dumps(sign))
    for s in swirl:
        if s["kc"] == 1.0 and s["ks"] == 1.0: print(s)


if __name__ == "__main__":
    main(sys.argv[1])
