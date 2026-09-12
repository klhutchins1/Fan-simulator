"""One-shot: scrub docs/roadmap.md mojibake → clean UTF-8."""
from __future__ import annotations

import json
import re
from pathlib import Path

p = Path("docs/roadmap.md")
t = p.read_text(encoding="utf-8-sig")

# Longer / more specific first. UTF-8 bytes misread as cp437/cp1252 then stored as Unicode.
FIX: list[tuple[str, str]] = [
    # multi-char compound phrases
    ("╬öpΓéÇ", "Δp_t"),  # AMCA total pressure — was Δpₜ style
    ("P_shaft_max/╧ë", "P_shaft_max/ω"),
    ("TΓÇô╧ë", "T–ω"),
    ("W┬╖c/╬╜", "W·c/ν"),
    ("1.15├ù", "1.15×"),
    ("QΓåÆ0", "Q→0"),
    ("aΓÇ▓", "a′"),
    ("(1ΓêÆa′)", "(1−a′)"),
    ("(1+a′)", "(1+a′)"),  # noop if already fixed
    ("ΓÇö", "—"),
    ("ΓÇô", "–"),
    ("ΓÇ£", '"'),
    ("ΓÇ¥", '"'),
    ("ΓÇÖ", "'"),
    ("ΓÇÿ", "'"),
    ("ΓÇª", "…"),
    ("ΓÇ▓", "′"),
    ("┬º", "§"),
    ("┬▓", "²"),
    ("┬╖", "·"),
    ("├ù", "×"),
    ("Γÿà", "★"),
    ("ΓåÆ", "→"),
    ("ΓåÉ", "←"),
    ("Γê⌐", "∩"),
    ("ΓêÆ", "−"),
    ("Γëê", "≈"),
    ("╬ö", "Δ"),
    ("╧ü", "ρ"),
    ("╧Ç", "π"),
    ("╬╖", "η"),
    ("╬┤", "δ"),
    ("╬╝", "μ"),
    ("╧â", "σ"),
    ("╬╕", "θ"),
    ("╬ë", "Ω"),
    ("╬⌐", "ω"),  # often omega in MRF context — check
    ("╧ë", "ω"),
    ("╬╜", "ν"),
    ("ΓéÇ", "ₜ"),  # leftover subscript t if any
]

# Verify ambiguous ones by counting before apply
before_samples = {
    "╬⌐": [m.start() for m in re.finditer("╬⌐", t)][:5],
    "╧ë": [m.start() for m in re.finditer("╧ë", t)][:5],
    "╬öpΓéÇ": t.count("╬öpΓéÇ"),
    "ΓéÇ": t.count("ΓéÇ"),
}

for a, b in FIX:
    t = t.replace(a, b)

# Remaining suspicious starters
bad = re.findall(r"[Γ┬╧╬├ÂÃ]", t)
# Also box-drawing remnants
box = re.findall(r"[\u2500-\u257F]", t)

# Update §11.6 note that full scrub was deferred
t = t.replace(
    "Section 11 rewritten in clean UTF-8; full-file mojibake scrub deferred when tools\n"
    "  allow a whole-file rewrite without corrupting Greek/math.",
    "Section 11 rewritten in clean UTF-8; full-file mojibake scrub DONE 2026-09-11\n"
    "  (em-dashes, §, Greek μ/σ/η/…, ΔP, arrows, primes).",
)

# If the deferred sentence is one line different, try another pattern
if "full-file mojibake scrub deferred" in t:
    t = t.replace(
        "full-file mojibake scrub deferred when tools",
        "full-file mojibake scrub DONE 2026-09-11; was deferred when tools",
    )

p.write_text(t, encoding="utf-8", newline="\n")

# Report remaining
remain = []
for i, line in enumerate(t.splitlines(), 1):
    if re.search(r"[Γ┬╧╬├ÂÃ\u2500-\u257F]", line):
        remain.append({"line": i, "text": line[:200]})

report = {
    "before_samples": before_samples,
    "bad_after": len(bad),
    "box_after": len(box),
    "remain_lines": remain[:40],
    "counts": {
        "emdash": t.count("\u2014"),
        "section": t.count("\u00a7"),
        "mu": t.count("μ"),
        "sigma": t.count("σ"),
        "eta": t.count("η"),
        "delta": t.count("Δ"),
        "omega": t.count("ω"),
        "Omega": t.count("Ω"),
    },
}
Path("_moji_report.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("done remain", len(remain), "bad", len(bad))
