"""One cup-fuse strategy run (QA r4 request 5). Usage: python cupfuse_job.py <strategy> <outdir>
Builds Stock (fit_envelope) -> export_print_ready(mount=spec.motor_mount) -> write_print_fit_sidecars,
recording per-stage peak RSS (VmHWM after /proc/self/clear_refs=5) into <outdir>/stages.json.
Strategies: B S1 S2 S3 S4 S5 S6 S7 (S5/S7 differ only in how the driver launches this script)."""
import json, os, sys, time
from pathlib import Path

strategy, outdir = sys.argv[1], Path(sys.argv[2])
outdir.mkdir(parents=True, exist_ok=True)
stages = []


def _hwm():
    with open("/proc/self/status") as f:
        for ln in f:
            if ln.startswith("VmHWM:"):
                return int(ln.split()[1]) // 1024
    return 0


def _reset():
    try:
        with open("/proc/self/clear_refs", "w") as f:
            f.write("5")
    except OSError:
        pass


def wrap(mod, name, label):
    fn = getattr(mod, name)

    def w(*a, **k):
        _reset(); t = time.time()
        try:
            return fn(*a, **k)
        finally:
            stages.append({"stage": label, "hwm_mb": _hwm(), "s": round(time.time() - t, 2)})
            _reset()
    setattr(mod, name, w)


import cadquery as cq  # noqa: E402
import fansim.geometry.blade as blade  # noqa: E402
import fansim.manufacturability.print_export as pe  # noqa: E402
from fansim.fan_spec import get_fan_spec  # noqa: E402
from fansim.optimize.search_space import stock_blade_flat  # noqa: E402
from fansim.cockpit.placement import fit_envelope  # noqa: E402

if strategy in ("S3", "S6"):  # serial OCCT booleans
    import cadquery.occ_impl.shapes as shp
    _orig_m = shp.Shape._bool_op

    def _bool_serial(self, args, tools, op, parallel=True):
        return _orig_m(self, args, tools, op, parallel=False)
    shp.Shape._bool_op = _bool_serial
if strategy == "S4":
    from OCP.OSD import OSD_ThreadPool
    OSD_ThreadPool.DefaultPool_s(2)


def fuse_seq(hub, blades, ring=None):
    f = hub
    for b in blades:
        f = f.fuse(b)
    f = f.clean()
    if ring is not None:
        f = f.fuse(ring).clean()
    return f


def fuse_tree(hub, blades, ring=None):
    parts = list(blades)
    while len(parts) > 1:
        nxt = [parts[i].fuse(parts[i + 1]) for i in range(0, len(parts) - 1, 2)]
        if len(parts) % 2:
            nxt.append(parts[-1])
        parts = nxt
    f = hub.fuse(parts[0]).clean()
    if ring is not None:
        f = f.fuse(ring).clean()
    return f


if strategy in ("S1", "S6"):
    blade.fuse_impeller = fuse_seq
elif strategy == "S2":
    blade.fuse_impeller = fuse_tree

wrap(blade, "build_impeller_parts", "build_parts")
wrap(pe, "carve_motor_mount", "carve_hub")
wrap(blade, "fuse_impeller", "fuse")
wrap(pe, "export_stl", "export_stl")
wrap(pe, "export_step", "export_step")
wrap(pe, "watertight_report", "watertight_report")

t0 = time.time()
spec = get_fan_spec("a12x25")
flat = fit_envelope(stock_blade_flat("a12x25"), spec).flat
from fansim.optimize.search_space import blade_from_flat  # noqa: E402
params = blade_from_flat(flat)
stl = outdir / "print.stl"
rep = pe.export_print_ready(params, stl, mount=spec.motor_mount)
from fansim.manufacturability.mount_gauge import write_print_fit_sidecars  # noqa: E402
_reset(); tg = time.time()
g = write_print_fit_sidecars(stl, spec, report_mount_fits=rep.mount_fits,
                             report_mount_msg=rep.mount_msg or "")
stages.append({"stage": "gauge", "hwm_mb": _hwm(), "s": round(time.time() - tg, 2)})
res = {"strategy": strategy, "wall_s": round(time.time() - t0, 1), "rep_ok": bool(rep.ok),
       "mount_fits": rep.mount_fits, "gauge": {"watertight": bool(g.watertight),
       "frame_ok": bool(g.frame_ok), "mount_ok": bool(g.mount_ok)}, "stages": stages,
       "env": {k: os.environ.get(k) for k in ("MALLOC_ARENA_MAX",)}}
(outdir / "stages.json").write_text(json.dumps(res, indent=1))
print(json.dumps({k: res[k] for k in ("strategy", "wall_s", "rep_ok", "gauge")}))
