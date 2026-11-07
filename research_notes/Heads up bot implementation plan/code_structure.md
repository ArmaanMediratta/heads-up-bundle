# Code Structure and Architecture of heads-up-bundle

All sources are files in the repository at the repo root (`heads-up-bundle/`) (git HEAD `c83ab6e "good luck"`, a single commit, 17 tracked files). Links are repo-relative paths with line numbers. Everything below was read directly from source.

## 1. Directory tree, languages, frameworks, dependencies

### Takeaway
A small, flat, pure-Python (3.12 target) bundle: about 3,650 lines across 4 core modules (`evaluator.py`, `game.py`, `judge_engine.py`, `agent.py`), 4 baseline bots, 1 pytest file, 2 Dockerfiles and 2 build/smoke tools. The only runtime dependencies are FastAPI 0.156.1 and uvicorn 0.54.0 (bot side). The engine and judge use only the standard library. There is no pyproject, Makefile, CI, or `.dockerignore`.

### Cited Findings
- Full tracked-file tree (excluding .git, research_notes/, reports/, caches), with line counts:
  ```
  heads-up-bundle/
  ├── README.md                          126  participant guide (rules, run, test, submit, scoring)
  ├── agent.py                           236  THE participant bot (FastAPI server + 3 strategy hooks)
  ├── game.py                            627  rules + single-hand state machine + data types + tunable constants
  ├── evaluator.py                       262  card encoding, string helpers, short-deck 5-card ranking, lookup table, omaha_score
  ├── judge_engine.py                   1044  HTTP referee: plays halves/matches, time bank, errors, duplicate scoring, CLI
  ├── test_agent.py                      197  pytest suite that drives agent.py via FastAPI TestClient
  ├── requirements.txt                     2  fastapi==0.156.1, uvicorn==0.54.0
  ├── requirements-dev.txt                 3  -r requirements.txt, pytest>=8, httpx==0.28.1
  ├── baseline-bots/
  │   ├── baseline_random.py             168  uniform random legal action (seeded Random(0) per half)
  │   ├── baseline_calling_station.py    164  always CHECK_CALL
  │   ├── baseline_always_half.py        166  RAISE_HALF if legal else CHECK_CALL
  │   └── baseline_always_pot.py         166  RAISE_POT if legal else CHECK_CALL
  ├── docker/
  │   ├── Dockerfile.base                102  python:3.12-slim + locked FastAPI/uvicorn + numpy + CPU torch, user 10001
  │   └── Dockerfile.agent                63  installs requirements.txt with constraints, copies repo to /app, CMD python agent.py
  └── tools/
      ├── check_build.sh                 120  builds base + bot images, checks size (<3 GiB added), runs smoke test in a locked container
      ├── smoke_test.py                  199  stdlib-only HTTP check of a running bot (hard-coded sample observations)
      └── __pycache__/smoke_test.cpython-312-pytest-9.2.0.pyc   (committed build artifact, cruft)
  ```
  — [git ls-files / wc -l](./)
- Empty untracked directories `reports/` and `research_notes/` also exist at root. — [ls -la](./)
- Runtime deps: `fastapi==0.156.1`, `uvicorn==0.54.0` — [requirements.txt:1-2](requirements.txt)
- Dev deps: `-r requirements.txt`, `pytest>=8`, `httpx==0.28.1` (httpx is needed by `fastapi.testclient`) — [requirements-dev.txt:1-3](requirements-dev.txt)
- Base image: `python:3.12-slim`, FastAPI/uvicorn installed first and frozen to `/opt/poker/constraints.txt`; numpy and CPU-only torch preinstalled (not locked); env `OMP_NUM_THREADS=1` etc., `HOME=/tmp`, `PORT=5008`; non-root user uid/gid 10001; setuid bits stripped — [docker/Dockerfile.base:24-102](docker/Dockerfile.base)
- Agent image: `pip install -c /opt/poker/constraints.txt --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt`, then `COPY . /app`, chown root and make read-only, fail if `/app/agent.py` missing, run as 10001, `CMD ["python", "agent.py"]` — [docker/Dockerfile.agent:14-63](docker/Dockerfile.agent)
- The judge is explicitly "Standard library only (the judge does not need FastAPI)" — [judge_engine.py:49](judge_engine.py)
- `smoke_test.py` "uses only the Python standard library" and "does NOT import game.py" (sample observations are hard-coded) — [tools/smoke_test.py:16-18](tools/smoke_test.py)
- `.dockerignore` is described in the README file table but does not exist in the repo — [README.md:16](README.md); confirmed absent by `ls`.
- No `.github/`, `Makefile`, `pyproject.toml`, or `setup.cfg` exist — `ls` check at repo root.

