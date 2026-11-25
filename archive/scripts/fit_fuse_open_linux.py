"""Refit Linux open-fan remaining fuse growth from QA r12 Task B (QA-35); rule in
docs/validation/audits/2026-10-15-fuse-open-refit.md (pre-registered).

    python scripts/fit_fuse_open_linux.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
R12 = ROOT / "handoff/2026-10-14_from-qa-12/data/b_results.jsonl"
GIB = 2.0 ** 30
KIB = 1024.0


def rows():
    out = []
    for line in R12.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if r.get("outcome") != "OK" or r.get("kind") == "shrouded":
            continue
        ev = {e["ev"]: e for e in r.get("events", [])}
        if "call" not in ev or "exit" not in ev:
            continue
        remaining = (ev["exit"]["VmHWM"] - ev["call"]["VmRSS"]) * KIB / GIB
        out.append((r["id"], r["kind"], int(ev["call"]["n_faces"]), remaining))
    return out


def main() -> int:
    data = rows()
    faces = np.array([d[2] for d in data], float)
    rem = np.array([d[3] for d in data], float)
    b, a = np.polyfit(faces, rem, 1)
    worst = float(np.max(rem / (a + b * faces)))
    note = "least squares"
    if worst > 1.0:
        a = float(np.max(rem / 0.95 - b * faces))
        note = "intercept raised so the worst open ratio is 0.95"
    ratios = rem / (a + b * faces)
    print(f"n={len(data)}  a={a:.3f} GiB  b={b * GIB / KIB:.1f} KiB/face  ({note})")
    for (sid, kind, f, r), q in sorted(zip(data, ratios), key=lambda z: -z[1]):
        print(f"  {sid:14s} {kind:8s} faces {f:6d}  remaining {r:.3f}  ratio {q:.3f}")
    plausible = a >= 0.0 and 50.0 <= b * GIB / KIB <= 150.0
    print("worst ratio %.3f; plausible %s" % (float(ratios.max()), plausible))
    return 0 if plausible else 1


if __name__ == "__main__":
    raise SystemExit(main())
