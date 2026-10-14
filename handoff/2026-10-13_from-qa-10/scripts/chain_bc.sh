#!/bin/bash
# QA r10b: B (resumable) then C.2 (resumable), one build at a time. setsid nohup bash chain_bc.sh
cd /workspace/fansim/repo-r10; export PYTHONPATH=/workspace/fansim/repo-r10; PY=/workspace/fansim/repo-r9/.venv/bin/python
S=handoff/2026-10-13_from-qa-10/scripts
$PY $S/run_b.py /tmp/qa10b_sample.jsonl /tmp/qa10b_out > /tmp/qa10b_run.log 2>&1
$PY $S/c2_measure.py /tmp/qa10_c1.jsonl /tmp/qa10_c2.jsonl > /tmp/qa10c2_run.log 2>&1
echo CHAIN_DONE >> /tmp/qa10c2_run.log