### Inferences
- Python >= 3.10 is required locally because of `X | None` syntax in annotations (e.g. `async def _read_request(...) -> tuple[dict, JSONResponse | None]` at [agent.py:136](agent.py)); 3.12 is the tournament runtime.
- Because `Dockerfile.agent` does `COPY . /app` with no `.dockerignore`, everything in the repo (including `research_notes/`, `reports/`, tests, baseline bots) ends up in the image. That is harmless for small files but counts toward the 3 GB cap if large files (models, datasets) are added. Adding a `.dockerignore` is worth considering.

### Gaps
- None for structure. Exact torch version in the real base image is not pinned in-repo (`TORCH_SPEC=torch`, "newest CPU release at build time") — [docker/Dockerfile.base:33-35](docker/Dockerfile.base).

## 2. Core abstractions (cards, state, actions, observations)

### Takeaway
Cards are ints 0-35 (`rank = c >> 2`, `suit = c & 3`). `game.py` defines the enums `Street` and `Action`, immutable dataclasses `Deal`, `Observation`, `ObservedAction`, `HandResult`, `ActionRecord`, `GameResult`, `AgentConfig`, and the mutable single-hand state machine `Game`. `evaluator.py` provides a precomputed `{36-bit mask: score}` table and `omaha_score(hole, board) -> int`. The judge adds `AgentStats`, `HttpAgentHandle`, `HalfResult` and `MatchResult`.

### Cited Findings
**evaluator.py (no repo imports, stdlib only)**
- Constants: `NUM_RANKS=9`, `NUM_SUITS=4`, `NUM_CARDS=36`, `RANK_CHARS="6789TJQKA"`, `SUIT_CHARS="cdhs"`, `ACE=8`, `NINE=3` — [evaluator.py:30-38](evaluator.py)
- Encoding: `rank = card >> 2` (0=six..8=ace), `suit = card & 3` (0=c,1=d,2=h,3=s); card 0="6c", 35="As" — [evaluator.py:6-9](evaluator.py)
- Helpers: `card_rank(card)->int` [L41](evaluator.py), `card_suit(card)->int` [L46](evaluator.py), `card_to_str(card)->str` [L51](evaluator.py), `str_to_card(text)->int` [L58](evaluator.py), `cards_to_str(cards)->str` [L72](evaluator.py), `cards_from_str(text)->list[int]` (accepts "Ah Kd 6c" or "AhKd6c") [L77-86](evaluator.py)
- Category constants, short-deck order: `HIGH_CARD=0, ONE_PAIR=1, TWO_PAIR=2, STRAIGHT=3, THREE_OF_A_KIND=4, FULL_HOUSE=5, FLUSH=6, FOUR_OF_A_KIND=7, STRAIGHT_FLUSH=8` (trips beat straight, flush beats full house) — [evaluator.py:92-104](evaluator.py)
- Score layout: category at bits >= 20, then up to five 4-bit kicker slots (slot 0 at bits 16-19). `category_of(score)` = `score >> 20`; `category_name(score)` — [evaluator.py:118-141](evaluator.py)
- Straights: wheel A-6-7-8-9 counts as a nine-high straight (lowest straight) — [evaluator.py:144-155](evaluator.py)
- `_score_ranks(ranks_desc, is_flush)` is the reference classifier; `score_five(cards)` validates 5 distinct cards and scores — [evaluator.py:158-197](evaluator.py)
- Lookup table: `_build_table()` enumerates all C(36,5)=376,992 five-card hands into `dict[mask]->score`; `get_table()` builds lazily into global `_TABLE`; `warmup()` forces the build ("takes a few seconds the first time") — [evaluator.py:204-238](evaluator.py)
- `omaha_score(hole, board) -> int`: requires exactly 5 hole and 5 board cards; max over 10 hole-pairs x 10 board-triples = 100 dict lookups — [evaluator.py:241-262](evaluator.py)

