"""r28 E (PREREG f208f30): export print-ready Stock A12x25 with and without a print-id via export_print_ready; no CFD.
Usage: python e_export.py <outdir> <code>"""
import json, sys, time
from pathlib import Path
from fansim.geometry.config import load_blade_params
from fansim.fan_spec import get_fan_spec
from fansim.manufacturability.print_export import export_print_ready
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True); code = sys.argv[2]
p = load_blade_params("config/problems/a12x25_reference.yaml"); mount = get_fan_spec("a12x25").motor_mount
R = {"code": code, "hub_radius": p.hub_radius, "rear_bore_dia_mm": getattr(mount, "rear_bore_dia_mm", None)}
for tag, pid in (("sibling", None), ("marked", code)):
    t0 = time.monotonic()
    try:
        rep = export_print_ready(p, out / f"{tag}.stl", mount=mount, print_id=pid, also_step=True)
        R[tag] = {k: (v if isinstance(v, (int, float, str, bool, type(None))) else str(v)) for k, v in vars(rep).items()}
    except Exception as e:  # noqa: BLE001
        import traceback; R[tag] = {"error": traceback.format_exc()[-1500:]}
    R[tag]["build_s"] = round(time.monotonic() - t0, 1)
    json.dump(R, open(out / "export.json", "w"), indent=1, default=str)
print(json.dumps(R, indent=1, default=str))
