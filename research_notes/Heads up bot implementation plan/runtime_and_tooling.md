# Runtime, Tooling, Testing, Packaging and Extension Points (heads-up-bundle)

Scope: how the repo at `/Users/armaanmediratta/Desktop/datathon/heads-up-bundle` is run, tested and submitted, what the runtime enforces, what a bot sees, and where a new bot plugs in. Sources are repo files (cited as `file:line`) and commands actually run on 2026-11-07 (macOS, Python 3.13.2 in a scratch venv; output pasted below). Repo HEAD `c83ab6e`; no tracked files were modified (`git status` shows only the untracked `research_notes/`).

Source link convention: `[agent.py:61](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/agent.py)` means that file, that line. "Run log" means output I captured by running the command myself.

---

## 1. Setup and running a local match (commands, entry points, CLI args, config)

### Takeaway
There is no Makefile or config file: the setup is `pip install -r requirements-dev.txt`, then three processes. Your bot (`python agent.py`, port 5008), an opponent (`python baseline-bots/<bot>.py`, port 5009), and the referee (`python judge_engine.py`). The judge is configured only by CLI flags or env vars. I ran this and it works: a 1000-deal duplicate match between simple bots takes about 3 s.

### Cited Findings
- Setup is `pip install -r requirements-dev.txt` (a venv is suggested). That file is `-r requirements.txt`, `pytest>=8`, `httpx==0.28.1`. `requirements.txt` pins `fastapi==0.156.1` and `uvicorn==0.54.0` — [README.md §2](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/README.md), [requirements-dev.txt](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/requirements-dev.txt), [requirements.txt](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/requirements.txt)
- Local environment note: system `python3` (3.13.2) did not have fastapi installed, there is no `python` alias, and `docker` is not installed on this machine. Installing requirements-dev into a fresh venv worked (fastapi 0.156.1, uvicorn 0.54.0, httpx 0.28.1, pytest 9.2.0, starlette 1.10.0) — run log
- Docs say three terminals: `python agent.py` (port 5008), `python baseline-bots/baseline_random.py` (port 5009), `python judge_engine.py --deals 200` — [README.md §4](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/README.md)
- Ports: `agent.py` reads `PORT` and defaults to 5008. Every baseline defaults to 5009 ([agent.py:235-236](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/agent.py), [baseline_random.py](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/baseline-bots/baseline_random.py)). The default constants are `AGENT1_DEFAULT_PORT = 5008` and `AGENT2_DEFAULT_PORT = 5009` — [game.py:41-42](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/game.py)
- Baseline bots: `baseline_random.py` (RandomBot, seeded `random.Random(0)` per half), `baseline_always_pot.py` (AlwaysPot), `baseline_always_half.py`, and `baseline_calling_station.py`. All are built from the agent.py template, and they add `sys.path.insert(0, parent dir)` so they can import `game`/`evaluator` from `baseline-bots/` — [baseline-bots/](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/baseline-bots/), diff vs agent.py (run log)
- Judge CLI flags and their env-var fallbacks:
  - `--agent1` (env `AGENT1_URL`, default 5008) and `--agent2` (env `AGENT2_URL`, default 5009). Each takes a port or a full `http://host:port` URL.
  - `--half 1|2` (env `HALF`).
  - `--seed` (env `MATCH_SEED`, default "1").
  - `--deals` (default 1000).
  - `--json PATH`, and `--logs` to include every hand.
  - A subcommand `combine h1.json h2.json [--json PATH]`.
  - Tokens come from `AGENT1_TOKEN` / `AGENT2_TOKEN`.
  - Exit codes: 0 when finished, 2 for bad args, 3 when it cannot run.
  — [judge_engine.py:913-1040](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/judge_engine.py)
