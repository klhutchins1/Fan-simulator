"""LBM-noise-score a feature-isolation study: the smooth CONTROL vs every featured trial.

The feature study (run_feature_study.py) only measured flow/efficiency, which came back ~null — but
the bio-feature thesis (owl serrations, whale tubercles) is ACOUSTIC. This runs the FluidX3D CV-force
noise evaluator on the control STL and each trial STL, reporting the band-limited on-axis dB(A) and BPF
tone delta vs the smooth control. Quiet-vs-smooth is the real test of the features.

HONEST CAVEAT: LBM at ~1 mm/cell under-resolves the ~2 mm blade AND the ~1-4 mm features, so a null or
noisy result may reflect resolution, not physics. Absolute dB is not meaningful; the RELATIVE delta at a
consistent band-limit is the signal. Run with the GPU free.

Usage:  uv run python scripts/score_feature_noise.py --run runs/feat_study2 [--cutoff 2500]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from evaluate_noise import evaluate_noise  # noqa: E402

_t0 = time.time()


def _score(stl: Path, label: str, cutoff: float) -> dict | None:
    if not stl.exists():
        print(f"  [{label}] no STL, skip")
        return None
    m = evaluate_noise(str(stl), label=label, cutoff_hz=cutoff)
    m["label"] = label
    print(f"  [{label}] dBA_band={m.get('noise_dba_band', float('nan')):.1f} "
          f"BPF={m.get('bpf_tone_db', float('nan')):.1f} thrust={m.get('thrust_n', float('nan')):.3f} "
          f"(wall {time.time()-_t0:.0f}s)")
    sys.stdout.flush()
    return m


def main() -> int:
    ap = argparse.ArgumentParser(description="LBM-noise-score a feature study vs its smooth control")
    ap.add_argument("--run", default="runs/feat_study2")
    ap.add_argument("--cutoff", type=float, default=2500.0)
    args = ap.parse_args()
    run = Path(args.run)

    control = _score(run / "control" / "impeller.stl", "control", args.cutoff)
    trials = []
    for td in sorted((run / "trials").glob("trial_*")):
        m = _score(td / "impeller.stl", td.name, args.cutoff)
        if m:
            trials.append(m)

    out = {"control": control, "trials": trials}
    (run / "feature_noise.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    print("\n===== FEATURE NOISE vs SMOOTH CONTROL (band-limited dB(A) @1m, lower=quieter) =====")
    if control:
        cdb = control.get("noise_dba_band", float("nan"))
        ctone = control.get("bpf_tone_db", float("nan"))
        print(f"  control: dBA_band {cdb:.1f}  BPF {ctone:.1f}")
        quieter = 0
        for m in sorted(trials, key=lambda r: r.get("noise_dba_band", 1e9)):
            d_db = m.get("noise_dba_band", float("nan")) - cdb
            d_tone = m.get("bpf_tone_db", float("nan")) - ctone
            if d_db < -0.3:
                quieter += 1
            print(f"  {m['label']}: dBA_band {m.get('noise_dba_band', float('nan')):.1f} "
                  f"({d_db:+.1f})  BPF {m.get('bpf_tone_db', float('nan')):.1f} ({d_tone:+.1f})")
        print(f"\n  {quieter}/{len(trials)} featured designs quieter than smooth (>0.3 dB). "
              + ("Features CUT noise on some designs." if quieter else
                 "No featured design was meaningfully quieter (features didn't help noise here)."))
    print(f"  -> {run/'feature_noise.json'}  (total {time.time()-_t0:.0f}s)")
    return 0


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    os._exit(code)
