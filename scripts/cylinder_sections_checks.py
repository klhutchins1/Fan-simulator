"""Pre-registered checks V1, V3 and V4 for wrapped blade sections (roadmap 27.4).

Spec: docs/superpowers/specs/2026-10-12-cylinder-sections-design.md (checks fixed before any build).

    python scripts/cylinder_sections_checks.py --main "T:/Projects/Fan Simulator" --out runs/cyl_checks.json

``--main`` is the checkout that holds runs/ and the gitignored QA data (stress inputs, QA round-8 sample).

- V1  built = sliders: cylinder-cut chord within 3 % of the slider; cut camber within 0.005 and stagger
      within 1.5 deg of the SAME section read analytically through the same estimator (that removes the
      estimator's own bias, as QA round 8 did per station).
- V3  20 stress designs (full blade count) build watertight, one body, inside the tip radius, nothing
      below the hub face.
- V4  the cylinder direction proof on wrapped rebuilds of the QA-19 cases makes 0 CONCLUSIVE-wrong calls.

V1 and V4 build 2 blades (sections are read per blade; disclosed as in QA rounds 7-8).
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import gzip
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fansim.audit.direction import prove_direction
from fansim.geometry import build_impeller, export_stl
from fansim.geometry.blade import _hub_axial_range, _section_points_3d
from fansim.geometry.chord_realisation import _station_measure_fracs
from fansim.geometry.config import load_blade_params
from fansim.geometry.features import Features
from fansim.optimize.search_space import blade_from_flat
from fansim.validation.section_compare import _measure_loop, measure_sections

CHORD_REL, CAMBER_ABS, STAGGER_DEG = 0.03, 0.005, 1.5
EXPECTED = (1, -1, -1)  # builder convention: omega +1, pump -1, chirality -1


def _stress_rows(main: Path) -> dict[str, dict]:
    p = main / "handoff/2026-10-11_from-qa-7/stress/inputs.jsonl.gz"
    return {r["id"]: r for r in (json.loads(ln) for ln in gzip.open(p, "rt")) if not r.get("sample_error")}


def _from_stress(row) -> object:
    return blade_from_flat(row["flat"], Features(**(row.get("features") or {})))


def _from_design_json(path: Path):
    d = json.loads(path.read_text(encoding="utf-8"))
    flat = {k: v for k, v in d["params"].items() if k != "section_wrap"}  # rebuild it WRAPPED
    return blade_from_flat(flat)


def _from_csv(main: Path, design_id: str):
    with open(main / "handoff/2026-10-09_to-qa-2/cfd_designs.csv", newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["design_id"] == design_id:
                return blade_from_flat(json.loads(row["flat"]))
    raise KeyError(design_id)


def _wrapped(p, n_blades=None):
    kw = {"section_wrap": "cylinder"}
    if n_blades:
        kw["n_blades"] = n_blades
    return dataclasses.replace(p, **kw)


def _build_mesh(p, td: Path, name: str):
    stl = td / f"{name}.stl"
    export_stl(build_impeller(p), stl)
    m = trimesh.load(stl, force="mesh")
    m.merge_vertices()
    return stl, m


def _analytic(p, st, r_mm: float, omega: int, n: int) -> dict | None:
    """The station's designed section, wrapped at r with no lean/sweep, read by the same estimator."""
    kw = {k: v for k, v in _thick_kw(p).items()}
    pts = _section_points_3d(
        r=r_mm, r_frac=st.r_frac, chord=st.chord, stagger_deg=st.stagger_deg, thickness=st.thickness,
        max_camber=st.max_camber, camber_pos=st.camber_pos, sweep=0.0, skew=0.0, le_sweep=0.0,
        lean_deg=0.0, n_chord=max(int(p.n_chord), 60), features=Features(), **kw)
    arr = np.array([[v.x, v.y, v.z] for v in pts])
    return _measure_loop(arr, r_mm, omega, n)


def _thick_kw(p):
    from fansim.geometry.blade import _thick_scale_kw

    kw = _thick_scale_kw(p)
    kw["wrap"] = True
    return kw


