"""Subprocess worker: run evaluate_mixed_flow from a JSON job."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict


def main() -> int:
    job = json.loads(open(sys.argv[1], encoding="utf-8").read())
    from fansim.isolated_job import watch_parent

    watch_parent(job)  # exit if the cockpit that started us is gone (QA-37)
    from fansim.centrifugal.evaluate import evaluate_mixed_flow
    from fansim.centrifugal.params_io import mixed_params_from_flat
    from fansim.fan_spec import fan_spec_from_dict

    params = mixed_params_from_flat(job["flat"])
    spec = fan_spec_from_dict(job["spec"])
    result = evaluate_mixed_flow(
        params,
        job["workdir"],
        spec=spec,
        procs=int(job.get("procs", 8)),
        base_cell=float(job.get("base_cell", 0.006)),
        iters=int(job.get("iters", 500)),
        load_pa=float(job.get("load_pa", 1.0)),
        refine_op=bool(job.get("refine_op", False)),
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
