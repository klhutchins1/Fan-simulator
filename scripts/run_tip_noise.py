# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Does rounding the tip run QUIETER? — GPU LBM noise on the tip-round variants.

The blunt square tip sheds a strong tip vortex, a real broadband + tonal noise source; rounding it is
a classic quieting trick. The CPU tip study (run_tip_study.py) answered the FLOW/EFF side with RANS;
RANS can't see tip-vortex noise, so this runs the GPU FluidX3D CV-force noise model on the same tip
variants. Builds each variant's STL fresh (the CFD study's case dirs collide on disk) and scores it,
using the SAME band-limit for all so the RELATIVE dB deltas are the trustworthy signal (absolute
broadband is coarse-grid-limited — see the noise-tier notes).

Usage:  uv run python scripts/run_tip_noise.py --design-id opt_extended2_t36 --out runs/tip_study
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))   # so `evaluate_noise` (a script) imports

from evaluate_noise import evaluate_noise  # noqa: E402
from fansim.catalog import get_entry  # noqa: E402
from fansim.geometry import build_impeller, export_stl, watertight_report  # noqa: E402
from fansim.optimize.search_space import blade_from_flat  # noqa: E402

_t0 = time.time()

# Same tip variants as the CPU flow/eff study, so the two graphs line up. (label, tip_round, tip_start).
CONFIGS = [
    ("control",   0.0, 0.80),
    ("round 0.2", 0.2, 0.80),
    ("round 0.4", 0.4, 0.80),
    ("round 0.6", 0.6, 0.80),
    ("round 0.8", 0.8, 0.80),
]


def main() -> int:
    ap = argparse.ArgumentParser(description="tip-round GPU noise study")
    ap.add_argument("--design-id", default="opt_extended2_t36")
    ap.add_argument("--out", default="runs/tip_study")
    ap.add_argument("--cutoff", type=float, default=2500.0)
    args = ap.parse_args()

    e = get_entry(args.design_id)
    if e is None:
        print(f"'{args.design_id}' not in the catalog.")
        return 2
    out = Path(args.out)
    stl_dir = out / "noise_stls"
    stl_dir.mkdir(parents=True, exist_ok=True)
    print(f"[base] {args.design_id} — GPU tip-round noise (build STL + FluidX3D CV-noise per config)", flush=True)

    results = []
    for label, tr, ts in CONFIGS:
        f = dict(e.params)
        if tr:
            f.update(tip_round=tr, tip_round_start=ts)
        stl = stl_dir / f"{label.replace(' ', '_')}.stl"
        try:
            export_stl(build_impeller(blade_from_flat(f)), stl)
            wt = watertight_report(stl).ok
            m = evaluate_noise(stl, label=label, cutoff_hz=args.cutoff)
        except Exception as exc:  # noqa: BLE001 - one config failing shouldn't kill the run
            print(f"  {label:12s}: FAILED {type(exc).__name__}: {exc}", flush=True)
            results.append({"label": label, "tip_round": tr, "error": str(exc)})
            continue
        rec = {"label": label, "tip_round": tr, "tip_start": ts, "watertight": wt,
               "noise_dba_band": round(float(m.get("noise_dba_band", 0.0)), 2),
               "bpf_tone_db": round(float(m.get("bpf_tone_db", 0.0)), 2),
               "peak_tone_db": round(float(m.get("peak_tone_db", m.get("bpf_tone_db", 0.0))), 2),
               "thrust_n": round(float(m.get("thrust_n", 0.0)), 4)}
        results.append(rec)
        print(f"  {label:12s} tr={tr}: dBA_band {rec['noise_dba_band']:5.1f}  BPF {rec['bpf_tone_db']:5.1f}  "
              f"peak-tone {rec['peak_tone_db']:5.1f}  thrust {rec['thrust_n']:+.3f}N  "
              f"(wall {time.time()-_t0:.0f}s)", flush=True)

    (out / "tip_noise.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    ok = [r for r in results if "noise_dba_band" in r]
    ctrl = next((r for r in ok if r["tip_round"] == 0), None)
    print("\n===== TIP-ROUND NOISE (vs square-tip control) =====")
    if ctrl:
        print(f"  control: dBA_band {ctrl['noise_dba_band']}  BPF {ctrl['bpf_tone_db']}  "
              f"peak-tone {ctrl['peak_tone_db']}")
        for r in ok:
            if r is ctrl:
                continue
            print(f"  {r['label']:12s}: dBA {r['noise_dba_band']-ctrl['noise_dba_band']:+.1f}  "
                  f"BPF {r['bpf_tone_db']-ctrl['bpf_tone_db']:+.1f}  "
                  f"peak {r['peak_tone_db']-ctrl['peak_tone_db']:+.1f}")

    try:  # graph: tip_round vs band-limited dBA + peak tone
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        curve = sorted(ok, key=lambda r: r["tip_round"])
        if len(curve) >= 3:
            xs = [r["tip_round"] for r in curve]
            fig, ax = plt.subplots(figsize=(7, 4.5))
            ax.plot(xs, [r["noise_dba_band"] for r in curve], "o-", color="tab:purple", label="dBA band (rel)")
            ax.plot(xs, [r["peak_tone_db"] for r in curve], "s--", color="tab:orange", label="peak tone dB")
            ax.set_xlabel("tip_round (0 = square tip, 1 = fully rounded)")
            ax.set_ylabel("noise (dB — RELATIVE, band-limited)")
            ax.set_title(f"Does rounding the tip run quieter?  base {args.design_id}")
            ax.legend(); ax.grid(alpha=0.3)
            fig.tight_layout(); fig.savefig(out / "tip_noise.png", dpi=110)
            print(f"  graph -> {out/'tip_noise.png'}")
    except Exception as exc:  # noqa: BLE001
        print(f"  (graph skipped: {exc})")

    print(f"  -> {out/'tip_noise.json'}  (total {time.time()-_t0:.0f}s)")
    return 0


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    os._exit(code)
