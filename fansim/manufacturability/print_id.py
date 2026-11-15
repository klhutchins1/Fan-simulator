"""Short Crockford print-part IDs issued at Export (roadmap 28.2 / 28.3).

The registry lives here (no CAD). Recessed hub glyphs are cut in
``print_id_mark.engrave_print_id`` from the stroke layout below.
"""
from __future__ import annotations

import hashlib
import json
import math
import secrets
import subprocess
from dataclasses import asdict, is_dataclass
from pathlib import Path

CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
CHECK_ALPHABET = CROCKFORD + "*~$=U"
INDEX_PATH = Path(__file__).resolve().parents[2] / "validation" / "prints" / "index.jsonl"

# Hub-face mark-spec (QA r10, docs/qa/notes/print-id-mark-spec-r10.md). +Z inlet.
# P6 / QA-80 (2026-11-11): H7MQ8 T3 FAIL — 3.2 mm cap / 0.6 mm stroke unreadable on 0.6 mm
# PLA+. Cap 5.0 mm, stroke 0.9 mm, advance 3.6 mm; depth unchanged.
MARK_R_INNER = 11.5
MARK_R_OUTER = 16.5
MARK_DEPTH_MM = 0.5
MARK_STROKE_MM = 0.9
GLYPH_ADVANCE_MM = 3.6
MARK_THETA0_DEG = 90.0
_GLYPH_WIDTH_MM = GLYPH_ADVANCE_MM * 0.75  # 2.7 mm cell; 0.9 mm gap
_BORE_KEEP_MM = 1.0
_RIM_KEEP_MM = 1.0


def _s(*xy: float) -> tuple[tuple[float, float, float, float], ...]:
    """Pack (x0,y0,x1,y1)+ into stroke tuples. y up, unit cell."""
    out = []
    for i in range(0, len(xy), 4):
        out.append((xy[i], xy[i + 1], xy[i + 2], xy[i + 3]))
    return tuple(out)


# 7-segment bits plus a few distinct letters so 8/B, 0/D, 5/S stay readable at 5.0 mm.
_A, _B, _C, _D, _E, _F, _G = (
    (0.22, 0.88, 0.78, 0.88),
    (0.78, 0.88, 0.78, 0.50),
    (0.78, 0.50, 0.78, 0.12),
    (0.22, 0.12, 0.78, 0.12),
    (0.22, 0.12, 0.22, 0.50),
    (0.22, 0.50, 0.22, 0.88),
    (0.22, 0.50, 0.78, 0.50),
)


def _seg(*bits: tuple[float, float, float, float]) -> tuple[tuple[float, float, float, float], ...]:
    return bits


