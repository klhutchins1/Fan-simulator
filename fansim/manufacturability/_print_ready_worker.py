"""Subprocess worker: print-ready Stock export (roadmap 23.55).

The OCCT cup fuse peaks ~7.6 GB and keeps it. Running it here means the pytest parent
does not hold that RSS after the test (QA-15 S5: isolation does not lower the *worker*
peak, it does drop the suite peak).
"""

from __future__ import annotations

import json
import os
import sys


def main() -> int:
    job = json.loads(open(sys.argv[1], encoding="utf-8").read())
    from fansim.isolated_job import watch_parent

    watch_parent(job)  # exit if the cockpit that started us is gone (QA-37)
    from fansim.fan_spec import MotorMount
    from fansim.manufacturability.print_export import export_print_ready
    from fansim.optimize.search_space import blade_from_flat

    params = blade_from_flat(job["flat"])
    mount = MotorMount(**job["mount"]) if job.get("mount") else None
    rep = export_print_ready(
        params,
        job["out"],
        mount=mount,
        also_step=bool(job.get("also_step", True)),
    )
    with open(job["result"], "w", encoding="utf-8") as fh:
        json.dump(
            {
                "ok": bool(rep.ok),
                "mount_fits": rep.mount_fits,
                "mount_msg": rep.mount_msg or "",
            },
            fh,
        )
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        import traceback

        traceback.print_exc()
        sys.stderr.write(f"{type(exc).__name__}: {exc}\n")
        os._exit(3)
