"""Counter-rotating stacked rotors (roadmap §4.2) — geometry scaffold."""

from fansim.cror.geometry import CrorParams, build_cror, export_cror_stl

__all__ = ["CrorArchetype", "CrorParams", "build_cror", "export_cror_stl"]


def __getattr__(name: str):
    if name == "CrorArchetype":
        from fansim.cror.archetype import CrorArchetype
        return CrorArchetype
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
