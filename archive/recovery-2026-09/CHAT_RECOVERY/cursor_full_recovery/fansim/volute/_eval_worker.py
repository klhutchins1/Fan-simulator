"""Subprocess worker: run evaluate_volute from a JSON job."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict


def main() -> int:
    job = json.loads(open(sys.argv[1], encoding="utf-8").read())
    from fansim.volute.evaluate import evaluate_volute
    from fansim.volute.params_io import volute_params_from_flat

    params = volute_params_from_flat(job["flat"])
    result = evaluate_volute(
        params,
        job["workdir"],
        procs=int(job.get("procs", 8)),
        base_cell=float(job.get("base_cell", 0.006)),
        iters=int(job.get("iters", 500)),
        load_pa=float(job.get("load_pa", 50.0)),
        rpm=float(job.get("rpm", 3000.0)),
        mesh_only=bool(job.get("mesh_only", False)),
    )
    with open(job["out"], "w", encoding="utf-8") as f:
        json.dump(asdict(result), f)
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
