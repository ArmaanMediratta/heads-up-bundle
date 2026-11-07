# Why agent.py loses to jammer (and only grinds out a small win against mc_grinder)

Everything below comes from reading the repository source and running experiments on 2026-11-07. Scratch scripts and raw outputs are in `/private/tmp/claude-501/-Users-armaanmediratta-Desktop-datathon-heads-up-bundle/2424e626-b048-4c5c-b38d-bbae1d4a40ae/scratchpad/`:
- `instr.py`: an instrumented match that logs every decision the bot makes, its estimates and the opponent model's state.
- `analyze.py`: computes the true equity against jammer's actual range by Monte Carlo.
- `variant.py`: a copy of agent.py with candidate fixes monkeypatched in. Fixes are switched on with harness `@key=value` flags.
- Raw outputs: `sweep_jammer.txt`, `mc_sweep.txt`, `regress.txt`, `leaks_jammer.txt`, `leaks_mc.txt`.

No tracked file was modified. All harness runs used `--jobs 2` and 1000 deals per match. Results are paired bb/deal with the harness's pooled 95% CI.

## What jammer, _spar_common and mc_grinder actually do

### Takeaway
Jammer plays a fixed raise-or-fold strategy:
- Preflop, it pot-raises at every chance with the top 30% of hands by its own heuristic (`hand_pct >= 0.7`). It folds everything else to any bet, and checks if it is not facing one.
- Once it has raised it never folds.
- Postflop it pot-raises with any "jam" hand or with trips or better. Otherwise it checks or folds.

mc_grinder is a tight player that compares Monte Carlo equity with pot odds. Its preflop line:
- top 20%: pot-raises while fewer than 3 raises have been made this street;
- top 45%: half-pot raises an unraised pot;
- otherwise: calls if `pct > 0.3 + pot_odds`.

### Cited Findings
- Jammer's preflop rule is `jam = hand_pct(obs.hole_cards) >= 0.7`, then `raise_or_call(obs, RAISE_POT)` if jam, otherwise `check_or_fold(obs)`. Postflop it raises when `jam or made_category >= THREE_OF_A_KIND` — [dev/sparring/jammer.py](dev/sparring/jammer.py)
- `raise_or_call` falls back to CHECK_CALL when it can no longer raise, so a jam hand never folds. `check_or_fold` folds whenever `to_call > 0` — [dev/sparring/_spar_common.py](dev/sparring/_spar_common.py)
- `hand_pct` is a hand-made two-card-combination score (high cards, pairs, connectedness, suitedness, penalties for 4-flush and trips in hand). It is calibrated to a percentile over 4000 random hands and is independent of the bot's `preflop.PCT` table — [dev/sparring/_spar_common.py](dev/sparring/_spar_common.py)
- Rules: blinds 1/2, stacks 80 chips (40bb) reset every hand, pot-limit, at most 4 raises per street — [game.py](game.py) lines 30-33
- Against our bot, jammer's VPIP and PFR are both 30.0%. It went to showdown on 99.3% of the flops it saw, and its postflop aggression (raises/calls) was 35.18 — [dev/results/latest.html](dev/results/latest.html)
- mc_grinder's preflop thresholds are pct > 0.8 (pot-raise while `raises_this_street < 3`), pct > 0.55 (half-pot raise if unraised) and pct > 0.3 + po (call). Postflop it uses MC equity against a random hand minus 0.08 per raise this street. It raises pot above 0.8, raises half above 0.65 and calls when eq > pot odds + 0.05 — [dev/sparring/mc_grinder.py](dev/sparring/mc_grinder.py)

### Inferences
- The best response to jammer is simple. Steal freely, since it folds 70% to any bet. Against its jams, continue only when equity against its top-30% range clears the all-in price, because once it has raised it never folds.

### Gaps
- No gaps for this question.

## Where the chips are lost against jammer (how hands end, position, folding vs calling)

### Takeaway
The bot almost never folds to a jam. It continued in 98.4% of first decisions facing a jammer raise and folded only 0.6% of all hands preflop. So nearly every jammer jam becomes a 40bb all-in, which the bot wins only 43% of the time.

