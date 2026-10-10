"""Build + check ONE stress design (PREREG §2-3). Run by run_stress.py in its own process.
Usage: python design_job.py <design.json> <workdir> <result.json>"""
import hashlib, json, math, os, sys, threading, time, traceback
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
        if code is not None and (code < 0 or code >= 128 or "Traceback" not in s):
            return "CRASH", msg[-1500:]
        return "BUILD_FAIL", msg[-1500:]
    return "BUILD_FAIL", msg[-1500:]


def build(kind, flat, feats, mount=None, tier="8gb", timeout=300.0):
    from fansim.geometry.isolated import build_stl_isolated
    os.environ["FANSIM_MEMORY_TIER"] = tier
    out = wd / f"{kind}.stl"
    out.unlink(missing_ok=True)
    s = Sampler(); t0 = time.time(); m0 = time.monotonic(); c0 = os.times()
    try:
        build_stl_isolated(flat, feats, out, timeout=timeout, preview=False, motor_mount=mount)
        oc, err = "OK", None
    except BaseException as exc:  # noqa: BLE001
        oc, err = classify(exc)
    c1 = os.times(); wall = time.time() - t0; mono = time.monotonic() - m0
    b = {"outcome": oc, "s": round(wall, 2), "mono_s": round(mono, 2),
         "child_cpu_s": round((c1.children_user + c1.children_system) - (c0.children_user + c0.children_system), 2),
         "suspect_suspend": bool(wall - mono > 60), "peak_mb": s.stop(), "tier": tier, "err": err}
    if oc == "OK" and out.is_file():
        b["sha256"] = hashlib.sha256(out.read_bytes()).hexdigest()
        b["bytes"] = out.stat().st_size
    elif oc == "OK":
        b["outcome"], b["err"] = "BUILD_FAIL", "exit 0 but no STL"
    R["builds"][kind] = b
    os.environ["FANSIM_MEMORY_TIER"] = "8gb"
    save()
    return out if b["outcome"] == "OK" else None


