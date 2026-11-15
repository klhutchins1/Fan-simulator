"""Read a phone WAV of a running fan: rpm from the blade-pass tone, tone strength, relative level.

    python scripts/analyze_fan_recording.py genuine.wav --blades 9 --rpm 2000
    python scripts/analyze_fan_recording.py genuine.wav printed.wav --blades 9 --rpm 2000   # B minus A

``--rpm`` is the tach reading (a hint: the tone is searched within 15 % of it). The level is A-weighted dB
relative to full scale, not dB(A) SPL; only the difference between two matched recordings means anything.
Add ``--json out.json`` to keep the numbers with the session's records.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from validation import recording as rec  # noqa: E402


def _show(name: str, r: dict) -> None:
    print(f"{name}: {r['seconds']} s at {r['sample_rate']} Hz")
    if r["rpm"] is None:
        print("  rpm from sound: not found")
    else:
        off = 100 * (r["rpm"] / r["rpm_hint"] - 1)
        print(f"  rpm from sound: {r['rpm']:.0f}  (tach said {r['rpm_hint']:.0f}; {off:+.1f} %)")
        print(f"  blade-pass tone: {r['bpf_hz']:.1f} Hz, {r['bpf_prominence_db']:.1f} dB above the noise around it")
        extra = ", ".join(f"{h['harmonic']}x {h['prominence_db']:+.0f} dB" for h in r["harmonics"][1:])
        if extra:
            print(f"  harmonics: {extra}")
    print(f"  level: {r['level_dba_rel']:.1f} dB (A-weighted, relative to full scale; not dB(A) SPL)")
    for w in r["warnings"]:
        print(f"  WARNING: {w}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("wav", nargs="+", type=Path, help="one recording, or two (A then B) to compare")
    ap.add_argument("--blades", type=int, required=True)
    ap.add_argument("--rpm", type=float, nargs="+", required=True, help="tach rpm (one value, or one per file)")
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args(argv)
    if len(args.wav) > 2:
        ap.error("give one or two recordings")
    hints = args.rpm if len(args.rpm) == len(args.wav) else [args.rpm[0]] * len(args.wav)

    results = []
    for path, hint in zip(args.wav, hints):
        try:
            x, fs = rec.load_wav(path)
            r = rec.analyze(x, fs, n_blades=args.blades, rpm_hint=hint)
        except (OSError, ValueError) as exc:
            print(f"cannot read {path}: {exc}. Record uncompressed WAV (not m4a/mp3).")
            return 2
        r["file"] = str(path)
        results.append(r)
        _show(path.name, r)
    out: dict = {"recordings": results}
    if len(results) == 2:
        d = rec.compare(results[0], results[1])
        out["b_minus_a"] = d
        print(f"\n{args.wav[1].name} minus {args.wav[0].name}: {d['level_dba_rel_delta']:+.1f} dB")
        if not d["comparable"]:
            print("  NOT comparable: the two speeds differ by more than 3 %, a speed was not found, or a "
                  "recording has a warning. Re-record at matched rpm.")
    if args.json:
        args.json.write_text(json.dumps(out, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
