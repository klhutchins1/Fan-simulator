"""Regenerate or check the validation scoreboard (RV-2).

    python scripts/scoreboard.py           # print the table; exit 1 if the page is stale or a verdict flipped
    python scripts/scoreboard.py --write   # rewrite docs/validation/scoreboard.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fansim.validation import scoreboard as sb


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    if args.write:
        rows = sb.write()
        print(f"wrote {sb.PAGE_PATH} ({len(rows)} claims)")
        return 0
    rows = sb.evaluate(sb.load_claims())
    page = sb.render(rows)
    print(page)
    bad = [r["id"] for r in rows if r["verdict"] != r["recorded_verdict"]]
    stale = (sb.ROOT / sb.PAGE_PATH).read_text(encoding="utf-8") != page \
        if (sb.ROOT / sb.PAGE_PATH).is_file() else True
    if bad:
        print("verdict changed: " + ", ".join(bad))
    if stale:
        print(f"{sb.PAGE_PATH} is stale: run with --write")
    return 1 if (bad or stale) else 0


if __name__ == "__main__":
    raise SystemExit(main())