_FONT: dict[str, tuple[tuple[float, float, float, float], ...]] = {
    "0": _seg(_A, _B, _C, _D, _E, _F),
    "1": _seg(_B, _C),
    "2": _seg(_A, _B, _G, _E, _D),
    "3": _seg(_A, _B, _G, _C, _D),
    "4": _seg(_F, _G, _B, _C),
    "5": _seg(_A, _F, _G, _C, _D),
    "6": _seg(_A, _F, _G, _E, _C, _D),
    "7": _seg(_A, _B, _C),
    "8": _seg(_A, _B, _C, _D, _E, _F, _G),
    "9": _seg(_A, _B, _C, _D, _F, _G),
    "A": _seg(_A, _B, _C, _E, _F, _G),
    "B": _s(0.18, 0.12, 0.18, 0.88, 0.18, 0.88, 0.60, 0.88,
            0.60, 0.88, 0.80, 0.70, 0.80, 0.70, 0.60, 0.50,
            0.60, 0.50, 0.18, 0.50, 0.60, 0.50, 0.80, 0.30,
            0.80, 0.30, 0.60, 0.12, 0.60, 0.12, 0.18, 0.12),
    "C": _seg(_A, _F, _E, _D),
    "D": _s(0.18, 0.12, 0.18, 0.88, 0.18, 0.88, 0.52, 0.88,
            0.52, 0.88, 0.82, 0.50, 0.82, 0.50, 0.52, 0.12,
            0.52, 0.12, 0.18, 0.12),
    "E": _seg(_A, _F, _E, _D, _G),
    "F": _seg(_A, _F, _E, _G),
    # QA-75: no half bar. At 0.6 mm stroke in a 1.8 mm cell (same ratio as 0.9 / 2.7) the half bar fused with the left stroke, so G cut
    # exactly like 6. 7-segment G (A F E D C) differs from 6 (bar), C (lower right) and U/0 (top bar / left).
    "G": _seg(_A, _F, _E, _D, _C),
    "H": _seg(_F, _E, _B, _C, _G),
    "J": _seg(_B, _C, _D, _E),
    "K": _s(0.22, 0.12, 0.22, 0.88, 0.22, 0.50, 0.78, 0.88, 0.22, 0.50, 0.78, 0.12),
    "M": _s(0.18, 0.12, 0.18, 0.88, 0.18, 0.88, 0.50, 0.50,
            0.50, 0.50, 0.82, 0.88, 0.82, 0.88, 0.82, 0.12),
    "N": _s(0.22, 0.12, 0.22, 0.88, 0.22, 0.88, 0.78, 0.12, 0.78, 0.12, 0.78, 0.88),
    "P": _seg(_A, _B, _G, _F, _E),
    "Q": _seg(_A, _B, _C, _D, _E, _F, (0.50, 0.38, 0.82, 0.12)),
    "R": _seg(_A, _B, _G, _F, _E, (0.50, 0.50, 0.78, 0.12)),
    "S": _s(0.78, 0.82, 0.30, 0.88, 0.30, 0.88, 0.22, 0.70,
            0.22, 0.70, 0.22, 0.52, 0.22, 0.52, 0.78, 0.48,
            0.78, 0.48, 0.78, 0.22, 0.78, 0.22, 0.22, 0.12),
    "T": _s(0.18, 0.88, 0.82, 0.88, 0.50, 0.88, 0.50, 0.12),
    "V": _s(0.18, 0.88, 0.50, 0.12, 0.50, 0.12, 0.82, 0.88),
    "W": _s(0.12, 0.88, 0.28, 0.12, 0.28, 0.12, 0.50, 0.50,
            0.50, 0.50, 0.72, 0.12, 0.72, 0.12, 0.88, 0.88),
    "X": _s(0.22, 0.12, 0.78, 0.88, 0.22, 0.88, 0.78, 0.12),
    "Y": _s(0.18, 0.88, 0.50, 0.50, 0.82, 0.88, 0.50, 0.50, 0.50, 0.50, 0.50, 0.12),
    "Z": _s(0.22, 0.88, 0.78, 0.88, 0.78, 0.88, 0.22, 0.12, 0.22, 0.12, 0.78, 0.12),
    "*": _s(0.50, 0.18, 0.50, 0.82, 0.22, 0.50, 0.78, 0.50,
            0.28, 0.22, 0.72, 0.78, 0.28, 0.78, 0.72, 0.22),
    "~": _s(0.18, 0.42, 0.38, 0.62, 0.38, 0.62, 0.50, 0.50,
            0.50, 0.50, 0.62, 0.62, 0.62, 0.62, 0.82, 0.42),
    "$": _seg(_A, _F, _G, _C, _D, (0.50, 0.08, 0.50, 0.92)),
    "=": _s(0.22, 0.38, 0.78, 0.38, 0.22, 0.62, 0.78, 0.62),
    "U": _seg(_F, _E, _D, _C, _B),
}


def glyph_strokes(ch: str) -> tuple[tuple[float, float, float, float], ...]:
    """Single-stroke segments for one Crockford / check character, in the unit cell."""
    if not ch:
        return ()
    return _FONT.get(ch.strip().upper(), ())


def hub_can_take_mark(hub_radius: float, bore_r: float = 10.0) -> bool:
    """True when the r10 preferred band fits with ≥1 mm keep-out from bore and rim."""
    r = float(hub_radius)
    b = float(bore_r)
    return MARK_R_INNER - _BORE_KEEP_MM >= b - 1e-9 and MARK_R_OUTER + _RIM_KEEP_MM <= r + 1e-9