Showdown losses total -12.7 bb/deal and showdown wins +10.3 bb/deal. The preflop folds that jammer's 70% fold rate hands us are worth +1.04 bb/deal, but that does not cover the gap. The leak is calling far too light, not folding too much.

### Cited Findings
- Baseline over 10 matches: -1.378 bb/deal, 95% CI [-1.880, -0.877], W-C-L 0-6-4 (`python3 dev/harness.py --opp dev/sparring/jammer.py --deals 1000 --seeds 10 --jobs 2`). This agrees with latest.html: -1.374 [-1.88, -0.87], 0-6-4 — [sweep_jammer.txt (scratchpad)](/private/tmp/claude-501/-Users-armaanmediratta-Desktop-datathon-heads-up-bundle/2424e626-b048-4c5c-b38d-bbae1d4a40ae/scratchpad/sweep_jammer.txt); [dev/results/latest.html](dev/results/latest.html)
- leaks.py over 4 seeds (-1.463 [-2.259, -0.667]) breaks down by how hands ended. Showdown accounts for 29.7% of hands and carries all the loss:

  | How the hand ended | Hands | Share | bb/deal |
  |---|---|---|---|
  | Showdown lost | 1274 | 15.9% | -12.730 |
  | Showdown won | 1030 | 12.9% | +10.290 |
  | They folded preflop | 5557 | 69.5% | +1.041 |
  | We folded preflop vs pot | 44 | 0.6% | -0.038 |

  [leaks_jammer.txt (scratchpad)](/private/tmp/claude-501/-Users-armaanmediratta-Desktop-datathon-heads-up-bundle/2424e626-b048-4c5c-b38d-bbae1d4a40ae/scratchpad/leaks_jammer.txt)
