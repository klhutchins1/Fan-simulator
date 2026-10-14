"""QA r10 Task A (PREREG_R10 26aa359): hub-face mark-spec on print-ready wrapped Stock v3. Usage: python a_mark.py <outdir>"""
import ast, json, math, sys, time
from dataclasses import asdict
from pathlib import Path
import numpy as np, trimesh
import cadquery as cq
from fansim.geometry.config import load_blade_params
from fansim.geometry import export_stl
from fansim.geometry.blade import _hub_axial_range
from fansim.fan_spec import get_fan_spec
from fansim.manufacturability.print_export import build_impeller_with_mount, mount_hub_params
OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
src = Path("/workspace/fansim/repo-r9/handoff/2026-10-12_from-qa-9/scripts/job_a.py").read_text()
fn = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == "cup_measure")
ns = {"np": np, "math": math}; exec(ast.get_source_segment(src, fn), ns); cup_measure = ns["cup_measure"]
R = {}
p = load_blade_params("config/problems/a12x25_reference.yaml"); spec = get_fan_spec("a12x25"); mount = spec.motor_mount
gp, note = mount_hub_params(p, mount); zb, zt = map(float, _hub_axial_range(gp)); R.update(section_wrap=p.section_wrap, hub_radius=p.hub_radius, root_embed=p.root_embed, hub_z=[zb, zt], grow_note=note, mount=asdict(mount))
t0 = time.monotonic(); model, fits, msg = build_impeller_with_mount(p, mount); R["build_s"] = round(time.monotonic() - t0, 1); R["mount_fits"] = fits; R["mount_msg"] = msg
shape = model.val(); R["solids"] = len(shape.Solids())
def mesh_of(shp, name):
    f = OUT / name; export_stl(cq.Workplane(obj=shp), f, tolerance=0.02, angular_tolerance=0.1); return trimesh.load(f, force="mesh")
m = mesh_of(shape, "stock_print.stl")
def basic(mm, hub_face):
    d = {"watertight": bool(mm.is_watertight), "bodies": len(mm.split(only_watertight=False)), "volume": float(mm.volume), "zmin": float(mm.bounds[0][2]), "zmax": float(mm.bounds[1][2])}
    d["K7"] = cup_measure(mm, hub_face, mount); return d
R["base"] = basic(m, zb)
def grid(mm, z_plane, up):
    """Equivalent of the registered first-hit ray grid (no embree on the box; 0.7 M rays were too slow): a cell is flat face
    iff it lies in the projection of the plane's flat triangles (all vertices within 0.02 mm of the plane, normal along the
    face) and no material in front of the plane (faces with centroid > 0.02 mm in front, r <= hub_radius + 2.5) projects onto
    it. Rasterised with PIL at 0.025 mm/px; polar grid cells sample the nearest pixel."""
    from PIL import Image, ImageDraw
    rs = np.arange(0.0, p.hub_radius + 2.0, 0.05); th = np.radians(np.arange(0, 360, 0.25))
    RR, TT = np.meshgrid(rs, th, indexing="ij"); x, y = RR * np.cos(TT), RR * np.sin(TT)
    tri = mm.vertices[mm.faces]; cz = tri[:, :, 2].mean(1); nz = mm.face_normals[:, 2]; cr = np.hypot(tri[:, :, 0].mean(1), tri[:, :, 1].mean(1))
    sgn = 1 if up else -1
    fl = (np.abs(tri[:, :, 2] - z_plane).max(1) <= 0.02) & (sgn * nz > 0.999)
    oc = (sgn * (cz - z_plane) > 0.02) & (cr <= p.hub_radius + 2.5)
    L = p.hub_radius + 3.0; px = 0.025; N = int(2 * L / px) + 1
    img = Image.new("1", (N, N), 0); dr = ImageDraw.Draw(img)
    to = lambda T: [((float(v[0]) + L) / px, (float(v[1]) + L) / px) for v in T]
    for T in tri[fl]: dr.polygon(to(T), fill=1)
    for T in tri[oc]: dr.polygon(to(T), fill=0, outline=0)
    A = np.array(img, bool)  # A[row=y, col=x]
    ix = np.clip(np.rint((x + L) / px).astype(int), 0, N - 1); iy = np.clip(np.rint((y + L) / px).astype(int), 0, N - 1)
    return rs, np.degrees(th), A[iy, ix], {"n_flat_tri": int(fl.sum()), "n_occluder_tri": int(oc.sum())}