**game.py (imports `NUM_CARDS, card_to_str, omaha_score` from evaluator)** — [game.py:23](game.py)
- Tunable constants block (marked "PROVISIONAL and may be tuned before the tournament"): `BIG_BLIND=2`, `SMALL_BLIND=1`, `STARTING_STACK=80` (reset every hand), `RAISE_CAP_PER_STREET=4`, `NUM_DEALS=1000`, `TIME_BANK_SECONDS=8.0`, `NETWORK_GRACE_SECONDS=0.001`, `ACTION_TIMEOUT_SECONDS=1.0`, `STARTUP_TIMEOUT_SECONDS=15.0`, `ERROR_LIMIT=5`, `CHOP_Z=1.96`, `AGENT1_DEFAULT_PORT=5008`, `AGENT2_DEFAULT_PORT=5009` — [game.py:25-43](game.py)
- `NUM_HOLE_CARDS=5`, `NUM_BOARD_CARDS=5` — [game.py:45-46](game.py)
- `class Street(IntEnum)`: PREFLOP=0, FLOP=1, TURN=2, RIVER=3; `BOARD_CARDS_VISIBLE = {PREFLOP:0, FLOP:3, TURN:4, RIVER:5}` — [game.py:49-59](game.py)
- `class Action(IntEnum)`: FOLD=0, CHECK_CALL=1, RAISE_HALF=2, RAISE_POT=3; `RAISE_ACTIONS=(RAISE_HALF, RAISE_POT)` — [game.py:62-71](game.py)
- `class IllegalActionError(Exception)` — [game.py:74-75](game.py)
- `@dataclass(frozen=True) AgentConfig(starting_stack, big_blind, small_blind, num_hands, time_bank_seconds, raise_cap)` with `to_dict()` / `from_dict()` (ignores unknown keys) — [game.py:78-100](game.py)
- `button_for_deal(deal_index) -> int` = `deal_index % 2` — [game.py:103-105](game.py)
- `default_action(to_call) -> Action`: CHECK_CALL if to_call == 0 else FOLD (used on error/forfeit/timeout) — [game.py:108-111](game.py)
- `@dataclass(frozen=True) Deal(hole_cards: tuple[tuple[int,...], tuple[int,...]], board: tuple[int,...])` with `.flop`, `.turn`, `.river` properties — [game.py:118-142](game.py)
- `make_deal(match_seed, deal_index) -> Deal`: `random.Random(f"{match_seed}:{deal_index}").sample(range(36), 15)`; seat 0 gets cards[0:5] (sorted), seat 1 cards[5:10] (sorted), board cards[10:15] (unsorted, in deal order) — [game.py:145-156](game.py)
- `@dataclass(frozen=True) ObservedAction(street, is_me, action, amount, street_total)` + to/from_dict (enums serialized by name). Blinds are not listed as actions. — [game.py:163-196](game.py)
- `@dataclass(frozen=True) Observation` fields: `hand_index, street, hole_cards, board, pot, to_call, my_bet, opp_bet, my_stack, opp_stack, is_button, legal_actions: tuple[Action,...], raise_to: dict[Action,int], min_raise_to, raises_this_street, action_history: tuple[ObservedAction,...], big_blind`; `to_dict()` / `from_dict()` — [game.py:199-269](game.py)
- `@dataclass(frozen=True) HandResult(hand_index, my_net, pot, went_to_showdown, board, opp_hole: Optional[tuple], winner: 'me'|'opp'|'split')` — [game.py:272-313](game.py)
- `@dataclass(frozen=True) ActionRecord(seat, street, action, amount, street_total)` (engine-side, seat-based) — [game.py:316-334](game.py)
- `@dataclass(frozen=True) GameResult(nets: tuple[int,int], pot, went_to_showdown, winner_seat: Optional[int], board_revealed, history)`; nets sum to 0 — [game.py:337-350](game.py)
- `class Game` — one hand. Public API: `__init__(deal, button_seat, hand_index=0)`, properties/attrs `pot`, `to_act`, `is_terminal`, `street`, `stacks`, `bets`, `contributed`, `history`; methods `legal_actions()`, `raise_to(action)`, `apply(action)`, `observation(seat)`, `result()`, `hand_result(seat)`, `clone()` — [game.py:357-559](game.py)
- `Game.clone()` is documented as "A cheap independent copy, e.g. for simulation-based agents" (shallow-copies mutable lists, shares immutable Deal/history records) — [game.py:546-559](game.py)

