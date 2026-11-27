"""Prop CFD 2-D section CLI runner (release R2.2a / R2.2a′ rung A0).

Thin CLI wrapper over :mod:`fansim.propeller.section_2d` (RV-4, #74).

Defaults are rung A: NACA 4406 at Re 8e4, α 0–8°, SST and SST-LM.
Rung A0: ``--section 0012 --re 6e6 --alphas 0 5 10 --models kOmegaSST --tu 0.001``.

Pre-registered: docs/validation/audits/2026-10-17-prop-cfd-fix-prereg.md (rung A),
amended in docs/validation/audits/2026-10-19-prereg-amendments-r17.md section 4,
and docs/validation/audits/2026-10-20-rulings-r18-r19-rungA.md §1 (A0 vs Ladson).

The fast suite only builds the case (no Docker, no solve). The runner writes
summary.json after every α/model unit and will not start a new unit after 15:30 local.

    python scripts/prop_section_2d.py --build-only
    python scripts/prop_section_2d.py
    python scripts/prop_section_2d.py --section 0012 --re 6e6 --alphas 0 5 10 --models kOmegaSST --tu 0.001
    python scripts/prop_section_2d.py --analyze

A0c gate grid (defaults stay 48/60/32, far field 8c). Iteration count is not tuning:

    python scripts/prop_section_2d.py --build-only --mesh cgrid --section 0012 --re 6e6 --iters 10000 --cgrid-tangent 128 --cgrid-normal 120 --cgrid-wake 64 --cgrid-far 50 --cgrid-wake-len 50 --cgrid-end-cell 0.001 --cgrid-max-ratio 1.2 --cgrid-normal-growth 1.15
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fansim.propeller.section_2d import (  # noqa: F401
    A0_CD_0,
    A0_CD_TOL,
    A0_CL_5,
    A0_CL_10,
    A0_CL_TOL,
    A0_TU,
    ALPHAS,
    CGRID_U,
    CHORD,
    CMU,
    DEFAULT_SECTION,
    MODELS,
    N_CGRID_NORMAL,
    N_CGRID_TANGENT,
    N_CGRID_WAKE,
    N_ITERS,
    N_THETA,
    R_OUTER,
    RE,
    REF_CD_4,
    REF_CL_4,
    REF_CL_4_HI,
    REF_CL_4_LO,
    SPAN,
    TU_NCRIT9,
    WAKE_LEN,
    WAKE_STREAM_ASPECT,
    _cgrid_geometry,
    first_cell_yplus,
    is_a0_campaign,
    judge_summary,
    parse_cl_cd,
    parse_layer_coverage,
    parse_naca4_code,
    parse_surface_cells,
    parse_yplus,
    section_xy,
    solve_u_nu,
    u_inf,
    verdict,
    verdict_a0,
    wall_spacing_m,
    write_case,
)

OUT = ROOT / "runs" / "prop_section_2d"
CUTOFF_HOUR = 15
CUTOFF_MINUTE = 30

# Backward-compatible aliases for private names previously defined here.
_is_a0 = is_a0_campaign
_judge = judge_summary


def parse_cli(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build-only", action="store_true", help="write one SST case and stop")
    ap.add_argument("--analyze", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--iters", type=int, default=N_ITERS)
    ap.add_argument("--section", default=DEFAULT_SECTION, help="NACA 4-digit code (default 4406)")
    ap.add_argument("--re", type=float, default=RE)
    ap.add_argument("--alphas", type=float, nargs="+", default=list(ALPHAS))
    ap.add_argument("--models", nargs="+", default=list(MODELS))
    ap.add_argument("--tu", type=float, default=TU_NCRIT9, help="freestream Tu as a fraction")
    ap.add_argument(
        "--mesh", choices=("snappy", "cgrid"), default="snappy",
        help="snappy+layers (rung A default) or structured C-grid (A0 mesher fix)",
    )
    ap.add_argument("--cgrid-tangent", type=int, default=N_CGRID_TANGENT,
                    help="C-grid cells along each airfoil surface (default 48)")
    ap.add_argument("--cgrid-normal", type=int, default=N_CGRID_NORMAL,
                    help="C-grid cells from the wall to the far field (default 60)")
    ap.add_argument("--cgrid-wake", type=int, default=N_CGRID_WAKE,
                    help="minimum C-grid cells along the wake (default 32); "
                         "raised when clustering would make the outlet cell longer than the span")
    ap.add_argument("--cgrid-far", type=float, default=R_OUTER / CHORD,
                    help="far-field radius in chords (default 8)")
    ap.add_argument("--cgrid-wake-len", type=float, default=WAKE_LEN / CHORD,
                    help="wake length downstream of the trailing edge, in chords (default 16)")
    ap.add_argument("--cgrid-end-cell", type=float, default=None,
                    help="cluster the LE and TE cells to this fraction of chord")
    ap.add_argument("--cgrid-max-ratio", type=float, default=1.2,
                    help="max adjacent tangential cell-size ratio when clustering")
    ap.add_argument("--cgrid-normal-growth", type=float, default=None,
                    help="cap on wall-normal growth; the normal count is raised if needed")
    ap.add_argument("--cgrid-refine", type=int, default=1,
                    help="after the main angles, solve one angle on a grid refined by this factor")
    ap.add_argument("--cgrid-refine-alpha", type=float, default=None,
                    help="angle for the refined grid (default: the last --alphas value)")
    return ap.parse_args(argv)


def cgrid_jobs(ns: argparse.Namespace) -> list[dict]:
    """Solve campaigns. A refine factor adds one finer grid at a single angle."""
    base = {
        "alphas": [float(x) for x in ns.alphas],
        "n_tangent": int(ns.cgrid_tangent),
        "n_normal": int(ns.cgrid_normal),
        "n_wake": int(ns.cgrid_wake),
        "far_chords": float(ns.cgrid_far),
        "wake_chords": float(ns.cgrid_wake_len),
        "end_cell_frac": None if ns.cgrid_end_cell is None else float(ns.cgrid_end_cell),
        "max_ratio": float(ns.cgrid_max_ratio),
        "normal_growth": (
            None if ns.cgrid_normal_growth is None else float(ns.cgrid_normal_growth)
        ),
        "yplus_target": 0.8,
        "tag": "base",
    }
    jobs = [base]
    refine = int(ns.cgrid_refine or 1)
    if refine > 1:
        fine = dict(base)
        fine["n_tangent"] *= refine
        fine["n_normal"] *= refine
        fine["n_wake"] *= refine
        if fine["end_cell_frac"] is not None:
            fine["end_cell_frac"] = float(fine["end_cell_frac"]) / refine
        fine["yplus_target"] = 0.8 / refine
        alpha = base["alphas"][-1] if ns.cgrid_refine_alpha is None else ns.cgrid_refine_alpha
        fine["alphas"] = [float(alpha)]
        fine["tag"] = f"refine{refine}"
        jobs.append(fine)
    return jobs


def _cgrid_kwargs(job: dict | None) -> dict:
    if not job:
        return {}
    return {
        key: job[key]
        for key in (
            "n_tangent", "n_normal", "n_wake", "far_chords", "wake_chords",
            "end_cell_frac", "max_ratio", "normal_growth", "yplus_target",
        )
    }


def _past_cutoff(now: datetime | None = None) -> bool:
    t = now or datetime.now(UTC).astimezone()
    return (t.hour, t.minute) >= (CUTOFF_HOUR, CUTOFF_MINUTE)


def _write_progress(out: Path, payload: dict) -> None:
    (out / "progress.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    a = parse_cli(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    section = str(a.section)
    re_n = float(a.re)
    tu = float(a.tu)
    mesh = str(a.mesh)
    alphas = [float(x) for x in a.alphas]
    models = list(a.models)
    for m in models:
        if m not in MODELS:
            raise SystemExit(f"model must be one of {MODELS}, got {m!r}")

    n_iters = int(a.iters)
    campaigns = cgrid_jobs(a) if mesh == "cgrid" else [None]

    if a.build_only:
        write_case(
            out / "build_only", alpha_deg=alphas[0] if alphas else 4.0,
            model=models[0] if models else "kOmegaSST",
            n_iters=n_iters,
            section=section, re=re_n, tu=tu, mesh=mesh,
            **_cgrid_kwargs(campaigns[0]),
        )
        print(f"wrote {out / 'build_only'} y+={first_cell_yplus(re_n):.3f} section={section}")
        return 0

    summ_path = out / "summary.json"
    try:
        summary = json.loads(summ_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        summary = {
            "section": section, "re": re_n, "chord_m": CHORD, "tu": tu, "mesh": mesh,
            "ref_cl_4": REF_CL_4,
            "ref_cl_4_band": [REF_CL_4_LO, REF_CL_4_HI], "ref_cd_4": REF_CD_4,
            "yplus_first": first_cell_yplus(re_n), "points": {},
        }

    if a.analyze:
        v = judge_summary(summary, section=section, re=re_n, alphas=alphas)
        summary["verdict"] = v
        summ_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps(v))
        return 0

    from fansim.cfd.runner import OpenFOAMRunner, image_available

    if not image_available():
        print("OpenFOAM image not available; wrote no solves. Use --build-only.", file=sys.stderr)
        return 2

    for campaign in campaigns:
        camp_tag = "base" if campaign is None else campaign["tag"]
        ckw = _cgrid_kwargs(campaign)
        run_alphas = alphas if campaign is None else campaign["alphas"]
        bucket = summary if camp_tag == "base" else summary.setdefault(camp_tag, {"points": {}})
        points = bucket.setdefault("points", {})
        yp_req = first_cell_yplus(re_n) if campaign is None else float(campaign["yplus_target"])
        mesh_dir = out / ("_mesh" if camp_tag == "base" else f"_mesh_{camp_tag}")
        mesh_src = mesh_dir / "constant" / "polyMesh"
        if not (mesh_src / "points").is_file():
            write_case(
                mesh_dir, alpha_deg=0.0, model="kOmegaSST", n_iters=n_iters,
                section=section, re=re_n, tu=tu, mesh=mesh, **ckw,
            )
            mesh_run = OpenFOAMRunner(mesh_dir)
            mesh_run.run("blockMesh")
            coverage: float | None
            if mesh == "cgrid":
                mesh_run.run("checkMesh")
                coverage = 100.0
            else:
                mesh_run.run("surfaceFeatureExtract")
                mesh_run.run("snappyHexMesh -overwrite")
                snap_log = (mesh_dir / "logs" / "snappyHexMesh.log")
                coverage = None
                if snap_log.is_file():
                    coverage = parse_layer_coverage(
                        snap_log.read_text(encoding="utf-8", errors="replace"))
            mesh_info = {
                "kind": mesh,
                "layer_coverage_pct": coverage,
                "surface_cells": parse_surface_cells(mesh_dir),
                "yplus_requested": yp_req,
            }
            if camp_tag == "base":
                summary["mesh"] = mesh_info
            else:
                bucket["mesh"] = mesh_info
            summ_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        for model in models:
            points.setdefault(model, {})
            for alpha in run_alphas:
                key = f"{alpha:.1f}"
                if points[model].get(key, {}).get("cl") is not None:
                    continue
                if _past_cutoff():
                    _write_progress(out, {
                        "stopped": "cutoff", "next": [model, alpha], "grid": camp_tag,
                    })
                    summary["verdict"] = judge_summary(
                        summary, section=section, re=re_n, alphas=alphas)
                    summ_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
                    print("stopped before 15:30 local; remaining units left for another day")
                    return 0
                tag = f"{model}_a{key}" if camp_tag == "base" else f"{camp_tag}_{model}_a{key}"
                case = out / tag
                _write_progress(out, {"current": tag, "start": time.time()})
                write_case(
                    case, alpha_deg=alpha, model=model, n_iters=n_iters,
                    section=section, re=re_n, tu=tu, mesh=mesh, **ckw,
                )
                dest = case / "constant" / "polyMesh"
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(mesh_src, dest)
                run = OpenFOAMRunner(case)
                t0 = time.time()
                if mesh == "cgrid":
                    run.run("potentialFoam -writep")
                run.run("simpleFoam")
                parsed = parse_cl_cd(case)
                cl, cd = (None, None) if parsed is None else parsed
                yp = parse_yplus(case)
                points[model][key] = {
                    "cl": cl, "cd": cd, "wall_s": time.time() - t0,
                    "yplus_first": yp_req,
                    "yplus": yp,
                }
                summary["verdict"] = judge_summary(
                    summary, section=section, re=re_n, alphas=alphas)
                summ_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
                print(f"{tag} Cl={cl} Cd={cd} y+={yp}")
    print(json.dumps(summary.get("verdict")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
