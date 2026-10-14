"""QA r10b Task B job (PREREG_R10 26aa359; from r9 job_a, + fuse_many log (W6) and refused-hang): ONE design, P build planar + P build cylinder (order by a_idx parity),
W1-W3/W5 measures on both, C (cup) on cylinder if kind_C (W4 = round-7 K7). Derived from round-7 design_job.py
(build/cup/proof helpers unchanged). Usage: python job_b.py <design.json> <workdir> <result.json>"""
import hashlib, json, math, os, re, statistics, sys, threading, time, traceback
from dataclasses import asdict
from pathlib import Path

import numpy as np

d = json.loads(Path(sys.argv[1]).read_text())
wd = Path(sys.argv[2]); wd.mkdir(parents=True, exist_ok=True)
res_path = Path(sys.argv[3])
R = {"id": d["id"], "stratum": d["stratum"], "seq": d["seq"], "builds": {}, "checks": {}, "meas": {}}
os.environ["FANSIM_MEMORY_TIER"] = "8gb"
KEEP = Path(os.environ.get("STRESS_KEEP_DIR", "/tmp/stress_keep"))


def save():
    res_path.write_text(json.dumps(R, default=float))


def finite(x):
    if isinstance(x, dict):
        return all(finite(v) for v in x.values())
    if isinstance(x, (list, tuple)):
        return all(finite(v) for v in x)
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return math.isfinite(x)
    return True


class Sampler:
    """Peak RSS (MB) of this process's descendants (the build worker), sampled every 0.2 s."""
    def __init__(self):
        self.peak = 0; self._stop = False
        self.t = threading.Thread(target=self.run, daemon=True); self.t.start()

    def kids(self):
        me = os.getpid(); ch = {}
        for p in os.listdir("/proc"):
            if p.isdigit():
                try:
                    with open(f"/proc/{p}/stat") as f:
                        pp = int(f.read().rsplit(")", 1)[1].split()[1])
                    ch.setdefault(pp, []).append(int(p))
                except (OSError, ValueError, IndexError):
                    pass
        out, todo = [], list(ch.get(me, []))
        while todo:
            p = todo.pop(); out.append(p); todo += ch.get(p, [])
        return out

    def run(self):
        while not self._stop:
            tot = 0
            for p in self.kids():
                try:
                    with open(f"/proc/{p}/status") as f:
                        for ln in f:
                            if ln.startswith("VmRSS:"):
                                tot += int(ln.split()[1]) // 1024; break
                except OSError:
                    pass
            self.peak = max(self.peak, tot)
            time.sleep(0.2)

    def stop(self):
        self._stop = True; self.t.join(1); return self.peak


def classify(exc):
    msg = f"{type(exc).__name__}: {exc}"
    if isinstance(exc, TimeoutError):
        return "TIMEOUT", msg
    if isinstance(exc, ValueError):
        return "REJECTED", msg
    if isinstance(exc, RuntimeError) and "exit" in str(exc):
        s = str(exc)
        if "ValueError" in s and ("validate" in s or "BladeParams" in s or "invalid" in s.lower()):
            return "REJECTED", msg[-1500:]
        try:
            code = int(s.split("exit ", 1)[1].split(")")[0])
        except (IndexError, ValueError):
            code = None
        pyexc = "Traceback" in s or re.search(r"\b\w+(Error|Exception)\b", s) is not None  # amendment 11
        if code is not None and (code < 0 or code >= 128 or not pyexc):
            return "CRASH", msg[-1500:]
        return "BUILD_FAIL", msg[-1500:]
    return "BUILD_FAIL", msg[-1500:]


def mem_avail_gb():
    with open("/proc/meminfo") as f:
        return next(int(l.split()[1]) for l in f if l.startswith("MemAvailable")) / 1048576


