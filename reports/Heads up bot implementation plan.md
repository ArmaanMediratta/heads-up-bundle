# Build a robust equity bot, then exploit

The way to win this tournament is a **robust, time-budgeted, equity-driven bot that adapts to each opponent**. Building a solver would be the wrong investment. The heads-up-bundle repository is a small, flat Python project, and the tournament runs only your `agent.py` plus whatever files it imports. The game is heads-up Short Deck (36-card) 5-card Pot-Limit Omaha. Stacks are **80 chips (40 bb), reset every hand**. Blinds are 1/2, there are **only four actions** (fold, check/call, half-pot raise, pot raise), and raises are capped at 4 per street. Each match is **2,000 duplicate hands**: 1,000 deals, then the same deals again with seats swapped. You score 1 point only if the 95% confidence interval of your paired bb/deal sits entirely above zero. Two constraints dominate the design. First, **five errors in one half forfeit the whole match**, so robustness comes first. Second, an **8-second thinking bank per 1,000-hand half on one CPU** works out to about 3-8 ms per decision. That rules out real-time CFR and allows a few hundred Monte Carlo rollouts per decision. The recommended plan has five parts. A precomputed preflop table covers the **19,998 suit-isomorphic Short Deck PLO5 starting-hand classes**. Postflop decisions use range-weighted Monte Carlo equity, with a vectorized evaluator under an adaptive time budget. Actions are chosen by EV, including commitment logic for the shallow 40 bb stacks. Opponent statistics feed exploitative adjustments. A fast in-process duplicate-match harness with confidence intervals gates every change. Most published PLO strategy is for 4-card, 52-card, 100 bb games and transfers only loosely. Short Deck ranks flushes above full houses and trips above straights, and the stacks here are shallow.

## A 3,650-line bundle where only agent.py is yours

The repository is a single commit (`c83ab6e`) of **17 tracked files**. About 3,650 lines of pure Python target 3.12, and the only runtime dependencies are `fastapi==0.156.1` and `uvicorn==0.54.0` ([requirements.txt](../requirements.txt)). The judge and the rules engine use only the standard library ([judge_engine.py:49](../judge_engine.py)). Each module has a single job:

| Path | Lines | Role | Edit? |
|---|---|---|---|
| `agent.py` | 236 | Your bot: a FastAPI server with three strategy hooks plus fixed "SERVER PLUMBING" | Only `PARTICIPANT`, `AGENT_NAME`, and the `YOUR CODE HERE` block |
| `game.py` | 627 | Rules, the single-hand `Game` state machine, dataclasses, tunable constants | No (the referee uses its own copy) |
| `evaluator.py` | 262 | Card encoding, Short Deck 5-card ranking, the 376,992-entry lookup table, `omaha_score` | No, but import its helpers |
| `judge_engine.py` | 1,044 | HTTP referee: halves, time bank, errors, duplicate scoring, CLI | No |
| `test_agent.py` | 197 | 11-12 pytest tests that drive `agent.py` through `TestClient` | Add tests at the bottom |
| `baseline-bots/` | 4 × ~166 | Random, CallingStation, AlwaysHalf, AlwaysPot | Copy freely |
| `docker/` | 165 | Base image (python:3.12-slim, FastAPI, numpy, CPU torch, uid 10001) and agent image | No effect on the real build |
| `tools/` | 319 | `check_build.sh` (Docker build plus locked-down smoke test) and `smoke_test.py` | Use, don't edit |

Sources: [code-structure notes, git ls-files](../README.md), [Dockerfile.base:24-102](../docker/Dockerfile.base).

The dependency graph is strictly layered. `evaluator.py` has no repo imports. `game.py` imports `NUM_CARDS, card_to_str, omaha_score` from it ([game.py:23](../game.py)). `agent.py`, the judge and the baselines all sit on top of `game.py`. Cards are integers 0-35, with `rank = c >> 2` (0 = six through 8 = ace) and `suit = c & 3` ([evaluator.py:6-9](../evaluator.py)). Hand categories follow Short Deck order: `STRAIGHT=3` sits below `THREE_OF_A_KIND=4`, and `FULL_HOUSE=5` sits below `FLUSH=6`. A score keeps its category in bits 20 and up, so `score >> 20` gives the made-hand class ([evaluator.py:92-141](../evaluator.py)). `omaha_score(hole, board)` requires exactly 5 hole cards and 5 board cards and takes the maximum over 10 hole pairs × 10 board triples, which is 100 dictionary lookups ([evaluator.py:241-262](../evaluator.py)). Flop and turn equity therefore always require completing the board.