def ring_stats(rs, th, ok):
    # per theta: contiguous flat radial runs; report the run containing the most cells (outermost if tie)
    runs = []
    for j in range(ok.shape[1]):
        col = ok[:, j]; best = (0, 0, 0)
        i = 0
        while i < len(col):
            if col[i]:
                k = i
                while k < len(col) and col[k]: k += 1
                if (k - i) >= best[2]: best = (rs[i], rs[k - 1], k - i)
                i = k
            else: i += 1
        runs.append(best[:2])
    runs = np.array(runs, float); return runs
def best_annulus(rs, th, ok, width=6.0, arc=25.0):
    """max-arc contiguous theta window over which a fixed radial band [a, a+width] is all flat; search a."""
    best = None; n = ok.shape[1]
    for a in np.arange(0, rs[-1] - width, 0.1):
        band = ok[(rs >= a - 1e-9) & (rs <= a + width + 1e-9), :].all(axis=0)
        if band.all(): L = 360.0
        else:
            b2 = np.r_[band, band]; L = cur = 0
            for v in b2:
                cur = cur + 1 if v else 0; L = max(L, cur)
            L = min(L, n) * 0.25
        if best is None or L > best[1]: best = (float(a), L)
    return {"width": width, "r_in": best[0], "r_out": best[0] + width, "arc_deg": best[1], "pass": best[1] >= arc}
for face, up, zp in (("top", True, zt), ("bed", False, zb)):
    rs, th, ok, gi = grid(m, zp, up); runs = ring_stats(rs, th, ok)
    np.savez_compressed(OUT / f"grid_{face}.npz", rs=rs, th=th, ok=ok)
    w = runs[:, 1] - runs[:, 0]
    R[face] = {"grid_info": gi, "z_plane": zp, "flat_frac_of_disk": float(ok[rs <= p.hub_radius].mean()), "run_r_in_median": float(np.median(runs[:, 0])),
               "run_r_out_min": float(runs[:, 1].min()), "run_r_out_median": float(np.median(runs[:, 1])), "run_width_min": float(w.min()), "run_width_median": float(np.median(w)),
               "M1_6mm": best_annulus(rs, th, ok), "max_width_full_circle": None}
    for wd in np.arange(12, 0, -0.5):
        if best_annulus(rs, th, ok, width=wd)["arc_deg"] >= 360: R[face]["max_width_full_circle"] = float(wd); break
    for wd in (8.0, 10.0):
        R[face][f"annulus_{int(wd)}mm"] = best_annulus(rs, th, ok, width=wd)
