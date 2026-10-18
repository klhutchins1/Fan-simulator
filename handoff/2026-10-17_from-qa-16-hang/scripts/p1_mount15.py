"""QA r16 hang (report-only): the optimizer validates hang on the AUTO hub; a12x25 Export/cup Preview grow the hub to
min_hub_height_mm (15) symmetrically (mount_hub_params), which lowers the motor face by (15 - h_auto)/2. Count how the
validator verdict and the clip plane differ between the two, on P1 (analytic, uses fansim's own functions).
Usage: python p1_mount15.py <p1.jsonl> <out.json>"""
import json, sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from p2_built import params_of
from fansim.geometry import blade as B
from fansim.fan_spec import get_fan_spec
from fansim.manufacturability.print_export import mount_hub_params

mount = get_fan_spec("a12x25").motor_mount
P1 = [json.loads(l) for l in open(sys.argv[1])]
rows = []
for r in P1:
    if r["h_d"] <= 0: continue
    p = params_of(r); pm, note = mount_hub_params(p, mount)
    rows.append(dict(id=r["id"], h_d=r["h_d"], hub_h=r["hub_h"], face_shift=B._hub_axial_range(p)[0] - B._hub_axial_range(pm)[0],
                     h_d_mount=B.blade_hang_below_hub_mm(pm)))
res = dict(n_hanging=len(rows), n_auto_hub_lt15=sum(x["hub_h"] < 15 for x in rows),
           refused_auto=sum(x["h_d"] > 2 for x in rows), refused_at_mount_hub=sum(x["h_d_mount"] > 2 for x in rows),
           refused_auto_but_pass_at_mount=sum(x["h_d"] > 2 and x["h_d_mount"] <= 2 for x in rows),
           allowed_with_clip_plane_moved=sum(0 < x["h_d"] <= 2 and x["face_shift"] > 1e-6 for x in rows),
           allowed_no_longer_hanging_at_mount=sum(0 < x["h_d"] <= 2 and x["h_d_mount"] == 0 for x in rows),
           face_shift_max=max(x["face_shift"] for x in rows), rows=rows)
json.dump(res, open(sys.argv[2], "w"), indent=1)
print({k: v for k, v in res.items() if k != "rows"})
