"""Subprocess worker: build one mixed-flow STL from a JSON job."""

from __future__ import annotations

import json
import os
import sys


def main() -> int:
    job = json.loads(open(sys.argv[1], encoding="utf-8").read())
    from fansim.centrifugal.geometry import export_mixed_flow_stl
    from fansim.centrifugal.params_io import mixed_params_from_flat

    params = mixed_params_from_flat(job["flat"])
    export_mixed_flow_stl(params, job["out"])
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
