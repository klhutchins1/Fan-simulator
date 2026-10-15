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


# --- Fuse RAM (roadmap 25.5 / 27.1) --------------------------------------------------------------
# Whole-peak working set, Windows 2026-10-11 (docs/validation/audits/2026-10-11-fuse-memory.md):
# 18 084 faces -> 2.0 GB; featured S5_0011 71 229 faces -> 6.5 GB. ~0.37 GB + 86 kB/face.
# The *guard* must model remaining growth after the call: the worker already holds 1–2 GB of lofts
# (QA r8: Linux increment 0.28 GB + 72 KiB/face; r9: shroud extra ~66 KiB per *blade* face, not
# the ring's 4 faces). Windows remaining-growth constants are in _growth_constants().
FUSE_BASE_GB = 0.37
FUSE_GB_PER_FACE = 8.6e-5
FUSE_MARGIN = 1.15  # headroom over remaining growth before a build is allowed
ENV_FUSE_GUARD = "FANSIM_FUSE_GUARD"  # "1" = refuse builds that would not fit (set by the cockpit)
_KIB = 1024.0


def _kib_per_face_to_gb(kib: float) -> float:
    return kib * _KIB / GB


def _growth_constants() -> tuple[float, float, float]:
    """(base_gb, gb_per_face, shroud_gb_per_blade_face) for remaining growth after the guard call.

    Remaining = peak at exit − RSS/working set at the ``check_fuse_memory`` call.
    Linux: QA r12 open-fan refit (0.515 GB + 82.3 KiB/face; was the r8 0.28 + 72); r9 Task E shroud
    extra 66 KiB per *blade* face (the ring itself is four faces).
    Windows: 2026-10-13 ``scripts/measure_fuse_growth.py`` (PeakWorkingSet − WorkingSet at
    call). Two open builds want a negative intercept; intercept is pinned at 0.10 GB and the
    slope (103 KiB/face) is taken from Stock v3 so both open points sit under the line. The
    ring extra is 26 KiB per blade face (open_9b vs ring_9b twins), not the Linux 66.
    """
    if sys.platform == "win32":
        return 0.10, _kib_per_face_to_gb(103.0), _kib_per_face_to_gb(26.0)
    # Linux open fans refit 2026-10-15 (QA-35, r12 Task B): the r8 0.28 GB + 72 KiB/face under-asked
    # open 9/11-blade fuses (S7_0172_twin 1.03x the ask). Pre-registered rule, audit
    # 2026-10-15-fuse-open-refit: worst r12 open build at 0.95 of the estimate; r8 open builds <= 0.76
    # of the ask. The shroud term is unchanged (shrouded builds sit <= 0.80).
    return 0.515, _kib_per_face_to_gb(82.3), _kib_per_face_to_gb(66.0)


def fuse_peak_estimate_gb(n_faces: int) -> float:
    """Whole-process peak (diagnostic / K12). The guard uses ``fuse_remaining_estimate_gb``."""
    return FUSE_BASE_GB + FUSE_GB_PER_FACE * float(n_faces)


def fuse_remaining_estimate_gb(
    n_faces: int, *, shrouded: bool = False, n_blade_faces: int | None = None,
) -> float:
    """RAM the fuse still needs after ``check_fuse_memory`` runs (process already holds the lofts)."""
    base, per_face, shroud_per_blade = _growth_constants()
    need = base + per_face * float(max(0, int(n_faces)))
    if shrouded:
        blades = int(n_faces) if n_blade_faces is None else int(n_blade_faces)
        need += shroud_per_blade * float(max(0, blades))
    return need


def process_rss_bytes() -> int | None:
    """This process's current RAM (Windows working set / Linux VmRSS), or None."""
    if sys.platform == "win32":
        ws = _process_working_set_windows()
        return None if ws is None else ws[0]
    return _process_vm_linux("VmRSS")


def process_peak_rss_bytes() -> int | None:
    """Peak RAM for this process (Windows PeakWorkingSet / Linux VmHWM), or None."""
    if sys.platform == "win32":
        ws = _process_working_set_windows()
        return None if ws is None else ws[1]
    return _process_vm_linux("VmHWM")


def _process_working_set_windows() -> tuple[int, int] | None:
    class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    counters = PROCESS_MEMORY_COUNTERS()
    counters.cb = ctypes.sizeof(counters)
    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    handle = kernel32.GetCurrentProcess()
    get_info = getattr(kernel32, "K32GetProcessMemoryInfo", None)
    if get_info is None:
        get_info = ctypes.windll.psapi.GetProcessMemoryInfo  # type: ignore[attr-defined]
    get_info.argtypes = [ctypes.c_void_p, ctypes.POINTER(PROCESS_MEMORY_COUNTERS), ctypes.c_ulong]
    get_info.restype = ctypes.c_int
    if not get_info(handle, ctypes.byref(counters), counters.cb):
        return None
    return int(counters.WorkingSetSize), int(counters.PeakWorkingSetSize)


def _process_vm_linux(key: str) -> int | None:
    try:
        with open("/proc/self/status", encoding="ascii") as fh:
            for line in fh:
                if line.startswith(key + ":"):
                    return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        return None
    return None


def check_fuse_memory(
    n_faces: int, *, shrouded: bool = False, n_blade_faces: int | None = None,
) -> None:
    """Raise ``MemoryError`` with a plain message when the fuse would not fit in free RAM.

    Guards *remaining* growth (lofts are already in RAM), plus a shroud term that scales with
    blade faces — the ring itself is only four faces (QA r9 Task E). A build that swaps can freeze
    the whole machine (QA round 6 saw 6 h of a frozen box), so it is refused up front. Only where a
    person reads the message: the cockpit sets ``FANSIM_FUSE_GUARD=1``. In batch work (optimizer,
    Assess scoring, scripts, tests) a refusal would be recorded as an infeasible design, so those
    builds always go ahead. Also skipped if free RAM can't be read or the tier is forced.
    """
    if os.environ.get(ENV_FUSE_GUARD, "") != "1" or os.environ.get(ENV_TIER):
        return
    free = free_ram_bytes()
    if free is None:
        return
    need = fuse_remaining_estimate_gb(
        n_faces, shrouded=shrouded, n_blade_faces=n_blade_faces) * FUSE_MARGIN
    have = free / GB
    if need > have:
        raise MemoryError(
            f"This design needs about {need:.1f} GB of free memory to finish building "
            f"({n_faces:,} surfaces; surface features add many) but only {have:.1f} GB is free. "
            f"Close other programs, or turn some surface features off, and try again.")
