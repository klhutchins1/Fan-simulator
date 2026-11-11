"""Export a short hub washer with the recessed print-id (P6 / QA-80).

Re-print this to check T3, not another full impeller. Put the marked face on the bed.

Usage:
    uv run python scripts/export_id_coupon.py
    uv run python scripts/export_id_coupon.py --code H7MQ8
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fansim.manufacturability.print_export import export_id_coupon  # noqa: E402
from fansim.manufacturability.print_id import (  # noqa: E402
    GLYPH_ADVANCE_MM,
    MARK_R_INNER,
    MARK_R_OUTER,
    MARK_STROKE_MM,
    export_stem,
    verify_print_id,
)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Hub-face print-id coupon (T3 check)")
    ap.add_argument("--code", default="H7MQ8", help="5-char print-id to engrave (default H7MQ8)")
    ap.add_argument("--out", default=None, help="output directory (default exports/)")
    return ap


def main() -> int:
    args = build_parser().parse_args()
    code = str(args.code).strip().upper()
    if not verify_print_id(code):
        print(f"ERROR: {code!r} is not a valid 5-char print-id.")
        return 2
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_dir = Path(args.out) if args.out else Path("exports")
    out_dir.mkdir(parents=True, exist_ok=True)
    stl = out_dir / f"{export_stem(code, 'id_coupon', stamp)}.stl"
    rep = export_id_coupon(stl, code)
    cap = MARK_R_OUTER - MARK_R_INNER
    md = stl.with_suffix(".md")
    md.write_text(
        "\n".join([
            f"# Print-id coupon — {code}",
            "",
            f"**Sharpie: `{code}`**  (same as H7MQ8 if you used the default).",
            "",
            f"Washer Ø 43 mm × 8 mm, 20 mm bore. Recessed on +Z, cap {cap:.1f} mm, "
            f"stroke {MARK_STROKE_MM:.1f} mm, advance {GLYPH_ADVANCE_MM:.1f} mm, "
            f"band r {MARK_R_INNER:.1f}–{MARK_R_OUTER:.1f} mm.",
            "",
            "Slice: marked face on the bed. No supports. PLA+ / 0.6 mm nozzle is fine.",
            "This is a T3 readability coupon, not a fan. Do not mount it on the motor.",
            "",
            f"Watertight: {'YES' if rep.ok else 'NO'} · {rep.n_bodies} body · "
            f"{rep.volume_mm3/1000:.1f} cm³",
            "",
        ]),
        encoding="utf-8",
    )
    print(f"wrote {stl}  watertight={rep.ok}  {rep.volume_mm3/1000:.1f} cm3")
    print(f"wrote {md}")
    return 0 if rep.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
