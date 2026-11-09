#!/bin/bash
# ui-hunt-1 (PREREG cf2c813) re-check runner, adapted from qa_r25b/run_a.sh. Cockpit headless; Preview-only clicks.
set -u; R=/workspace/fansim/repo-r26-g2; P=8811; Q25=/workspace/fansim/qa_r25/scripts; Q=/workspace/fansim/qa_ui_hunt1; PW=/workspace/fansim/qa_tooltips/pwenv/bin/python
D=$Q/data/recheck; S=$Q/screens/recheck; RUN=$Q/cockpit_run; mkdir -p $D $S; rm -rf $RUN; mkdir -p $RUN
cd $R && nohup .venv/bin/python scripts/cockpit.py --run $RUN --port $P > $D/cockpit.log 2>&1 &
for i in $(seq 1 90); do curl -s -o /dev/null http://127.0.0.1:$P/ && break; sleep 2; done
export QA_PORT=$P
$PW $Q25/a_ui.py $D/a_ui.json $S > $D/a_ui.log 2>&1; echo "a_ui $?"
$PW $Q25/a_tooltips.py $D/a_tooltips.json > $D/a_tooltips.log 2>&1; echo "a_tooltips $?"
pkill -f "scripts/cockpit.py --run $RUN"
cd $R; export QA_REPO=$R QA_DATA=$D
.venv/bin/python $Q25/scan_controls.py $R $D/scan.json > $D/scan.log 2>&1; echo "scan $?"
.venv/bin/python $Q25/build_inventory.py > $D/inventory.log 2>&1; echo "inventory $?"
QA_RANGE_OUT=$D/range_check.json .venv/bin/python $Q25/range_check.py $R > $D/range.log 2>&1; echo "range $?"