- Without `--half`, `play_match` plays both halves back to back against the same two processes. Its docstring says "LOCAL PRACTICE ONLY... a bot could remember half 1's cards in half 2" — [judge_engine.py:794-804](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/judge_engine.py)
- Tournament-faithful flow: run `--half 1 --seed 7 --json h1.json`, restart both bots, run `--half 2 ... --json h2.json`, then `combine h1.json h2.json` — [README.md §4](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/README.md)
- Run log: starter agent (check-or-fold) vs RandomBot, `--deals 200 --seed 7 --json ... --logs`:
  ```
  Duplicate match: 200 deals (400 hands), seed 7
  agent1: -0.995 bb/deal  (std 0.72, stderr 0.051)
  Confidence interval (z=1.96): [-1.095, -0.895] bb/deal
  half1: agent1 -199 chips ... half2: agent1 -199 chips
  agent1 half1: thinking 0.00s of 8s (wall 0.06s), calls 223, errors 0
  Speed: 400 hands in 0.20s (2,045 hands/s)
  VERDICT: AGENT2 WINS  (Challenges Team / RandomBot ...)
  RESULT: AGENT2_WIN
  ```
- Run log: AlwaysPot vs RandomBot, 1000 deals, seed 3. `agent1: +8.950 bb/deal (std 29.92, stderr 0.946)`, CI `[+7.096, +10.805]`, AGENT1_WIN, `2000 hands in 2.85s (702 hands/s)`. Calls per half were about 1979 for AlwaysPot and about 2454 for RandomBot.
- Run log: running separate halves plus `combine` works. A single half ends with `RESULT: HALF_DONE`, and `combine` prints the full verdict report.
- The README says the tournament runs each half in a fresh Kubernetes pod with fresh bot containers and the same secret seed (`secrets.token_hex(16)`) — [judge_engine.py:10-19, 109-116](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/judge_engine.py)

### Inferences
- For fast iteration, the AlwaysPot-vs-Random variance (std about 30 bb per paired deal) means 1000 deals gives a CI half-width of about ±1.9 bb/deal. Finer comparisons between your own versions need many seeds or an in-process harness (see §6).
- For non-trivial bots, the safe local pattern is the `--half` + restart + `combine` flow. It catches bugs where the bot relies on globals carrying over between halves.

### Gaps
- `check_build.sh` could not be executed: Docker is not installed on this machine. Its behavior is documented from source only.

---

## 2. Runtime limits enforced in code

### Takeaway
Every limit lives in one constants block in `game.py`. The judge enforces them:
- 8 s thinking bank per half, minus 1 ms free per request.
- 1 s hard limit per request.
- 15 s startup.
- 5 errors means a forfeit, and a forfeit loses the whole match.

The container caps (1 CPU, 4 GB RAM, 512 MB `/tmp`, no network, read-only FS, 256 pids) are applied in `check_build.sh`. A request over 1 s counts as an error (with the default action played). Running out of bank is not an error. I verified each behavior by fault injection.

### Cited Findings
- Constants (the comment calls them "PROVISIONAL and may be tuned"):
  - `STARTING_STACK=80` (reset every hand), `BIG_BLIND=2`, `SMALL_BLIND=1`
  - `RAISE_CAP_PER_STREET=4`, `NUM_DEALS=1000`
  - `TIME_BANK_SECONDS=8.0`, `NETWORK_GRACE_SECONDS=0.001`
  - `ACTION_TIMEOUT_SECONDS=1.0`, `STARTUP_TIMEOUT_SECONDS=15.0`
  - `ERROR_LIMIT=5`, `CHOP_Z=1.96`
  — [game.py:25-43](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/game.py)
