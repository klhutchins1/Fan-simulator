# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Does UNEVEN blade spacing actually cut the tonal noise? — GPU LBM test.

Even blade spacing concentrates all the acoustic energy at one blade-pass frequency (N x rev) = a loud
tone. Spacing the blades unevenly (but kept mass-BALANCED, Sum e^{i.theta}=0) spreads that energy across
harmonics of 1 x rev, lowering the peak tone. It's decoupled from solidity, so unlike the bio-features
(which tested null), it attacks the tone directly. We built the balanced-uneven generator + an analytic
peak-tone predictor but never checked it against real LBM acoustics — this does.

For a base design it builds even + several uneven-spread variants, scores each on the GPU (FluidX3D
CV-force noise), and compares the LBM-measured BPF tone (bpf_tone_db) vs even AND vs the analytic
prediction. A drop in the measured tone with little change in broadband/thrust = the lever works.

Best tested on an ODD blade count (7/9/11) — even counts give near-symmetric balanced patterns that
barely spread the tone (~1 dB), while odd counts reach ~4-5 dB analytically.

Usage:  uv run python scripts/run_spacing_study.py --design-id opt_run1_t9006 --out runs/spacing_study
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from fansim.acoustics.tonal import peak_tone_reduction_db  # noqa: E402
from fansim.catalog import get_entry  # noqa: E402
from fansim.geometry import build_impeller, export_stl  # noqa: E402
from fansim.geometry.blade import set_uneven_spacing  # noqa: E402
from fansim.optimize.search_space import blade_from_flat  # noqa: E402
from evaluate_noise import evaluate_noise  # noqa: E402

_t0 = time.time()
SPREADS = [0.0, 0.4, 0.6, 0.8]   # 0 = even (control); larger spreads for a stronger tonal effect


def _angles_rad(params) -> np.ndarray:
    if params.blade_angles_deg is not None:
        return np.radians(np.asarray(params.blade_angles_deg, float))
    n = params.n_blades
    return np.array([k * 2 * np.pi / n for k in range(n)])


def main() -> int:
    ap = argparse.ArgumentParser(description="uneven-spacing tonal-noise study (LBM)")
    ap.add_argument("--design-id", required=True, help="base design from the catalog (odd blade count best)")
    ap.add_argument("--out", default="runs/spacing_study")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    e = get_entry(args.design_id)
    if e is None:
        print(f"Design '{args.design_id}' not in the catalog. Run `catalog build`, then `catalog list`.")
        return 2
    flat = e.params
    print(f"[base] {args.design_id}, nB={flat.get('n_blades')} — even vs uneven spacing", flush=True)

    results = []
    for spread in SPREADS:
        params = blade_from_flat(flat)
        if spread > 0:
            set_uneven_spacing(params, spread=spread, rng=np.random.default_rng(args.seed))
        else:
            params.blade_angles_deg = None      # force a truly EVEN control (ignore any stored spacing)
        even = params.blade_angles_deg is None
        predicted = 0.0 if even else float(peak_tone_reduction_db(_angles_rad(params)))
        stl = out / f"spacing_{spread:g}.stl"
        export_stl(build_impeller(params), stl)
        m = evaluate_noise(str(stl), label=f"spread{spread:g}")
        # peak_tone_db (loudest tone over ALL harmonics) is the HONEST metric here — uneven spacing
        # spreads energy OFF the single BPF, which a BPF-only measure can't see.
        rec = {"spread": spread, "even": even, "predicted_tone_drop_db": round(predicted, 2),
               "peak_tone_db": m.get("peak_tone_db"), "bpf_tone_db": m.get("bpf_tone_db"),
               "noise_dba_band": m.get("noise_dba_band"), "thrust_n": m.get("thrust_n")}
        results.append(rec)
        print(f"  spread={spread:g} {'(EVEN)' if even else '     '}: "
              f"peak tone {rec['peak_tone_db']:.1f} dB  broadband {rec['noise_dba_band']:.1f} dBA  "
              f"thrust {rec['thrust_n']:.3f}  [analytic predicts -{predicted:.1f} dB tone] "
              f"(wall {time.time()-_t0:.0f}s)", flush=True)

    (out / "spacing_verdict.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    even_tone = next(r["peak_tone_db"] for r in results if r["even"])
    print("\n===== UNEVEN SPACING vs EVEN (peak tone over all harmonics) =====")
    print(f"  even peak tone = {even_tone:.1f} dB")
    best = None
    for r in results:
        if r["even"]:
            continue
        d = r["peak_tone_db"] - even_tone
        if best is None or d < best[1]:
            best = (r["spread"], d)
        print(f"  spread {r['spread']:g}: peak tone {r['peak_tone_db']:.1f} dB "
              f"({d:+.1f} vs even)  broadband {r['noise_dba_band']:.1f} dBA  "
              f"[predicted -{r['predicted_tone_drop_db']:.1f}]")
    if best and best[1] < -0.5:
        print(f"  => uneven spacing CUT the tone by {-best[1]:.1f} dB (best at spread {best[0]:g}). "
              "The lever works.")
    else:
        print("  => no clear tonal benefit at this fidelity (tone drop within noise).")
    print(f"  -> {out/'spacing_verdict.json'}  (total {time.time()-_t0:.0f}s)")
    return 0


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    os._exit(code)
