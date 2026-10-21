"""QA r19 B (PREREG_R19 cab2825): fansim BEMT (as shipped) on the TUD benchmark prop and UIUC DA4002. Resumable jsonl.
Usage: python b_bemt.py <tud_geom.txt> <tud_forces.json> <uiuc_dir> <sda1075_section.json> <out.jsonl>"""
import json, math, os, sys, time
from fansim.geometry.blade import BladeParams, RadialStation
from fansim.propeller import bemt
from fansim.propeller.polar import nondim

MM_PER_IN = 25.4


def geom_rows(path):
    rows = []
    for line in open(path):
        try: rows.append(tuple(float(x) for x in line.split()[:3]))
        except ValueError: pass
    return rows


def blade(rows, R_mm, *, thickness, camber, twist_add=0.0, chord_scale=1.0, n_blades=2):
    r0 = rows[0][0]
    st = [RadialStation((rr - r0) / (1.0 - r0), cr * R_mm * chord_scale, b + twist_add, thickness, camber, 0.4) for rr, cr, b in rows]
    return BladeParams(n_blades=n_blades, hub_radius=r0 * R_mm, tip_radius=R_mm, stations=st)


def cases(tud_geom, tud_forces, uiuc, sda):
    F = json.load(open(tud_forces)); Js = [round(p["J"], 4) for p in F["CT"]["points"]]
    tud = geom_rows(tud_geom); out = []
    for sec, (t, c) in (("known_naca4412", (0.12, 0.04)), ("generic_naca4406", (0.06, 0.04))):
        for be in ("table", "neuralfoil"):
            out.append(dict(prop="TUD", section=sec, backend=be, variant="nominal", rpm=5000.0, D_m=0.30, Js=Js, t=t, c=c))
    for be in ("table", "neuralfoil"):
        for v in ("twist+0.5", "twist-0.5", "chord+2%", "chord-2%", "rho1.18", "nelem48"):
            out.append(dict(prop="TUD", section="known_naca4412", backend=be, variant=v, rpm=5000.0, D_m=0.30, Js=Js, t=0.12, c=0.04))
    S = json.load(open(sda)); Jd = [0.0, 0.24, 0.4, 0.6]
    for g in ("design", "surveyed"):
        for be in ("table", "neuralfoil"):
            for rpm in (5028.0, 3030.0):
                out.append(dict(prop="DA4002", geom=g, section="sda1075_mapped", backend=be, variant="nominal", rpm=rpm, D_m=9.05 * 0.0254,
                                Js=Jd, t=round(S["thickness"], 4), c=round(S["camber"], 4)))
            out.append(dict(prop="DA4002", geom=g, section="generic_naca4406", backend=be, variant="nominal", rpm=5028.0, D_m=9.05 * 0.0254,
                            Js=Jd, t=0.06, c=0.04))
    for k, c in enumerate(out): c["key"] = f"{c['prop']}|{c.get('geom','')}|{c['section']}|{c['backend']}|{c['variant']}|{int(c['rpm'])}"
    return out


def run(c, tud_geom, uiuc):
    bemt.set_polar_backend(c["backend"])
    rows = geom_rows(tud_geom) if c["prop"] == "TUD" else geom_rows(os.path.join(uiuc, "da4002_geom.txt" if c["geom"] == "design" else "da4002_9x6.75_geom.txt"))
    R = c["D_m"] * 500.0; v = c["variant"]
    kw = dict(thickness=c["t"], camber=c["c"], twist_add=0.5 if v == "twist+0.5" else -0.5 if v == "twist-0.5" else 0.0,
              chord_scale=1.02 if v == "chord+2%" else 0.98 if v == "chord-2%" else 1.0)
    p = blade(rows, R, **kw); rho = 1.18 if v == "rho1.18" else bemt.RHO_AIR; ne = 48 if v == "nelem48" else 24
    res = []
    for J in c["Js"]:
        V = J * c["rpm"] / 60.0 * c["D_m"]
        perf = bemt.analyze(p, rpm=c["rpm"], v_forward=V, rho=rho, n_elem=ne)
        nd = nondim(perf.thrust_n, perf.power_w, rpm=c["rpm"], diameter_m=c["D_m"], v_inf=V, rho=rho)
        res.append(dict(J=J, CT=nd["CT"], CP=nd["CP"], T=perf.thrust_n, P=perf.power_w, converged=bool(perf.converged)))
    return res


def main(tud_geom, tud_forces, uiuc, sda, out):
    C = cases(tud_geom, tud_forces, uiuc, sda)
    done = {json.loads(l)["key"] for l in open(out)} if os.path.exists(out) else set()
    t0 = time.monotonic(); print("cases", len(C), "todo", len([c for c in C if c["key"] not in done]), flush=True)
    for c in C:
        if c["key"] in done: continue
        t1 = time.monotonic(); rec = dict(c)
        try: rec["res"] = run(c, tud_geom, uiuc)
        except Exception as e: rec["error"] = f"{type(e).__name__}: {e}"[:300]
        rec["mono_s"] = round(time.monotonic() - t1, 1)
        with open(out, "a") as f: f.write(json.dumps(rec) + "\n")
        print(c["key"], rec.get("error") or [(r["J"], round(r["CT"], 4), round(r["CP"], 4)) for r in rec["res"]][:3], rec["mono_s"], round(time.monotonic() - t0), flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
