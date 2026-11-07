# Policy audit: structural weaknesses of the one-step EV bot (bot/policy.py and friends)

Scope: `bot/policy.py`, `bot/opponent.py`, `bot/equity.py`, `bot/preflop.py`, `bot/timebank.py`, `bot/fasteval.py`, checked against the rules in `game.py`. Every "Source" below is either a code location in the repo at commit `563675b` or an experiment script I ran (all in the scratchpad `/private/tmp/claude-501/-Users-armaanmediratta-Desktop-datathon-heads-up-bundle/2424e626-b048-4c5c-b38d-bbae1d4a40ae/scratchpad/`, files `exp1.py` to `exp8.py`, `h1.txt`). I did no web research; all claims rest on the code and on measurements. Sample sizes are small (500-deal matches, 1-2 seeds), so read the match numbers as direction, not precise effect sizes.

**Ranked list (most EV at stake first; details are in the sections below)**

| # | Flaw | Where | Evidence | Fix | Effort | Extra compute per decision |
|---|---|---|---|---|---|---|
| 1 | Raise EV has no opponent re-raise branch, and fold equity comes from one pooled `fold_to_raise` number used as a percentile threshold. The model sees ~30% folds from ranges that never fold, so the bot escalates preflop raise wars. | policy.py:92-109, opponent.py:40-76 | Bot vs jammer.py: -2.42 bb/deal (harness, 2 seeds). Model 3-bet EV is +0.8 to +1.3 chips; true EV is -2.4 to -15 chips. | A 3-branch response tree (fold/call/re-raise) built from the existing samples, plus fold/re-raise stats split by node | 1-2 days | <0.3 ms (reweighting only) |
| 2 | The range model only counts made hands (`opp_now`), it narrows geometrically (`1-r^n`), and it judges earlier-street bets by the current board. It ignores draws and drops missed-draw bluffs. | policy.py:39-63, equity.py:60 | Hero equity overstated by 2-11 points against equity-ranked ranges of the same width; bot folds 58%/66%/72% to bets on flop/turn/river vs exploiter | Mix an opponent "potential" score (4 extra runouts) into `opp_now`; narrow by street, without compounding | 0.5-1 day | +0.1-0.2 ms per 256 samples |
| 3 | Constant realization (0.95/0.85). No future-street, implied or reverse-implied odds. The call branch has no commitment check while the raise branch does. | policy.py:79-83, 106-107 | BB facing a 4-bet: 228 jams / 72 folds / 0 calls. Calls leaving SPR 0.24 are still discounted by 15%. | Per-sample showdown-pot model (extra bet when both final hands are strong). Or a fitted R table. Commit check on calls. | 0.5-1 day | ~0.05 ms |
| 4 | Preflop: raises 99.7% of SB hands and 99.7% vs a limp. No explicit strategy for 3-bet/4-bet/jam spots. | policy.py as a whole, preflop.py | exp2 node table (below) | Offline equity-vs-top-x% table (no noise, 0 ms) plus #1's tree | 0.5 day build plus #1 | -0.5 to -3.4 ms (saves time) |
| 5 | Deterministic argmax. Checking range is capped (no check has eq > 0.60), and the bot overfolds to bets. | policy.py:112 | exp6: 0% of postflop checks had eq > 0.6 | Trap a fraction of strong hands. Randomize within ±2 SE. Track our own fold-to-bet against MDF. | 0.5 day | ~0 |
| 6 | Monte Carlo noise. Effective sample size is only 16-50% of the samples drawn, and decisions flip. | equity.py, policy.py:71-74 | 37.5% of flop facing-bet spots flip at 256 samples, 25% at 1536 | Exact river enumeration (~1-2 ms). Adaptive extra samples when the EV gap is under 2 SE. Range-targeted preflop sampling. | 0.5-1 day | river +1-2 ms; close spots +1-3 ms |
| 7 | About 60% of the time bank goes unused, because the `max_samples` cap binds, not the budget | policy.py:31, timebank.py:14-48 | 2.4 s of 8 s average per half (1.5-3.3 s) | Spend it on #6 (close spots, rivers) | small | within budget |
| 8 | Small bugs and edge cases: fold-count bias, pooled raise stats, half-size raise assumes the same calling range | opponent.py:63-76, policy.py:108 | Counted fold rate 0.267 vs true 0.239 (exploiter); 0.411 vs 0.347 (jammer) | Count calls that end the hand in `hand_end` | 1 hour | 0 |

