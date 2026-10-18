#!/bin/bash
# QA r15 R3.3 (report-only, since the install section does not exist yet): follow README "Quickstart" at 9562574
# in a fresh clone with an empty uv cache. Docker/OpenFOAM steps are skipped (not allowed on this box).
# Step 2 (full fast suite) is replaced by the UI test file; the full suite peaks at ~8 GB (QA_REVIEW).
LOG=/workspace/fansim/repo-r15/handoff/2026-10-17_from-qa-15/data/r33_quickstart.log
D=/tmp/qa15_install; export UV_CACHE_DIR=/tmp/qa15_uvcache
t0=$(date +%s.%N); el(){ python3 -c "import time;print(round(time.monotonic(),1))"; }
{
echo "START $(date -Is) mono=$(el)"
rm -rf $D && git clone -q /workspace/fansim/repo-r15 $D && cd $D && git checkout -q 9562574 && git log --oneline -1
echo "== uv sync --extra dev"; s=$(el); uv sync --extra dev > /tmp/qa15_uvsync.out 2>&1; echo "rc=$? secs=$(python3 -c "print(round($(el)-$s,1))")"; tail -5 /tmp/qa15_uvsync.out
echo "== python version"; uv run python -V
echo "== import fansim"; uv run python -c "import fansim,sys;print(fansim.__file__)"; echo rc=$?
echo "== UI test file"; uv run python -m pytest -q -p no:cacheprovider tests/test_ui_says_what_it_does.py 2>&1 | tail -2
echo "== cockpit --help"; timeout 120 uv run python scripts/cockpit.py --help 2>&1 | head -15; echo rc=${PIPESTATUS[0]}
echo "== plain uv sync has no pytest? (README claim; not run: would remove dev deps)"
echo "CHAIN_DONE $(date -Is) mono=$(el)"
} >> $LOG 2>&1
