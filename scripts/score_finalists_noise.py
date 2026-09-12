# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Score an optimization run's Pareto finalists on NOISE (the expensive 3rd objective).

For each finalist in runs/<dir>/pareto.json, runs the LBM control-volume noise evaluator on its
exported STL and tabulates flow/efficiency (from the search) alongside the band-limited relative
dB(A). Noise is evaluated ONLY on finalists (per the plan: cheap RANS proxy screens every candidate,
the GPU LBM scores the Pareto front), so the search stays fast while finalists get a real, ranked
acoustic number. Writes runs/<dir>/finalist_noise.json + prints a comparison table.

Usage:  uv run python scripts/score_finalists_noise.py runs/opt_v3 [--cutoff 2500]
"""
import argparse
import glob
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate_noise import evaluate_noise  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--cutoff", type=float, default=2500.0)
    a = ap.parse_args()
    run = Path(a.run_dir)
    pareto = json.loads((run / "pareto.json").read_text())

    rows = []
    for fin in pareto:
        tr = fin["trial"]
        cands = glob.glob(str(run / "pareto" / f"trial_{tr:04d}_*.stl"))
        if not cands:
            print(f"  (no STL for trial {tr}, skipping)")
            continue
        m = evaluate_noise(cands[0], label=f"trial{tr}", cutoff_hz=a.cutoff)
        m.update(trial=tr, n_blades=fin.get("n_blades"), cfm_free=fin.get("cfm_free"),
                 cfm_load=fin.get("cfm_load"), efficiency=fin.get("efficiency"))
        rows.append(m)

    if not rows:
        sys.exit("no finalists scored")
    rows.sort(key=lambda r: r["noise_dba_band"])   # quietest first
    quietest = rows[0]["noise_dba_band"]

    print(f"\nFinalist noise ranking ({run.name}, quietest first; band-limited @ {a.cutoff:.0f} Hz):\n")
    print(f"{'trial':>6}{'nB':>4}{'cfm_free':>9}{'cfm_load':>9}{'eff%':>7}"
          f"{'thrust_N':>9}{'BPF_dB':>8}{'dBA_band':>9}{'d(rel)':>8}")
    for r in rows:
        print(f"{r['trial']:>6}{r.get('n_blades',0):>4}{r.get('cfm_free',0):>9.1f}"
              f"{r.get('cfm_load',0):>9.1f}{r.get('efficiency',0):>7.1f}{r['thrust_n']:>9.3f}"
              f"{r['bpf_tone_db']:>8.1f}{r['noise_dba_band']:>9.1f}"
              f"{r['noise_dba_band']-quietest:>+8.1f}")

    out = run / "finalist_noise.json"
    out.write_text(json.dumps(rows, indent=2))
    print(f"\n-> {out}")
    print("dBA_band is a RELATIVE metric (consistent band-limit); d(rel) = dB louder than the")
    print("quietest finalist. Absolute level is coarse-grid-limited; the ranking is the signal.")


if __name__ == "__main__":
    main()