**judge_engine.py**
- `AgentStats` (time_seconds, wall_seconds, calls, skipped_calls, timed_out, errors, forfeited, error_messages) — [judge_engine.py:130-176](judge_engine.py)
- `coerce_action(raw) -> Optional[Action]`: accepts action name string or int; rejects bools — [judge_engine.py:179-194](judge_engine.py)
- `_DeadlineReader`, `_DeadlineSocket`, `_DeadlineHTTPConnection`: give each HTTP request one total deadline and a 1,000,000-byte reply cap — [judge_engine.py:205-252](judge_engine.py)
- `HttpAgentHandle(base_url, config, token)` with `wait_healthy`, `start_half`, `act`, `hand_end`, `flush_hand_results` — [judge_engine.py:259-480](judge_engine.py)
- `HalfResult` (per-agent nets per deal, stats, optional logs; `to_dict`/`from_dict`, `kind="half_result"`) — [judge_engine.py:487-568](judge_engine.py)
- `MatchResult` (paired_bb, mean/std/stderr, ci, verdict, points, reason, …) — [judge_engine.py:571-629](judge_engine.py)

### Inferences
- The `Observation` gives the bot no direct access to the `Deal` or a `Game` object. A bot that wants to simulate must rebuild a `Game` itself (e.g. construct a `Deal` with sampled opponent cards and replay `action_history`), or write its own lightweight simulator. `Game.clone()` exists for this purpose but needs a `Game` instance.
- `omaha_score` only accepts a full 5-card board, so equity on the flop or turn needs board completion (enumerating or sampling run-outs), as hinted at [agent.py:85-86](agent.py).
- Scores are comparable ints, so `category_of(score)` gives a quick made-hand class for heuristics.

### Gaps
- No docstring states whether the `TUNABLE CONSTANTS` actually changed for the final tournament. The bot should read `AgentConfig` from `/new-half` rather than hard-coding them.

## 3. Hand flow from start to showdown; where rules live

### Takeaway
All rules are in `game.Game`. The flow is: `make_deal`, then `Game.__init__` (stacks reset to 80, button posts SB=1, other posts BB=2, button acts first preflop), then a loop of `observation`/`apply`, with `_advance` closing streets (the non-button acts first postflop). Showdown happens on the river, or immediately when someone is all-in with matched bets. `_showdown` compares `omaha_score`s and `_finish` pays out. Pot-limit sizing is in `_raise_to`. The judge's `play_half` drives this loop over 1000 deals.

