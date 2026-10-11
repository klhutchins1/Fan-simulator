"""Memory tiers: pick the CAD strategy that fits the RAM actually free on this machine.

The heavy step is the boolean fuse of the hub + N lofted blades (motor-cup Preview, Export, the
mount gauge). Its peak depends only on how it is run; every strategy gives the same solid (equal
volume and vertex count; the STL files differ only in face order, so they are NOT byte-identical:
QA-20, round 6) (QA round 4, ``docs/qa/notes/cup-fuse-memory.md``, Stock A12x25 with motor cup, Linux):

=============================================  =========  ======
strategy                                         peak RAM   time
=============================================  =========  ======
parallel fuse, all blades at once (OCCT default)  7.7 GB     73 s
serial fuse, all blades at once                   4.9 GB     85 s
serial fuse, one blade at a time                  4.5 GB    200 s
=============================================  =========  ======

(~1.9 GB of that is the process itself: imports + lofts.) These figures are for Stock-like blades.
Surface features multiply the face count and the fuse peak with it (featured 9-blade: 6.5 GB on
every strategy); ``check_fuse_memory`` below refuses a build that would not fit (roadmap 25.5). The tier is chosen from the RAM that is
*available* when the build starts, not the installed total: a 32 GB desktop with a CFD VM holding
12 GB has ~9 GB free and must not start a 7.7 GB fuse.

Tiers follow common machine sizes. Below ~6 GB free even the leanest strategy cannot fuse a motor-cup
impeller, so the cockpit says so instead of starting a build that would swap or crash; the plain
(non-cup) Preview needs no fuse and works on every tier.

``FANSIM_MEMORY_TIER`` (a tier name below) overrides detection, e.g. for tests or to force the
lean path on a shared machine.
"""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from dataclasses import dataclass

ENV_TIER = "FANSIM_MEMORY_TIER"
GB = 1024 ** 3


@dataclass(frozen=True)
class MemoryTier:
    name: str
    min_free_gb: float          # this tier applies when at least this much RAM is free
    fuse_parallel: bool         # OCCT boolean in parallel (fast, ~7.7 GB) or serial (~4.9 GB)
    fuse_one_blade_at_a_time: bool  # sequential hub+b1, +b2, ... (lowest peak, ~2.7x slower)
    cup_build_ok: bool          # enough free RAM to fuse a motor-cup impeller at all
    note: str


# Ordered from largest to smallest; the first whose min_free_gb is met wins.
TIERS: tuple[MemoryTier, ...] = (
    MemoryTier("32gb", 24.0, True, False, True, "parallel fuse (fastest)"),
    MemoryTier("16gb", 10.0, True, False, True, "parallel fuse"),
    MemoryTier("8gb", 6.5, False, False, True, "serial fuse (~4.9 GB peak, ~15 % slower)"),
    MemoryTier("6gb", 5.0, False, True, True,
               "serial fuse one blade at a time (~4.5 GB peak, ~2.7x slower)"),
    MemoryTier("4gb", 3.0, False, True, False,
               "too little free RAM for a motor-cup build; plain Preview only"),
    MemoryTier("2gb", 0.0, False, True, False,
               "too little free RAM for a motor-cup build; plain Preview only"),
)
_BY_NAME = {t.name: t for t in TIERS}


def _free_bytes_windows() -> int | None:
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

    st = MEMORYSTATUSEX()
    st.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st)):  # type: ignore[attr-defined]
        return None
    return int(st.ullAvailPhys)


def _free_bytes_linux() -> int | None:
    try:
        with open("/proc/meminfo", encoding="ascii") as fh:
            for line in fh:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) * 1024
    except OSError:
        return None
    return None


def _free_bytes_macos() -> int | None:
    try:
        out = subprocess.run(["vm_stat"], capture_output=True, text=True, timeout=5).stdout
        page = int(out.split("page size of")[1].split()[0])
        pages = 0
        for line in out.splitlines():
            if line.startswith(("Pages free:", "Pages inactive:", "Pages speculative:")):
                pages += int(line.split(":")[1].strip().rstrip("."))
        return pages * page
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        return None


def free_ram_bytes() -> int | None:
    """RAM available to a new process right now, or None if it cannot be read."""
    if sys.platform == "win32":
        return _free_bytes_windows()
    if sys.platform == "darwin":
        return _free_bytes_macos()
    return _free_bytes_linux()


def tier_for_free_gb(free_gb: float) -> MemoryTier:
    for tier in TIERS:
        if free_gb >= tier.min_free_gb:
            return tier
    return TIERS[-1]


def current_tier() -> MemoryTier:
    """Tier from ``FANSIM_MEMORY_TIER`` if set, else from the RAM free right now.

    If free RAM cannot be read, assume the 8 GB tier (serial fuse): safe everywhere, ~15 % slower.
    """
    forced = os.environ.get(ENV_TIER, "").strip().lower()
    if forced:
        if forced not in _BY_NAME:
            raise ValueError(f"{ENV_TIER}={forced!r}: expected one of {sorted(_BY_NAME)}")
        return _BY_NAME[forced]
    free = free_ram_bytes()
    return _BY_NAME["8gb"] if free is None else tier_for_free_gb(free / GB)


# --- Fuse peak from the face count (roadmap 25.5) ------------------------------------------------
# The fuse's peak RAM grows with how many faces it joins, whatever the strategy above. Measured on
# Windows 2026-10-11 (docs/validation/audits/2026-10-11-fuse-memory.md): 9-blade plain design,
# 18 084 faces -> 2.0 GB; featured S5_0011 (tubercles + serrations + dimples), 71 229 faces -> 6.5 GB
# (6.0 GB even one blade at a time). Both fit ~0.37 GB (process + imports) + 86 kB per face.
FUSE_BASE_GB = 0.37
FUSE_GB_PER_FACE = 8.6e-5
FUSE_MARGIN = 1.15  # headroom over the estimate before a build is allowed


def fuse_peak_estimate_gb(n_faces: int) -> float:
    return FUSE_BASE_GB + FUSE_GB_PER_FACE * float(n_faces)


def check_fuse_memory(n_faces: int) -> None:
    """Raise ``MemoryError`` with a plain message when the fuse would not fit in free RAM.

    A build that swaps can freeze the whole machine (QA round 6 saw 6 h of a frozen box), so it is
    refused up front. If free RAM can't be read, or the tier is forced, the build goes ahead.
    """
    if os.environ.get(ENV_TIER):
        return
    free = free_ram_bytes()
    if free is None:
        return
    need = fuse_peak_estimate_gb(n_faces) * FUSE_MARGIN
    have = free / GB
    if need > have:
        raise MemoryError(
            f"This design needs about {need:.1f} GB of free memory to build ({n_faces:,} surfaces; "
            f"surface features add many) but only {have:.1f} GB is free. Close other programs, or "
            f"turn some surface features off, and try again.")
