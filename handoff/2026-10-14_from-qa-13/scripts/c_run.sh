#!/bin/bash
# QA r13 Task C: chunked fast suite + RSS sampler. setsid nohup bash c_run.sh. Args after: optional "--chunk K" (resume one chunk).
D=/workspace/fansim/repo-r13/handoff/2026-10-14_from-qa-13/data; S=/workspace/fansim/repo-r13/handoff/2026-10-14_from-qa-13/scripts
PY=/workspace/fansim/repo-r9/.venv/bin/python
cd /workspace/fansim/qa/run_r13; export PYTHONPATH=$PWD PYTHONDONTWRITEBYTECODE=1
echo "start $(date -Is) mono $(cut -d' ' -f1 /proc/uptime) oom_kill $(grep oom_kill /proc/vmstat | cut -d' ' -f2)" >> $D/c_meta.txt
SEL=${1:---all}; shift
$PY scripts/pytest_chunks.py --chunks 3 $SEL "$@" -- -m "not docker and not slow" -q --tb=line -p no:cacheprovider >> $D/c_suite.log 2>&1 &
PID=$!; $PY $S/c_sampler.py $PID $D/c_suite.log $D/c_rss.jsonl & wait $PID; RC=$?
echo "end $(date -Is) rc $RC oom_kill $(grep oom_kill /proc/vmstat | cut -d' ' -f2)" >> $D/c_meta.txt