### Cited Findings
- Driver loop (judge): for each deal `d`: `button = button_for_deal(d)`; `game = Game(make_deal(match_seed, d), button, hand_index=d)`; `while not game.is_terminal: seat = game.to_act; game.apply(bots[seat].act(game.observation(seat)))`; record `res.nets`; queue `game.hand_result(seat)` for both bots; finally `flush_hand_results()` — [judge_engine.py:653-702](judge_engine.py)
- Init: `stacks=[80,80]`, `contributed`, `bets`, `acted=[False,False]`, `raises_this_street=0`, `last_increment=BIG_BLIND`; button posts SB, other seat posts BB; `to_act = button_seat` — [game.py:369-391](game.py)
- `pot` = `contributed[0] + contributed[1]` (whole hand, including current-street bets) — [game.py:395-398](game.py)
- `_to_call(seat) = max(0, bets[opp] - bets[seat])` — [game.py:406-408](game.py)
- Raise legality `_can_raise`: `raises_this_street < 4` AND own stack > to_call AND opponent stack > 0 — [game.py:410-416](game.py)
- Min raise: `_min_raise_to = bets[opp] + max(last_increment, BIG_BLIND)` — [game.py:418-420](game.py)
- Pot-limit sizing `_raise_to`: `pot_raise_to = opp_bet + pot + to_call`; `half_raise_to = opp_bet + (pot + to_call)//2`; result = `min(max(target, min_raise_to), pot_raise_to, my_bet + my_stack)` (clamped up to min-raise, down to pot max and all-in) — [game.py:422-431](game.py)
- Legal actions: FOLD only if to_call > 0; CHECK_CALL always; both raises if `_can_raise` — [game.py:433-441](game.py)
- `apply`: validates (raises `IllegalActionError`); FOLD ends the hand (opponent wins, no showdown); CHECK_CALL puts in `min(to_call, stack)`; a raise sets `last_increment = new_total - bets[opp]`, increments `raises_this_street`, and resets `acted[opp]=False`; then `_record` and `_advance` — [game.py:455-491](game.py)
- `_advance`: street over when both acted and bets equal. On RIVER: showdown. If any stack is 0: jump to RIVER and showdown (board run-out, no more betting). Otherwise next street, reset bets/acted/raises/last_increment, `to_act = 1 - button_seat` — [game.py:567-587](game.py)
- `_showdown`: `omaha_score` for each seat over the full 5-card board; higher wins, equal is a split — [game.py:589-599](game.py)
- `_finish`: split gives `pot//2` each ("pot is always even at showdown"); nets = received - contributed; `board_revealed` = full board on showdown else the visible cards; sets `is_terminal`, `to_act=None` — [game.py:601-621](game.py)
- `observation(seat)`: `legal_actions`/`raise_to` populated only on that seat's turn; `board` sliced to visible cards; history mapped to `is_me` — [game.py:493-521](game.py)
- `hand_result(seat)`: `opp_hole` revealed only if went_to_showdown — [game.py:529-544](game.py)
- Worked example from the smoke test (button preflop): pot 3, to_call 1, `raise_to {RAISE_HALF: 4, RAISE_POT: 6}`, `min_raise_to 4` — [tools/smoke_test.py:43](tools/smoke_test.py)

### Inferences
- The BB gets its preflop option: after the SB limps, bets are equal but `acted[BB]` is still False, so the round continues — derived from [game.py:381](game.py) and [game.py:569](game.py).
- Since stacks reset to 80 every hand and both start equal, there are no side pots or uneven all-ins. Every hand is independent with an effective stack of 40 BB.
- RAISE_HALF and RAISE_POT can resolve to the same amount when clamped (e.g. both at all-in or both at min-raise). Both remain "legal" in that case.
- With a 4-raise cap per street and pot-limit sizing on 80-chip stacks, preflop pot-raise sequences reach all-in quickly (6 → 18 → 54 → 80), so the cap rarely binds before all-in.
- `hand_index` equals the deal index and is identical in both halves of a duplicate match. Seat assignment is not sent to the bot. Only `is_button` is.

### Gaps
- None; rules are fully contained in `game.py`. Note the README says editing `game.py` "has no effect on the evaluation platform's match referee's game" — [README.md:9](README.md).

## 4. The bot/player interface and example bots

### Takeaway
Participants implement three plain (non-async) Python functions in `agent.py`: `new_half(config, memory)`, `choose_action(obs, memory) -> Action`, and `on_hand_end(result, memory)`. These are wrapped by fixed FastAPI routes `GET /`, `POST /new-half`, `POST /act` and `POST /hand-end`. Four baseline bots in `baseline-bots/` use the same template with trivial strategies. The starter `agent.py` strategy is "check if free, else fold".

