"""Export a short hub ring with grip pads, to test motor fit without a full impeller.

Usage:
    python scripts/export_hub_fit_coupon.py
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fansim.fan_spec import get_fan_spec, mount_grip_pad_layout  # noqa: E402
from fansim.manufacturability.print_export import export_hub_fit_coupon  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Short hub ring to test the motor-pad fit")
    ap.add_argument("--height", type=float, default=6.0, help="ring height in mm (default 6)")
    ap.add_argument("--out", default=None, help="output directory (default exports/)")
    args = ap.parse_args()
    mount = get_fan_spec("a12x25").motor_mount
    layout = mount_grip_pad_layout(mount)
    if layout is None:
        print("ERROR: A12x25 mount has no grip pads.")
        return 2
    _cav_r, r_center, grip_r = layout
    tip_dia = 2.0 * (r_center - grip_r)
    stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    out_dir = Path(args.out) if args.out else Path("exports")
    out_dir.mkdir(parents=True, exist_ok=True)
    stl = out_dir / f"hub_fit_{tip_dia:.2f}mm_{stamp}.stl"
    rep = export_hub_fit_coupon(stl, mount, height_mm=float(args.height))
    md = stl.with_suffix(".md")
    md.write_text(
        "\n".join([
            "# Hub fit coupon",
            "",
            f"Ring Ø {2 * 21.5:.0f} mm × {float(args.height):.0f} mm, 20 mm center hole.",
            f"Pad tips at **{tip_dia:.2f} mm** (same circle as the next full Stock export).",
            f"Volume {rep.volume_mm3 / 1000:.1f} cm³. About {rep.volume_mm3 / 1000:.0f} g in solid PLA.",
            "",
            "Slice: either face on the bed. No supports. PLA+ / 0.6 mm nozzle, same as H7MQ8.",
            "Press the motor boss into the pad ring. This is a fit check, not a fan.",
            "",
            f"Watertight: {'YES' if rep.ok else 'NO'} · {rep.n_bodies} body",
            "",
        ]),
        encoding="utf-8",
    )
    print(f"wrote {stl}  watertight={rep.ok}  {rep.volume_mm3 / 1000:.2f} cm3  pad tips {tip_dia:.2f} mm")
    print(f"wrote {md}")
    return 0 if rep.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