- Time charging: each POST is timed. `time_seconds += max(0, elapsed - 0.001)`. The timeout used is `min(1.0, bank_left + 0.001)`. — [judge_engine.py:358-386](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/judge_engine.py)
- What is charged: `/new-half`, `/act` and `/hand-end` all go through `_post`, so all are charged. `on_hand_end` runs inside the next `/act` request, so its CPU time counts against the bank — [judge_engine.py:435-481](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/judge_engine.py), [agent.py:200-220](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/agent.py)
- Timeout classification: if a timeout happens while the limit came from the bank (`bank_left < 1.0`), it only sets `timed_out` and is not an error. Otherwise it is recorded as the error `"<label> took longer than 1s"` — [judge_engine.py:368-375](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/judge_engine.py)
- Bank empty: `_usable()` returns False, increments `skipped_calls`, and the default action is played. The default is `CHECK_CALL` if `to_call == 0`, else `FOLD` — [judge_engine.py:348-356, 447-451](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/judge_engine.py), [game.py:108-111](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/game.py)
- Errors that count:
  - connection errors and malformed or oversized replies (>1,000,000 bytes)
  - HTTP non-200 replies, including a 500 that carries a traceback
  - a missing `action` field
  - a non-Action reply (booleans are rejected)
  - an illegal action
  - each `on_hand_end` exception listed in `hand_end_errors`

  `errors >= 5` gives `forfeited=True`. After that, the bot is never called again and plays the default action — [judge_engine.py:96, 179-194, 336-342, 376-401, 447-468](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/judge_engine.py)
- A failed `/new-half` means an immediate forfeit for that half (`start_half`: `if reply is None: forfeited = True`). A bot that doesn't answer `GET /` within 15 s also forfeits — [judge_engine.py:435-445, 987-998](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/judge_engine.py)
- A forfeit in either half loses the match (`AGENT2_WIN`/`AGENT1_WIN`/`BOTH_FORFEIT`), whatever the chips say — [judge_engine.py:742-762](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/judge_engine.py)
- The judge "cannot stop a computation already running inside the bot. The bot handles one request at a time, so after a timeout later requests may queue behind the slow one and time out too" — [judge_engine.py:273-276](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/judge_engine.py)
- Container restrictions in `check_build.sh`, which the README describes as matching the tournament:
  - `--network none --read-only --tmpfs /tmp:rw,nosuid,nodev,size=512m`
  - `--cap-drop ALL --security-opt no-new-privileges --pids-limit 256`
  - `--cpus 1 --memory 4g`
  - `PORT=5008 AGENT_TOKEN=local-check`

  — [tools/check_build.sh:28-29, 42-43, 98-110](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/tools/check_build.sh)
- Base image environment:
  - `OMP_NUM_THREADS=1` (also MKL, OPENBLAS, NUMEXPR and TF intra/inter = 1), because the VM has "96 cores shared by many bots"
  - `HOME=/tmp`, `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUNBUFFERED=1`
  - runs as non-root uid 10001
  - Python 3.12-slim

  — [docker/Dockerfile.base:24-60, 88-101](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/docker/Dockerfile.base)
- Fault-injection run log. Each case is a copy of agent.py in the scratchpad, played vs RandomBot for one half of 200 deals:
  - `choose_action` raises: `calls 6, errors 5 FORFEITED`, first error `choose_action raised RuntimeError: boom` plus the full traceback.
  - returns `"FOLD"` when not legal: `calls 28, errors 5 FORFEITED`, `choose_action returned illegal action FOLD (legal: CHECK_CALL, RAISE_HALF, RAISE_POT)`.
  - sleeps 1.2 s per decision: `thinking 5.00s of 8s ... calls 6, errors 5 FORFEITED`, `choose_action took longer than 1s`. So per-request timeouts are errors, and five of them forfeit.
  - sleeps 50 ms per decision, 1000 deals: `thinking 8.00s of 8s (wall 8.15s), calls 150, errors 0 TIME BANK EMPTY (979 calls skipped)`. No forfeit; the bot just check/folds afterwards.
- Run log, incidental: when a new bot process could not bind a port still held by a killed one, the judge reported `new_half connection error: ConnectionRefusedError` and gave an immediate `errors 1 FORFEITED`. This confirms that a single `/new-half` failure forfeits the half.
- Logging: uvicorn runs with `log_level="info", access_log=False`. Stdout is captured by Docker. `check_build.sh` prints `docker logs --tail 40` on failure — [agent.py:236](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/agent.py), [check_build.sh:112-117](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/tools/check_build.sh)
- Run log: `evaluator.warmup()` took 0.12 s on this Mac, and `omaha_score` cost about 15 µs per call (1000 random calls in 14.7 ms).