### Cited Findings
- Signatures: `def new_half(config: AgentConfig, memory: dict) -> None` [agent.py:48](agent.py); `def choose_action(obs: Observation, memory: dict) -> Action` [agent.py:61](agent.py); `def on_hand_end(result: HandResult, memory: dict) -> None` [agent.py:96](agent.py)
- The `choose_action` docstring enumerates every Observation field (hand_index, street, hole_cards sorted 0-35, board 0/3/4/5 cards, pot, to_call, my_bet/opp_bet, my_stack/opp_stack, is_button, legal_actions, raise_to, min_raise_to, raises_this_street (max 4), action_history, big_blind) — [agent.py:64-86](agent.py)
- Starter strategy: `if obs.to_call == 0: return Action.CHECK_CALL; return Action.FOLD` — [agent.py:89-93](agent.py)
- Starter memory use: `memory["hands_played"]` init to 0 and incremented in `on_hand_end` — [agent.py:58](agent.py), [agent.py:107](agent.py)
- Startup: `warmup()` called at import so the 376,992-entry table is built before the first decision; "Do any other slow setup (loading a model, ...) here too" — [agent.py:35-39](agent.py)
- Imports available to the bot: `card_rank, card_suit, cards_to_str, omaha_score, warmup` from evaluator; `Action, AgentConfig, HandResult, Observation, Street` from game — [agent.py:32-33](agent.py)
- Server plumbing: `app = FastAPI()`, global `MEMORY`, `STATUS`, `TOKEN = os.environ.get("AGENT_TOKEN")` — [agent.py:130-133](agent.py)
- `_read_request`: checks `x-agent-token` before reading the body (401), refuses non-`/new-half` calls before a half starts (409), and requires a JSON object body (400) — [agent.py:136-153](agent.py)
- `GET /` returns `{"participant", "agent_name"}` (health check) — [agent.py:179-182](agent.py)
- `POST /new-half` body `{"config": {...}}`: clears MEMORY, sets started, calls `new_half`; a crash returns a 500 with a traceback — [agent.py:185-197](agent.py)
- `POST /act` body `{"observation": {...}, "hand_results": [...]}`: runs `on_hand_end` for each queued result (errors collected), then `Observation.from_dict` and `choose_action`; reply `{"action": <name>, "hand_end_errors": [...]}` — [agent.py:200-220](agent.py)
- `POST /hand-end` body `{"results": [...]}` for leftover hands at half end — [agent.py:223-229](agent.py)
- Entry: `port = int(os.environ.get("PORT", "5008")); uvicorn.run(app, host="0.0.0.0", port=port, ...)` — [agent.py:232-236](agent.py)
- Judge side of the interface: `act()` sends the observation plus pending results, coerces the reply, and records an error for a missing field, a non-Action, or an illegal action; it falls back to `default_action` — [judge_engine.py:447-468](judge_engine.py)
- Time accounting: each request is charged `elapsed - 0.001s`; per-request timeout is `min(1.0, bank_left)`; running out of bank is not an error (sets `timed_out`; later calls are skipped with the default action); 5 errors means a forfeit — [judge_engine.py:336-401](judge_engine.py)
- The bot is not told the half number or its seat at `/new-half`, only the config — [judge_engine.py:435-445](judge_engine.py)
- Baseline bots (all `PARTICIPANT = "Challenges Team"`, default port 5009, `sys.path.insert` of the parent dir to import game.py, do NOT call `warmup()` or import evaluator):
  - RandomBot: `memory["rng"] = random.Random(0)` per half; `memory["rng"].choice(obs.legal_actions)` — [baseline-bots/baseline_random.py:29-39](baseline-bots/baseline_random.py)
  - CallingStation: always `Action.CHECK_CALL` — [baseline-bots/baseline_calling_station.py:33-35](baseline-bots/baseline_calling_station.py)
  - AlwaysHalf: RAISE_HALF if legal else CHECK_CALL — [baseline-bots/baseline_always_half.py:33-37](baseline-bots/baseline_always_half.py)
  - AlwaysPot: RAISE_POT if legal else CHECK_CALL — [baseline-bots/baseline_always_pot.py:33-37](baseline-bots/baseline_always_pot.py)
- The baseline plumbing below `END OF YOUR CODE` is the same as agent.py's, apart from comments and default port — verified by `diff agent.py baseline-bots/*.py`.

### Inferences
- `choose_action` may return an `Action`, or a name/int (the route passes str/int through and `coerce_action` accepts both). Returning `Action` members is the safe path.
- Routes are `async def` and call user code synchronously on one event-loop thread, so decisions never run concurrently. Heavy computation blocks the server, and a slow decision can cause queued requests to time out too ([judge_engine.py:273-275](judge_engine.py)).
- Opponent modelling can only use `action_history` within a hand, plus `HandResult` (including `opp_hole` at showdown) across hands, all stored in `memory`. Nothing persists across halves in the tournament.