# blade material in the hub top plane: min r of mesh section at zt - 0.05 outside hub circle? use section of blades just above top
sec = m.section(plane_origin=[0, 0, zt + 0.05], plane_normal=[0, 0, 1])
R["blade_rmin_just_above_top"] = float(np.hypot(sec.vertices[:, 0], sec.vertices[:, 1]).min()) if sec is not None else None
(OUT / "a_geom.json").write_text(json.dumps(R, indent=1, default=float)); print(json.dumps({k: R[k] for k in ("top", "bed", "blade_rmin_just_above_top")}, indent=1, default=float), flush=True)
# pocket
face = "top" if R["top"]["M1_6mm"]["pass"] else ("bed" if R["bed"]["M1_6mm"]["pass"] else None); R["pocket_face"] = face
if face:
    g = np.load(OUT / f"grid_{face}.npz"); rs, th, ok = g["rs"], g["th"], g["ok"]
    A = R[face]["M1_6mm"]; rc = A["r_in"] + 3.0
    # theta centre: a theta where the band is flat, with the most flat margin
    band = ok[(rs >= A["r_in"]) & (rs <= A["r_out"]), :].all(axis=0); idx = np.where(band)[0]
    # choose centre of longest run
    b2 = np.r_[band, band]; best = (0, 0); cur = 0
    for i, v in enumerate(b2):
        cur = cur + 1 if v else 0
        if cur > best[1]: best = (i - cur + 1, cur)
    tc = ((best[0] + best[1] / 2) * 0.25) % 360 if best[1] < len(band) else 90.0
    zp = R[face]["z_plane"]; sgn = -1 if face == "top" else 1
    R["pocket"] = {"r_c": rc, "theta_c_deg": tc, "z_face": zp, "depth": 0.5, "l_tan": 8.0, "w_rad": 3.2,
                   "r_inner": rc - 1.6, "r_outer_corner": math.hypot(rc + 1.6, 4.0), "theta_span_deg": math.degrees(2 * math.atan(4.0 / (rc - 1.6)))}
    # M3 footprint check on the grid (dilated 1 mm): all cells inside dilated rect must be flat
    RR, TT = np.meshgrid(rs, np.radians(th), indexing="ij"); X, Y = RR * np.cos(TT), RR * np.sin(TT)
    c, s = math.cos(math.radians(tc)), math.sin(math.radians(tc)); u = X * c + Y * s - rc; v = -X * s + Y * c
    inside = (np.abs(u) <= 1.6 + 1.0) & (np.abs(v) <= 4.0 + 1.0)
    R["M3_footprint_cells"] = int(inside.sum()); R["M3_footprint_all_flat"] = bool(ok[inside].all())
    cav_r = mount.cavity_dia_mm / 2 + (mount.grip_clearance_mm or 0); R["cavity_reach_r"] = cav_r
    floor_z = R["base"]["K7"].get("floor_z"); R["cup_floor_z"] = floor_z
    pocket_floor = zp - 0.5 if face == "top" else zp + 0.5
    overl = (rc - 1.6 - 1.0) < cav_r
    R["M3_axial_gap_to_cup_floor"] = (pocket_floor - floor_z) if (face == "top" and floor_z is not None) else None
    R["M3_radial_gap_to_cavity"] = (rc - 1.6) - cav_r
    box = cq.Solid.makeBox(3.2, 8.0, 0.6, cq.Vector(rc - 1.6, -4.0, (zp - 0.5) if face == "top" else (zp - 0.1)))
    box = box.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), tc)
    t1 = time.monotonic(); cut = shape.cut(box); R["cut_s"] = round(time.monotonic() - t1, 1); R["cut_solids"] = len(cut.Solids())
    m2 = mesh_of(cut, "stock_print_pocket.stl"); R["pocketed"] = basic(m2, zb)
    R["dV_mm3"] = R["base"]["volume"] - R["pocketed"]["volume"]
    k0, k1 = R["base"]["K7"], R["pocketed"]["K7"]
    k7 = lambda k: k.get("floor_above_hub_face") is not None and abs(k["floor_above_hub_face"] - 13.0) <= 0.2 and k.get("grip_count") == 20 and abs(k.get("grip_protrude_mm", 0) - 0.70) <= 0.15
    R["K7_base"], R["K7_pocket"] = k7(k0), k7(k1)
    R["M2"] = bool(R["cut_solids"] == 1 and R["pocketed"]["watertight"] and R["pocketed"]["bodies"] == 1 and abs(R["dV_mm3"] - 12.8) <= 1.5 and R["K7_base"] and R["K7_pocket"])
    gap_ok = (R["M3_axial_gap_to_cup_floor"] is None or R["M3_axial_gap_to_cup_floor"] >= 1.0) if overl else R["M3_radial_gap_to_cavity"] >= 1.0
    R["M3"] = bool(R["M3_footprint_all_flat"] and gap_ok)
    R["aero_ratio"] = (8 * 3.2) / (math.pi * p.hub_radius ** 2)
(OUT / "a_geom.json").write_text(json.dumps(R, indent=1, default=float))
print(json.dumps({k: R.get(k) for k in ("pocket_face", "pocket", "M2", "M3", "M3_footprint_all_flat", "M3_axial_gap_to_cup_floor", "M3_radial_gap_to_cavity", "dV_mm3", "cut_solids", "K7_base", "K7_pocket", "aero_ratio", "build_s")}, indent=1, default=float))
