# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Bio-inspired blade features, applied as perturbations to airfoil sections.

Each feature modulates the chordwise (a) and thickness (b) coordinates of a section as a
function of spanwise position ``r_frac`` and chordwise fraction ``x`` (0 = leading edge,
1 = trailing edge). They are deliberately implemented as smooth deformations of the loft --
not boolean cuts -- so the resulting solid stays watertight and meshable.

  * tubercles  -- humpback-whale leading-edge undulation (delays stall; can cut noise)
  * serrations -- owl-wing sawtooth trailing edge (broadband noise reduction)
  * dimples    -- golf-ball-style surface depressions (trip the boundary layer)

References: Miklosovic 2004 (tubercles), Howe 1991 (TE serrations), plus the fan-specific
studies in docs/bibliography.md.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

TWO_PI = 2.0 * np.pi


@dataclass
class Features:
    """Feature-layer parameters. All amplitudes 0 => feature off (base blade)."""

    tubercle_amp: float = 0.0      # leading-edge undulation, fraction of chord
    tubercle_waves: int = 0        # number of undulations along the span
    serration_amp: float = 0.0     # trailing-edge sawtooth depth, fraction of chord
    serration_waves: int = 0       # number of serrations along the span
    dimple_amp: float = 0.0        # depression depth, fraction of local thickness
    dimple_rows: int = 0           # dimples along the chord
    dimple_cols: int = 0           # dimples along the span

    @property
    def active(self) -> bool:
        return bool(
            (self.tubercle_amp > 0 and self.tubercle_waves > 0)
            or (self.serration_amp > 0 and self.serration_waves > 0)
            or (self.dimple_amp > 0 and self.dimple_rows > 0 and self.dimple_cols > 0)
        )

    # Loft resolution per feature wave. Kept modest (~6/wave) so featured geometry stays
    # light enough to generate and mesh quickly; capped so the search can't explode it.
    SECTIONS_PER_WAVE = 6
    MAX_SPAN_SECTIONS = 72

    def required_span_sections(self, base: int) -> int:
        """Spanwise loft resolution needed to resolve the active features."""
        waves = max(self.tubercle_waves, self.serration_waves, self.dimple_cols)
        need = base if waves == 0 else max(base, self.SECTIONS_PER_WAVE * waves + 1)
        return min(need, self.MAX_SPAN_SECTIONS)

    def required_chord_points(self, base: int) -> int:
        if self.dimple_rows > 0:
            return min(max(base, 6 * self.dimple_rows), 96)
        return base


def _sawtooth(phase: np.ndarray | float) -> np.ndarray | float:
    """Triangular wave in [-1, 1] with unit period (symmetric serration teeth)."""
    frac = np.asarray(phase) % 1.0
    return 2.0 * np.abs(2.0 * (frac - np.floor(frac + 0.5))) - 1.0


def apply_features(
    x: np.ndarray, a: np.ndarray, b: np.ndarray, r_frac: float, chord: float, feat: Features
) -> tuple[np.ndarray, np.ndarray]:
    """Return (a, b) modified in place-safe fashion for the active features.

    ``a`` is chordwise distance from mid-chord (LE negative, TE positive); ``b`` is
    thickness-wise distance. ``x`` is the chord fraction of each point (0=LE, 1=TE).
    """
    a = a.copy()
    b = b.copy()

    if feat.tubercle_amp > 0 and feat.tubercle_waves > 0:
        # Undulate the leading edge; effect ramps from full at LE (x=0) to 0 at mid-chord.
        ramp_le = np.clip((0.5 - x) / 0.5, 0.0, 1.0)
        delta = feat.tubercle_amp * chord * np.cos(TWO_PI * feat.tubercle_waves * r_frac)
        a = a - delta * ramp_le  # negative a = forward (leading edge)

    if feat.serration_amp > 0 and feat.serration_waves > 0:
        # Sawtooth the trailing edge; effect ramps from 0 at mid-chord to full at TE (x=1).
        ramp_te = np.clip((x - 0.5) / 0.5, 0.0, 1.0)
        delta = feat.serration_amp * chord * _sawtooth(feat.serration_waves * r_frac)
        a = a + delta * ramp_te

    if feat.dimple_amp > 0 and feat.dimple_rows > 0 and feat.dimple_cols > 0:
        # Grid of smooth depressions: thin the section locally (dents both surfaces inward).
        along_chord = 0.5 + 0.5 * np.cos(TWO_PI * feat.dimple_rows * x)
        along_span = 0.5 + 0.5 * np.cos(TWO_PI * feat.dimple_cols * r_frac)
        factor = 1.0 - feat.dimple_amp * along_chord * along_span
        b = b * np.clip(factor, 0.2, 1.0)  # keep thickness safely positive

    return a, b
