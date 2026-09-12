# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Subprocess worker: run one full CFD evaluation from a JSON job, in an isolated process.

Run as ``python -m fansim.optimize._eval_worker <job.json>`` where the JSON is
{"flat": <flat param dict>, "features": <Features field dict>, "workdir": <case dir>,
 "spec": <fan_spec dict>, "procs": int, "base_cell": float, "iters": int, "out": <result json>}.

Isolating the whole evaluate_candidate() (CadQuery/OCP impeller build + OpenFOAM orchestration) in
its own process means a native crash (an OCP segfault, which is especially likely when geometry is
built off the main thread of the live-VTK cockpit) or a hang cannot take down the caller -- the
parent just sees a non-zero exit / timeout. Exits via os._exit(0) on success to skip the known
harmless OCP/VTK teardown segfault; the result JSON is already written by then.
"""

import json
import os
import sys
from dataclasses import asdict


def main() -> int:
    job = json.loads(open(sys.argv[1]).read())
    from fansim.fan_spec import fan_spec_from_dict
    from fansim.geometry.features import Features
    from fansim.optimize.objectives import evaluate_candidate
    from fansim.optimize.search_space import blade_from_flat

    # blade_from_flat ignores unknown (feature) keys, so a merged flat dict is safe here.
    params = blade_from_flat(job["flat"], Features(**job.get("features", {})))
    spec = fan_spec_from_dict(job["spec"])
    result = evaluate_candidate(
        params, job["workdir"],
        procs=int(job.get("procs", 8)),
        base_cell=float(job.get("base_cell", 0.006)),
        iters=int(job.get("iters", 500)),
        spec=spec,
    )
    with open(job["out"], "w") as f:
        json.dump(asdict(result), f)
    sys.stdout.flush()
    os._exit(0)  # skip OCP/VTK teardown segfault (the result JSON is already written)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 - report to the parent via stderr + non-zero exit
        import traceback
        traceback.print_exc()
        sys.stderr.write(f"{type(exc).__name__}: {exc}\n")
        os._exit(3)