def build(kind, flat, feats, mount=None, tier="8gb", timeout=300.0, need_gb=3.0, wait_s=300):
    from fansim.geometry.isolated import build_stl_isolated
    tw = time.time(); waited_ok = wait_mem(need_gb, limit=wait_s)  # amendment 10
    gate = {"need_gb": round(need_gb, 2), "wait_s": round(time.time() - tw, 1), "met": waited_ok,
            "mem_avail_gb_start": round(mem_avail_gb(), 2)}
    if not waited_ok and kind != "P":
        R["builds"][kind] = {"outcome": "SKIPPED_MEM", "gate": gate}; save(); return None
    os.environ["FANSIM_MEMORY_TIER"] = tier
    out = wd / f"{kind}.stl"
    out.unlink(missing_ok=True)
    flog = wd / f"{kind}.faces"; flog.unlink(missing_ok=True)
    os.environ["STRESS_FACES_LOG"] = str(flog)
    qlog = wd / f"{kind}.fuse"; qlog.unlink(missing_ok=True); os.environ["QA_FUSE_LOG"] = str(qlog)
    s = Sampler(); t0 = time.time(); m0 = time.monotonic(); c0 = os.times()
    try:
        build_stl_isolated(flat, feats, out, timeout=timeout, preview=False, motor_mount=mount)
        oc, err = "OK", None
    except BaseException as exc:  # noqa: BLE001
        oc, err = classify(exc)
    c1 = os.times(); wall = time.time() - t0; mono = time.monotonic() - m0
    b = {"outcome": oc, "s": round(wall, 2), "mono_s": round(mono, 2),
         "child_cpu_s": round((c1.children_user + c1.children_system) - (c0.children_user + c0.children_system), 2),
         "suspect_suspend": bool(wall - mono > 60), "peak_mb": s.stop(), "tier": tier, "err": err, "gate": gate}
    os.environ.pop("STRESS_FACES_LOG", None); os.environ.pop("QA_FUSE_LOG", None)
    if qlog.exists():
        b["fuse_calls"] = [json.loads(x) for x in qlog.read_text().splitlines() if x.strip()]; qlog.unlink(missing_ok=True)
    if b["outcome"] != "OK" and b.get("err") and "hang" in b["err"] and "below the hub" in b["err"]:
        b["outcome"] = "REFUSED_HANG"
    if flog.exists():
        nf = [int(x) for x in flog.read_text().split() if x.strip().isdigit()]
        b["fuse_n_faces"] = nf; flog.unlink(missing_ok=True)
    if oc == "OK" and out.is_file():
        b["sha256"] = hashlib.sha256(out.read_bytes()).hexdigest()
        b["bytes"] = out.stat().st_size
    elif oc == "OK":
        b["outcome"], b["err"] = "BUILD_FAIL", "exit 0 but no STL"
    R["builds"][kind] = b
    os.environ["FANSIM_MEMORY_TIER"] = "8gb"
    save()
    return out if b["outcome"] == "OK" else None


def measure_p(kind, p, params, hub_face):
    import trimesh
    from fansim.geometry.blade import TIP_TRIM_TOL_MM, open_tip_rmax_mm
    from fansim.audit.direction import prove_direction
    from fansim.cfd.orientation import builder_direction_refusal
    from fansim.geometry.blade import signed_design_camber
    m = trimesh.load(p, force="mesh"); areas = m.area_faces
    P = {"faces": len(m.faces), "watertight": bool(m.is_watertight), "bodies": len(m.split(only_watertight=False)),
         "volume": float(m.volume), "degenerate": int((areas < 1e-9).sum()), "zmin": float(m.bounds[0][2]),
         "rmax": float(np.hypot(m.vertices[:, 0], m.vertices[:, 1]).max())}
    t = float(getattr(params, "shroud_thick_mm", 0) or 0)
    P["k2"] = P["watertight"] and P["bodies"] == 1 and P["volume"] > 0 and P["degenerate"] == 0
    P["k3"] = P["zmin"] >= hub_face - 0.05
    if t > 0:
        P["ring_r"] = open_tip_rmax_mm(params) + t; P["k4"] = abs(P["rmax"] - P["ring_r"]) <= 0.1
    else:
        P["k4"] = P["rmax"] <= params.tip_radius + TIP_TRIM_TOL_MM
    try:
        dc = float(signed_design_camber(params)); pr = prove_direction(m); K = proof_record(pr); K["design_camber"] = dc
        if pr.verdict == "CONCLUSIVE":
            why = builder_direction_refusal(pr, dc); K["refusal"] = why[:300] if why else None
            K["k5"] = "FAIL" if why else "PASS"
        else:
            K["k5"] = "INCONCLUSIVE"
        P["K5"] = K
    except Exception as exc:  # noqa: BLE001
        P["K5"] = {"k5": "ERROR", "err": f"{type(exc).__name__}: {exc}"[-400:]}
    M = R["meas"]; M[kind] = P
    if not (P["k2"] and P["k3"] and P["k4"]) and p.stat().st_size < 8e6:
        KEEP.mkdir(parents=True, exist_ok=True)
        if len(list(KEEP.glob("*.stl"))) < 12:
            import shutil; shutil.copy(p, KEEP / f"{d['id']}_{kind}.stl")
    save()


