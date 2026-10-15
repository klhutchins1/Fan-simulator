"""Subprocess worker: build volute preview or impeller+casing STLs from a JSON job."""

from __future__ import annotations

import json
import os
import sys


def main() -> int:
    job = json.loads(open(sys.argv[1], encoding="utf-8").read())
    from fansim.isolated_job import watch_parent

    watch_parent(job)  # exit if the cockpit that started us is gone (QA-37)
    from fansim.volute.geometry import (
        export_volute_preview_stl,
        export_volute_stls,
    )
    from fansim.volute.params_io import volute_params_from_flat

    params = volute_params_from_flat(job["flat"])
    kind = job.get("kind", "preview")
    if kind == "stls":
        export_volute_stls(params, job["out_dir"])
    else:
        export_volute_preview_stl(params, job["out"])
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
