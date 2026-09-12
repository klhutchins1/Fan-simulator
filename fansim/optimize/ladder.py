# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Fidelity ladder: run cheap evals on everything, expensive evals only on what survives.

Plan Architecture principle #2 -- the optimizer should spend its expensive evaluations (fine RANS,
LBM noise) only on promising candidates. A ladder is an ordered list of Tiers; each tier evaluates
the candidates promoted from the previous one and selects which advance. Tier evaluate/promote
functions are injected, so this is pure orchestration and unit-tested with mock evaluators (no CFD).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Tier:
    name: str
    evaluate: Callable[[Any], dict]                 # candidate -> result dict (with objective keys)
    promote: Callable[[list[tuple[Any, dict]]], list] = None  # (cand,result) pairs -> subset to advance


@dataclass
class LadderRun:
    funnel: dict[str, int] = field(default_factory=dict)         # tier name -> #evaluated
    records: list[dict] = field(default_factory=list)            # per candidate: results + top tier

    def reached(self, tier_name: str) -> list:
        """Candidates that reached (were evaluated at) the named tier."""
        return [r["candidate"] for r in self.records if tier_name in r["results"]]


def top_k(k: int, key: str, maximize: bool = True) -> Callable:
    """Promote the k best candidates by a scalar result key."""
    def _sel(pairs):
        ordered = sorted(pairs, key=lambda cr: cr[1].get(key, float("-inf")), reverse=maximize)
        return [c for c, _ in ordered[:k]]
    return _sel


def _dominates(a: dict, b: dict, keys, directions) -> bool:
    """True if result a Pareto-dominates b over the given objective keys/directions."""
    better_any = False
    for key, d in zip(keys, directions):
        av, bv = a.get(key, 0.0), b.get(key, 0.0)
        if d == "minimize":
            av, bv = -av, -bv
        if av < bv:
            return False
        if av > bv:
            better_any = True
    return better_any


def pareto_front(objective_keys, directions) -> Callable:
    """Promote the non-dominated (Pareto-front) candidates over the given objectives."""
    def _sel(pairs):
        front = []
        for i, (ci, ri) in enumerate(pairs):
            if not any(_dominates(rj, ri, objective_keys, directions)
                       for j, (_, rj) in enumerate(pairs) if j != i):
                front.append(ci)
        return front
    return _sel


class FidelityLadder:
    """Route candidates through ordered tiers, promoting only survivors to the expensive ones."""

    def __init__(self, tiers: list[Tier]):
        if not tiers:
            raise ValueError("need at least one tier")
        self.tiers = tiers

    def run(self, candidates: list) -> LadderRun:
        run = LadderRun()
        results: dict[int, dict] = {id(c): {"candidate": c, "results": {}, "top_tier": None}
                                    for c in candidates}
        current = list(candidates)
        for tier in self.tiers:
            run.funnel[tier.name] = len(current)
            pairs = []
            for c in current:
                res = tier.evaluate(c)
                rec = results[id(c)]
                rec["results"][tier.name] = res
                rec["top_tier"] = tier.name
                pairs.append((c, res))
            if tier.promote is None or tier is self.tiers[-1]:
                break
            current = tier.promote(pairs)
        run.records = list(results.values())
        return run
