#!/usr/bin/env bash
# test_zoo.sh - play our bot against every practice bot in dev/zoo/ (any new
# *.py you drop there is picked up automatically; files starting with _ are
# helpers and skipped) and print W-C-L, bb/deal and thinking time per opponent.
#
# Each "game" is one full duplicate match, scored like the tournament:
# 1000 deals, then the same deals with seats swapped. WIN = 95% interval
# above 0, LOSS = below 0, CHOP = touches 0.
#
# Usage: dev/test_zoo.sh [options]
#   -n GAMES    matches per opponent (default 3)
#   -d DEALS    deals per match (default 1000, like the tournament)
#   -b BOT      bot under test, optionally with param overrides,
#               e.g. "agent.py@r_oop=0.9" (default agent.py)
#   -B          also play the four baseline-bots/
#   -t SECONDS  time bank per half (default 8; lower it to mimic a slower CPU)
#   -j JOBS     matches run in parallel on this machine (default: half the cores)
#   -s OFFSET   seed offset, to get fresh deals (default 0)
#   -h          show this help
#
# Python: uses $PYTHON if set, else .venv/bin/python or venv/bin/python if
# present, else python3.
#
# Examples:
#   dev/test_zoo.sh                    # 3 matches vs each zoo bot
#   dev/test_zoo.sh -n 10 -B           # 10 matches vs zoo + baselines
#   dev/test_zoo.sh -n 5 -t 4          # half the time bank
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

GAMES=3
DEALS=1000
BOT="agent.py"
BANK=8
JOBS=""
OFFSET=0
OPP_GROUPS=(zoo)

usage() { sed -n '2,/^set -euo/p' "$0" | sed '$d' | sed 's/^# \{0,1\}//'; }

while getopts "n:d:b:Bt:j:s:h" opt; do
  case "$opt" in
    n) GAMES="$OPTARG" ;;
    d) DEALS="$OPTARG" ;;
    b) BOT="$OPTARG" ;;
    B) OPP_GROUPS+=(baselines) ;;
    t) BANK="$OPTARG" ;;
    j) JOBS="$OPTARG" ;;
    s) OFFSET="$OPTARG" ;;
    h) usage; exit 0 ;;
    *) usage; exit 2 ;;
  esac
done

if [[ -n "${PYTHON:-}" ]]; then
  PY="$PYTHON"
elif [[ -x .venv/bin/python ]]; then
  PY=.venv/bin/python
elif [[ -x venv/bin/python ]]; then
  PY=venv/bin/python
else
  PY=python3
fi

if ! "$PY" -c "import numpy, fastapi" 2>/dev/null; then
  echo "error: $PY can't import numpy/fastapi. Run: $PY -m pip install -r requirements-dev.txt numpy" >&2
  exit 1
fi

shopt -s nullglob
ZOO=(dev/zoo/[!_]*.py)
if [[ ${#ZOO[@]} -eq 0 ]]; then
  echo "error: no bots found in dev/zoo/" >&2
  exit 1
fi
echo "zoo bots: $(basename -a "${ZOO[@]}" | tr '\n' ' ')"

ARGS=(--bot "$BOT" --opp "${OPP_GROUPS[@]}" --deals "$DEALS" --seeds "$GAMES"
      --bank "$BANK" --seed-offset "$OFFSET")
[[ -n "$JOBS" ]] && ARGS+=(--jobs "$JOBS")

exec "$PY" dev/harness.py "${ARGS[@]}"
