"""Short Crockford print-part IDs issued at Export (roadmap 28.2). No hub cut."""
from __future__ import annotations

import hashlib
import json
import secrets
import subprocess
from dataclasses import asdict, is_dataclass
from pathlib import Path

CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
CHECK_ALPHABET = CROCKFORD + "*~$=U"
INDEX_PATH = Path(__file__).resolve().parents[2] / "validation" / "prints" / "index.jsonl"


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
