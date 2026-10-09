#!/bin/bash
# $1 label; extra env passed through
.venv/bin/python -m pytest -q -p no:cacheprovider "tests/test_mount_gauge.py::test_gauge_accepts_carved_stock_export" > /tmp/pp_$1.log 2>&1 &
PID=$!; peak=0; dumped=0; t0=$(date +%s.%N)
while kill -0 $PID 2>/dev/null; do
  r=$(awk '/VmRSS/{print int($2/1024)}' /proc/$PID/status 2>/dev/null); th=$(awk '/Threads/{print $2}' /proc/$PID/status 2>/dev/null)
  [ -n "$r" ] && [ "$r" -gt "$peak" ] && peak=$r
  if [ -n "$r" ] && [ "$r" -gt 4000 ] && [ $dumped -eq 0 ]; then dumped=1; ${PYSPY:-py-spy} dump --native --pid $PID > /tmp/pp_$1.spy 2>&1; echo "dump at ${r} MB threads=$th"; fi
  sleep 0.5
done
echo "$1 peak=${peak} MB $(tail -1 /tmp/pp_$1.log)"
