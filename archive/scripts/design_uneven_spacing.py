"""Design an uneven-but-balanced blade spacing that minimizes the blade-pass tone — COMPUTE-FREE.

Searches balanced spacing patterns (fansim.structural.balance) and scores each by the array-factor
peak-tone ratio (fansim.acoustics.tonal) — pure geometry/algebra, no CFD. Reports the best pattern,
its peak-tone reduction vs equal spacing, and (optionally) builds its STL. This is the whole
uneven-spacing feature's design step; evaluating the acoustic benefit in the LBM is the later,
compute-gated confirmation.

Usage:  uv run python scripts/design_uneven_spacing.py --n-blades 7 --samples 400 [--build-stl]
"""
import argparse
import json
from pathlib import Path

import numpy as np

from fansim.acoustics.tonal import (
    blade_passing_modes,
    peak_tone_reduction_db,
    tonal_peak_ratio,
)
from fansim.structural.balance import balanced_uneven_spacing, equal_spacing, static_unbalance


def _min_gap_deg(ang):
    gaps = np.degrees(np.diff(np.concatenate([ang, [ang[0] + 2 * np.pi]])))
    return float(gaps.min())


def search(n_blades, samples, spreads, seed=0, min_gap_deg=25.0):
    """Lowest peak-tone ratio among balanced patterns whose smallest gap >= min_gap_deg (no collisions)."""
    rng = np.random.default_rng(seed)
    best = None
    for _ in range(samples):
        spread = float(rng.choice(spreads))
        ang = balanced_uneven_spacing(n_blades, spread=spread, rng=rng)
        if _min_gap_deg(ang) < min_gap_deg:
            continue  # blades too close -> would collide at high solidity
        ratio = tonal_peak_ratio(ang)
        if best is None or ratio < best["ratio"]:
            best = {"angles": ang, "ratio": ratio, "spread": spread}
    if best is None:
        raise RuntimeError(f"no pattern met min_gap={min_gap_deg} deg; lower it or reduce spread")
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-blades", type=int, default=7)
    ap.add_argument("--samples", type=int, default=400)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--build-stl", action="store_true", help="also build the best pattern's impeller STL")
    ap.add_argument("--min-gap", type=float, default=25.0,
                    help="minimum angular gap [deg] between adjacent blades (avoid collisions)")
    a = ap.parse_args()

    spreads = np.linspace(0.15, 0.9, 16)
    best = search(a.n_blades, a.samples, spreads, a.seed, min_gap_deg=a.min_gap)
    ang = best["angles"]
    gaps = np.degrees(np.diff(np.concatenate([ang, [ang[0] + 2 * np.pi]])))
    red = peak_tone_reduction_db(ang)

    print(f"n_blades={a.n_blades}  samples={a.samples}")
    print(f"equal-spacing gap = {360.0/a.n_blades:.1f} deg  (peak-tone ratio 1.00, 0.0 dB)")
    print(f"best uneven pattern: spread={best['spread']:.2f}")
    print(f"  angles (deg): {np.round(np.degrees(ang), 1).tolist()}")
    print(f"  gaps   (deg): {np.round(gaps, 1).tolist()}")
    print(f"  static unbalance: {static_unbalance(ang).normalized:.2e} (0 = balanced)")
    print(f"  peak-tone ratio:  {best['ratio']:.3f}  ->  {red:.1f} dB peak-tone reduction vs equal")

    out = Path("build") / f"uneven_spacing_n{a.n_blades}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"n_blades": a.n_blades, "angles_deg": np.degrees(ang).tolist(),
                               "peak_tone_ratio": best["ratio"], "peak_tone_reduction_db": red,
                               "spread": best["spread"]}, indent=2))
    print(f"-> {out}")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        m_e, a_e = blade_passing_modes(equal_spacing(a.n_blades), 4 * a.n_blades)
        m_u, a_u = blade_passing_modes(ang, 4 * a.n_blades)
        fig, ax = plt.subplots(figsize=(9, 4))
        ax.stem(m_e - 0.15, a_e, linefmt="C0-", markerfmt="C0o", basefmt=" ", label="equal spacing")
        ax.stem(m_u + 0.15, a_u, linefmt="C3-", markerfmt="C3s", basefmt=" ", label="uneven (balanced)")
        ax.set_xlabel("shaft harmonic m  (blade-pass tone at m = N)")
        ax.set_ylabel("tonal source amplitude  |Σ e^{-imθ}|")
        ax.set_title(f"Blade-pass tone spreading, N={a.n_blades}: peak {red:.1f} dB lower")
        ax.legend()
        ax.grid(True, alpha=0.25)
        png = out.with_suffix(".png")
        fig.tight_layout()
        fig.savefig(png, dpi=130)
        print(f"-> {png}")
    except Exception as e:  # noqa: BLE001
        print(f"(plot skipped: {e})")

    if a.build_stl:
        from fansim.geometry import BladeParams, build_impeller, export_stl
        p = BladeParams(n_blades=a.n_blades, blade_angles_deg=np.degrees(ang).tolist())
        stl = export_stl(build_impeller(p), out.with_suffix(".stl"))
        print(f"-> {stl}")


if __name__ == "__main__":
    main()