def v1(designs, td: Path) -> dict:
    out, all_ok = {}, True
    for name, p in designs:
        p2 = _wrapped(p, 2)
        stl, _ = _build_mesh(p2, td, name)
        fr = _station_measure_fracs(p2)
        pairs = [(f, s) for f, s in zip(fr, p2.stations) if f is not None]
        rows = measure_sections(stl, [f for f, _ in pairs])
        recs = []
        for (f, s), r in zip(pairs, rows):
            if not r.get("n_blades"):
                recs.append({"r_frac_tip": f, "ok": False, "why": "no section"})
                all_ok = False
                continue
            a = _analytic(p2, s, r["r_mm"], int(r.get("omega_sign", 1)), int(r["n_blades"]))
            d_chord = r["chord_mm"] / s.chord - 1.0
            d_camb = r["camber_ratio"] - a["camber_ratio"]
            d_stag = r["stagger_deg"] - a["stagger_deg"]
            ok = abs(d_chord) <= CHORD_REL and abs(d_camb) <= CAMBER_ABS and abs(d_stag) <= STAGGER_DEG
            all_ok &= ok
            recs.append({"r_mm": round(r["r_mm"], 2), "chord": [s.chord, round(r["chord_mm"], 2)],
                         "camber_slider": s.max_camber, "camber_cut": round(r["camber_ratio"], 4),
                         "camber_analytic": round(a["camber_ratio"], 4),
                         "stagger": [s.stagger_deg, round(r["stagger_deg"], 2), round(a["stagger_deg"], 2)],
                         "d_chord": round(d_chord, 4), "d_camber": round(d_camb, 4),
                         "d_stagger": round(d_stag, 2), "ok": bool(ok)})
            print(f"V1 {name:10s} r {r['r_mm']:5.1f} chord {d_chord:+.3f} camber {d_camb:+.4f} "
                  f"stagger {d_stag:+.2f} {'ok' if ok else 'FAIL'}", flush=True)
        out[name] = recs
    return {"pass": bool(all_ok), "designs": out}


def v3(designs, td: Path) -> dict:
    out, all_ok = {}, True
    for name, p in designs:
        p2 = _wrapped(p)
        t0 = time.monotonic()
        try:
            _, m = _build_mesh(p2, td, name)
        except Exception as exc:  # noqa: BLE001 — a build failure is a V3 FAIL, recorded
            out[name] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"[:300]}
            all_ok = False
            print(f"V3 {name:10s} BUILD FAIL {exc}", flush=True)
            continue
        rmax = float(np.max(np.hypot(m.vertices[:, 0], m.vertices[:, 1])))
        z_face = float(_hub_axial_range(p2)[0])
        bodies = len(m.split(only_watertight=False))
        ok = (m.is_watertight and bodies == 1 and rmax <= p2.tip_radius + 0.05
              and float(m.bounds[0][2]) >= z_face - 0.05 and m.volume > 0)
        all_ok &= ok
        out[name] = {"ok": bool(ok), "watertight": bool(m.is_watertight), "bodies": bodies,
                     "rmax": round(rmax, 3), "tip": round(p2.tip_radius, 3),
                     "zmin": round(float(m.bounds[0][2]), 3), "hub_face": round(z_face, 3),
                     "volume": round(float(m.volume), 1), "s": round(time.monotonic() - t0, 1)}
        print(f"V3 {name:10s} {out[name]}", flush=True)
    return {"pass": bool(all_ok), "designs": out}


def v4(designs, td: Path) -> dict:
    out, wrong, conclusive = {}, 0, 0
    for name, p in designs:
        _, m = _build_mesh(_wrapped(p, 2), td, name)
        pr = prove_direction(m)
        got = (pr.omega_sign, pr.pump_sign, pr.chirality)
        is_c = pr.verdict == "CONCLUSIVE"
        bad = is_c and tuple(got) != EXPECTED
        conclusive += is_c
        wrong += bad
        out[name] = {"verdict": pr.verdict, "omega_pump_chi": got, "wrong": bool(bad), "note": pr.note}
        print(f"V4 {name:10s} {pr.verdict:12s} {got} {'WRONG' if bad else ''}", flush=True)
    return {"pass": wrong == 0, "wrong": wrong, "conclusive": conclusive, "n": len(designs),
            "designs": out}


