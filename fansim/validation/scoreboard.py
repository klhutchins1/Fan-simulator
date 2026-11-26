"""Validation scoreboard (RV-2): published-data claims, recomputed where possible and re-judged.

Claims live in ``docs/validation/scoreboard_claims.yaml``; the page is ``docs/validation/scoreboard.md``.
Each claim is judged only by the tolerance its own audit fixed before the data. Claims with no
pre-registered tolerance are shown as NOT JUDGED. Claims backed only by a markdown number are shown
as such, so the gap is visible.
"""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
CLAIMS_PATH = ROOT / "docs" / "validation" / "scoreboard_claims.yaml"
PAGE_PATH = Path("docs/validation/scoreboard.md")

UIUC_DIAMETER_IN = {"apcsf_9x4.7": 9.0, "apce_9x6": 9.0}
UIUC_STATIC_RPM = 6000.0


# ---------------------------------------------------------------- live: BEMT vs UIUC (Audit #3 procedure)

def _uiuc_coeffs(blade, dia_in: float, rpm: float, j: float) -> tuple[float, float]:
    from fansim.propeller.bemt import RHO_AIR, analyze

    d = dia_in * 0.0254
    n = rpm / 60.0
    p = analyze(blade, rpm, v_forward=j * n * d)
    return p.thrust_n / (RHO_AIR * n**2 * d**4), p.power_w / (RHO_AIR * n**3 * d**5)


def _uiuc_blade(prefix: str):
    from fansim.propeller.bemt_catalog import UIUC_DIR, load_uiuc_geometry_blade

    return load_uiuc_geometry_blade(UIUC_DIR / f"{prefix}_geom.txt", UIUC_DIAMETER_IN[prefix])


def uiuc_static(prefix: str) -> dict[str, float]:
    """Static C_T / C_P near 6000 rpm: UIUC measured vs BEMT on the UIUC geometry."""
    from fansim.propeller.bemt_catalog import UIUC_DIR, load_uiuc_performance

    rows = load_uiuc_performance(next(iter(sorted(UIUC_DIR.glob(f"{prefix}_static_*.txt")))))
    rpm, ct, cp = min(rows, key=lambda r: abs(r[0] - UIUC_STATIC_RPM))
    c, p = _uiuc_coeffs(_uiuc_blade(prefix), UIUC_DIAMETER_IN[prefix], rpm, 0.0)
    return {"rpm": rpm, "ct_pub": ct, "cp_pub": cp, "ct_ours": c, "cp_ours": p}


def _sweep_files(prefix: str) -> list[Path]:
    from fansim.propeller.bemt_catalog import UIUC_DIR

    return sorted(f for f in UIUC_DIR.glob(f"{prefix}_*_*.txt")
                  if "static" not in f.name and "geom" not in f.name)


def uiuc_ct_rms(prefix: str) -> float:
    """Worst C_T(J) RMS error over every UIUC sweep file for ``prefix``."""
    from fansim.propeller.bemt_catalog import load_uiuc_performance

    blade = _uiuc_blade(prefix)
    dia = UIUC_DIAMETER_IN[prefix]
    worst = 0.0
    for f in _sweep_files(prefix):
        rpm = float(f.stem.split("_")[-1])
        errs = [_uiuc_coeffs(blade, dia, rpm, j)[0] - ct for j, ct, _cp, _eta in load_uiuc_performance(f)]
        if errs:
            worst = max(worst, math.sqrt(sum(e * e for e in errs) / len(errs)))
    return worst


# ---------------------------------------------------------------- evaluation

def load_claims(path: Path = CLAIMS_PATH) -> list[dict[str, Any]]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))["claims"]


def _json_path(data: Any, path: str) -> float:
    for tok in re.findall(r"\[(\d+)\]|\.?([A-Za-z_][A-Za-z0-9_]*)", path):
        idx, key = tok
        data = data[int(idx)] if idx else data[key]
    return float(data)


def _from_data(spec: dict) -> float:
    import json

    return _json_path(json.loads((ROOT / spec["file"]).read_text(encoding="utf-8")), spec["path"])


def judge(ours: float, published: float | None, tol: dict | None) -> str:
    """PASS / FAIL under a pre-registered tolerance; NOT JUDGED without one."""
    if not tol:
        return "NOT JUDGED"
    eps = 1e-12
    if "rel" in tol:
        return "PASS" if abs(ours / published - 1.0) <= tol["rel"] + eps else "FAIL"
    if "abs" in tol:
        return "PASS" if abs(ours - published) <= tol["abs"] + eps else "FAIL"
    if "max" in tol:
        return "PASS" if ours <= tol["max"] + eps else "FAIL"
    raise ValueError(f"unknown tolerance {tol}")


