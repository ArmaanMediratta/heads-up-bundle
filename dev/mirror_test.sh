#!/usr/bin/env bash
# mirror_test.sh - agent-vs-agent test of the mirror detector (bot/mirror.py).
#
# Part 1 (detection, dev/mirror_report.py): single halves of agent.py@mirror=1
# vs each opponent; prints the flag rate per opponent and per set:
#   self (agent.py), near-relative (demon/demon.py), equity family (group
#   "equity": dev/cousins/* template cousins + mc_grinder + equity_caller),
#   independent (challenger/challenger.py, when present), and the
#   false-positive set (every other zoo, sparring and baseline bot).
# It also plays agent.py vs agent.py with BOTH detectors on vs off and prints
# average pot and raise share: flagging each other must never make play passive.
#
# Part 2 (value): paired duplicate matches via dev/compare.py, mirror on vs off
# (reference = off). With MIRROR_COUNTER = {} the two configs play the same
# strategy, so this measures only the detector's cost; rerun it once the
# counter bundle is plugged in.
#
# Usage: dev/mirror_test.sh [-n SEEDS] [-d DEALS] [-j JOBS] [-D] [-C]
#   -n SEEDS   halves per opponent in part 1, seeds in part 2 (default 3)
#   -d DEALS   deals per half / match (default 1000)
#   -j JOBS    parallel jobs (default 2)
#   -D         detection only (skip part 2)
#   -C         compare only (skip part 1)
#
# Part 2 by hand:
#   python3 dev/compare.py --opp agent.py "agent.py@mirror=1" demon/demon.py challenger/challenger.py \
#       cousins zoo sparring baselines --seeds 3 --jobs 2 off=agent.py on=agent.py@mirror=1
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PY="${PYTHON:-python3}"
SEEDS=3; DEALS=1000; JOBS=2; DETECT=1; COMPARE=1
while getopts "n:d:j:DCh" opt; do
  case "$opt" in
    n) SEEDS="$OPTARG" ;; d) DEALS="$OPTARG" ;; j) JOBS="$OPTARG" ;;
    D) COMPARE=0 ;; C) DETECT=0 ;;
    h) sed -n '2,/^set -euo/p' "$0" | sed '$d' | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) exit 2 ;;
  esac
done

if [[ $DETECT -eq 1 ]]; then
  echo "== detection"
  "$PY" dev/mirror_report.py --seeds "$SEEDS" --deals "$DEALS" --jobs "$JOBS"
fi

if [[ $COMPARE -eq 1 ]]; then
  echo
  echo "== value: paired duplicate matches, mirror on vs off (reference = off)"
  MAINS=(agent.py "agent.py@mirror=1" demon/demon.py)
  [[ -f challenger/challenger.py ]] && MAINS+=(challenger/challenger.py)
  "$PY" dev/compare.py --opp "${MAINS[@]}" cousins zoo sparring baselines \
      --seeds "$SEEDS" --deals "$DEALS" --jobs "$JOBS" off=agent.py on=agent.py@mirror=1
fi