---

## Q1. EV formulas: what they ignore, and should the bot do explicit small game-tree lookahead?

### Takeaway
Two things in the one-step formula drive the biggest measured losses. First, there is no opponent re-raise branch. Second, fold equity comes from a single pooled `fold_to_raise` frequency that ignores node, bet size and pot odds. Against an opponent that re-raises with a strong range and never folds after that (jammer.py), the model rates a 3-bet at +0.8 to +1.3 chips when its true value is -2.4 to -15 chips, and the bot loses about 2.4 bb/deal to that sparring bot. A tiny response tree (our action → opponent fold/call/re-raise → our fold/call) reuses the samples already drawn and costs well under 0.5 ms. It is the single highest-value change.

### Cited Findings
- The EV formulas are exactly: check/call `eq*r_call*(pot+to_call) - to_call`; raise `fa*pot + (1-fa)*(eq_call*r_raise*called_pot - added)`, with fold = 0 — [bot/policy.py:83,109](bot/policy.py). The opponent's only possible responses to our raise are fold or call. A re-raise is never modelled, even though `game.py` allows 4 voluntary raises per street (`RAISE_CAP_PER_STREET = 4`) — [game.py:30, game.py:410-416](game.py).
- Fold equity: `t = opponent.fold_to_raise(memory)` is one Beta-smoothed frequency with prior (3,5) = 0.375, pooled over every street, node and bet size. It is then used as a percentile threshold on the opponent's current strength (`cont = sigmoid((opp_now - t)/0.12)`). It does not depend on how many chips the opponent must call or what odds they get — [bot/policy.py:92-96](bot/policy.py), [bot/opponent.py:14,40-42](bot/opponent.py). RAISE_HALF assumes 85% of the pot-raise fold rate with the *same* continuing range and `eq_call` — [bot/policy.py:108](bot/policy.py).
- Pot-limit sizing from game.py at 80-chip stacks (pot-raise target = `opp_bet + pot + to_call`, [game.py:428](game.py)): preflop the raises go open to 6, 3-bet to 18, 4-bet to 54, then all-in (80). That is the 4-raise cap. SPR after the call is 6.2 (pot 12, 74 behind) in a single-raised pot, 1.7 (36 / 62) in a 3-bet pot, and 0.24 (108 / 26) in a 4-bet pot. Measured in [exp2.py](scratchpad/exp2.py) output: `(pot, to_call, stack, raise_to)` = `(8,4,78,{POT:18})`, `(24,12,74,{POT:54})`, `(72,36,62,{POT:80})`.
- Postflop in a single-raised pot (pot 12, 74 behind), a flop pot bet of 12 makes the pot 36, and a pot raise goes to 12+36+12 = 60 of the 74. So bet + raise is effectively all-in, and "commit within ~3 raises" holds: it takes 2 postflop raises in a single-raised pot, or 1 in a 3-bet pot (my arithmetic from [game.py:424-431](game.py)).
- Worked example, re-raise blindness (SB open, [exp5.py](scratchpad/exp5.py) part A). The test opponent folds its bottom 40%, calls 40-85%, and 3-bets the top 15%. The bot formula (prior f ≈ 0.33-0.43) rates a pot open at +0.39 / +0.87 / +1.24 / +1.61 / +1.69 / +1.93 chips for hands at the 5/20/40/60/80/95th percentile. With the 3-bet branch included (hero folds or gets it in, whichever is better), the values are -0.33 / +0.04 / +0.53 / +0.84 / +1.05 / +1.15. So the formula overstates open EV by about 0.7-0.8 chips (0.35-0.4 bb) per open against an opponent that 3-bets 15%. For a bottom-5% hand it picks a negative-EV raise over a positive limp (+0.48).
- Worked example, pooled fold stat (BB facing jammer's open, [exp5.py](scratchpad/exp5.py) part B). The opponent opens only its top 30% and never folds once it has raised. With the memory the bot actually builds against it (`fold_to_raise` ≈ 0.7, because jammer folds 70% of hands to our *opens*), the model expects f ≈ 0.29-0.31 folds to a 3-bet. Model 3-bet EV is -0.58 / +0.76 / +1.27 / +1.09 chips (30/50/70/90th percentile hand) against call EV +0.05 / +0.63 / +0.85 / +0.81. True 3-bet EV (always all-in vs the top 30%) is -15.1 / -5.8 / -2.4 / -3.6.
- Behaviour consistent with that: against jammer.py the bot raised 148 of 153 times facing an open and 142 of 146 facing a 3-bet. It almost never folded or flatted, and lost -0.90 bb/deal in a 500-deal duplicate match — [exp4.py](scratchpad/exp4.py) output. In the harness it lost -2.42 bb/deal [-3.97, -0.88] over 2×500 deals (0-1-1), while beating exploiter.py (+2.41) and tag.py (+1.47) — [h1.txt](scratchpad/h1.txt).
- The check EV (`eq*R*pot` when `to_call == 0`) also ignores what follows a check: the opponent betting and us folding part of our equity, or us check-raising — [bot/policy.py:83](bot/policy.py).

### Inferences
- **Recommended design (lookahead depth 2, built from existing samples).** For each raise size `a`, split the opponent's weighted range `w` by strength `s` (the percentile `opp_now`, or the draw-aware score from Q2) into three soft bands: fold (s < t_f), call (t_f ≤ s < t_r), re-raise (s ≥ t_r). Set the band edges from per-node observed frequencies, not one pooled stat:
  - `fold_vs_open`, `fold_vs_3bet+`, `fold_vs_flop_bet`, `fold_vs_turn/river_bet`
  - `reraise_vs_our_raise` (preflop and postflop)
  - bucket them, each with its own Beta prior
  - make the fold band pot-odds aware: cap the fold mass so a hand with equity above `to_call_opp / final_pot` is never assumed to fold. Facing a jam that leaves the opponent 26 to win 134, almost nothing folds.

  Then:
  `EV(a) = P_f*pot + P_c*(E_c*R*pot_c - added) + P_r*max(-added, EV_ourcall_vs_reraise)`,
  where `EV_ourcall_vs_reraise = E_r*R'*pot_r - (added + extra_call)` and `E_r` is our equity against the re-raise band (one weighted mean over the same samples). When the re-raise puts us at SPR < ~0.6, treat it as all-in (R' = 1). Because of the 4-raise cap and stacks committing in at most 3 pot raises, the tree is tiny (at most about 3 levels, 2-3 branches each). Every node is a weighted sum over the same `win` array: about 10-30 numpy reductions over ≤1536 elements, roughly 5-20 µs each. That is **well under 0.3 ms per decision**.
- Implementation effort: 1-2 days, including the new opponent stats (in `opponent.observe`/`hand_end`) and tuning the band thresholds in the harness. Expected payoff: it removes the dominant leak against re-raise-heavy and jam-heavy opponents (the -2.4 bb/deal vs jammer). It also trims thin opens, since the formula overstates open EV by ~0.35-0.4 bb against any 15% 3-bettor.
- A cheaper partial fix (2-4 hours): split `fold_to_raise` by node (unopened-preflop / facing re-raise / postflop) and add a single "re-raise probability × lose `added`" penalty term. This captures most of the jammer leak without the full tree.
- A full future-street tree (simulating turn and river betting) is not worth it at this time budget. Q3 gives a cheaper per-sample pot-growth model.

### Gaps
- I did not prototype the tree in the harness, so the bb/deal recovery is estimated from the EV gaps above, not measured. The 3-branch opponent used in example A is my own assumption, not a measured field-opponent profile.

---

## Q2. Range modelling: postflop range uses made-hand percentile `opp_now`, ignoring draws. How to add draw equity cheaply?

### Takeaway
`opp_now` ranks opponent hands only by the current made hand. Its rank correlation with the hand's true equity against a random hand is only 0.38-0.71 on test flops. Ranges built from it make our equity look 2-11 points better than against an equity-ranked range of the same width. Averaging the opponent's final-hand percentile over 4 extra runouts gives 0.57-0.70 correlation, and adding it is nearly free. Three more problems: `cut = 1 - r^n` compounds geometrically on repeated raises; earlier-street bets are judged by the current board, which removes missed draws (bluffs) from river ranges; and preflop calls don't narrow the range at all.

### Cited Findings
- `opp_now` on the flop and turn is `best_score(opp_pairs, board_triples(board))`, the opponent's made hand on the visible board, ranked among the samples. Draws contribute nothing — [bot/equity.py:60, 66-70](bot/equity.py). Postflop narrowing applies `sigmoid((opp_now - cut)/0.12)` to *every* opponent postflop raise in the history, using the current-street `opp_now` even for earlier-street bets — [bot/policy.py:54-57](bot/policy.py).
- Cut-offs compound: `cut = min(1 - r^n, 0.9)` for the n-th raise this hand. A 30% raiser's second raise is modelled as its top 9-10%, but jammer.py raises its same top 30% every time — [bot/policy.py:50-57](bot/policy.py), [dev/sparring/jammer.py](dev/sparring/jammer.py).
- Preflop calls never narrow the range: the call-narrowing branch requires `act.street != Street.PREFLOP` — [bot/policy.py:58-62](bot/policy.py).
- Draw-blindness measurement ([exp3.py](scratchpad/exp3.py), 3000 opponent hands per flop, true equity from 48 runouts against a random villain):

| Hero / flop | Spearman(opp_now, true eq) | 4-runout potential | top-30% overlap (now / 4-runout) | hero eq vs top-30% by made hand | vs top-30% by true equity |
|---|---|---|---|---|---|
| TsTd9c7h6d / Th8s6c (top set, wet) | 0.38 | 0.57 | 0.53 / 0.61 | 0.885 | 0.823 |
| AhKhQdJc7s / Th9h6c (nut flush draw + wrap) | 0.59 | 0.70 | 0.77 / 0.76 | 0.478 | 0.382 |
| AsAdKcQd7c / Ks8d6h (overpair) | 0.67 | 0.60 | 0.74 / 0.67 | 0.341 | 0.303 |
| KdQsJd9c7h / Ts8c6d (non-nut straight) | 0.71 | 0.68 | 0.75 / 0.74 | 0.268 | 0.172 |

  A single runout's final-hand percentile is a worse ranking than `opp_now` (correlation 0.34-0.45). In every case the made-hand range overstates hero equity, by +6.2, +9.6, +3.8 and +9.6 points.
- Against exploiter.py, which bets draws (pot raise with any flush draw when checked to), the bot folded to a single bet 262/452 times on the flop (58%), 124/187 on the turn (66%) and 36/50 on the river (72%). Minimum defence against a pot bet is 50% — [exp4.py](scratchpad/exp4.py) output.

### Inferences
- **Cheap draw-aware strength:** in `_batch`, draw K = 4 extra (turn, river) completions per sample (one extra `board5_triples` + `best_score` for the opponent only, roughly 0.1-0.2 ms per 256 samples). Average the opponent's final percentile over them to get `opp_pot`. Then use `s = λ·opp_now + (1-λ)·opp_pot` with λ ≈ 0.4-0.6 as the strength axis for narrowing and for the fold/continue bands. The table shows `opp_pot` alone ranks better than `opp_now` on wet boards (0.57 vs 0.38) and slightly worse on dry ones. A blend is the robust choice (my inference; not measured beyond these 4 flops). Effort: half a day including tuning.
- Narrow by street, not geometrically: use cut = 1 - r_street (one cut per street, with the latest raise counting slightly more). Or track per-opponent "re-raise | raised" frequencies so a repeat raiser isn't over-tightened. For earlier-street bets, apply the cut to the strength measured *on that street's board* (recompute `opp_now` for the flop and turn boards, which is cheap: one extra `best_score` per earlier street). Then missed draws stay in the river range. Effort: 2-4 hours.
- Add preflop-call narrowing (BB flatting our open removes roughly the bottom 20-40% by `opp_pct`), using an observed "fold vs open" stat.

### Gaps
- I measured on 4 hand-picked flops only, and treated "betting range = top-30% by equity vs random" as a stand-in for real opponents. The true betting ranges of field bots are unknown.

---

## Q3. Realization factors r_ip / r_oop are constants. Better alternatives? (Includes future-street, implied and reverse-implied odds, and stack commitment.)

### Takeaway
A constant R (0.95 in position, 0.85 out of position) treats nut hands and weak draws alike and ignores stack depth. Raises become R = 1 once "committed", but calls never get that treatment. This asymmetry biases the bot toward jamming over calling in low-SPR spots. A per-sample "showdown pot" model captures implied and reverse-implied odds at almost zero cost. A fitted R table is the simpler fallback.

### Cited Findings
- `r_base` = 0.95 (button) or 0.85. It is 1.0 only on the river or when the call is all-in (`to_call >= stack or opp_stack == 0`) — [bot/policy.py:23-24, 78-81](bot/policy.py). For raises, R = 1 when `added >= stack or (stack - added) < 0.6 * called_pot` — [bot/policy.py:106-107](bot/policy.py). Calls have no such commitment test.
- Consequence: facing a preflop 4-bet to 54 (pot 72, to_call 36, 62 behind), the bot jammed 228/300 hands, folded 72 and never called — [exp2.py](scratchpad/exp2.py). Calling would leave 26 behind in a 108 pot (SPR 0.24), yet call EV is discounted 15%: about 0.15·0.42·108 ≈ 6.8 chips for a 42%-equity hand. Here jamming is probably fine, because the opponent cannot fold getting 26 to win 134. The same asymmetry applies to flop calls in 3-bet pots, where the raise alternative is not equivalent.
- `commit_spr = 0.6` misses the single-raised-pot structure. After a flop pot bet (called pot 36, 62 behind), 62 < 0.6·36 is false, so a raise is treated as uncommitted (R = 0.85). In fact a pot raise there goes to 60 of 74 (my arithmetic from [game.py:428](game.py)).

### Inferences
- **Option A (recommended, ~0.5-1 day, ~0.05 ms):** a per-sample showdown-pot model. Return `hero_final` and `opp_final` from `_batch` (already computed; [bot/equity.py:57-58](bot/equity.py)) and rank them among the samples. For each sample, if both final hands are strong (both above the ~70th percentile), assume an extra bet of `min(stack_after, β·pot)` per player goes in (β ≈ 0.5-1; tune β), else no extra. Then `EV_call = Σ w_i [win_i (P + 2X_i) - (to_call + X_i)] / Σ w_i`. Nut draws gain value (implied odds) and second-best hands lose value when both get there (reverse implied odds, which matter a lot in Omaha where flush-over-flush and higher straights are common). Stack depth enters through `stack_after`, so commitment comes out of the model. Keep a small multiplicative R (about 0.95 OOP) only for "folded out" equity, or fit it.
- **Option B (~0.5 day + harness logging):** fit R(street, IP/OOP, SPR bucket, equity bucket) from self-play logs, regressing realized chip result on `eq·pot`. Use it as a lookup table. Cheaper to run, but it can't separate nut from non-nut hands of equal equity.
- Either way, add the commitment test to the call branch (R = 1 when `stack - to_call < commit_spr · (pot + to_call)`). That is about 1 line and removes the call/jam asymmetry.

### Gaps
- β and the strength threshold for Option A are unmeasured. I did not run a harness A/B of any realization variant.

---

## Q4. Preflop: behaviour in 3-bet/4-bet/all-in spots at 40bb, and is a precomputed push/call chart worthwhile?

### Takeaway
Preflop the bot is nearly always-raise: 299/300 SB hands are opened and 299/300 hands raise against a limp. Facing raises it mostly calls or re-raises, and it never flats a 4-bet. Most of the error is in the fold/re-raise model (Q1), not in equity accuracy. A precomputed table of equity against the top x% (x ∈ {10, 20, 30, 50, 100}) is still worth building. It removes preflop MC noise and frees 0.5-3.4 ms per preflop decision for postflop use, and it gives the Q1 tree exact band equities.

### Cited Findings
- Node behaviour with prior opponent stats (300 random hands per node, max_samples 1536) — [exp2.py](scratchpad/exp2.py):
  - SB unopened (pot 3): RAISE_POT 155, RAISE_HALF 144, CHECK_CALL 1
  - BB vs limp: RAISE_HALF 242, RAISE_POT 57, CHECK 1
  - BB vs open to 6: CALL 227, FOLD 65, RAISE 8
  - BB vs half-pot open to 4: CALL 290, FOLD 2, RAISE 8
  - SB vs 3-bet to 18: CALL 170, RAISE_POT (to 54) 109, FOLD 21
  - BB vs 4-bet to 54: jam 228, FOLD 72, CALL 0
- Preflop equities in this game are compressed: hands at the 5th and 95th percentile have 0.389 and 0.589 equity vs random, and only 0.319 vs 0.455 against a top-15% range — [exp5.py](scratchpad/exp5.py). So the prior fold rate (0.375) and realization dominate the open decision. The formula's open EV for a bottom-5% hand (+0.39 raise vs +0.48 limp) is within noise of 0.
- The existing table `preflop.npz` stores only equity vs random (`EQ`) and its percentile (`PCT`) for all 376,992 hands — [bot/preflop.py](bot/preflop.py). Preflop rollouts cost 0.50 ms per 256 samples and 3.4 ms per 1536, the most expensive street — [exp1.py](scratchpad/exp1.py).

### Inferences
- **Precomputed range-equity table:** for each of the 376,992 hands, store equity against the top-x% ranges, x ∈ {5, 10, 15, 20, 30, 50, 70, 100}. At ~200 samples per cell this is roughly 600M evaluations, about 20-30 minutes offline at the measured ~0.5M samples/s per core. Stored as uint8 it is about 3 MB. At runtime, interpolate on the modelled cut (0 ms, no noise). Under the soft-sigmoid weighting a hard top-x% is an approximation. Effort: half a day (the build script mirrors `dev/build_preflop_table.py`).
- Worth it mainly as an enabler: exact band equities (fold/call/re-raise bands in Q1) and freed time. A hand-built push/call chart alone wouldn't fix the leak, because the bot's problem is believing opponents fold to re-raises. Against a known jam range, the call threshold is simple pot odds: e.g. BB with 18 in facing an 80 jam needs eq ≥ 62/160 = 38.75% against the jam range, and the table lookup supplies that equity.
- Opening ~100% from the SB is exploitable by any bot that 3-bets light (see Q1 example A). With the tree in place, the open range should shrink naturally against 3-bet-heavy opponents. Against nits it may correctly stay wide.

### Gaps
- No measurement of the bot's preflop node frequencies after adaptation against each zoo bot (only priors and the jammer/exploiter logs).

---

## Q5. Mixed strategies and predictability: is deterministic argmax exploitable?

### Takeaway
Yes. Postflop the bot's checks are capped: in 0% of measured flop/river checks and 0-2% of turn checks did the bot hold equity above 0.6. It bets everything strong and overfolds to bets (58-72%). An adaptive bettor can profit by betting whenever the bot checks. exploiter.py does not yet exploit this (the bot still wins +2.1 to +2.4 bb/deal against it), but a stronger adaptive field bot could.

### Cited Findings
- Final choice is `max(evs, key=evs.get)` with no randomization — [bot/policy.py:112](bot/policy.py).
- Postflop unopened decisions vs exploiter.py: flop checks n=131 (mean eq 0.33, max 0.54), bets n=116 (mean 0.63, min 0.34); turn checks max eq 0.60; river checks max 0.52, bets min 0.59. Similar against stabber.py (flop check max 0.54, river bet min 0.59) — [exp6.py](scratchpad/exp6.py).
- Fold-to-single-bet rates vs exploiter: flop 58%, turn 66%, river 72% — [exp4.py](scratchpad/exp4.py).
- exploiter.py adapts its bluff frequency to the bot's fold-to-raise rate (`bluff_freq = (folder-0.3)*2`) and bets draws whenever checked to — [dev/sparring/exploiter.py](dev/sparring/exploiter.py). The bot still won +2.41 bb/deal [+1.12, +3.71] against it — [h1.txt](scratchpad/h1.txt).

### Inferences
- **Trap fraction:** OOP on flop/turn with eq ≥ ~0.75, check with probability ~15-25%. The lookahead (Q1) can price this properly if it models opponent bet-when-checked-to frequency, a new stat. Cost ~0 ms, effort 2-4 hours.
- **Noise-aware randomization:** choose uniformly (or softmax) among actions whose EV is within ~1-2 SE of the best, with SE from the weighted sample variance. This uses the existing MC noise deliberately instead of by accident. ~0 ms, 1-2 hours.
- **Self-MDF guard:** track our own fold-to-bet rate per street and size. When it exceeds 1 - MDF + margin (e.g. > 55% vs pot bets) against an opponent who bets a lot, lower the call threshold. Effort 2-3 hours.

### Gaps
- I did not write a dedicated "bet-whenever-checked-to" exploiter to measure how much these capped ranges actually lose.

---

## Q6. Monte Carlo noise: decisions near indifference flip. Variance reduction?

### Takeaway
Range weighting cuts the effective sample size to 16-50% of samples drawn, so equity standard errors are 0.018-0.032 even at the 1536 cap. 25-37.5% of flop facing-bet spots flip their decision across reruns. Exact river enumeration costs about 1 ms (plus ranking), so river noise can be removed completely. Common random numbers across actions are already implicit, because all actions share one sample set.

### Cited Findings
- Decision stability, 40 flop spots facing a pot bet, 30 reruns each: with 256 samples, 37.5% of spots had at least one flipped decision (mean minority-action frequency 11.6%; equity SD 0.046). With 1536 samples, 25% of spots flipped (6.6%; SD 0.020) — [exp1.py](scratchpad/exp1.py).
- Effective sample fraction `(Σw)²/Σw²/N`: BB vs open 0.50, SB vs 3-bet 0.47, BB vs 4-bet 0.27, flop vs bet 0.25, turn vs barrel 0.16. Implied equity SE at 1536 samples is ≤0.018, 0.019, 0.025, 0.025 and 0.032 respectively — [exp8.py](scratchpad/exp8.py). On a flop call into a 36-chip pot, an SE of 0.025 is about 0.025·0.85·36 ≈ 0.77 chips of EV noise.
- Batch cost (256 / 1536 samples): preflop 0.50 / 3.42 ms, flop 0.47 / 2.70 ms, turn 0.49 / 2.55 ms, river 0.21 / 1.38 ms — [exp1.py](scratchpad/exp1.py).
- Exact river enumeration of all C(26,5) = 65,780 opponent hands (per-pair best score over the 10 board triples, then max over each hand's 10 pairs, via a precomputed 65,780×10 index table) takes 0.99 ms. The test hand's equity was 0.0920 exact vs 0.0924 ± 0.0075 by 1536-sample MC. `_rank_pct` over 65,780 hands takes 3.05 ms, so it should be replaced by a cheaper rank (`np.unique` over a few hundred distinct scores, or `searchsorted` on the sorted scores) — [exp7.py](scratchpad/exp7.py).
- All actions are scored from the same `win`/`w` arrays, so EV differences between actions already share samples (common random numbers) — [bot/policy.py:71-109](bot/policy.py).

### Inferences
- **River:** exact enumeration with cheap ranking, about 1.5-2.5 ms total. Zero sampling noise on the street with the biggest pots. Effort: half a day.
- **Adaptive sampling:** after the first 256 samples, compute the EV gap between the top two actions and its SE. Continue to 1536-4096 samples only if gap < 2·SE and the pot is ≥ ~10 bb, otherwise stop early. Most decisions settle at 256. exp4 showed 50-58% of decisions have an EV gap under 0.5 chips, though many of those are harmless RAISE_HALF vs RAISE_POT near-ties.
- **Range-targeted sampling (importance sampling):** preflop, sample opponent hands directly from the PCT-sorted hand list restricted to the modelled range, which restores ESS ≈ 1. Better still, use the Q4 table and skip preflop rollouts. Postflop, oversample hands with high `opp_pct` after preflop raises, or stratify the turn/river cards (each remaining card equally often).

### Gaps
- The flip-rate test used prior-only opponent stats, and only the flop facing-bet node.

---

## Q7. Time usage: where would extra compute buy the most EV?

### Takeaway
The bot uses about 1.5-3.3 s of the 8 s bank per half. That is because `max_samples = 1536` caps sampling, while `timebank.budget` would allow far more. The spare ~4-5 s per half should go to rivers (exact enumeration), close or high-pot spots (adaptive sampling) and the cheap lookahead.

### Cited Findings
- Harness, 500 deals × 2 seeds: average decision 3.31 ms, p99 6.2-6.7 ms. Thinking per half: 3.25 s (exploiter), 2.47 s (tag), 1.53 s (jammer); average 2.42 s of 8 s — [h1.txt](scratchpad/h1.txt). Decisions per hand ranged from 1.15 (jammer) to 2.66 (exploiter) — [exp4.py](scratchpad/exp4.py).
- Budget = min(15 ms, 0.5 × bank left / expected decisions left). The harness charges `elapsed - 1 ms` per call — [bot/timebank.py:14-48](bot/timebank.py), [dev/harness.py](dev/harness.py) `Player._call`. The rollout stops at `max_samples` = 1536 regardless of budget — [bot/policy.py:31,71-73](bot/policy.py).

### Inferences
- Priority order for spare time: (1) river exact enumeration (+1-2 ms on ~5-15% of decisions); (2) adaptive extra samples on close turn and flop decisions in pots ≥ 10 bb (+1-3 ms on perhaps 20-30% of decisions); (3) the Q1 tree and the Q2/Q3 extra opponent runouts (+0.2-0.5 ms everywhere). The Q4 preflop table saves 0.5-3.4 ms on ~40-50% of decisions, which more than pays for (1)-(3). Keep SAFETY_FRACTION 0.5, because an opponent that forces ~4 decisions per hand would roughly double demand and the tournament CPU speed is unknown.

### Gaps
- No timing on the tournament CPU. Per-decision costs above are from this machine.

---

## Q8. Bugs and edge cases (raise_to equal amounts, all-in clamps, min_raise, fold when to_call == 0), verified against game.py

### Takeaway
No action-legality bugs were found: the rules are handled correctly, and `safety.legalize` backs them up. The real bugs are statistical: the fold-to-raise estimate is biased upward, and frequencies are pooled across very different nodes.

### Cited Findings
- **Fold when to_call == 0:** game.py lists FOLD only when `_to_call > 0`; policy adds FOLD only if it is legal; `safety.legalize` maps FOLD to CHECK_CALL otherwise — [game.py:433-440](game.py), [bot/policy.py:84-85](bot/policy.py), [bot/safety.py](bot/safety.py). Correct.
- **raise_to equal amounts:** `_raise_to` clamps to `min(max(target, min_raise_to), pot_raise_to, all_in_to)`, so HALF and POT can coincide (min-raise or all-in clamp). Policy iterates POT first and skips duplicate totals, so ties go to RAISE_POT — [game.py:424-431](game.py), [bot/policy.py:98-102](bot/policy.py). Correct. `min_raise_to` is unused by the policy, which is fine because `raise_to` already includes it.
- **All-in clamps:** raises are illegal when the opponent is all-in or we can't more than call (`stacks[seat] > to_call`) — [game.py:410-416](game.py). `opp_add = min(total - opp_bet, opp_stack)` is correct. Stacks reset to 80 every hand, so a raise can never exceed what the opponent can call. game.py has no uncalled-bet refund (the winner takes the whole pot, nets = received - contributed), but equal stacks make that moot — [game.py:30, 600-609](game.py).
- **Tie-break across actions:** dict insertion order is CHECK_CALL, FOLD, then raises, so an exact call/fold tie calls — [bot/policy.py:83-112](bot/policy.py). Harmless.
- **Bug, fold-to-raise counting bias:** `observe` counts a non-fold answer to our raise only if we get another decision afterwards. Calls that end the hand (river calls, calls of all-ins) are never counted, but folds always are (`hand_end`) — [bot/opponent.py:62-76](bot/opponent.py). Measured over 500 deals: true fold rate 0.239 vs bot estimate 0.267 (exploiter); 0.347 vs 0.411 (jammer); 0.216 vs 0.239 (stabber). In each case 46-75 faced raises went uncounted — [exp6.py](scratchpad/exp6.py). Fix: in `hand_end`, when `we_raised_last` and the hand went to showdown, count a faced-raise call. About 1 hour of work.
- **Pooling:** `pf_raise_freq` mixes first-in raises with re-raises, and `post_raise_freq` mixes leads, stabs and check-raises. `fold_to_raise` mixes steals with 4-bets — [bot/opponent.py](bot/opponent.py). This drives the Q1 jammer failure.
- **RAISE_HALF:** fold rate is fixed at 0.85× the pot-raise rate with an identical continuing range and `eq_call`, and `called_pot` differs only through `added` — [bot/policy.py:108](bot/policy.py). A smaller raise should face a wider calling range, which raises our `eq_call`. That is not modelled.
- **Panic mode** (bank < 0.6 s): `deadline = now`, so exactly one 256-sample batch runs (about 0.2-0.5 ms) — [bot/policy.py:69-70](bot/policy.py), [bot/timebank.py:17,37-38](bot/timebank.py). Fine.

### Inferences
- None of the edge cases risks illegal actions or forfeits. The statistics fixes (unbiased counting, node-split stats) are cheap and are prerequisites for the Q1 tree.

### Gaps
- I did not audit `agent.py`, `safety.py` beyond `legalize`/`fallback`, or the demon bot.