def _live(spec: dict) -> tuple[float | None, float]:
    if spec["func"] == "uiuc_static":
        s = uiuc_static(spec["prefix"])
        k = spec["coeff"]
        return s[f"{k}_pub"], s[f"{k}_ours"]
    if spec["func"] == "uiuc_ct_rms":
        return None, uiuc_ct_rms(spec["prefix"])
    raise ValueError(f"unknown live func {spec['func']}")


def evaluate(claims: list[dict]) -> list[dict[str, Any]]:
    rows = []
    for c in claims:
        ours_spec, pub_spec = c["ours"], c["published"]
        kind = ours_spec["kind"]
        if kind == "live":
            pub, ours = _live(ours_spec)
        elif kind == "data":
            ours = _from_data(ours_spec)
            pub = _from_data(pub_spec) if pub_spec.get("kind") == "data" else float(pub_spec["value"])
        else:
            ours = float(ours_spec["value"])
            pub = float(pub_spec["value"])
        tol = c.get("tolerance")
        error_pct = None if pub in (None, 0) else 100.0 * (ours / pub - 1.0)
        if pub is None:
            error_text = f"{ours:.4f}"
        elif tol and "abs" in tol:
            error_text = f"{ours - pub:+.1f} {pub_spec.get('unit', '')}".strip()
        else:
            error_text = f"{error_pct:+.1f} %"
        rows.append({
            "id": c["id"], "surface": c["surface"], "quantity": c["quantity"], "kind": kind,
            "published": pub, "ours": ours, "unit": pub_spec.get("unit", ""),
            "source": pub_spec.get("source", ""), "error_pct": error_pct, "error_text": error_text,
            "tolerance": tol, "verdict": judge(ours, pub, tol),
            "recorded_verdict": c["recorded_verdict"],
            "evidence": _evidence(ours_spec),
        })
    return rows


def _evidence(spec: dict) -> str:
    if spec["kind"] == "live":
        return "recomputed on every test run"
    if spec["kind"] == "data":
        return f"`{spec['file']}`"
    return f"**markdown only** (`{spec['where']}`), no result file committed"


# ---------------------------------------------------------------- page

def _num(x: float | None) -> str:
    if x is None:
        return "–"
    ax = abs(x)
    if ax >= 100:
        return f"{x:.0f}"
    if ax >= 10:
        return f"{x:.1f}"
    if ax >= 1:
        return f"{x:.3f}"
    return f"{x:.4f}"


def _tol_text(tol: dict | None, unit: str = "") -> str:
    if not tol:
        return "none pre-registered"
    if "rel" in tol:
        t = f"±{tol['rel'] * 100:g} %"
    elif "abs" in tol:
        u = f" {unit}" if unit not in ("", "-") else ""
        t = f"±{tol['abs']:g}{u}"
    else:
        t = f"≤ {tol['max']:g}"
    return f"{t} (`{tol['source'].split(' ')[0]}`)"


def render(rows: list[dict]) -> str:
    out = [
        "# Validation scoreboard",
        "",
        "Generated by `python scripts/scoreboard.py --write` from `docs/validation/scoreboard_claims.yaml`.",
        "Do not edit by hand. `tests/test_scoreboard.py` fails when this page is stale or when a",
        "recomputed verdict differs from the audit's.",
        "",
        "- **Verdict** uses only the tolerance the claim's audit fixed before the data.",
        "- **NOT JUDGED**: no tolerance was pre-registered, so the number is reported, not claimed as a pass.",
        "- **markdown only**: the number exists only in a report; its result file is not in the repo yet.",
        "",
        "| Surface | Quantity | Published | Ours | Error | Tolerance | Verdict | Evidence |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        unit = f" {r['unit']}" if r["unit"] not in ("", "-") else ""
        pub = _num(r["published"]) + (unit if r["published"] is not None else "")
        out.append(
            f"| {r['surface']} | {r['quantity']} | {pub} | {_num(r['ours'])}{unit} | {r['error_text']} "
            f"| {_tol_text(r['tolerance'], r['unit'])} | **{r['verdict']}** | {r['evidence']} |"
        )
    n = len(rows)
    count = {v: sum(1 for r in rows if r["verdict"] == v) for v in ("PASS", "FAIL", "NOT JUDGED")}
    md_only = sum(1 for r in rows if r["kind"] == "recorded")
    out += [
        "",
        (f"{n} claims: {count['PASS']} PASS, {count['FAIL']} FAIL, {count['NOT JUDGED']} NOT JUDGED. "
         f"{md_only} rest on a markdown number with no committed result file."),
        "",
    ]
    return "\n".join(out)


def write(path: Path = ROOT / PAGE_PATH) -> list[dict]:
    rows = evaluate(load_claims())
    Path(path).write_text(render(rows), encoding="utf-8")
    return rows