### Gaps
- None for the interface itself.

## 5. Files to edit vs. leave untouched

### Takeaway
Edit only `agent.py` (the `PARTICIPANT`/`AGENT_NAME` constants and the block between `# ===== YOUR CODE HERE =====` and `# ===== END OF YOUR CODE =====`), `requirements.txt` (adding deps, keeping fastapi/uvicorn pins), your own tests at the bottom of `test_agent.py`, and optionally `.dockerignore` or extra helper modules and model files. `game.py`, `evaluator.py`, `judge_engine.py`, `docker/`, and `tools/` are reference or tooling. Edits to them don't affect the tournament referee or build.

### Cited Findings
- "Your bot is one file, `agent.py` … You edit one marked section, and the tournament runs the file as-is." File name must be `agent.py` at repo root — [README.md:3-8](README.md)
- Edit `PARTICIPANT`, `AGENT_NAME`, and the three functions between the markers — [README.md:36-45](README.md); markers at [agent.py:46](agent.py) and [agent.py:109](agent.py); TODO at [agent.py:17-22](agent.py)
- "SERVER PLUMBING (you normally don't need to edit below)"; changing routes or the reply format makes every call an error — [agent.py:112](agent.py), [README.md:116](README.md)
- Must keep the `PORT` env read and `0.0.0.0` (also enforced by `test_reads_port_from_environment`) — [README.md:114](README.md), [test_agent.py:189-192](test_agent.py)
- `game.py`: "editing this has no effect on the evaluation platform's match referee's game"; `evaluator.py` "same as above, but its helpers are useful" — [README.md:9-10](README.md)
- Tunable constants should only be changed in that block ("Every other module reads them from here") — [game.py:25-28](game.py)
- `docker/`: "don't edit them; edits have no effect on the real build" — [README.md:17](README.md)
- `requirements.txt`: add your deps; must stay at the repo root; FastAPI and uvicorn are fixed — [README.md:14](README.md), [README.md:123](README.md)
- `test_agent.py`: "Add your own at the bottom" — [README.md:13](README.md), [test_agent.py:195-197](test_agent.py)
- `smoke_test.py` deliberately avoids game.py "so a participant's edited game.py can't change what is being tested" — [tools/smoke_test.py:17-18](tools/smoke_test.py)

### Inferences
- `agent.py` imports `game.py` and `evaluator.py`, and `Dockerfile.agent` copies the whole repo, so these files do ship inside the bot image and the bot's own parsing (`Observation.from_dict`) and evaluator depend on them. Editing them changes your bot's behavior but not the referee. The safe approach is to leave them unmodified and put custom code in new modules (e.g. `strategy.py`, precomputed tables) imported from `agent.py`.
- Helper modules and data files placed in the repo are allowed (README says model files can be committed; each must be under 100 MB, no Git LFS) — [README.md:126](README.md).

### Gaps
- The README does not explicitly say whether additional `.py` modules besides `agent.py` are allowed. It is implied by "any files they added" in [docker/Dockerfile.agent:5](docker/Dockerfile.agent).

## 6. Tests, CI, scripts, Makefile targets

### Takeaway
There is one pytest file (`test_agent.py`, 11 tests that drive `agent.py` in-process via `TestClient`), a stdlib smoke test (`tools/smoke_test.py`), and a Docker build+smoke script (`tools/check_build.sh`). There is no CI config, no Makefile, and no test coverage of `game.py` or `evaluator.py` themselves. (Detailed run/submission tooling is covered by another researcher.)