def mark_will_cut(code: str, hub_radius: float, bore_r: float = 10.0) -> bool:
    """True when ``engrave_print_id`` will actually recess the hub (QA-78)."""
    raw = (code or "").strip().upper()
    if len(raw) != 5 or any(ch in "ILO" for ch in raw):
        return False
    return hub_can_take_mark(hub_radius, bore_r)


def mark_strokes_xy(code: str) -> tuple[tuple[float, float, float, float], ...]:
    """World-XY centreline strokes for a 5-character code on the +Z hub band."""
    code = normalize_read(code)
    if len(code) != 5:
        return ()
    r_mid = 0.5 * (MARK_R_INNER + MARK_R_OUTER)
    h = MARK_R_OUTER - MARK_R_INNER
    w = _GLYPH_WIDTH_MM
    dtheta = GLYPH_ADVANCE_MM / r_mid
    theta0 = math.radians(MARK_THETA0_DEG)
    out: list[tuple[float, float, float, float]] = []
    # QA-73: seen from outside the +Z face (looking -Z) with glyph "up" radially outward, "right" is
    # clockwise (decreasing theta). Advance and the glyph u axis both run clockwise, or the mark is a
    # mirror image that reads backwards.
    for i, ch in enumerate(code):
        theta = theta0 - (i - 2) * dtheta

        def xy(u: float, v: float, theta: float = theta) -> tuple[float, float]:
            r = MARK_R_INNER + v * h
            th = theta - (u - 0.5) * w / r_mid
            return r * math.cos(th), r * math.sin(th)

        for x0, y0, x1, y1 in glyph_strokes(ch):
            a = xy(x0, y0)
            b = xy(x1, y1)
            out.append((a[0], a[1], b[0], b[1]))
    return tuple(out)


def normalize_read(text: str) -> str:
    """Sharpie / OCR: I and L read as 1, O as 0 (Crockford)."""
    out = []
    for ch in text.strip().upper():
        if ch in "IL":
            out.append("1")
        elif ch == "O":
            out.append("0")
        else:
            out.append(ch)
    return "".join(out)


def check_digit(body: str) -> str:
    n = 0
    for ch in body:
        n = n * 32 + CROCKFORD.index(ch.upper())
    return CHECK_ALPHABET[n % 37]


def verify_print_id(code: str) -> bool:
    code = normalize_read(code)
    if len(code) != 5:
        return False
    body, chk = code[:4], code[4]
    if any(c not in CROCKFORD for c in body):
        return False
    return chk == check_digit(body)


def _random_body(n: int = 4, rng=None) -> str:
    pick = rng.choice if rng is not None else secrets.choice
    return "".join(pick(CROCKFORD) for _ in range(n))


def list_ids(index: Path | None = None) -> set[str]:
    path = Path(index or INDEX_PATH)
    if not path.is_file():
        return set()
    ids: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ids.add(str(json.loads(line)["print_id"]))
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
    return ids


def issue_print_id(index: Path | None = None) -> str:
    used = list_ids(index)
    for _ in range(64):
        body = _random_body()
        pid = body + check_digit(body)
        if pid not in used:
            return pid
    raise RuntimeError("could not issue a unique print-id")


def record_export(index: Path | None = None, **fields) -> None:
    path = Path(index or INDEX_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(fields, sort_keys=True) + "\n")


def export_stem(print_id: str, base: str, stamp: str) -> str:
    return f"{print_id}_{base}_{stamp}"


def recipe_hash(params) -> str:
    payload = asdict(params) if is_dataclass(params) else dict(params)
    blob = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


def git_head(root: Path | None = None) -> str:
    cwd = Path(root) if root is not None else Path(__file__).resolve().parents[2]
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd, capture_output=True, text=True, timeout=5, check=False,
        )
        h = (r.stdout or "").strip()
        return h if r.returncode == 0 and h else "unknown"
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