### Inferences
- Budget: about 1000 to 2500 `/act` calls per half (observed 135 to 2459 depending on style) against 8 s gives roughly 3 to 8 ms of average thinking per decision. The 1 ms per-request grace adds about 1 to 2.5 s of effectively free time.
- A bot should track its own elapsed time with `time.perf_counter()` inside `choose_action`. It should keep a hard internal cap well under 1 s per decision (e.g., ≤200 ms) and an adaptive per-decision budget, about (remaining bank) / (expected remaining decisions). Without this, a slow solver either forfeits (more than 1 s, five times) or check/folds the rest of the half.
- `omaha_score` at about 15 µs means a few hundred Monte Carlo river rollouts per decision fit in about 5 ms. Heavy equity work should use precomputed tables or numpy.
- The Mac is likely faster than the tournament's shared amd64 1-CPU slot. Leave a safety margin, and use `PLATFORM=linux/amd64 ./tools/check_build.sh` to test under emulation.

### Gaps
- Actual tournament VM CPU speed is unknown. The memory limit is known only from `check_build.sh` defaults (4g), not from the real pod spec.

---

## 3. What a bot receives each decision and what it must return

### Takeaway
`choose_action(obs, memory)` receives a frozen `Observation` dataclass with 17 fields:
- the cards
- the pot and bets
- the legal actions
- the exact `raise_to` totals for the two raise sizes
- the per-street raise count
- the full action history of the hand (blinds excluded)

It must return one member of `obs.legal_actions`. `Action` enums, their string names, or ints 0 to 3 are accepted. Only four discrete actions exist (FOLD, CHECK_CALL, RAISE_HALF, RAISE_POT). The engine computes the bet sizes; the bot never sends an amount.