All rules live in `game.Game`. The constructor resets stacks to 80, posts SB = 1 for the button and BB = 2 for the other player, and gives the button the first preflop action ([game.py:369-391](../game.py)). Pot-limit sizing is `pot_raise_to = opp_bet + pot + to_call` and `half_raise_to = opp_bet + (pot + to_call)//2`. Both are clamped up to `min_raise_to = opp_bet + max(last_increment, 2)` and down to all-in ([game.py:418-431](../game.py)). Because of the clamping, **RAISE_HALF and RAISE_POT can resolve to the same amount**, and both stay "legal" when they do. When a player is all-in with bets matched, `_advance` runs the board out with no further betting ([game.py:567-587](../game.py)). The judge's `play_half` loop is small: `Game(make_deal(seed, d), d % 2, d)` and then observation/apply until terminal ([judge_engine.py:653-702](../judge_engine.py)). Deals are deterministic from `random.Random(f"{match_seed}:{deal_index}")` ([game.py:145-156](../game.py)). As a result, you can build a duplicate harness without HTTP by importing `Game`, `make_deal` and `Game.clone()`, which the source documents as "a cheap independent copy, e.g. for simulation-based agents" ([game.py:546-559](../game.py)).

There are three pieces of repository cruft to fix. The README's file table describes a `.dockerignore` that doesn't exist. `tools/__pycache__/*.pyc` is committed. And `Dockerfile.agent` runs `COPY . /app`, so `.git`, `research_notes/` and any training data ship inside the image and count toward the 3 GiB cap ([Dockerfile.agent](../docker/Dockerfile.agent), [README.md](../README.md)).

## The guide rewards significant, error-free wins over big ones

The participant guide describes a round-robin tournament between Python web servers. A referee "deals the cards, asks each bot for its move, enforces the rules, and keeps score", and "any approach is allowed: hand-written rules, simulations, statistics, or machine learning" (Guide p.3). The game rules are as follows:

- **Deck:** 36 cards, 6 through A (Guide p.5).
- **Ace-low straight:** A-6-7-8-9 is the lowest straight.
- **Hand construction:** each hand uses **exactly two of five hole cards and three of five board cards**, which gives 100 combinations.
- **Hand ranking:** flushes beat full houses, and trips beat straights.
- **Ties:** suits never break ties.

The guide's worked example makes the 2+3 rule concrete: four hearts on the board give no flush unless the player holds two hearts (Guide p.6). Action rules:

- **Action order:** the button acts first preflop and last postflop, and the big blind keeps its option after a limp.
- **FOLD:** legal only when `to_call > 0`. **CHECK_CALL:** always legal.
- **Raises:** both sizes require fewer than 4 raises this street, `my_stack > to_call`, and an opponent who is not all-in (Guide p.6-7).
- **Bet amounts:** the bot never picks an amount. `obs.raise_to` already holds the exact totals.

The shallow stacks show up quickly in the guide's own example. Pot, re-pot, call leaves a 36-chip pot with 62 behind, and a pot-sized bet on the flop then puts both players all-in (Guide p.7).

The interface is three synchronous functions:

- `new_half(config, memory)` runs once per 1,000 hands.
- `choose_action(obs, memory) -> Action` must return a member of `obs.legal_actions`.
- `on_hand_end(result, memory)` delivers `my_net`, `winner`, and `opp_hole` (showdowns only) ([agent.py:48-107](../agent.py)).

The `Observation` exposes 17 fields, including the pot, the bets, `raise_to`, `raises_this_street` and a full `action_history` of `(street, is_me, action, amount, street_total)` entries without blinds ([game.py:199-269](../game.py)). Memory is wiped every half, and in the tournament "each half also runs in a brand-new copy of your server, so nothing at all ... carries over" (Guide p.9). `on_hand_end` runs inside the next `/act` request, so its time is charged to the bank. Each exception it raises counts as a separate error ([judge_engine.py:435-481](../judge_engine.py)).

