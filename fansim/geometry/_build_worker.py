"""Subprocess worker: build one impeller STL from a JSON job, in an isolated process.

Run as ``python -m fansim.geometry._build_worker <job.json>`` where the JSON is
{"flat": <flat param dict>, "features": <Features field dict>, "out": <stl path>}. Isolating the
CadQuery/OCP build in its own process means a native crash (OCP segfault) or hang can't take down
the caller (e.g. the cockpit server) -- the parent just sees a non-zero exit / timeout. Exits via
os._exit(0) on success to skip the known harmless OCP/VTK teardown segfault.
"""

import json
import os
import sys


def main() -> int:
    job = json.loads(open(sys.argv[1]).read())
    from fansim.geometry.features import Features
    from fansim.optimize.search_space import blade_from_flat

    from fansim.geometry.chord_realisation import prepare_loft_chords
    from fansim.geometry.isolated import write_progress

    prog = job.get("progress")
    mount_dict = job.get("motor_mount")
    fast = bool(job.get("preview")) and not mount_dict
    build_label = ("lofting blades + hub" if fast else
                   "building + carving motor cup" if mount_dict else "building + fusing solid")
    write_progress(prog, 1, 4, "reading design")
    params = blade_from_flat(job["flat"], Features(**job.get("features", {})))
    # The build realises loft chords itself; doing it first (disk-cached, so the build reuses it)
    # lets the caller show the stage that dominates a new design's Preview (§23.17).
    write_progress(prog, 2, 4, "realising chords")
    prepare_loft_chords(params)
    write_progress(prog, 3, 4, build_label)
    if fast:
        # FAST path: non-fused visual mesh (skips the ~140s boolean fuse). Write an accurate volume
        # sidecar so the caller's weight/spec check doesn't rely on the overlapping mesh's own volume.
        from fansim.geometry.blade import build_impeller_preview
        dense = bool(job.get("preview_dense"))
        # Dense = recipe loft + finer tessellation (gold ✕ / LE overlay); default stays screen loft.
        mesh, volume_mm3 = build_impeller_preview(
            params, tol=(0.05 if dense else 0.15), screen=not dense)
        write_progress(prog, 4, 4, "writing mesh")
        mesh.export(job["out"])
        open(job["out"] + ".meta.json", "w").write(json.dumps({"volume_mm3": volume_mm3}))
    elif mount_dict:
        from fansim.fan_spec import MotorMount
        from fansim.geometry.export import export_stl
        from fansim.manufacturability.print_export import build_impeller_with_mount

        model, _fits, _msg = build_impeller_with_mount(params, MotorMount(**mount_dict))
        write_progress(prog, 4, 4, "writing STL")
        export_stl(model, job["out"])
    else:
        from fansim.geometry import build_impeller, export_stl
        model = build_impeller(params)
        write_progress(prog, 4, 4, "writing STL")
        export_stl(model, job["out"])
    sys.stdout.flush()
    os._exit(0)  # skip OCP/VTK teardown segfault (the STL is already written)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 - report to the parent via stderr + non-zero exit
        sys.stderr.write(f"{type(exc).__name__}: {exc}\n")
        os._exit(3)
