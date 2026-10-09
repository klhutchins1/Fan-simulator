"""Strip leading recovery-apology headers from fansim/*.py (§15.1).

Removes only consecutive leading comment lines that are recovery provenance
(RECOVERED-FROM-CHAT / RECONSTRUCTED / EXTRACTED-FROM-CURSOR / related). Mid-file
``# --- spliced`` markers are left alone. Docstrings and code are untouched.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path("fansim")

LEAD_MARKERS = (
    "RECOVERED-FROM-CHAT",
    "RECONSTRUCTED",
    "EXTRACTED-FROM-CURSOR",
    "EXTRACTED-FROM-TRANSCRIPT",
)
CONT_PREFIXES = (
    "# source:",
    "# NOT verified",
    "# Prefer any real",
    "# VERIFY against",
    "# --- RECONSTRUCTED",
    "# --- spliced from",  # only strip if still in the leading block
)


def _is_lead_header(line: str) -> bool:
    s = line.strip()
    if not s.startswith("#"):
        return False
    if any(m in s for m in LEAD_MARKERS):
        return True
    low = s.lower()
    return any(s.startswith(p) or low.startswith(p.lower()) for p in CONT_PREFIXES)


def strip_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    if not lines:
        return False
    i = 0
    removed = 0
    while i < len(lines):
        raw = lines[i]
        if _is_lead_header(raw):
            i += 1
            removed += 1
            continue
        # drop one blank line right after the header block
        if removed and raw.strip() == "":
            i += 1
            removed += 1
            continue
        break
    if removed == 0:
        return False
    path.write_text("".join(lines[i:]), encoding="utf-8")
    return True


def main() -> None:
    changed = []
    for path in sorted(ROOT.rglob("*.py")):
        if strip_file(path):
            changed.append(path.as_posix())
    print(f"stripped {len(changed)} files")
    for p in changed:
        print(f"  {p}")


if __name__ == "__main__":
    main()