### Cited Findings
- `test_agent.py` loads a fresh copy of agent.py via importlib, sets `module.TOKEN="test-token"`, and uses `fastapi.testclient.TestClient` — [test_agent.py:31-44](test_agent.py)
- `play_hands(client, num_hands, seed, raise_rate)`: runs real `Game`s locally. The bot is seat 0, the opponent is random (raises with probability `raise_rate`, else CHECK_CALL). Results are delivered batched like the judge does, and every action is asserted legal — [test_agent.py:53-88](test_agent.py)
- Tests: `test_names_are_set`, `test_new_half_works`, `test_every_decision_is_legal` (200 hands), `test_works_in_both_seats_and_both_halves`, `test_handles_aggressive_opponent` (raise_rate=1.0), `test_memory_is_fresh_each_half` (MEMORY keys after reset must equal what `new_half` sets), `test_token_is_checked`, `test_bad_token_is_refused_before_the_body_is_read`, `test_malformed_body_is_rejected`, `test_act_before_new_half_is_refused`, `test_crashes_are_reported_to_the_judge`, `test_reads_port_from_environment` — [test_agent.py:95-192](test_agent.py)
- Note: in `play_hands` the bot always sits in seat 0 (only the button alternates), and the `half`/`seat` keys in the test's `/new-half` body are ignored by the server — [test_agent.py:47-50](test_agent.py), [agent.py:194](agent.py)
- `smoke_test.py` checks `GET /` within 15 s, `/new-half`, five hard-coded `/act` situations (legal and <= 1 s each), and `/hand-end` — [tools/smoke_test.py:131-178](tools/smoke_test.py)
- `check_build.sh` builds base and bot images, enforces `MAX_ADDED_BYTES=3221225472`, and runs the container with `--network none --read-only --tmpfs /tmp:...size=512m --cap-drop ALL --pids-limit 256 --cpus 1 --memory 4g`, `AGENT_TOKEN=local-check` — [tools/check_build.sh:38-117](tools/check_build.sh)
- Judge CLI: `--agent1/--agent2` (port or URL; env AGENT1_URL/AGENT2_URL), `--half` (env HALF), `--seed` (env MATCH_SEED, default "1"), `--deals`, `--json`, `--logs`; `combine h1.json h2.json`; exit codes 0/2/3 — [judge_engine.py:913-1044](judge_engine.py)

### Inferences
- `test_memory_is_fresh_each_half` constrains design: anything put in `memory` outside `new_half` must be gone after a reset. Since MEMORY is cleared on `/new-half`, this holds as long as `new_half` is deterministic in its keys.
- The local judge (`play_half`) plus `make_deal` and `Game` can be imported directly for offline simulation or self-play without HTTP. `play_half` expects `HttpAgentHandle`-like objects with `start_half/act/hand_end/flush_hand_results/stats/describe`, so a duck-typed in-process handle would allow fast local evaluation.

### Gaps
- No CI or Makefile exists, so nothing more to report there.

## Appendix: Module dependency graph and architecture summary (from the sources above)

```
evaluator.py  (stdlib: collections, itertools)
    ^
    |  NUM_CARDS, card_to_str, omaha_score
game.py  (stdlib: random, dataclasses, enum)  -- rules, data types, constants
    ^            ^                ^
    |            |                |
agent.py     judge_engine.py   baseline-bots/*.py
(fastapi,    (stdlib http.client,(fastapi, uvicorn;
 uvicorn;     socket, statistics; imports game only,
 imports      imports game +      via sys.path hack)
 game +       evaluator)
 evaluator)      ^
    ^            | coerce_action
    |            |
test_agent.py (pytest, fastapi.testclient/httpx; imports game, judge_engine, loads agent.py)

tools/smoke_test.py  (stdlib only; independent, HTTP to a running bot)
tools/check_build.sh -> docker/Dockerfile.base -> docker/Dockerfile.agent -> runs smoke_test.py in container
```
— derived from import lines at [evaluator.py:20-24](evaluator.py), [game.py:16-23](game.py), [agent.py:25-33](agent.py), [judge_engine.py:52-90](judge_engine.py), [test_agent.py:11-25](test_agent.py), [baseline-bots/baseline_random.py:10-21](baseline-bots/baseline_random.py).

Runtime architecture: the judge process (`judge_engine.py`) owns the authoritative `Game` per hand and talks HTTP/JSON (keep-alive, optional `X-Agent-Token`) to two bot servers. Each bot server (`agent.py`) deserializes `Observation`/`HandResult` with game.py's `from_dict` and calls the participant's three functions. Match = 2 halves x 1000 deals on identical cards with seats swapped; each half runs in a fresh pod in the tournament. Score = mean paired bb/deal with a 95% CI; a forfeit in either half loses — [judge_engine.py:1-48](judge_engine.py), [judge_engine.py:717-791](judge_engine.py).
