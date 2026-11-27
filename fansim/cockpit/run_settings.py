"""The cockpit settings a run uses, captured when Run is pressed (roadmap 25.11, QA-22..26).

Assess, Sweep and Mixed Assess take 30-40 min. They used to read the hose, material, fan model and
library parent from the live cockpit when they *finished*, so clicking another design mid-run filed
the result with that design's labels. Every run now takes one frozen ``RunSettings`` at the click
and uses only that, both to run and to label the result.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from fansim.cfd.metrics import CFD_VERSION
from fansim.cockpit.score_caption import stamp_score_extra
from fansim.optimize.presets import assess_load


@dataclass(frozen=True)
class RunSettings:
    preset: str
    wall_ks: bool
    refine_op: bool
    material: str
    fan_model: str
    spec: Any
    parent_id: str
    place_op: str
    selected_trial: int | None

    @property
    def load_pa(self) -> float:
        return float(assess_load(self.preset)[0])


def capture(state, active_spec: Callable[[], Any]) -> RunSettings:
    sel = getattr(state, "selected_trial", None)
    return RunSettings(
        preset=str(getattr(state, "assess_preset", None) or "case"),
        wall_ks=bool(getattr(state, "assess_wall_ks", False)),
        refine_op=bool(getattr(state, "assess_refine_op", False)),
        material=str(getattr(state, "assess_material", None) or "PETG"),
        fan_model=str(getattr(state, "fan_model", None) or "a12x25"),
        spec=active_spec(),
        parent_id=str(getattr(state, "library_parent_id", None) or ""),
        place_op=str(getattr(state, "library_place_op", None) or ""),
        selected_trial=None if sel is None else int(sel),
    )


def identity_extra(s: RunSettings) -> dict:
    """Labels that say what was tested: fan model, material and (if placed) the library parent."""
    out = {"fan_model": s.fan_model, "material": s.material}
    if s.parent_id:
        out.update(parent_id=s.parent_id, place_op=s.place_op or "fit_envelope",
                   placed_on=s.fan_model, cfd_stale=False)
    return out


def stamp(extra: dict, raw: dict | None, s: RunSettings) -> None:
    """Score stamps (hose, load, refine, wall-ks) from the snapshot, plus the solver generation."""
    stamp_score_extra(extra, raw, load_pa=s.load_pa, preset=s.preset, refine_op=s.refine_op)
    if s.wall_ks:
        if float(extra.get("wall_ks_mm") or 0.0) <= 0.0:
            from fansim.cfd.wall_roughness import FDM_WALL_KS_MM

            extra["wall_ks_mm"] = float(FDM_WALL_KS_MM)
    else:
        extra.pop("wall_ks_mm", None)
    extra["cfd_version"] = CFD_VERSION