def main():
    import trimesh
    from fansim.fan_spec import get_fan_spec, mount_min_hub_radius
    from fansim.geometry.blade import (TIP_TRIM_TOL_MM, _hub_axial_range, blade_solidity,
                                       min_blade_wall_mm, open_tip_rmax_mm, validate_blade_params)
    from fansim.geometry.features import Features
    from fansim.manufacturability.printability_score import grade_printability
    from fansim.optimize.search_space import blade_from_flat
    from fansim.audit.direction import prove_direction

    C = R["checks"]; M = R["meas"]
    flat, feats = d["flat"], d.get("features") or {}
    if d.get("sample_error"):
        R["builds"]["P"] = {"outcome": "REJECTED", "err": d["sample_error"]}; C["K1"] = "PASS"; return
    try:
        params = blade_from_flat(flat, Features(**feats))
        validate_blade_params(params)
    except ValueError as exc:
        R["builds"]["P"] = {"outcome": "REJECTED", "err": f"ValueError: {exc}"}; C["K1"] = "PASS"; return
    # inputs features
    st = params.stations
    M["inputs"] = {"n_blades": params.n_blades, "hub_radius": params.hub_radius, "tip_radius": params.tip_radius,
                   "max_camber": flat.get("max_camber"), "stagger": [s.stagger_deg for s in st],
                   "chord": [s.chord for s in st], "sweep": [s.sweep for s in st] if hasattr(st[0], "sweep") else None,
                   "lean": [s.lean_deg for s in st], "thickness": [s.thickness for s in st],
                   "shroud_thick_mm": float(getattr(params, "shroud_thick_mm", 0) or 0),
                   "shroud_height_frac": getattr(params, "shroud_height_frac", None)}
    # K11
    try:
        g = grade_printability(params); sol = blade_solidity(params); mw = min_blade_wall_mm(params)
        gd = {k: v for k, v in asdict(g).items() if isinstance(v, (int, float))} if hasattr(g, "__dataclass_fields__") else {}
        M["readouts"] = {"solidity": sol, "min_wall_mm": mw, "grade": gd}
        C["K11"] = "PASS" if finite(sol) and finite(mw) and finite(gd) else "FAIL"
    except Exception as exc:  # noqa: BLE001
        C["K11"] = "FAIL"; M["readouts_err"] = f"{type(exc).__name__}: {exc}"[-800:]
    save()
    # P
    p = build("P", flat, feats)
    oc = R["builds"]["P"]["outcome"]
    C["K1"] = "PASS" if oc in ("OK", "REJECTED") else "FAIL"
    hub_face = float(_hub_axial_range(params)[0]); M["hub_face_z"] = hub_face
    if p is not None:
        m = trimesh.load(p, force="mesh")
        areas = m.area_faces
        M["P"] = {"faces": len(m.faces), "verts": len(m.vertices), "watertight": bool(m.is_watertight),
                  "bodies": len(m.split(only_watertight=False)), "volume": float(m.volume),
                  "degenerate": int((areas < 1e-9).sum()), "zmin": float(m.bounds[0][2]),
                  "rmax": float(np.hypot(m.vertices[:, 0], m.vertices[:, 1]).max())}
        P = M["P"]
        C["K2"] = "PASS" if P["watertight"] and P["bodies"] == 1 and P["volume"] > 0 and P["degenerate"] == 0 else "FAIL"
        C["K3"] = "PASS" if P["zmin"] >= hub_face - 0.05 else "FAIL"
        t = M["inputs"]["shroud_thick_mm"]
        if t > 0:
            ring = open_tip_rmax_mm(params) + t; M["ring_r_designed"] = ring
            C["K4"] = "PASS" if abs(P["rmax"] - ring) <= 0.1 else "FAIL"
        else:
            C["K4"] = "PASS" if P["rmax"] <= params.tip_radius + TIP_TRIM_TOL_MM else "FAIL"
        try:
            pr = prove_direction(m)
            M["K5"] = {"verdict": pr.verdict, "omega": pr.omega_sign, "pump": pr.pump_sign,
                       "agreement": pr.agreement, "n": pr.n_sections, "note": pr.note[:200]}
            if pr.verdict == "CONCLUSIVE":
                C["K5"] = "PASS" if (pr.omega_sign, pr.pump_sign) == (1, -1) else "FAIL"
            else:
                C["K5"] = "INCONCLUSIVE"
            mm = m.copy(); T = np.eye(4); T[0, 0] = -1; mm.apply_transform(T)
            pm = prove_direction(mm)
            M["K6"] = {"verdict": pm.verdict, "omega": pm.omega_sign, "pump": pm.pump_sign}
            if pr.verdict == "CONCLUSIVE" and pm.verdict == "CONCLUSIVE":
                C["K6"] = "PASS" if pm.omega_sign == -pr.omega_sign else "FAIL"
            else:
                C["K6"] = "N/A"
        except Exception as exc:  # noqa: BLE001
            C["K5"] = "ERROR"; M["K5_err"] = f"{type(exc).__name__}: {exc}"[-500:]
        if "FAIL" in (C["K2"], C["K3"], C["K4"]) and p.stat().st_size < 5e6:
            KEEP.mkdir(parents=True, exist_ok=True)
            if len(list(KEEP.glob("*.stl"))) < 10:
                import shutil; shutil.copy(p, KEEP / f"{d['id']}_P.stl")
        save()
    # R
    if d.get("kind_R") and p is not None:
        build("R", flat, feats)
        rb = R["builds"]["R"]
        C["K10"] = "PASS" if rb.get("sha256") == R["builds"]["P"].get("sha256") else "FAIL"
    if p is not None:
        p.unlink(missing_ok=True); (wd / "R.stl").unlink(missing_ok=True)
    # C / T
    if d.get("kind_C"):
        spec = get_fan_spec("a12x25"); mmin = mount_min_hub_radius(spec)
        M["mount_min_hub_radius"] = mmin
        if mmin is not None and params.hub_radius < mmin:
            R["cup_na"] = True; C["K7"] = "N/A"
        else:
            mount = asdict(spec.motor_mount)
            c = build("C", flat, feats, mount=mount, tier="8gb", timeout=600.0)
            if c is not None:
                cm = trimesh.load(c, force="mesh")
                M["C"] = cup_measure(cm, hub_face, spec.motor_mount)
                M["C"]["volume"] = float(cm.volume); M["C"]["verts"] = len(cm.vertices)
                M["C"]["watertight"] = bool(cm.is_watertight)
                k = M["C"]
                C["K7"] = "PASS" if (k.get("floor_above_hub_face") is not None and abs(k["floor_above_hub_face"] - 13.0) <= 0.2
                                     and k["grip_count"] == 20 and abs(k["grip_protrude_mm"] - 0.70) <= 0.15) else "FAIL"
                if d.get("kind_T"):
                    tiers = {"8gb": {"volume": k["volume"], "verts": k["verts"], "sha256": R["builds"]["C"]["sha256"],
                                     "peak_mb": R["builds"]["C"]["peak_mb"], "s": R["builds"]["C"]["s"]}}
                    for tn in ("16gb", "6gb"):
                        need = max(2.0 * R["builds"]["C"]["peak_mb"] / 1024 + 1.0, 4.0)  # parallel ~1.6x serial (r4) + margin
                        R["meas"]["T16_mem_needed_gb"] = round(need, 2)
                        if tn == "16gb" and not wait_mem(need, limit=60):
                            R["builds"]["T16gb"] = {"outcome": "SKIPPED_MEM"}; continue
                        tp = build(f"T{tn}", flat, feats, mount=mount, tier=tn, timeout=600.0)
                        if tp is not None:
                            tm = trimesh.load(tp, force="mesh")
                            b = R["builds"][f"T{tn}"]
                            tiers[tn] = {"volume": float(tm.volume), "verts": len(tm.vertices), "sha256": b["sha256"],
                                         "peak_mb": b["peak_mb"], "s": b["s"]}
                            tp.unlink(missing_ok=True)
                    M["T"] = tiers
                    ref = tiers["8gb"]; eq = []; byte = []
                    for tn, v in tiers.items():
                        if tn == "8gb":
                            continue
                        eq.append(abs(v["volume"] - ref["volume"]) <= 1e-6 * abs(ref["volume"]) and v["verts"] == ref["verts"])
                        byte.append(v["sha256"] == ref["sha256"])
                    C["K8"] = ("PASS" if all(eq) else "FAIL") if eq else "N/A"
                    M["K8_byte_identical"] = all(byte) if byte else None
                    budget = {"16gb": 10.0, "8gb": 6.5, "6gb": 5.0}
                    k9 = [tiers[tn]["peak_mb"] <= budget[tn] * 1024 for tn in tiers]
                    C["K9"] = "PASS" if all(k9) else "FAIL"
                c.unlink(missing_ok=True)
    save()


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