### Cited Findings
- `Observation` fields:
  - `hand_index`, `street` (Street enum 0-3), `hole_cards` (5 ints sorted ascending), `board` (0, 3, 4 or 5 ints)
  - `pot` (both players' total contributions this hand), `to_call`, `my_bet`, `opp_bet` (this street), `my_stack`, `opp_stack` (behind)
  - `is_button`, `legal_actions` (tuple of Action), `raise_to` (dict Action→total street bet), `min_raise_to`, `raises_this_street`
  - `action_history` (tuple of ObservedAction: `street, is_me, action, amount, street_total`), `big_blind`

  — [game.py:199-269](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/game.py), [agent.py:64-86](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/agent.py)
- Card encoding: an int 0-35, with `rank = card >> 2` (0=six .. 8=ace) and `suit = card & 3` (c, d, h, s). Helpers: `card_rank`, `card_suit`, `card_to_str`, `str_to_card`, `cards_to_str`, `cards_from_str`, `omaha_score(hole, board)` (needs exactly 5 and 5), `category_of`, `category_name`, `score_five` — [evaluator.py:1-80, 123-260](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/evaluator.py)
- Legal actions:
  - FOLD only if `to_call > 0`.
  - CHECK_CALL always.
  - Raises only if `raises_this_street < 4`, `my_stack > to_call`, and `opp_stack > 0`.

  — [game.py:410-441](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/game.py)
- Raise sizing:
  - `pot_raise_to = opp_bet + pot + to_call`
  - `half_raise_to = opp_bet + (pot + to_call)//2`
  - result `= min(max(target, min_raise_to), pot_raise_to, my_bet + my_stack)`
  - `min_raise_to = opp_bet + max(last_increment, BIG_BLIND)`

  — [game.py:418-431](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/game.py)
- The button posts SB and acts first preflop. The non-button acts first postflop. Stacks reset to 80 every hand. If someone is all-in and bets match, the board runs out — [game.py:369-391, 567-587](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/game.py)
- Concrete wire examples from the smoke test (generated by game.py):
  - Preflop button: `{'street':'PREFLOP','hole_cards':[1,12,17,24,28],'board':[],'pot':3,'to_call':1,'my_bet':1,'opp_bet':2,'my_stack':79,'opp_stack':78,'is_button':True,'legal_actions':['FOLD','CHECK_CALL','RAISE_HALF','RAISE_POT'],'raise_to':{'RAISE_HALF':4,'RAISE_POT':6},'min_raise_to':4,'raises_this_street':0,'action_history':[],'big_blind':2}`
  - Facing an all-in: `legal_actions ['FOLD','CHECK_CALL']`, `raise_to {}`.

  — [tools/smoke_test.py:40-61](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/tools/smoke_test.py)
- `HandResult` (to `on_hand_end`) has `hand_index`, `my_net`, `pot`, `went_to_showdown`, `board` (revealed only), `opp_hole` (only at showdown, else None), and `winner` ('me', 'opp' or 'split') — [game.py:272-313](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/game.py)
- `AgentConfig` (to `new_half`) has `starting_stack, big_blind, small_blind, num_hands, time_bank_seconds, raise_cap`. The judge sends only `{"config": ...}`, "not which half this is and not its seat" — [game.py:78-100](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/game.py), [judge_engine.py:435-443](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/judge_engine.py)
- Return value: the plumbing sends `action.name` for an Action. str, int, float, bool or None pass through raw, and other objects are sent as `repr`. The judge's `coerce_action` accepts the name string or an int 0-3 and rejects bool — [agent.py:213-220](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/agent.py), [judge_engine.py:179-194](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/judge_engine.py)
- HTTP protocol, reply format and status codes:

  | Route | Reply / behavior |
  |---|---|
  | `GET /` | `{participant, agent_name}`; also the health check |
  | `POST /new-half` | `{ok: true}` |
  | `POST /act` with `{observation, hand_results}` | `{action, hand_end_errors}` |
  | `POST /hand-end` with `{results}` | `{ok, hand_end_errors}` |
  | wrong or missing `X-Agent-Token` (when `AGENT_TOKEN` is set) | 401 |
  | any call before `/new-half` | 409 |
  | non-object body | 400 |
  | exception in your code | 500 with `error` and `traceback` |

  — [agent.py:112-229](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/agent.py)

### Inferences
- `action_history` gives the full betting sequence (with `is_me`). Opponent modelling within a hand and across hands (via `memory`) is possible.
- `opp_hole` at showdown is the only view of the opponent's cards, and it is lost between halves.
- Because amounts are fixed by the engine, the action space is tiny (at most 4). Game-tree or CFR-style abstractions only need to model those four choices and the cap of 4 raises per street.

### Gaps
- None material for the interface.

---

## 4. Logs and hand histories: what is produced and how to use them

### Takeaway
`--json PATH` writes a machine-readable result. Adding `--logs` includes every hand with both players' hole cards, the full board, and the seat-based action sequence with amounts and nets. These are full-information records, usable for offline equity analysis, opponent-profile studies, or supervised or RL training data. The judge's stdout report adds per-bot timing, call and error counts and the first traceback.

### Cited Findings
- Match JSON keys (run log): `kind, match_seed, num_deals, agent1_name, agent2_name, verdict, points, reason, mean_bb_per_deal, std_bb, stderr_bb, ci, chop_z, half_totals_chips, agent_stats, paired_bb, elapsed_seconds, logs`. `logs` is `{"half1": [...], "half2": [...]}` — [judge_engine.py:596-624](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/judge_engine.py)
- Half JSON keys (`kind: "half_result"`): `half, match_seed, num_deals, agent1_seat, names, total_chips, agent_stats, nets_agent1, nets_agent2, elapsed_seconds, logs` — [judge_engine.py:513-536](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/judge_engine.py)
- Per-hand log record (`_hand_log`): `half, deal_index, button_seat, hole_cards` (both seats, as strings), `board` (all 5 even if not revealed), `board_revealed, actions` (`seat, street, action, amount, street_total`), `pot, went_to_showdown, nets` — [judge_engine.py:632-646](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/judge_engine.py)
- Real example (run log, half 1 deal 3): hole cards `[["6h","7c","8c","8s","Jh"],["6d","7d","Jd","Qc","Ah"]]`, board `["9s","Jc","9h","Kd","Td"]`, `board_revealed: []`, actions `[seat1 PREFLOP RAISE_POT amount 5 street_total 6, seat0 PREFLOP FOLD 0 2]`, `pot 8`, `nets [-2, 2]`.
- `agent_stats` per half (run log): `{"calls":223,"skipped_calls":0,"timed_out":false,"errors":0,"forfeited":false,"error_messages":[],"time_seconds":0.000203,"wall_seconds":0.058649}`. The first 10 error messages are kept, with tracebacks — [judge_engine.py:92, 130-162](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/judge_engine.py)
- `paired_bb[d]` is agent1's half1+half2 result on deal d in bb. The CI is `mean ± 1.96·stdev/√n`. A win needs the whole CI above 0 — [judge_engine.py:705-740](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/judge_engine.py)
- Deals are deterministic: `random.Random(f"{match_seed}:{deal_index}")` samples 15 cards (seat0 5, seat1 5, board 5). The button is `deal_index % 2` — [game.py:103-156](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/game.py)
- The bot-side server log is only uvicorn's startup lines (access log off). Captured `agent.log`: "Started server process ... Uvicorn running on http://0.0.0.0:5108" — run log

### Inferences
- Logs contain hidden information, both hole cards and the unrevealed board. That makes them ideal for computing realized all-in equity, EV-adjusted results and per-spot statistics without re-simulation. A bot never sees them at runtime.
- Because the deal is reproducible from the seed, logs can be replayed through `game.Game` to reconstruct every `Observation`. That supports (observation, action, outcome) datasets for imitation or value learning against baseline styles.
- `paired_bb` per deal lets you study variance and estimate how many deals are needed to separate two bot versions.

### Gaps
- No built-in hand-history viewer or analysis script exists; analysis tooling would have to be written.

---

## 5. Packaging and submission artifacts

### Takeaway
There is no zip, manifest or upload script. You submit a public GitHub repo URL plus a 40-character commit SHA via a form. The organizers build that exact commit with `docker/Dockerfile.agent` on top of `Dockerfile.base`, then run `tools/smoke_test.py` inside the container. `./tools/check_build.sh` reproduces this locally and requires Docker.

### Cited Findings
- Submission steps: push to a public GitHub repo, get the SHA from `git rev-parse HEAD`, and submit team name, repo URL and SHA in the form. "The tournament builds exactly that commit"; later pushes are ignored unless the form is edited — [README.md §6](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/README.md)
- `agent.py` and `requirements.txt` must be in the repo root, and `agent.py` must keep that name — [README.md Files](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/README.md)
- Dockerfile.agent steps:
  1. `FROM poker-agent-base:local` (the organizers pass a digest-pinned registry image).
  2. Copy `requirements.txt`, then `pip install -c /opt/poker/constraints.txt --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt`.
  3. `COPY . /app`.
  4. Lock files to root, read-only.
  5. Fail if `/app/agent.py` is missing.
  6. Run as uid 10001 with `CMD python agent.py`.

  — [docker/Dockerfile.agent](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/docker/Dockerfile.agent)
- The base image installs FastAPI and uvicorn first and freezes them (with starlette, pydantic and other dependencies) into `constraints.txt`. Requesting other versions fails the build. numpy and CPU torch (`TORCH_SPEC=torch`, unpinned) are preinstalled but not locked — [docker/Dockerfile.base:27-35, 68-83](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/docker/Dockerfile.base)
- `check_build.sh` steps:
  1. Build the base.
  2. Build the bot.
  3. Size check: the bot may add at most 3 GiB (`MAX_ADDED_BYTES=3221225472`) on top of the base.
  4. Run the container under match restrictions.
  5. `docker exec ... python /smoke/smoke_test.py --port 5008 --startup 15`.

  It ends with `ALL CHECKS PASSED`. Options: `PLATFORM=linux/amd64`, `SMOKE_CPUS`, `SMOKE_MEMORY` — [tools/check_build.sh](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/tools/check_build.sh)
- `smoke_test.py` (standard library only; it does not import game.py) checks:
  1. `GET /` within 15 s.
  2. `/new-half` returns 200.
  3. Five sample `/act` situations each return a legal action in at most 1.0 s, with no `hand_end_errors`.
  4. `/hand-end` works.

  — [tools/smoke_test.py](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/tools/smoke_test.py)
- Model files are committed normally, each under 100 MB. Git LFS files are not downloaded. There is no GPU, so `[cuda]` extras are pointless. TensorFlow (about 2 GB) is allowed but eats most of the 3 GB — [README.md §8](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/README.md)
- `.dockerignore` is described in the README's file table, but no `.dockerignore` (or `.gitignore`) exists in the repo (`git ls-files` and `ls -a`, run log). A compiled `tools/__pycache__/smoke_test.cpython-312-pytest-9.2.0.pyc` is tracked in git — [README.md Files](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/README.md), run log

### Inferences
- Without a `.dockerignore`, `COPY . /app` copies everything, including `.git`, `research_notes/`, `reports/`, any logs or datasets and `__pycache__`, into the image. That counts toward the 3 GB. Add a `.dockerignore` (e.g., `.git`, `research_notes/`, `reports/`, `*.json` logs, training data, `__pycache__`) but never exclude `agent.py` or the modules it imports.
- Since the official build uses the committed tree only, untracked helper modules your agent imports will be missing. Commit everything that `agent.py` imports.
- `torch` in the base is unpinned ("newest CPU release at build time"). A saved model should be loaded in a version-tolerant way (e.g., a plain state_dict or numpy weights), or `torch` should be listed without a version to reuse the base copy.

### Gaps
- The submission form URL and deadlines are not in the repo.
- The real organizer `build_agent.sh` is referenced but not included.
- I could not run `check_build.sh` (no Docker here).

---

## 6. Extension points, recommended locations, and gotchas

### Takeaway
The only extension points the tournament honours are the three functions in `agent.py`'s `YOUR CODE HERE` block:
- `new_half(config, memory)`
- `choose_action(obs, memory) -> Action`
- `on_hand_end(result, memory)`

Plus module-level startup code next to `warmup()`, extra committed modules or data files in the repo, and `requirements.txt`. Edits to `game.py`/`evaluator.py` don't change the referee but can be imported as helpers. `game.Game` with `clone()` and `make_deal` is a ready local simulator for self-play and testing.

### Cited Findings
- The three hooks and their timing: `new_half` at the start of each 1000-hand half (memory is a fresh dict), `choose_action` on each turn, and `on_hand_end` once per finished hand, always before `choose_action` sees the next hand. Results arrive batched with the next `/act`, and the last ones arrive via `/hand-end` — [agent.py:46-109](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/agent.py), [README.md §3, §8](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/README.md)
- Startup hook: "Do any other slow setup (loading a model, ...) here too: the server must answer within 15 seconds of starting" — next to `warmup()` at [agent.py:35-39](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/agent.py)
- Identity: set `PARTICIPANT` and `AGENT_NAME` at [agent.py:41-43](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/agent.py). `test_names_are_set` requires non-empty strings — [test_agent.py:95-99](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/test_agent.py)
- Do not touch: the SERVER PLUMBING section (routes and reply format), the `PORT` env read, and `0.0.0.0` binding. `test_reads_port_from_environment` greps the source for `os.environ.get("PORT"` and `0.0.0.0` — [agent.py:112-236](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/agent.py), [test_agent.py:189-192](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/test_agent.py)
- `game.py` and `evaluator.py`: "editing this has no effect on the evaluation platform's match referee's game", but their helpers are usable — [README.md Files](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/README.md)
- Simulator API:
  - `Game(make_deal(seed, i), button_seat, hand_index)`
  - `.to_act`, `.observation(seat)`, `.legal_actions()`, `.raise_to(action)`, `.apply(action)`
  - `.is_terminal`, `.result()`, `.hand_result(seat)`
  - `.clone()`, described as "A cheap independent copy, e.g. for simulation-based agents"

  — [game.py:357-559](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/game.py)
- An in-process harness already exists. `test_agent.play_hands()` drives the bot via FastAPI `TestClient` against a random opponent with no real server, using the judge's `coerce_action`. The test file says "Add your own tests at the bottom" — [test_agent.py:53-88, 195-197](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/test_agent.py)
- Run log: `python -m pytest -q` passed 12 tests in 1.01 s. There was one deprecation warning from starlette's TestClient about httpx.
- Tests check:
  - legality over 200 hands vs random
  - both seats and halves
  - an aggressive opponent (raise_rate=1.0)
  - that `MEMORY` keys after `/new-half` equal the keys a fresh `new_half` produces
  - token, malformed-body, before-new-half and crash-reporting behavior

  — [test_agent.py:95-192](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/test_agent.py)
- State: in the tournament each half runs in a brand-new server process. Locally one process can play both halves, and only `memory` is wiped, "other global variables are not" — [README.md §3](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/README.md), [agent.py:124-128](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/agent.py)
- Concurrency: the routes are `async def` on one thread and call your functions directly, so "your functions never run twice at once". Keep your functions as normal `def` — [agent.py:120-122](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/agent.py)
- Randomness: the baseline seeds `memory["rng"] = random.Random(0)` in `new_half` "so results are repeatable" — [baseline_random.py](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/baseline-bots/baseline_random.py)
- Imports: the bot runs from `/app` with `CMD python agent.py`, so sibling modules in the repo root are importable. Baselines in a subfolder need `sys.path.insert` — [docker/Dockerfile.agent:46, 63](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/docker/Dockerfile.agent), [baseline_random.py](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/baseline-bots/baseline_random.py)
- Filesystem: the app dir is read-only and root-owned. Only `/tmp` (512 MB) is writable and it is wiped per half. `PYTHONDONTWRITEBYTECODE=1` is set — [Dockerfile.agent:54-56](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/docker/Dockerfile.agent), [Dockerfile.base:38-48](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/docker/Dockerfile.base)

### Inferences
Recommended layout:
- Keep `agent.py` thin. The three hooks call into a committed package in the repo root, e.g. `bot/` with `strategy.py`, `equity.py` and `opponent_model.py`.
- Put precomputed tables or model weights (each under 100 MB, not LFS) in e.g. `bot/data/`, loaded at module import beside `warmup()`.
- Put custom tests at the bottom of `test_agent.py`, or in a `tests/` folder; `test_agent.py` already handles that location via its BUNDLE logic.
- Put offline training and analysis scripts in a separate folder (e.g. `training/`) and list it in `.dockerignore`.

Gotchas to design around:
1. Put every per-half mutable state in `memory`, set up in `new_half`. Globals leak across halves locally, and the memory test expects the keys after `new_half` to be deterministic.
2. Read-only, precomputed globals (lookup tables, models) are fine and should be built at import time, within the 15 s startup.
3. Seed any RNG inside `new_half` (e.g., `memory["rng"] = random.Random(seed)`) for reproducibility. Note that a fixed seed makes your mixed strategy predictable across matches. Consider seeding from `os.urandom` in production while keeping a debug seed locally.
4. Wrap `choose_action` logic in try/except, with a fallback to a safe legal action (e.g. `CHECK_CALL` if legal). Do the same for `on_hand_end`: every exception there is a separate error, and five forfeit the whole match.
5. Always validate that the returned action is in `obs.legal_actions`. FOLD is illegal when `to_call == 0`, and raises disappear once the cap of 4 is hit or when facing an all-in.
6. Enforce your own time budget well under 1 s per call. A timeout is an error, and the slow computation keeps running and blocks later requests.
7. Don't rely on knowing the half or seat; only `obs.is_button` per hand is given. `hand_index` resets each half.
8. Use `Game.clone()` and `make_deal` for local self-play and evaluation without HTTP. For final validation, use the real judge with `--half` + restart + `combine`, and `./tools/check_build.sh` on the exact commit.

### Gaps
- No official guidance exists on whether bots may raise thread counts (the base image comment says "a bot may raise these itself", while the README says about 1 CPU).
- Whether the tournament's PROVISIONAL constants (stack, time bank) will change before the event is unknown. Read them from `config` in `new_half` rather than hardcoding.
