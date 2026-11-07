#!/usr/bin/env bash
# test_zoo.sh - play our bot against every practice bot in dev/zoo/ and
# dev/sparring/ (any new *.py you drop in either folder is picked up
# automatically; files starting with _ are helpers and skipped) and print
# W-C-L, bb/deal and thinking time per opponent. By default it also writes
# an HTML tearsheet report (dev/tearsheet.py) to dev/results/, and copies
# the newest one to dev/results/latest.html.
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
#   -g GROUPS   comma-separated opponent groups: zoo, sparring, baselines
#               (default zoo,sparring)
#   -B          also play the four baseline-bots/ (same as adding baselines to -g)
#   -t SECONDS  time bank per half (default 8; lower it to mimic a slower CPU)
#   -j JOBS     matches run in parallel on this machine (default: half the cores)
#   -s OFFSET   seed offset, to get fresh deals (default 0)
#   -o FILE     tearsheet output path (default dev/results/tearsheet_<time>.html)
#   -J          also save the tearsheet's raw data as .json next to the html
#   -O          open the tearsheet in a browser when done
#   -R          no report: quick harness table only (adds avg/p99 decision ms)
#   -h          show this help
#
# Python: uses $PYTHON if set, else .venv/bin/python or venv/bin/python if
# present, else python3.
#
# Examples:
#   dev/test_zoo.sh                    # 3 matches vs each zoo + sparring bot
#   dev/test_zoo.sh -n 10 -B           # 10 matches vs zoo + sparring + baselines
#   dev/test_zoo.sh -g sparring        # sparring bots only
#   dev/test_zoo.sh -n 10 -O           # report, then open it
#   dev/test_zoo.sh -R                 # quick table, no report
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
REPORT=1
OUT=""
JSON=0
OPEN=0
OPP_GROUPS=(zoo sparring)

usage() { sed -n '2,/^set -euo/p' "$0" | sed '$d' | sed 's/^# \{0,1\}//'; }

while getopts "n:d:b:g:Bt:j:s:o:JORh" opt; do
  case "$opt" in
    n) GAMES="$OPTARG" ;;
    d) DEALS="$OPTARG" ;;
    b) BOT="$OPTARG" ;;
    g) IFS=',' read -r -a OPP_GROUPS <<< "$OPTARG" ;;
    B) OPP_GROUPS+=(baselines) ;;
    t) BANK="$OPTARG" ;;
    j) JOBS="$OPTARG" ;;
    s) OFFSET="$OPTARG" ;;
    o) OUT="$OPTARG" ;;
    J) JSON=1 ;;
    O) OPEN=1 ;;
    R) REPORT=0 ;;
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
FOUND=0
for group in "${OPP_GROUPS[@]}"; do
  case "$group" in
    zoo)       bots=(dev/zoo/[!_]*.py) ;;
    sparring)  bots=(dev/sparring/[!_]*.py) ;;
    baselines) bots=(baseline-bots/*.py) ;;
    *) echo "error: unknown group '$group' (use zoo, sparring, baselines)" >&2; exit 2 ;;
  esac
  if [[ ${#bots[@]} -eq 0 ]]; then
    echo "warning: no bots found for group '$group'" >&2
    continue
  fi
  FOUND=$((FOUND + ${#bots[@]}))
  echo "$group bots: $(basename -a "${bots[@]}" | tr '\n' ' ')"
done
if [[ $FOUND -eq 0 ]]; then
  echo "error: no opponent bots found" >&2
  exit 1
fi

ARGS=(--bot "$BOT" --opp "${OPP_GROUPS[@]}" --deals "$DEALS" --seeds "$GAMES"
      --bank "$BANK" --seed-offset "$OFFSET")
[[ -n "$JOBS" ]] && ARGS+=(--jobs "$JOBS")

if [[ $REPORT -eq 0 ]]; then
  exec "$PY" dev/harness.py "${ARGS[@]}"
fi

# The tearsheet plays the matches itself (same rules as the harness) and
# prints the summary table, so nothing is played twice.
mkdir -p dev/results
[[ -z "$OUT" ]] && OUT="dev/results/tearsheet_$(date +%Y%m%d_%H%M%S).html"
ARGS+=(--out "$OUT")
[[ $JSON -eq 1 ]] && ARGS+=(--json)
"$PY" dev/tearsheet.py "${ARGS[@]}"
# Stable name for the newest report, so it's always easy to find.
[[ "$OUT" -ef dev/results/latest.html ]] || cp "$OUT" dev/results/latest.html
echo "latest report: $ROOT/dev/results/latest.html"

if [[ $OPEN -eq 1 ]]; then
  if command -v open >/dev/null; then open "$OUT"
  elif command -v xdg-open >/dev/null; then xdg-open "$OUT"
  else echo "open $OUT in a browser"; fi
fi
