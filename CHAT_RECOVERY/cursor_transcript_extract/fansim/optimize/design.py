# EXTRACTED-FROM-CURSOR-TRANSCRIPT 2026-09-12
# source: agent-transcripts/9f43d5b7...jsonl write@3411 + 0 later StrReplace
# NOT verified against lost E: tree — re-check before deleting RECOVERED-FROM-CHAT peers.

"""Evaluated design record shared by Optuna loaders and the cockpit.

Kept outside ``fansim.cockpit`` so optimizer helpers (e.g. ``cli_argv.merge_opt_designs``)
do not import the UI layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Design:
    """One evaluated design: its parameters, objectives, and geometry file."""

    trial: int
    params: dict
    objectives: dict  # cfm_free, cfm_load, efficiency (or archetype-specific)
    feasible: bool
    is_pareto: bool
    stl_path: Path | None
    reason: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def has_model(self) -> bool:
        return self.stl_path is not None and self.stl_path.exists()