| Limit | Value | Consequence |
|---|---|---|
| Time bank | 8 s per half; the first 1 ms of each request is free | When the bank is empty the bot auto check/folds for the rest of the half. This is not an error, but it is ruinous |
| Per request | 1 s | Exceeding it is an error. The slow computation keeps running and blocks queued requests |
| Startup | 15 s to answer `GET /` | Failing it forfeits the half |
| Errors | 5 per half | Forfeits the half, and **a forfeit in either half loses the match** |
| Machine | 1 CPU, 4 GB RAM, no network, read-only except a 512 MB `/tmp`, non-root, 256 pids | Fault injection confirmed every limit |
| Image | Up to 3 GiB added; 30-minute build; every file under 100 MB; no Git LFS | Model or table files must stay small |

Sources: [game.py:25-43](../game.py), Guide p.10-12, [check_build.sh:98-110](../tools/check_build.sh).

Local fault injection made these limits concrete. A bot that raised an exception forfeited after 6 calls. A bot that slept 1.2 s forfeited after 6 calls. A bot that slept 50 ms used up the bank after 150 calls, and the remaining 979 calls were auto-played ([runtime notes, judge_engine.py:336-401](../judge_engine.py)).

**Scoring** works as follows. For each deal, the judge sums your bb result across both seats, then takes the mean ± 1.96 standard errors over the 1,000 deals. A confidence interval entirely above 0 is a win (1 point). One entirely below 0 is a loss (0). Anything that touches 0 is a chop (0.5 each). Standings are ordered by points, with ties broken by average bb per deal (Guide p.11). This rule shapes the strategy. With n = 1,000, a win needs a mean edge larger than about **0.062 × the per-deal standard deviation**. The duplicate format cancels card luck, so the remaining variance comes from the two bots making different decisions. Against strong peers, lower variance turns chops into wins. Against weak bots, a large and consistent edge is enough.

**Submission** has three steps. First, register the team; the guide marks this as mandatory and warns that putting one person on two teams invalidates the whole team. Then push to a **public** GitHub repo. Finally, submit the team name, the repo URL, and the **full 40-character commit SHA** (Guide p.1, p.13). The organizers build that exact commit and smoke-test it. "Your latest successful build is the one that plays". If a build fails, the previous one is kept. The deadline and the section-9 form link are still `[[placeholders]]` in this version of the guide (Guide p.13). The guide also says stacks, blinds and the time bank "may be tuned before the tournament", in which case the updated `game.py` is authoritative (Guide p.14). Read these values from `config`; don't hard-code them.

## Monte Carlo equity fits the 3-8 ms budget; CFR does not

The budget follows from measurements. One half produces about 1,000-2,500 `/act` calls, depending on playing style (135 to 2,459 were observed). Against 8 s, that gives an average of **3-8 ms of thinking per decision**. `omaha_score` measured about **15 µs per call** on a Mac ([runtime notes; evaluator.py:241-262](../evaluator.py)). The guide claims "a few microseconds". Each hero-vs-opponent rollout needs two evaluations, so pure Python allows **about 150 rollouts in 5 ms**. That gives an equity standard error near 4 points, and the tournament's shared CPU will likely be slower than a laptop. Published poker-AI methods cost far more. DeepStack-style re-solving and Libratus-style subgame solving are the proven path in large heads-up games ([DeepStack](https://arxiv.org/abs/1701.01724), [Libratus](https://www.science.org/doi/10.1126/science.aao1733)). But even optimized parallel CFR spends about 50 ms per *iteration* on GPU-class hardware ([arXiv 2605.19928](https://arxiv.org/html/2605.19928)). No peer-reviewed strong PLO agent exists to copy, and public Omaha code such as PokerRL-Omaha relies on GPU-distributed Deep CFR and a self-described "naive and slow" evaluator ([PokerRL-Omaha](https://github.com/diditforlulz273/PokerRL-Omaha)). Real-time solving is therefore out. The hybrid that the AI literature recommends, an offline preflop table plus postflop equity estimates plus opponent modelling, is what fits ([ai_and_computation notes](https://arxiv.org/abs/1302.7008)).