- By position: button/SB -0.334 bb/deal, big blind -1.129 bb/deal. So the big blind (facing jammer's open jam with no chips in) is where most of the loss is — [leaks_jammer.txt](/private/tmp/claude-501/-Users-armaanmediratta-Desktop-datathon-heads-up-bundle/2424e626-b048-4c5c-b38d-bbae1d4a40ae/scratchpad/leaks_jammer.txt)
- Preflop action frequencies:
  - Facing a pot raise (n=4812): fold 0.9%, call 25.5%, half-pot raise 28.7%, pot raise 44.9%.
  - Facing only the blind on the button (n=4000): fold 0.1%, call 0.1%, raise 99.8%.

  [leaks_jammer.txt](/private/tmp/claude-501/-Users-armaanmediratta-Desktop-datathon-heads-up-bundle/2424e626-b048-4c5c-b38d-bbae1d4a40ae/scratchpad/leaks_jammer.txt)
- latest.html, 10 matches (20,000 hands):
  - Our fold-to-a-raise rate is 1.2%, and our showdown win rate is 43.3% against jammer's 53.3%.
  - Showdown: 29.2% of hands, -23,360 bb in total.
  - Opponent folds preflop: 69.9% of hands, +10,467 bb.
  - Our preflop folds: only 125 hands.

  [dev/results/latest.html](dev/results/latest.html)
- The biggest losers are all 40bb preflop all-ins with marginal hands, for example "us [7c 8d 9s Jh Qc] vs [9c 9h Qh Qs As]" on the line us:P op:P us:P op:P us:C — [leaks_jammer.txt](/private/tmp/claude-501/-Users-armaanmediratta-Desktop-datathon-heads-up-bundle/2424e626-b048-4c5c-b38d-bbae1d4a40ae/scratchpad/leaks_jammer.txt)

### Inferences
- Against jammer, essentially the whole loss comes from playing 40bb pots against a top-30% range with roughly 45% equity. Postflop play does not matter: we folded on the flop 17 times out of 8000 hands.

### Gaps
- No gaps for this question.

## Equity calibration, opponent.py frequency estimates and policy._weights against a 100%-raise-when-seen opponent

### Takeaway
**Root cause.** `bot/opponent.py` only counts opponent actions it sees in `obs.action_history` when it is our turn to act. Jammer's folds always end the hand before our next decision, so they are never counted:
- when jammer folds first as button, we never act;
- when jammer folds in the BB to our raise, we never act again.

As a result, the estimated preflop raise frequency converges to about 0.986, against a true value of 0.30. Then `policy._weights` sets its cut-off to `1 - r_pf**n` ≈ 0.014, which applies almost no range narrowing. The bot therefore computes equity as if jammer's jam could be any hand.

Our estimated equity facing a jam averages 0.491, while the true equity against jammer's actual range is 0.450. That 4-5 point overestimate is consistent across every equity bin.

The same unweighted range makes the raise EV assume about 45% fold equity when we re-raise a jammer, which never folds. That is why the bot re-raises 74% of the time.

### Cited Findings
- `observe()` increments `pf_acts`/`post_acts` only for history entries it sees (lines 45-63). `hand_end()` adds only `faced_raise`/`folded_to_raise` when we raised last and won without a showdown (lines 71-77). An opponent fold never reaches `pf_acts` or `post_acts` — [bot/opponent.py](bot/opponent.py)
- Instrumented run against jammer (2 seeds × 1000 deals):
  - At hand ~397 the model state was `pf_acts 234, pf_raises 234` (r_pf = 0.979).
  - At hand ~955 it was `pf_acts 540, pf_raises 539` (r_pf = 0.989), with `post_acts 68, post_raises 67`.
  - The mean r_pf after hand 500 was 0.986, against jammer's true 30% raise rate (latest.html PFR 30.0%).

  [instr.py](/private/tmp/claude-501/-Users-armaanmediratta-Desktop-datathon-heads-up-bundle/2424e626-b048-4c5c-b38d-bbae1d4a40ae/scratchpad/instr.py) + [analyze.py](/private/tmp/claude-501/-Users-armaanmediratta-Desktop-datathon-heads-up-bundle/2424e626-b048-4c5c-b38d-bbae1d4a40ae/scratchpad/analyze.py) output
- Range cut-offs: `cut = min(1.0 - r_pf ** n_pf, p["max_cut"])` and `w *= sigmoid((opp_pct - cut)/temp_pre)` — [bot/policy.py](bot/policy.py) line 52
  - With r_pf = 0.986: cut ≈ 0.014 for n=1 and ≈ 0.03 for n=2.
  - The measured mean weighting shift (weighted eq minus unweighted eq) was only -0.011, and the effective sample size stayed about 1367 of 1536. In other words, the weights barely did anything.
- Calibration across 2322 preflop decisions facing a jammer raise (1200 sampled; true equity from 400 MC samples each against opponent hands with jammer's `hand_pct >= 0.7`):

  | Measure | Mean equity |
  |---|---|
  | Estimated (weighted) | 0.491 |
  | Estimated (unweighted) | 0.502 |
  | True vs jammer's range | 0.450 |

  By bin, estimated → true: 0.40 → 0.382, 0.45 → 0.418, 0.50 → 0.455, 0.55 → 0.495, 0.60 → 0.538. The ranking of hands is fine; the level is about 0.045 too high. The cause is the range, not the evaluator — [analyze.py output](/private/tmp/claude-501/-Users-armaanmediratta-Desktop-datathon-heads-up-bundle/2424e626-b048-4c5c-b38d-bbae1d4a40ae/scratchpad/analyze.py)
- Fold equity in raise EV: `t = fold_to_raise` ≈ 0.446 (pooled over all spots). `cont = sigmoid((opp_now - t)/temp_post)`, so with an unnarrowed range f ≈ share of samples below 0.446 ≈ 0.45. That value feeds `evs[a] = fa*pot + (1-fa)*(...)` — [bot/policy.py](bot/policy.py) lines 91-109
  - Jammer's real fold rate after it has raised is 0%, because `raise_or_call` never folds ([_spar_common.py](dev/sparring/_spar_common.py)).
  - The measured `fold_to_raise` of 0.446 is a blend of jammer folding about 70% to our first raise and 0% once it has raised.
- Secondary design flaw: the `1 - r^n` rule assumes each extra raise narrows the range geometrically. Against jammer, the 2nd, 3rd and 4th raises carry no extra information, since it uses the same top 30% every time. With correct counting (r = 0.3): n=1 gives cut 0.70, which is correct, but n=2 gives 0.91, capped at `max_cut` 0.9, which treats the range as top 10% (over-tight). In the experiment this flaw was harmless (see the flatcut result below) — [bot/policy.py](bot/policy.py) line 52; [sweep_jammer.txt](/private/tmp/claude-501/-Users-armaanmediratta-Desktop-datathon-heads-up-bundle/2424e626-b048-4c5c-b38d-bbae1d4a40ae/scratchpad/sweep_jammer.txt)
- The call EV is `eq * r_call * (pot + to_call) - to_call` with `r_call = 1` only when the call itself is all-in (lines 80-83). Facing jammer's 3-bet to 18 after our open to 6, the bot sees "call 12 into 36" odds (about 35% needed) instead of the real price of getting 74 more in — [bot/policy.py](bot/policy.py) lines 80-83

### Inferences
- The counting bug is general, not jammer-specific. Any opponent that folds often to our raises, or folds first on the button, has its raise frequency inflated. So the bot never narrows ranges against tight or fold-heavy opponents. The variant results below against nit (+1.02 → +1.77) and mc_grinder (+1.01 → +1.39) fit this.
- The opposite problem would appear against an opponent that limps or calls a lot. It would look passive in the counts.

### Gaps
- I did not measure how well jammer's `hand_pct` ordering correlates with the bot's `preflop.PCT`. Even a perfect cut on PCT may only approximate jammer's range. Still, the fix below recovers most of the gap.

## Correct game-theoretic call thresholds at 40bb pot-limit vs jammer, compared with the bot's decisions

### Takeaway
Because jammer never folds after raising, every continue is effectively a stack-off: final pot 160 chips, and we put in 80 in total. The required equity is (80 - chips already in) / 160:
- BB facing jammer's open pot-raise to 6 (we have 2 in): 48.75%.
- Button facing jammer's re-raise after our pot open to 6: 46.25%.
- After our limp, facing a raise (we have 2 in): 48.75%.

Against these prices, the bot should fold about 57% of BB spots and about 34% of button spots. It folds about 1.5%. At n_pf = 1 the bot folded 1.4% of the time where 67% of those spots were folds.

### Cited Findings
- Stacks 80, blinds 1/2, pot raise = opp_bet + pot + to_call — [game.py](game.py) lines 30-33 and `_raise_to`. Jammer's open from the button is to 6. Our pot open to 6 is answered by jammer re-raising to 18.
- Measured over the instrumented first decisions facing a jam (n = 903):
  - Overall: continued 98.4%; continued with true equity below threshold in 43.6% of spots.
  - At n_pf = 1 (first jam, n = 627): mean threshold 0.477, true equity 0.449, bot fold rate 1.4%, correct fold rate 67.0%.
  - At n_pf = 2 (deeper in the raising war, more chips already in): threshold 0.322, true equity 0.451, bot fold rate 1.0%, correct fold rate 20.1%.
  - BB: bot continues 98.6% vs should continue 43.3%.
  - Button: bot continues 98.3% vs should continue 66.2%.
  - Estimated equity ≥ threshold in 73.6% of spots; true equity ≥ threshold in only 55.0%.

  [analyze.py output](/private/tmp/claude-501/-Users-armaanmediratta-Desktop-datathon-heads-up-bundle/2424e626-b048-4c5c-b38d-bbae1d4a40ae/scratchpad/analyze.py)
- Approximate EV lost by continuing below threshold, assuming all-in: about 1.9 bb per first-decision spot. Jammer jams in about 30% of hands, which is roughly the observed -1.4 bb/deal plus what we give up by not stealing better — [analyze.py output](/private/tmp/claude-501/-Users-armaanmediratta-Desktop-datathon-heads-up-bundle/2424e626-b048-4c5c-b38d-bbae1d4a40ae/scratchpad/analyze.py)

### Inferences
- Button opening strategy, by back-of-envelope arithmetic I did not test:
  - Raise-then-fold-to-3bet with weak hands: about 0.7 × (+2) + 0.3 × (-6) = -0.4 chips.
  - Limp-then-fold-to-raise: about 0.7 × (≈+1.5 postflop steal) + 0.3 × (-2) ≈ +0.45 chips.
  - Against this kind of opponent, limping or small-raising weak hands loses less when jammer has a hand. The bot currently raises 99.8% of buttons.
- The "first decision" sample in analyze.py includes some n_pf = 2 spots, because only a subsample of decisions was analysed. Treat the per-position numbers as approximate (±a few points).

### Gaps
- The limp-vs-raise button exploit was not tested experimentally.

## Experiments: parameter overrides and code-level fixes (effect sizes with CIs)

### Takeaway
No PARAMS override moves the jammer result significantly; all stay within about ±0.3 bb/deal of baseline with overlapping CIs. That is expected, because none of them repairs the inflated `r_pf`.

Fixing the opponent-fold counting (`fixcount`) swings the jammer result from -1.38 to +0.37 bb/deal, an improvement of about 1.75 bb/deal, far outside the CIs. It also raises mc_grinder from +1.01 (3-7-0) to +1.39 (10-0-0), and shows no regression against 15 other opponents.

Adding a stack-off (commit) rule on top makes jammer significantly positive, +0.41 [+0.16, +0.65]. Its mc_grinder result (+1.26, 9-1-0) is not distinguishable from fixcount alone (+1.39).

Matches against jammer remain mostly CHOP. Per-deal std is about 25 bb, so a 1000-deal match needs about +1.6 bb/deal for a WIN verdict.

### Cited Findings
- **Jammer, 10 seeds × 1000 deals, same seeds h0-h9** ([sweep_jammer.txt](/private/tmp/claude-501/-Users-armaanmediratta-Desktop-datathon-heads-up-bundle/2424e626-b048-4c5c-b38d-bbae1d4a40ae/scratchpad/sweep_jammer.txt)):

  | Bot | bb/deal | 95% CI | W-C-L |
  |---|---|---|---|
  | agent.py (baseline) | -1.378 | [-1.880, -0.877] | 0-6-4 |
  | `r_ip=0.8,r_oop=0.7` | -1.144 | [-1.614, -0.674] | 0-7-3 |
  | `temp_pre=0.2` | -1.339 | [-1.839, -0.839] | 0-7-3 |
  | `max_cut=0.6` | -1.408 | [-1.909, -0.907] | 0-6-4 |
  | `commit_spr=2` | -1.433 | [-1.936, -0.930] | 0-6-4 |
  | `half_fold_scale=0.4` | -1.124 | [-1.615, -0.634] | 0-8-2 |
  | `call_cut_scale=1.2` | -1.371 | [-1.872, -0.869] | 0-7-3 |
  | `max_samples=512` | -1.439 | [-1.939, -0.939] | 0-7-3 |
  | `temp_post=0.25` | -1.463 | [-1.967, -0.958] | 0-6-4 |
  | variant `fixcount=1` | +0.368 | [-0.056, +0.793] | 1-9-0 |
  | variant `fixcount=1,flatcut=1` | +0.378 | [-0.046, +0.801] | 2-8-0 |
  | variant `commit=1` (stack-off rule only, no count fix) | +0.224 | [-0.142, +0.591] | 1-9-0 |
  | variant `fixcount=1,commit=1` | **+0.407** | **[+0.160, +0.654]** | 1-9-0 |

- **mc_grinder, 10 seeds × 1000 deals** ([mc_sweep.txt](/private/tmp/claude-501/-Users-armaanmediratta-Desktop-datathon-heads-up-bundle/2424e626-b048-4c5c-b38d-bbae1d4a40ae/scratchpad/mc_sweep.txt)):

  | Bot | bb/deal | 95% CI | W-C-L |
  |---|---|---|---|
  | agent.py | +1.012 | [+0.691, +1.334] | 3-7-0 |
  | fixcount | +1.391 | [+1.146, +1.636] | 10-0-0 |
  | fixcount+commit | +1.264 | [+1.018, +1.510] | 9-1-0 |

  latest.html had agent.py at +1.014, 7-3-0. The W-C-L count varies between runs because BOT_SEED is unset, so the bot's RNG is unseeded.
- **Regression check, fixcount, 3 seeds × 1000 deals:** 42.0 / 45 points, W-C-L 39-6-0, no losses. Compared with latest.html (agent.py, 10 seeds):

  | Opponent | fixcount | agent.py (latest.html) |
  |---|---|---|
  | nit | +1.767 | +1.02 |
  | blind_stealer | +3.041 | +3.43 |
  | trapper | +1.585 | +1.54 |
  | tag | +1.177 | +1.16 |
  | stabber | +2.634 | +2.79 |
  | maniac | +10.48 | +10.03 |
  | equity_caller | +0.307 | +0.43 |

  Differences are within noise except nit, which improves. In this 3-seed run jammer came out at -0.136 [-0.91, +0.64], noisier than the 10-seed +0.37 — [regress.txt](/private/tmp/claude-501/-Users-armaanmediratta-Desktop-datathon-heads-up-bundle/2424e626-b048-4c5c-b38d-bbae1d4a40ae/scratchpad/regress.txt). The regression run for fixcount+commit was stopped early to stay within the time budget.
- **mc_grinder leak profile (baseline, 3 seeds, +1.033 [+0.434, +1.632]):**
  - By position: BB +0.036 bb/deal vs button +0.997.
  - Biggest losses are again 40bb preflop raising wars against its top-20% pot-raising range, for example us [6s 7c Tc Td Jd] vs [8c 9h Ks Ac As] on op:P us:h op:P us:h op:C.
  - We fold to its postflop pot bets 69-94% of the time. That is appropriate, since it bets pot only with eq > 0.8.

  [leaks_mc.txt](/private/tmp/claude-501/-Users-armaanmediratta-Desktop-datathon-heads-up-bundle/2424e626-b048-4c5c-b38d-bbae1d4a40ae/scratchpad/leaks_mc.txt)

### Inferences
- **Fix 1 (highest value, small change).** In `bot/opponent.py` `hand_end`, when `not result.went_to_showdown and result.my_net > 0`, the opponent's final action was an unseen fold. Count it as a non-raise act on that street:
  - `pf_acts += 1` if `len(result.board) == 0`;
  - otherwise `post_acts += 1`.

  This is exactly what `variant.py@fixcount=1` does. It is worth about +1.75 bb/deal against jammer and about +0.4 against mc_grinder, with no observed regressions.
- **Fix 2 (worth trying).** Condition fold-to-raise on whether the opponent has already raised this hand, i.e. keep separate counters in `opponent.py`. Then the raise EV at `policy.py` lines 91-109 stops assuming fold equity against a re-raiser. After Fix 1 the narrowed range already pushes `f` toward 0 in these spots, so the extra gain may be small. Not tested separately.
- **Fix 3 (optional exploit, gated).** When an opponent re-raises almost every time it continues against our raise (rate measured as `rr / (faced_raise - folded_to_raise)`, gate > 0.6), evaluate preflop calls and raises against a raise as all-in: EV = eq × (pot + to_call + 2 × (eff - to_call)) - eff. This replaces the per-street call EV at `policy.py` lines 80-83, which ignores the commitment. It adds about +0.04 against jammer (not significant on its own) and tightens the CI. It may cost a little against mc_grinder (-0.13, not significant).
- **Not needed now.** `flatcut` (dropping the `r^n` compounding on repeat raises) made no measurable difference: +0.378 vs +0.368.
- Turning jammer CHOPs into WINs probably needs further exploitation, either stealing more cheaply as described in the threshold section or lowering variance by folding more. Even a perfect fold policy may leave the edge near the +1.6 bb/deal WIN line.

### Gaps
- fixcount+commit was not run through the full regression suite (stopped for time).
- Fix 2 and the button limp exploit were not tested.
- The CIs compare independent runs, not paired per-deal differences between variants on the same deals. The true difference CIs may be somewhat tighter.
