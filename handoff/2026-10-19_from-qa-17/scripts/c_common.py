"""QA r17 Task C (PREREG_R17 a212b29): shared helpers. Export hub = a12x25 mount need, growth below the blades."""
from dataclasses import replace
from fansim.geometry import blade as B
from fansim.fan_spec import get_fan_spec

MOUNT = get_fan_spec("a12x25").motor_mount
NEED = max(float(MOUNT.min_hub_height_mm or 0.0), float(MOUNT.cavity_depth_mm) + float(MOUNT.min_wall_mm or 0.0))
F = 1.75; LIM = 2.0


def export_hub(p):
    z0, z1 = B._hub_axial_range(p); h0 = z1 - z0
    if h0 >= NEED - 1e-6:
        return p, 0.0
    d = NEED - h0
    px = replace(p, hub_height_mm=NEED, blade_hub_z_mm=float(p.blade_hub_z_mm or 0.0) + d / 2.0)
    x0, x1 = B._hub_axial_range(px)
    assert abs(x1 - z1) < 1e-6 and abs((z0 - x0) - d) < 1e-6, (z0, z1, x0, x1, d)
    return px, d


def rules(p):
    px, d = export_hub(p)
    hd, hx = B.blade_hang_below_hub_mm(p), B.blade_hang_below_hub_mm(px)
    try:
        B.validate_blade_params(p); v = "ok"
    except ValueError as e:
        v = "hang" if "hang" in str(e) else "other:" + str(e)[:80]
    return dict(h_d=hd, h_x=hx, dh=d, validator=v, base=hd > LIM, i=F * hd > LIM, ii=hx > LIM, both=F * hx > LIM)