Four engineering moves make equity both cheap and accurate. **First, precompute preflop.** Enumerating all C(36,5) = 376,992 hands under suit permutation gives **19,998 isomorphic classes**; we computed this count in this session. Offline, you can estimate each class's equity against a random hand, and against a "strong range" made of the top X% of hands. You can also store features: pairs, double-suitedness, the nut-flush ace, connectivity, and danglers. The result is a table of a few hundred KB, loaded at import alongside `warmup()`. Preflop decisions then reduce to a table lookup costing microseconds. **Second, vectorize postflop evaluation.** Re-index `evaluator.get_table()` into a dense numpy `int32` array using the combinatorial number system. Precompute hero's 10 hole-pair masks once per decision. Each batch of sampled runouts and opponent hands then costs 100 array gathers per player. This is our inference and must be benchmarked, but 500-2,000 rollouts per few milliseconds is a plausible target. numpy is preinstalled in the base image ([Dockerfile.base:27-35](../docker/Dockerfile.base)). **Third, use exact enumeration where it is cheap.** On the turn, only 26 river cards remain once hero's 5 hole cards and the 4 board cards are removed. So the opponent hand becomes the only sampled dimension. **Fourth, weight the opponent's range by their actions.** Use rejection-sampling of opponent hands against the preflop table's percentile, tightened after each opponent raise and loosened against opponents measured as loose. Equity against a random hand overstates hero's chances when facing a pot-raise.

