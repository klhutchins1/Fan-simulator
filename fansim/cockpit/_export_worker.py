"""Subprocess worker: print-ready STL export from a JSON job (see fan_export.do_export).

Run as ``python -m fansim.cockpit._export_worker <job.json>``. Keeps the multi-minute OCP build out
of the cockpit process (GIL starvation froze the busy caption; a native crash killed the server).
"""

import json
import os
import sys


def main() -> int:
    job = json.loads(open(sys.argv[1], encoding="utf-8").read())
    os.environ["FANSIM_FUSE_GUARD"] = "1"  # cockpit Export: refuse plainly rather than swap (25.5)
    from fansim.cockpit.fan_export import do_export
    from fansim.fan_spec import fan_spec_from_dict
    from fansim.geometry.features import Features
    from fansim.optimize.search_space import blade_from_flat

    params = blade_from_flat(job["flat"], Features(**job.get("features", {})))
    summary = do_export(
        params, job["out"], fan_spec_from_dict(job["spec"]),
        bool(job.get("also_mirror")),
        print_id=job.get("print_id") or None,
        design_id=str(job.get("design_id") or ""),
    )
    with open(job["result"], "w", encoding="utf-8") as f:
        json.dump(summary, f)
    sys.stdout.flush()
    os._exit(0)  # skip the known OCP/VTK teardown segfault; the result is already written


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        sys.stderr.write(f"{type(exc).__name__}: {exc}\n")
        os._exit(3)
