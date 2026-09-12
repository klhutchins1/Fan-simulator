"""Sand-grain wall roughness for OpenFOAM ``nut`` BCs (roadmap §7.6 stage 2).

Default screening stays smooth ``nutkWallFunction``. Opt-in ``wall_ks_mm`` switches the
printed impeller (and optional frame/stator) to ``nutkRoughWallFunction``. The circular
screening casing stays smooth — it is a duct artifact, not an FDM part.
"""

from __future__ import annotations

# ~0.2 mm FDM layer → sand-grain order of magnitude (not a fit to one paper).
FDM_WALL_KS_MM = 0.10
ROUGH_CS = 0.5


def wall_ks_m(wall_ks_mm: float | None) -> float:
    """Non-negative roughness height in metres; ``None`` / ≤0 → smooth (0)."""
    if wall_ks_mm is None:
        return 0.0
    return max(0.0, float(wall_ks_mm) * 1e-3)


def nut_wall_bc(name: str, wall_ks_m: float = 0.0) -> str:
    """One ``0/nut`` boundary patch block (trailing newline)."""
    ks = float(wall_ks_m)
    if ks > 0.0:
        return (
            f"    {name}\n"
            f"    {{\n"
            f"        type            nutkRoughWallFunction;\n"
            f"        Ks              uniform {ks};\n"
            f"        Cs              uniform {ROUGH_CS};\n"
            f"        value           uniform 0;\n"
            f"    }}\n"
        )
    return f"    {name} {{ type nutkWallFunction; value uniform 0; }}\n"