The decision layer is a one-step EV comparison over at most four actions. Calling is worth `E·(pot + to_call) − to_call`, discounted by a realization factor when out of position or deep, and the pot odds threshold is `to_call / (pot + to_call)` (Guide p.13-14). A raise to R is worth `f·pot + (1−f)·(E_c·(pot + 2R') − R')`. Here `f` is the opponent's estimated fold-to-raise rate, `E_c` is equity against their calling range, and `R'` is the chips hero adds. Commitment logic matters in a 40 bb game. Once the stack-to-pot ratio falls to about 1, pot-limit play is "virtually committed once you catch any piece" ([Card Player SPR](https://cardplayer.com/cardplayer-poker-magazines/66224-poker-year-in-review-26-1/articles/21011-pot-limit-omaha-the-stack-to-pot-ratio-spr-part-i)). After a called preflop re-pot, the SPR is about 62/36 ≈ 1.7. The bot should therefore treat "raise pot" as "get it in" whenever the raise would commit more than about a third of its stack, and decide that spot on all-in equity alone.

Some published PLO strategy transfers to this game and some does not. The heads-up-specific findings point the same way as the game structure. A 100 bb heads-up MonkerSolver solve has the button playing **87.5% of hands, almost all as pot raises**, and the big blind continuing 61.4% ([PLO.com HU ranges](https://plo.com/plo-heads-up-ranges)). Position and big pairs gain value heads-up ([OmahaPlanet](https://www.omahaplanet.com/pot-limit-omaha/strategy/heads-up-introduction/)). "Draw to the nuts" remains the core postflop rule ([rec.poker](https://rec.poker/announcements/blog/plo-for-beginners-tame-the-game-of-draws/)). The rest needs caution. All of these numbers come from **4-card, 52-card, 100 bb, raked** games. Here every player holds 5 of only 36 cards, and each suit has only 9 cards, so flushes are rarer and outrank full houses. Straights are cheaper to make and lose to trips. Card removal is much larger, and equities probably run even closer than PLO's "rarely above 65% vs random" ([ThinkGTO](https://thinkgto.com/blog/plo-preflop-strategy-from-theory-to-practice)). Use the published ranges as a sanity check, not as targets. Derive the thresholds from your own self-play.

Exploitation will likely be worth more than balance. The field will contain the four baseline styles (random, calling station, always half, always pot) and many hand-tuned bots. The bot should track several counts in `memory`: opponent VPIP, preflop raise rate, raise rate per street, fold-to-raise rate, and showdown strength against their aggression. Use Bayesian shrinkage toward a prior so early hands don't overreact. Two adjustments follow. Against a calling station, value-bet thinner and stop bluffing. Against an always-raiser, call down far wider and let them bluff. Commercial PLO solvers now ship exactly this kind of profile-based, node-locked exploitation ([PokerNews, Jul 2026](https://www.pokernews.com/news/2026/07/gto-wizard-launches-major-updates-to-its-plo-solver-52006.htm)).

## Seven build phases turn the starter into a contender

Keep `agent.py` thin. Its three hooks should delegate to a committed `bot/` package in the repo root. The image runs `python agent.py` from `/app`, so sibling packages are importable ([Dockerfile.agent:46-63](../docker/Dockerfile.agent)). The new files are:

| New file | Responsibility |
|---|---|
| `bot/__init__.py` | Exports `on_new_half`, `decide`, and `observe_result` |
| `bot/safety.py` | `legalize(action, obs)`, a safe fallback (CHECK_CALL if legal, otherwise FOLD), and exception guards |
| `bot/timebank.py` | Tracks its own `perf_counter` spend. Per-decision budget = min(150 ms, 0.7 × bank left ÷ expected decisions left) |
| `bot/features.py` | Canonical suit-isomorphic key, nut-flush and blocker flags, made-hand class via `score >> 20`, Short Deck draw counts |
| `bot/preflop.py` + `bot/data/preflop.npy` | 19,998-class equity and feature table, plus the preflop policy |
| `bot/equity.py` | Dense numpy evaluator, range-weighted Monte Carlo or turn enumeration, deadline-aware loops |
| `bot/opponent.py` | Frequency counters with priors, plus the range-tightening rules |
| `bot/policy.py` | EV comparison, commitment and SPR logic, river bluff selection with blockers, mixing via a seeded RNG |
| `dev/build_preflop_table.py` | Offline table generation, run once and committed |
| `dev/harness.py` | In-process duplicate matches using `Game` and `make_deal` with no HTTP. Writes paired bb/deal, CI and timing |
| `dev/zoo/` | Opponent styles beyond the baselines (nit, maniac, equity-only, and previous versions of your bot) |
| `tests/test_bot.py` | Legality fuzzing, timing, fault-path, and memory-key tests |
| `.dockerignore` | Excludes `.git`, `research_notes/`, `reports/`, `dev/`, logs and `__pycache__`. Must never exclude `bot/` |

Build in phases, and make each phase a submittable state. **Phase 0** sets `PARTICIPANT` and `AGENT_NAME`, adds the safety wrapper and the timebank, and submits a trivial bot that beats random. That locks in a working build, because a later failed build keeps it (Guide p.13). **Phase 1** writes the harness and the confidence-interval reporting before any strategy, so every later change is measured. **Phase 2** builds the preflop table and a strength-threshold preflop policy. **Phase 3** adds postflop Monte Carlo equity and the EV and pot-odds policy, and should already beat all four baselines decisively. **Phase 4** adds range weighting and commitment logic. **Phase 5** adds the opponent model and the exploit adjustments. **Phase 6** tunes the thresholds by self-play against the zoo. Coordinate search over a small parameter vector is enough. Training a model is optional, and the guide permits shipping one (Guide p.14). **Phase 7** is hardening plus the Docker check.

Safety and error handling must be designed in from the start:

- Every hook body sits in `try/except BaseException-safe` code that returns `legalize(fallback)`. This applies to `on_hand_end` too, where every exception is its own error.
- Every return value is checked against `obs.legal_actions`. FOLD is illegal at `to_call == 0`, and raises disappear facing an all-in or at the cap.
- Monte Carlo loops check a deadline. A hard internal cap far below 1 s, about 150 ms, protects the request limit even on a slow machine.
- All per-half state is created in `new_half`, with deterministic keys, because `test_memory_is_fresh_each_half` compares key sets after a reset ([test_agent.py:95-192](../test_agent.py)).
- Locally, globals leak across halves, but in the tournament they don't ([agent.py:124-128](../agent.py)).
- Seed the RNG in `new_half`. Use a fixed seed for debugging and `os.urandom` in production.
- Avoid importing torch unless the bot actually uses a model. Startup must finish within 15 s.
- Leave the `PORT` read and the `0.0.0.0` binding untouched; a test greps for them ([test_agent.py:189-192](../test_agent.py)).

## Duplicate self-play with confidence intervals gates every change

Evaluation must mirror the scoring. The real judge works but is slow, and its default mode plays both halves against the same process. Its own docstring calls that mode "LOCAL PRACTICE ONLY" ([judge_engine.py:794-804](../judge_engine.py)). The in-process harness should run the same deals twice with seats swapped, using a fresh `bot` state each half. It should record paired bb per deal and report the mean, standard deviation, CI and verdict. It should also record per-decision timing percentiles and the projected bank use per half. The noise is large. A crude bot pair (AlwaysPot vs Random) produced a **per-deal standard deviation of about 30 bb**, which leaves ±1.9 bb/deal of confidence-interval width over 1,000 deals ([runtime notes](../judge_engine.py)). Comparing two versions of your own bot therefore needs many seeds. Size the runs with n ≈ (2.8σ/δ)² deals for 80% power to detect a difference δ, and record each version's results against each opponent so regressions show up. Each stage of the workflow has its own command:

| Stage | Command / check | Pass criterion |
|---|---|---|
| Unit | `python -m pytest -q`, including the new `tests/test_bot.py` (10k-hand legality fuzz against random and always-pot opponents, injected-exception paths) | All green, with zero illegal actions |
| Harness | `python dev/harness.py --opp zoo --deals 1000 --seeds 20` | CI above 0 against every baseline; no regression against the previous version |
| Timing | Harness timing report | p99 decision under 20 ms, and total spend **under 4 s per half on a laptop** (a 2× margin for the slower tournament CPU) |
| Real judge | `python judge_engine.py --half 1 --seed 7 --json h1.json`, restart both bots, `--half 2 ...`, then `combine h1.json h2.json` | 0 errors, no FORFEITED or TIME BANK EMPTY flags |
| Container | `./tools/check_build.sh`, and `PLATFORM=linux/amd64 ./tools/check_build.sh` | `ALL CHECKS PASSED`, image under 3 GiB added |

Sources: [README.md §4](../README.md), [check_build.sh](../tools/check_build.sh), Guide p.12-13.

Two local gaps need attention. Docker is not installed on this machine, so `check_build.sh` could not run; install Docker or use a teammate's machine before the first real submission. And the bundled `play_hands` test always seats your bot in seat 0, so the harness must exercise both seats itself ([test_agent.py:47-88](../test_agent.py)).

The submission checklist in order:

1. Update `requirements.txt`. Keep the FastAPI and uvicorn pins exactly, and add `numpy` without a version so the base copy is reused under the frozen constraints.
2. Commit every imported module and data file.
3. Add the `.dockerignore`.
4. Remove the tracked `.pyc` file.
5. Push to the public repo.
6. Take the SHA from `git rev-parse HEAD`.
7. Submit with the same team name every time.

Submit only versions that have passed the harness. "Latest successful build" means a bot that builds but plays worse still replaces your best one.

Several questions remain open for the organizers:

| Question | Why it matters |
|---|---|
| What are the final deadline and submission form? The section-9 link and the date are placeholders | Planning; whether the forms.gle link on p.1 is authoritative |
| Will stacks, blinds, the bank, or the raise cap change before the event? | Thresholds and the time budget are tuned to 40 bb and 8 s |
| How fast is the tournament CPU compared with a laptop, and is `/new-half` time charged? | Sets the safety margin |
| How are "last raise size" and re-opening defined after a short all-in? | Edge cases in `min_raise_to` (the answer lives in `game.py`) |
| Are baselines entered in the round robin, and how many teams are there? | Decides how much to invest in exploiting weak bots versus being robust against strong ones |
| Do pip installs have network access at build time, and which numpy and torch versions are used? | Dependency safety |
| Is multithreading allowed above `OMP_NUM_THREADS=1`? | The base image says a bot "may raise these", but the hardware is 1 CPU |
| Are there team-size, presentation, or code-sharing rules? | The guide is silent on these |

## Conclusion

The edge in this contest is mostly engineering. The scoring is all-or-nothing on statistical significance, and a single fault path can forfeit a match. A bot that never errors, never runs out of time, and reliably beats the baseline styles collects most of the available points before any strategy refinement matters. Strategy work should then go where the format pays: commitment decisions in a 40 bb pot-limit game where a re-potted pot is nearly all-in, range-weighted equity instead of equity against a random hand, and opponent-specific exploitation that turns chops into wins.

Almost nothing published covers Short Deck PLO5. The 19,998-class preflop table and your own duplicate self-play data will therefore be the most reliable strategy sources available. Treat 4-card PLO solver numbers as hypotheses to test, not as answers.
