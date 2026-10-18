"""QA r16 hang (PREREG 52eca5f, Option B G1 control): rebuild a G1-failed design WITHOUT the skirt (original hub,
clip off, then a12x25 mount growth as Export does). Same failure => not caused by the extension.
Usage: python optB_g1_control.py <p1.jsonl> <id>"""
import json, sys, os
from dataclasses import replace
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from p2_built import params_of
from fansim.fan_spec import get_fan_spec
from fansim.manufacturability.print_export import build_impeller_with_mount
P1 = {json.loads(l)["id"]: json.loads(l) for l in open(sys.argv[1])}
p = replace(params_of(P1[sys.argv[2]]), clip_below_hub=False)
try:
    model, fits, msg = build_impeller_with_mount(p, get_fan_spec("a12x25").motor_mount)
    print(json.dumps(dict(id=sys.argv[2], control="original hub, clip off", build_ok=True, fits=bool(fits), msg=msg)))
except Exception as exc:  # noqa: BLE001
    print(json.dumps(dict(id=sys.argv[2], control="original hub, clip off", build_ok=False, error=f"{type(exc).__name__}: {exc}"[:300])))