def main():
    import trimesh
    from fansim.fan_spec import get_fan_spec, mount_min_hub_radius
    from fansim.geometry.blade import _hub_axial_range, validate_blade_params
    from fansim.geometry.features import Features
    from fansim.optimize.search_space import blade_from_flat
    C = R["checks"]; M = R["meas"]; R["group"] = d.get("group")
    feats = d.get("features") or {}
    fl = {"planar": dict(d["flat"], section_wrap="planar"), "cylinder": dict(d["flat"], section_wrap="cylinder")}
    params = {}
    for w in fl:
        try:
            params[w] = blade_from_flat(fl[w], Features(**feats))
            if w == "cylinder":
                from fansim.geometry.blade import blade_hang_below_hub_mm
                R["designed_hang"] = blade_hang_below_hub_mm(params[w])
            validate_blade_params(params[w])
            R.setdefault("wrap_attr", {})[w] = params[w].section_wrap
        except ValueError as exc:
            R["builds"]["P" + w[0]] = {"outcome": "REFUSED_HANG" if "below the hub's motor face" in str(exc) else "REJECTED", "err": f"ValueError: {exc}"}
            params.pop(w, None)
    hub_face = float(_hub_axial_range(params.get("cylinder") or params.get("planar"))[0]) if params else None
    M["hub_face_z"] = hub_face
    order = ["planar", "cylinder"] if d["a_idx"] % 2 == 0 else ["cylinder", "planar"]
    for w in order:
        if w not in params:
            continue
        k = "P" + w[0]
        p = build(k, fl[w], feats)
        if p is not None:
            measure_p(k, p, params[w], hub_face); k12(R["builds"][k], k); p.unlink(missing_ok=True)
    if d.get("kind_C") and "cylinder" in params:
        spec = get_fan_spec("a12x25"); mmin = mount_min_hub_radius(spec); pc = params["cylinder"]
        if mmin is not None and pc.hub_radius < mmin:
            C["K7"] = "N/A"
        else:
            mount = asdict(spec.motor_mount)
            from fansim.manufacturability.print_export import mount_hub_params
            gp, gnote = mount_hub_params(pc, spec.motor_mount)
            hub_face_c = float(_hub_axial_range(gp)[0]); M["hub_face_z_mount"] = hub_face_c
            c = build("C", fl["cylinder"], feats, mount=mount, tier="8gb", timeout=600.0, need_gb=3.5, wait_s=900)  # amendment A1
            if c is None and R["builds"]["C"].get("outcome") == "SKIPPED_MEM":
                C["K7"] = "N/A_SKIPPED_MEM"
            elif c is None:
                C["K7"] = "FAIL_BUILD"
            else:
                cm = trimesh.load(c, force="mesh")
                M["C"] = cup_measure(cm, hub_face_c, spec.motor_mount)
                M["C"].update(zmin=float(cm.bounds[0][2]), volume=float(cm.volume), watertight=bool(cm.is_watertight))
                k = M["C"]
                C["K7"] = "PASS" if (k.get("floor_above_hub_face") is not None and abs(k["floor_above_hub_face"] - 13.0) <= 0.2
                                     and k["grip_count"] == 20 and abs(k["grip_protrude_mm"] - 0.70) <= 0.15) else "FAIL"
                c.unlink(missing_ok=True)
    save()


