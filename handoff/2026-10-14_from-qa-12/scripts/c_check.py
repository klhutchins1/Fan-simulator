"""QA r12 Task C checks P0-P4 (PREREG_R12 42004b3) on the cockpit export. Usage: python c_check.py c_cockpit.json c_check.json"""
import ast, json, math, re, sys
from pathlib import Path
import numpy as np, trimesh
from fansim.manufacturability.print_id import verify_print_id
from fansim.geometry.config import load_blade_params
from fansim.geometry.blade import _hub_axial_range
from fansim.fan_spec import get_fan_spec
from fansim.manufacturability.print_export import mount_hub_params
R = json.load(open(sys.argv[1])); new = R["index_new"]
stl = Path(re.search(r"Saved (\S+\.stl)", R["export_msg"]).group(1)); name = stl.name
B = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
m0 = re.match(r"^([0-9A-Z*~$=]{5})_(.+)_(\d{8}-\d{6})\.stl$", name); pid = m0.group(1) if m0 else None
C = {"stl": str(stl), "pid": pid}
C["P0"] = bool(m0 and all(c in B for c in pid[:4]) and pid[4] in B + "*~$=U" and verify_print_id(pid))
md = stl.with_suffix(".md").read_text(); first = next(l for l in md.splitlines() if l.strip())
C["readme_first_line"] = first; C["P1"] = bool(pid and pid in first and "Sharpie" in md)
C["readme_material_lines"] = [l for l in md.splitlines() if re.search(r"PETG|PLA|nozzle|bed", l, re.I)][:8]
pf = json.loads(stl.with_name(stl.stem + "_print_fit.json").read_text())
C["print_fit_subset"] = {k: pf.get(k) for k in ("print_id", "section_wrap", "recipe_hash", "git", "material")}
C["P2"] = pf.get("print_id") == pid and all(pf.get(k) for k in ("section_wrap", "recipe_hash", "git", "material"))
C["P3"] = R["index_n1"] - R["index_n0"] == 1 and len(new) == 1 and new[0].get("print_id") == pid and Path(new[0].get("stl", "")).resolve() == stl.resolve()
m = trimesh.load(stl, force="mesh")
src = open("/workspace/fansim/repo-r10/handoff/2026-10-13_from-qa-10/scripts/job_b.py").read()
fn = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == "cup_measure")
ns = {"np": np, "math": math}; exec(ast.get_source_segment(src, fn), ns)
spec = get_fan_spec("a12x25"); p = load_blade_params("/workspace/fansim/qa/run_r12/config/problems/a12x25_reference.yaml")
gp, _ = mount_hub_params(p, spec.motor_mount); zb = float(_hub_axial_range(gp)[0])
K = ns["cup_measure"](m, zb, spec.motor_mount)
C["mesh"] = {"watertight": bool(m.is_watertight), "bodies": len(m.split(only_watertight=False)), "volume": float(m.volume),
             "degenerate": int((m.area_faces < 1e-9).sum()), "hub_face_z": zb, "K7": K}
C["P4"] = bool(m.is_watertight and C["mesh"]["bodies"] == 1 and K.get("grip_count") == 20
               and abs(K["floor_above_hub_face"] - 12.985) <= 0.05 and abs(K["grip_protrude_mm"] - 0.696) <= 0.05)
json.dump(C, open(sys.argv[2], "w"), indent=1, default=str)
print({k: C[k] for k in ("pid", "P0", "P1", "P2", "P3", "P4")}, C["mesh"]["K7"], C["mesh"]["volume"])
