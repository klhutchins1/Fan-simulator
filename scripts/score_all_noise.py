# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Score NOISE on every feasible trial of an optimization study (for design-rule extraction).

Unlike score_finalists_noise (Pareto only), this evaluates the LBM CV-noise metric on ALL feasible
COMPLETE trials so we have enough (geometry -> noise) points to correlate. Writes incrementally to
runs/<dir>/all_noise.json (survives interruption/resume). ~2.5 min/trial on the RTX 4070 Ti.

Usage:  uv run python scripts/score_all_noise.py runs/opt_v3 [--cutoff 2500]
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

import optuna

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate_noise import evaluate_noise  # noqa: E402

optuna.logging.set_verbosity(optuna.logging.WARNING)
INFEASIBLE = -1e5


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--cutoff", type=float, default=2500.0)
    a = ap.parse_args()
    run = Path(a.run_dir)
    name = sqlite3.connect(run / "study.db").execute("select study_name from studies").fetchone()[0]
    st = optuna.load_study(study_name=name, storage=f"sqlite:///{run.as_posix()}/study.db")

    out = run / "all_noise.json"
    done = {r["trial"]: r for r in json.loads(out.read_text())} if out.exists() else {}
    feasible = [t for t in st.trials if t.state.name == "COMPLETE" and t.values and t.values[0] > INFEASIBLE]
    print(f"{len(feasible)} feasible trials; {len(done)} already scored")

    for t in feasible:
        if t.number in done:
            continue
        stl = run / "trials" / f"trial_{t.number:04d}" / "impeller.stl"
        if not stl.exists():
            print(f"  trial {t.number}: no STL, skip")
            continue
        try:
            m = evaluate_noise(stl, label=f"t{t.number}", cutoff_hz=a.cutoff)
        except Exception as e:  # noqa: BLE001
            print(f"  trial {t.number}: FAILED ({e})")
            continue
        m.update(trial=t.number, n_blades=t.params.get("n_blades"),
                 cfm_free=round(t.values[0], 2), cfm_load=round(t.values[1], 2),
                 efficiency=round(t.values[2], 2), params=t.params)
        done[t.number] = m
        out.write_text(json.dumps(sorted(done.values(), key=lambda r: r["trial"]), indent=2))
        print(f"  trial {t.number}: dBA_band={m['noise_dba_band']}  BPF={m['bpf_tone_db']}  "
              f"thrust={m['thrust_n']}  (saved {len(done)}/{len(feasible)})")
    print(f"\ndone -> {out}")


if __name__ == "__main__":
    main()
