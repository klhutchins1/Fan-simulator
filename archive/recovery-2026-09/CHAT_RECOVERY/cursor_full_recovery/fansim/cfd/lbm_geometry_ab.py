"""LBM geometry A/B campaign helpers (sickle / notched / stepped casing).

Impeller variants can run FluidX3D ``mode=shutoff`` (impeller STL + tip clearance).
Stepped inlet is a **casing** change: we export plain vs stepped ``casing.stl`` for
ducted OpenFOAM / future ducted-LBM, but do not claim shut-off Pa from impeller-only
LBM for that pair.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from fansim.geometry.blade import (
    SICKLE_DEFAULT_MM,
    apply_notched_tips,
    apply_sickle,
)
from fansim.optimize.search_space import blade_from_flat

IMPORTER_VARIANTS: tuple[tuple[str, str], ...] = (
    ("default", "baseline (no LE sickle / notches)"),
    ("sickle", "sickle LE (--sickle)"),
    ("notched_tips", "notched TE tips (--notched-tips)"),
)

CASING_VARIANTS: tuple[tuple[str, bool, str], ...] = (
    ("casing_plain", False, "plain circular duct"),
    ("casing_stepped", True, "stepped inlet (--stepped-inlet)"),
)

HONESTY = "impeller_lbm_shutoff_plus_casing_stl_export"


def load_base_params(path: Path, trial: int | None = None) -> dict:
    """Load a flat blade-param dict from trial JSON / list / bare params."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        if trial is None:
            raise ValueError("list base JSON requires --trial")
        row = next(r for r in data if int(r["trial"]) == int(trial))
        return dict(row["params"])
    if isinstance(data, dict) and "params" in data:
        return dict(data["params"])
    if isinstance(data, dict) and "n_blades" in data:
        return dict(data)
    raise ValueError(f"unrecognized base json shape in {path}")


def blade_params_for_variant(flat: dict, name: str):
    """Return BladeParams for an impeller A/B slug (no CAD build).

    Strips ``sickle_mm`` / notch stamps from the base flat so ``default`` is a
    clean baseline even when the source trial was a ``--sickle`` study.
    """
    clean = deepcopy(flat)
    sickle_mm = float(clean.pop("sickle_mm", 0.0) or 0.0)
    clean.pop("notched_tips", None)
    clean.pop("tip_notch_count", None)
    clean.pop("tip_notch_depth_mm", None)
    p = blade_from_flat(clean)
    if name == "default":
        return p
    if name == "sickle":
        apply_sickle(p, sickle_mm if sickle_mm > 0.0 else SICKLE_DEFAULT_MM)
        return p
    if name == "notched_tips":
        apply_notched_tips(p)
        return p
    raise ValueError(f"unknown impeller variant: {name}")


def compare_shutoff_deltas(
    results: list[dict[str, Any]],
    *,
    baseline: str = "default",
) -> list[dict[str, Any]]:
    """Δ shut-off Pa / residual CFM vs baseline when both rows have shutoff metrics."""
    by_name = {str(r.get("variant")): r for r in results}
    base = by_name.get(baseline)
    if not base:
        return []
    base_so = base.get("shutoff")
    if not isinstance(base_so, dict) or "shut_off_pa" not in base_so:
        return []

    out: list[dict[str, Any]] = []
    base_pa = float(base_so["shut_off_pa"])
    base_cfm = base_so.get("residual_cfm")
    for slug, _label in IMPORTER_VARIANTS:
        if slug == baseline:
            continue
        row = by_name.get(slug)
        if not row:
            continue
        so = row.get("shutoff")
        if not isinstance(so, dict) or "shut_off_pa" not in so:
            continue
        pa = float(so["shut_off_pa"])
        entry: dict[str, Any] = {
            "variant": slug,
            "vs": baseline,
            "delta_shut_off_pa": round(pa - base_pa, 2),
            "shut_off_pa": pa,
            "baseline_shut_off_pa": base_pa,
        }
        cfm = so.get("residual_cfm")
        if base_cfm is not None and cfm is not None:
            entry["delta_residual_cfm"] = round(float(cfm) - float(base_cfm), 2)
        out.append(entry)
    return out


def stepped_inlet_row(
    *,
    casing_plain: str | None,
    casing_stepped: str | None,
) -> dict[str, Any]:
    """Campaign row for stepped vs plain casing (not impeller-only LBM shut-off)."""
    return {
        "variant": "stepped_inlet",
        "label": "stepped inlet casing (--stepped-inlet)",
        "stl": None,
        "casing_plain_stl": casing_plain,
        "casing_stepped_stl": casing_stepped,
        "note": (
            "Casing-only A/B: FluidX3D mode=shutoff is impeller+tip_clear only. "
            "Use exported casing STLs with ducted OpenFOAM evaluate_candidate "
            "(--stepped-inlet) or a future ducted-LBM path; do not attribute "
            "impeller-only shut-off Pa to stepped inlet."
        ),
        "skipped": "casing-only; no impeller-only LBM shutoff",
        "shutoff": None,
    }


def summary_markdown(payload: dict[str, Any]) -> str:
    """Human-readable campaign summary from the JSON payload."""
    lines = [
        "# LBM geometry A/B",
        "",
        f"Date: {payload.get('date')}",
        f"Base: `{payload.get('base_json')}`",
        f"Honesty: `{payload.get('honesty', HONESTY)}`",
        "",
        "## Variants",
        "",
    ]
    for r in payload.get("results") or []:
        skip = r.get("skipped")
        stl = r.get("stl")
        extra = f" — skipped: {skip}" if skip else ""
        lines.append(
            f"- **{r.get('variant')}**: {r.get('label')} — stl=`{stl}`{extra}"
        )
        if r.get("casing_plain_stl") or r.get("casing_stepped_stl"):
            lines.append(
                f"  - casing plain=`{r.get('casing_plain_stl')}` "
                f"stepped=`{r.get('casing_stepped_stl')}`"
            )
    deltas = payload.get("deltas") or []
    if deltas:
        lines.extend(["", "## Shut-off deltas vs default", ""])
        for d in deltas:
            line = (
                f"- **{d['variant']}**: ΔPa={d['delta_shut_off_pa']} "
                f"({d['shut_off_pa']} vs {d['baseline_shut_off_pa']})"
            )
            if "delta_residual_cfm" in d:
                line += f", Δresidual CFM={d['delta_residual_cfm']}"
            lines.append(line)
    lines.append("")
    return "\n".join(lines)