def pick_v1(main: Path, stress: dict) -> list:
    picks = [("stock", load_blade_params(ROOT / "config/problems/a12x25_reference.yaml")),
             ("t9005", _from_csv(main, "t9005")), ("t9003", _from_csv(main, "t9003")),
             ("lt120", load_blade_params(ROOT / "docs/qa/benchmarks/lt120/fansim_params.json"))]
    plain, feat = [], []
    for sid in sorted(stress):
        r = stress[sid]
        if abs(float(r["flat"].get("lean_tip", 0.0))) < 30.0:
            continue
        (feat if Features(**(r.get("features") or {})).active else plain).append(sid)
    for sid in plain[:3] + feat[:1]:
        picks.append((sid, _from_stress(stress[sid])))
    return picks


def pick_v3(stress: dict) -> list:
    ids = sorted(stress)
    chosen: list[str] = []
    for s in ("S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"):
        chosen += [i for i in ids if stress[i]["stratum"] == s][:2]

    def first(pred):
        return next((i for i in ids if i not in chosen and pred(stress[i])), None)

    extras = [first(lambda r: float(r["flat"].get("shroud_thick_mm", 0) or 0) > 0),
              first(lambda r: int(r["flat"].get("tip_notch_count", 0) or 0) > 0
                    or r["flat"].get("notched_tips")),
              first(lambda r: Features(**(r.get("features") or {})).active),
              first(lambda r: float(r["flat"].get("winglet_sweep", 0) or 0) != 0
                    or float(r["flat"].get("winglet_lean", 0) or 0) != 0)]
    chosen += [e for e in extras if e]
    for i in ids:
        if len(chosen) >= 20:
            break
        if i not in chosen:
            chosen.append(i)
    return [(i, _from_stress(stress[i])) for i in chosen[:20]]


def pick_v4(main: Path, stress: dict) -> list:
    picks = []
    for t, run in (("9605", "top5"), ("9606", "reserve"), ("9620", "reserve"), ("9630", "reserve")):
        picks.append((t, _from_design_json(
            main / f"runs/bem_screen_r3_{run}/cockpit_assess/design_{t}/design.json")))
    named = ["S3_0002", "S4_0005", "S4_0012", "S3_0014"]
    sample = main / "handoff/2026-10-12_from-qa-8/data/b_sample.jsonl.gz"
    with gzip.open(sample, "rt") as fh:
        cell = [r["id"] for r in (json.loads(ln) for ln in fh) if r["cell_sel"] == "S3cell"]
    for sid in named + [c for c in cell if c not in named]:
        if sid in stress:
            picks.append((sid, _from_stress(stress[sid])))
        else:
            print(f"V4 {sid}: not in the stress inputs, skipped", flush=True)
    return picks


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--main", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--only", choices=("V1", "V3", "V4"), action="append")
    a = ap.parse_args(argv)
    stress = _stress_rows(a.main)
    res = json.loads(a.out.read_text()) if a.out.is_file() else {}
    with tempfile.TemporaryDirectory() as tdn:
        td = Path(tdn)
        for key, fn, picker in (("V1", v1, lambda: pick_v1(a.main, stress)),
                                ("V3", v3, lambda: pick_v3(stress)),
                                ("V4", v4, lambda: pick_v4(a.main, stress))):
            if a.only and key not in a.only:
                continue
            res[key] = fn(picker(), td)
            a.out.parent.mkdir(parents=True, exist_ok=True)
            a.out.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
            print(f"{key}: {'PASS' if res[key]['pass'] else 'FAIL'}", flush=True)
    return 0


if __name__ == "__main__":
    rc = main()
    sys.stdout.flush()
    os._exit(rc)