def proof_record(pr, sections=True):
    note = pr.note or ""
    if pr.verdict == "CONCLUSIVE":
        reason = None
    elif note.startswith("no cambered"):
        reason = "no_cambered_sections"
    elif note.startswith("sections span only"):
        reason = "single_radius"
    elif note.startswith("sections disagree"):
        reason = "sections_disagree"
    else:
        reason = "other"
    rd = list(pr.readings or ())
    out = {"verdict": pr.verdict, "omega": pr.omega_sign, "pump": pr.pump_sign, "chirality": pr.chirality,
           "agreement": pr.agreement, "n": pr.n_sections, "note": note[:200], "reason": reason}
    mflat = re.search(r"(\d+) flat", note); mlow = re.search(r"(\d+) low-quality", note)
    out["n_flat_skipped"] = int(mflat.group(1)) if mflat else None
    out["n_lowq_skipped"] = int(mlow.group(1)) if mlow else None
    if rd:
        chis = [int(r.chirality) for r in rd]
        out["section_chirality_majority"] = max(set(chis), key=chis.count)
        out["camber_ratio_median"] = float(statistics.median(float(r.camber_ratio) for r in rd))
        if sections:
            out["sections"] = [{"r": round(float(r.r_mm), 3), "omega": int(r.omega_sign), "pump": int(r.pump_sign),
                                "chi": int(r.chirality), "camber_ratio": round(float(r.camber_ratio), 5)} for r in rd]
    return out


def k12(b, kind="P"):
    """PREREG amendment 8: fuse memory model vs measured peak (P build)."""
    from fansim.resources import FUSE_MARGIN, fuse_peak_estimate_gb
    nf = b.get("fuse_n_faces") or []
    if b.get("outcome") != "OK" or not nf:
        R["checks"]["K12_" + kind] = "N/A"; return
    n = max(nf); est = fuse_peak_estimate_gb(n); act = b["peak_mb"] / 1024
    have = b.get("gate", {}).get("mem_avail_gb_start")
    R["meas"]["K12_" + kind] = {"n_faces": n, "est_gb": round(est, 3), "peak_gb": round(act, 3),
                        "resid_gb": round(act - est, 3), "ratio": round(act / est, 3),
                        "guard_would_refuse": (est * FUSE_MARGIN > have) if have is not None else None,
                        "suspect_suspend": b.get("suspect_suspend")}
    R["checks"]["K12_" + kind] = "FAIL" if act > FUSE_MARGIN * est else "PASS"


def wait_mem(gb, limit=600):
    t0 = time.time()
    while time.time() - t0 < limit:
        with open("/proc/meminfo") as f:
            av = next(int(l.split()[1]) for l in f if l.startswith("MemAvailable")) / 1048576
        if av >= gb:
            return True
        time.sleep(5)
    return False


def cup_measure(m, hub_face, mount):
    def prof(z, n):
        a = np.linspace(0, 2 * np.pi, n, endpoint=False)
        loc, idx, _ = m.ray.intersects_location(np.tile([0, 0, z], (n, 1)), np.c_[np.cos(a), np.sin(a), 0 * a])
        r = np.full(n, np.inf)
        for q, i in zip(loc, idx):
            rr = math.hypot(q[0], q[1])
            if rr > 1e-6:
                r[i] = min(r[i], rr)
        return r
    rc = mount.cavity_dia_mm / 2 + (mount.grip_clearance_mm or 0)
    lo, hi = m.bounds[0][2], m.bounds[1][2]
    zs = np.arange(lo + 0.01, hi, 0.05)
    incup = []
    for z in zs:
        r = prof(z, 36); fin = r[np.isfinite(r)]
        incup.append(len(fin) == 36 and abs(np.median(fin) - rc) < 0.3)
    incup = np.array(incup)
    if not incup.any():
        return {"cup_found": False, "floor_above_hub_face": None, "grip_count": 0, "grip_protrude_mm": 0.0}
    top = float(zs[incup].max()) + 0.025  # cup floor (open side is at zmin)
    zmid = float(zs[incup].mean())
    r = prof(zmid, 2880); wall = float(np.median(r[np.isfinite(r)])); tip = float(np.min(r))
    pad = r < wall - 0.35
    return {"cup_found": True, "floor_z": top, "floor_above_hub_face": top - hub_face,
            "cup_dia_mm": 2 * wall, "grip_count": int(np.sum(pad & ~np.roll(pad, 1))),
            "grip_protrude_mm": wall - tip}


try:
    main()
except Exception:  # noqa: BLE001
    R["job_error"] = traceback.format_exc()[-2000:]
save()
