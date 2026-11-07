# Strategy switching by opponent statistics: in-repo experiments

All numbers come from in-process duplicate matches I ran on 2026-11-07 (judge-like scoring: each deal played twice with seats swapped, fresh memory every half, 1000 deals per match, 95% CI with z = 1.96). I wrote the scripts and kept the raw data in the scratchpad at `/private/tmp/claude-501/-Users-armaanmediratta-Desktop-datathon-heads-up-bundle/2424e626-b048-4c5c-b38d-bbae1d4a40ae/scratchpad/ssw/`:
- `sweep.py` runs agent.py configs against opponents. It uses `dev/harness.py`'s `Player` and logs per-hand nets for each half plus snapshots of `memory['opp']` at hands 25/50/100/200/400/999.
- `analyze.py` gives per-cell means with pooled CIs and paired (same deals) differences against the default config.
- `classify.py` runs a nearest-centroid opponent classifier.
- `bandit.py` runs a Thompson-sampling simulation on bootstrapped hand results.
- `demon_meta.py` counts how often demon switches experts.
- Raw JSONL files: `base.jsonl` (default config, 16 opponents, seeds h0-h3), `grid.jsonl` (6 variants, 5 opponents, seeds h0-h1) and `confirm.jsonl` (the best variant from the screen against default, on fresh seeds h4-h7).

The parameter variants. All are harness `agent.py@k=v` overrides of the `PARAMS` in `bot/policy.py`; defaults are r_ip .95, r_oop .85, max_cut .9, call_cut_scale .6, half_fold_scale .85, commit_spr .6.
- **loose**: max_cut .75, call_cut_scale .4
- **tight**: max_cut .97, call_cut_scale .85
- **rhi**: r_oop .95, r_ip 1.0
- **rlo**: r_oop .75, r_ip .88
- **passive**: half_fold_scale .6, commit_spr 1.2
- **aggr**: half_fold_scale 1.0, commit_spr .3

Units: "bb/deal" is the harness metric (both seats of one duplicate deal combined). "bb/hand" is one hand in one half, which is about half of bb/deal.

## Q1. Upper bound: how much does the best per-opponent parameter set gain over the default (the "oracle" gain)?

### Takeaway
The default config only fails to WIN against five of the 16 opponents (jammer, mc_grinder, nit, demon, equity_caller). Against those five, the best of six parameter bundles gains about +0.3 to +0.4 bb/deal at most, and only two of those gains held up on fresh seeds: aggr vs mc_grinder (+0.36) and passive vs jammer (+0.29). Over a 16-opponent field that is worth about +1 to +1.5 W-C-L points. Jammer stays a net loss under every variant, which shows that the jammer problem is structural (see the stats bug in Q2), not a matter of parameters.

### Cited Findings
- **Default agent.py baseline** (4 seeds x 1000 deals, bb/deal [95% CI], W-C-L). It wins every match against the 4 baselines, maniac, blind_stealer, exploiter, flush_hunter, stabber, tag and trapper, by +1.2 to +11.9 bb/deal. The weak spots:
  - jammer: -1.84 [-2.64, -1.05], 0-2-2
  - demon: -0.06 [-0.47, +0.35], 1-3-0
  - mc_grinder: +0.75 [+0.24, +1.26], 0-4-0
  - equity_caller: +0.39 [+0.21, +0.57], 2-2-0
  - nit: +1.12 [+0.70, +1.53], 3-1-0

  — [base.jsonl via analyze.py](/private/tmp/claude-501/-Users-armaanmediratta-Desktop-datathon-heads-up-bundle/2424e626-b048-4c5c-b38d-bbae1d4a40ae/scratchpad/ssw/base.jsonl)
- **Screening grid** (seeds h0-h1, paired difference vs default on the same deals, bb/deal [95% CI]):
  - jammer: passive +0.30 [+0.04, +0.55]; aggr +0.12; rlo +0.12; rhi +0.07; loose +0.03; tight -0.06. Every variant still loses about 1.7 to 2.1 bb/deal and lands 0-1-1.
  - mc_grinder: aggr +0.41 [-0.11, +0.92] (0-2-0 became 2-0-0); rlo +0.12; rhi +0.05; loose -0.05; passive -0.10; tight -0.22.
  - nit: rlo +0.20 [-0.06, +0.45]; tight +0.12; loose +0.12; passive -0.06; aggr -0.34 [-0.60, -0.09]; rhi -0.34 [-0.64, -0.04].
  - demon: rhi +0.51 [-0.28, +1.30]; loose +0.39; aggr +0.24; tight -0.14; rlo -0.33; passive -0.40 [-1.14, +0.34].
  - equity_caller: passive +0.24 [+0.01, +0.46]; rhi +0.23 [+0.04, +0.42]; tight +0.11; rlo +0.07; aggr 0.00; loose -0.02.

  — [grid.jsonl via analyze.py](/private/tmp/claude-501/-Users-armaanmediratta-Desktop-datathon-heads-up-bundle/2424e626-b048-4c5c-b38d-bbae1d4a40ae/scratchpad/ssw/grid.jsonl)
- **Fresh-seed confirmation** of each opponent's screen winner (seeds h4-h7, 4 x 1000 deals, paired vs default). These figures avoid the winner's curse.
  - mc_grinder aggr: +0.36 [+0.005, +0.72]. Default 3-1-0 (+1.13) became 4-0-0 (+1.49).
  - jammer passive: +0.29 [+0.09, +0.48]. Default 0-2-2 (-1.35) became 0-4-0 (-1.06).
  - nit rlo: +0.02 [-0.20, +0.23]. 2-2-0 both ways, so the screen result did not replicate.
  - demon rhi: +0.38 [-0.18, +0.93]. 0-4-0 both ways.

  — [confirm.jsonl via analyze.py](/private/tmp/claude-501/-Users-armaanmediratta-Desktop-datathon-heads-up-bundle/2424e626-b048-4c5c-b38d-bbae1d4a40ae/scratchpad/ssw/confirm.jsonl)
- **Pooled over 6 seeds** (screen plus confirmation, slightly optimistic because of selection), W-C-L points:
  - mc_grinder aggr: +0.38 [+0.08, +0.67]; 4.5/6 → 6/6.
  - jammer passive: +0.29 [+0.14, +0.45]; 1.5/6 → 2.5/6.
  - nit rlo: +0.08 [-0.09, +0.24]; 5/6 → 5/6.
  - demon rhi: +0.42 [-0.03, +0.87]; 3/6 → 3/6.

  — [all.jsonl](/private/tmp/claude-501/-Users-armaanmediratta-Desktop-datathon-heads-up-bundle/2424e626-b048-4c5c-b38d-bbae1d4a40ae/scratchpad/ssw/all.jsonl)
- **The best set really does depend on the opponent.** aggr helps against mc_grinder (+0.36 to +0.41) but hurts against nit (-0.34 [-0.60, -0.09]). rhi helps against demon and equity_caller but hurts against nit (-0.34). passive helps against jammer and equity_caller but trends negative against demon (-0.40). — [grid.jsonl](/private/tmp/claude-501/-Users-armaanmediratta-Desktop-datathon-heads-up-bundle/2424e626-b048-4c5c-b38d-bbae1d4a40ae/scratchpad/ssw/grid.jsonl)
- **Structural fixes beat any parameter set against jammer.** A separate concurrent experiment in the shared scratchpad, which I did not run or check, tested `variant.py@fixcount=1,commit=1`. Its fixes count unseen opponent folds and treat jammer's re-raises as all-in commitments. It reports jammer +0.41 [+0.16, +0.65], 1-9-0, against agent.py's -1.38, 0-6-4. — [sweep_jammer.txt](/private/tmp/claude-501/-Users-armaanmediratta-Desktop-datathon-heads-up-bundle/2424e626-b048-4c5c-b38d-bbae1d4a40ae/scratchpad/sweep_jammer.txt); [variant.py](/private/tmp/claude-501/-Users-armaanmediratta-Desktop-datathon-heads-up-bundle/2424e626-b048-4c5c-b38d-bbae1d4a40ae/scratchpad/variant.py)

### Inferences
- Realistic oracle upside from parameter switching is about +0.3 to +0.4 bb/deal on 2 to 4 of the 16 opponents. In points, roughly +0.5 from mc_grinder (CHOPs turned into WINs) and +0.5 to +1 from jammer (LOSSes turned into CHOPs), so about +1 to +1.5 points per 16 matches with perfect identification. The 11 opponents we already beat by more than 1 bb/deal gain nothing in points.
- Jammer is insensitive to range parameters (loose, tight and max_cut moved the result by at most 0.06 bb/deal) because the biased raise frequency (Q2) makes the range cut-off 1 - r^n about 0.01-0.03, so max_cut never binds. Fixing the model has more upside than switching parameters.
- With six variants and five opponents (30 comparisons), I expect one or two false "significant" screen results. The nit rlo result that did not replicate is an example. Treat any per-opponent mapping as unproven until it is confirmed on fresh seeds.

### Gaps
- The grid was small: six bundles, two screening seeds. I did not tune single parameters (temp_pre, temp_post alone) or try combined bundles, so the true oracle gain may be somewhat larger.
- equity_caller passive/rhi (+0.23) was not checked on fresh seeds.
- I did not run the opponents in sparring/zoo that the default already crushes through the grid, because there are no points left to gain there.

## Q2. Which observable stats separate the opponents, and after how many hands?

### Takeaway
agent.py's three memory['opp'] rates plus "postflop actions per hand" identify the 16 known bots with 80% accuracy at hand 25, 89% at hand 50 and 98% at hand 100 (leave-one-half-out nearest centroid). The clusters that need different parameters (jammer, grinder-like, nit-like, stations) are clear by hand 50. One caveat matters: the preflop raise frequency is biased upward, because the opponent's preflop folds are never seen.

### Cited Findings
- **Opponent stats at hand 50 → hand 999**, mean over 8 halves, Beta priors as in `bot/opponent.py` (pf raise freq / post raise freq / fold-to-raise):
  - jammer: 0.84/0.53/0.45 → 0.99/0.92/0.44, but only about 4 postflop actions by hand 50 and 58 by hand 999.
  - mc_grinder: 0.57/0.27/0.44 → 0.61/0.26/0.43.
  - nit: 0.32/0.16/0.54 → 0.39/0.13/0.57.
  - demon: 0.54/0.40/0.30 → 0.63/0.50/0.26.
  - equity_caller: 0.04/0.02/0.29 → 0.00/0.00/0.26.
  - trapper: 0.06/0.25/0.48 → 0.00/0.30/0.48.
  - tag: 0.42/0.14/0.34 → 0.40/0.14/0.33.
  - maniac: 0.71/0.69/0.05 → 0.70/0.72/0.00.
  - calling_station: 0.04/0.01/0.04.
  - always_pot: 0.93/0.89/0.06.
  - flush_hunter: 0.29/0.24/0.46.
  - stabber: 0.45/0.72/0.26.

  The between-half standard deviation of each rate is about 0.02 to 0.10 at hand 50 and 0.01 to 0.05 at hand 200. — [base.jsonl via analyze.py](/private/tmp/claude-501/-Users-armaanmediratta-Desktop-datathon-heads-up-bundle/2424e626-b048-4c5c-b38d-bbae1d4a40ae/scratchpad/ssw/base.jsonl)
- **Nearest-centroid classification**, 16-way, 128 halves. Features: pf rate, post rate, fold-to-raise, and post_acts/hand.
  - hand 25: 0.80. Errors: nit vs flush_hunter or mc_grinder, flush_hunter vs tag, demon vs exploiter.
  - hand 50: 0.89. Errors: mostly nit vs flush_hunter and blind_stealer vs random/exploiter.
  - hand 100: 0.98.
  - hand 200: 0.98.

  — [classify.py](/private/tmp/claude-501/-Users-armaanmediratta-Desktop-datathon-heads-up-bundle/2424e626-b048-4c5c-b38d-bbae1d4a40ae/scratchpad/ssw/classify.py)
- **Bias in the counting.** `opponent.observe` only runs on our turn and resets its cursor whenever hand_index changes. An opponent's fold ends the hand before our next turn, so that action is never counted. pf_raise_freq is therefore really "raises / non-fold actions". That is why jammer reads 0.99 although it folds about 70% of hands. — [bot/opponent.py lines 45-63](/Users/armaanmediratta/Desktop/datathon/heads-up-bundle/bot/opponent.py)
- **How policy.py uses that rate.** It sets the range cut-off to min(1 - r_pf^n, max_cut), so a rate of about 0.99 means almost no range narrowing for raises. — [bot/policy.py line 52](/Users/armaanmediratta/Desktop/datathon/heads-up-bundle/bot/policy.py)

### Inferences
- Identification is not the bottleneck: by hand 50 to 100, the stats place an opponent in one of a few action-relevant clusters:
  - "preflop jammer": pf ≥ 0.8 and few postflop actions per hand.
  - "solid grinder": pf 0.5-0.65, post 0.2-0.35, fold-to-raise 0.4-0.47 (mc_grinder).
  - "nit / passive-tight": fold-to-raise ≥ 0.5, post ≤ 0.2.
  - "station": pf and post < 0.1.
- demon (0.54/0.40/0.30) sits close to exploiter and tag at hand 25 to 50. Telling it apart reliably takes about 100 hands.
- Fix the fold-counting bias before building a classifier on these stats. Otherwise the features (and the policy's ranges) will keep shifting once the bug is fixed.
- The classifier was fit and tested on the same 16 bots. Accuracy against unknown tournament bots will be lower, so it should default to the base parameters when the nearest centroid is far away.

### Gaps
- Stats were logged only under the default config. Our own play changes fold-to-raise (it depends on our raise sizes), so a switched config could move an opponent's features.
- I did not test generalisation to bots outside the zoo.

## Q3. How noisy are per-hand chip results, and how many hands would a bandit need?

### Takeaway
Per-hand results are far too noisy for a reward-driven selector to separate arms whose gaps are 0.1 to 0.2 bb/hand within a 1000-hand half. That would take tens of thousands of hands per arm. A Thompson-sampling simulation over 7 arms picked the best arm at about chance rate (14-20%) and recovered only 0-25% of the oracle gain.

### Cited Findings
- **Per-hand standard deviation**, single half, bb/hand: demon 16.1, mc_grinder 14.4, jammer 21.2, nit 10.7, equity_caller 6.6, tag 10.7, trapper 8.1, maniac 25.5, always_pot 31.2. Duplicate pairing does not cut per-deal noise much: the per-deal standard deviation of (seat1 + seat2)/2 is 5.9 to 25.6 bb. — [base.jsonl via analyze.py](/private/tmp/claude-501/-Users-armaanmediratta-Desktop-datathon-heads-up-bundle/2424e626-b048-4c5c-b38d-bbae1d4a40ae/scratchpad/ssw/base.jsonl)
- **Standard deviation of the per-deal paired difference** between a variant and default on identical deals (this is the best case, since an online bandit cannot replay deals): 11.6 bb (mc_grinder aggr), 6.2 (jammer passive), 6.6 (nit rlo), 17.9 (demon rhi). — [all.jsonl](/private/tmp/claude-501/-Users-armaanmediratta-Desktop-datathon-heads-up-bundle/2424e626-b048-4c5c-b38d-bbae1d4a40ae/scratchpad/ssw/all.jsonl)
- **Required sample size**, n per arm = 2(1.96σ/Δ)²:
  - σ = 15, Δ = 0.25 bb/hand: about 27,700 hands (56,000 for 80% power).
  - σ = 15, Δ = 0.5: about 6,900.
  - σ = 8, Δ = 0.25: about 7,900.

  The confirmed gaps are about 0.15 to 0.2 bb/hand, so even a perfect 50% variance reduction leaves more than 10,000 hands per arm. — [bandit.py](/private/tmp/claude-501/-Users-armaanmediratta-Desktop-datathon-heads-up-bundle/2424e626-b048-4c5c-b38d-bbae1d4a40ae/scratchpad/ssw/bandit.py)
- **Thompson sampling simulation**: 7 arms (default plus 6 variants), Gaussian posterior with a 20-pseudo-hand prior, 1000 hands, 400 runs, hands bootstrapped from that opponent's own results on seeds h0-h1. Columns are P(arm with the highest mean is chosen at the end) / gain vs always-default / oracle gain, in bb/hand:
  - demon: 0.18 / +0.03 / +0.26
  - mc_grinder: 0.20 / +0.02 / +0.20
  - jammer: 0.14 / +0.04 / +0.15
  - nit: 0.17 / -0.02 / +0.10
  - equity_caller: 0.20 / +0.05 / +0.12

  — [bandit.py](/private/tmp/claude-501/-Users-armaanmediratta-Desktop-datathon-heads-up-bundle/2424e626-b048-4c5c-b38d-bbae1d4a40ae/scratchpad/ssw/bandit.py)

### Inferences
- Chip results can only act as a coarse safety check, such as reverting to default after a large cumulative loss. They cannot select parameters. Selection has to come from features (Q2) mapped to sets chosen offline (Q1).
- Using our decision-time EV as a control variate (scoring EV rather than realised chips at all-ins and showdowns) could plausibly cut variance by a meaningful fraction. Even halving it still leaves the required n an order of magnitude above 1000.

### Gaps
- I did not measure how much variance an EV or all-in-adjusted control variate would remove. That would need per-decision EV logging, which agent.py stores only as `memory['last_eq']`.
- The bootstrap assumes hand results are independent and stationary. Adaptive opponents such as exploiter and demon break that assumption.

## Q4. Is demon.py's meta-selector and Q-lens design (and dev/demon_lab.py) a sound basis? What would a minimal robust version look like?

### Takeaway
Demon's meta-selector, as shipped, is a noise-chasing greedy rule with an all-zero prior. Despite the docstring, it switches experts 18 to 87 times per half. The Q-lens residual tables are untrained (zero), and the data file holds only expert parameters. The architecture can serve as scaffolding, but the selection logic is not sound for 1000-hand halves. A minimal robust replacement is a rule-based classifier with 3 to 4 profiles, decided around hand 75 to 100, with hysteresis and a default fallback.

### Cited Findings
- **The docstring's claim.** It says the Q tables and meta prior are all zero, "so the bot currently plays the grinder expert with online learning off". — [demon/demon.py lines 46-50](/Users/armaanmediratta/Desktop/datathon/heads-up-bundle/demon/demon.py)
- **What `_pick_expert` actually does.** It returns the argmax over (meta_sum + prior·150) / (meta_n + 150) for the current one of 27 profile cells, with META_EXPLORE = 0. `_hand_end` adds each hand's net bb to meta_sum on every hand, whether or not DEMON_ONLINE is set. With a prior of 0, any expert whose running sum in a cell goes negative loses the argmax to an untried expert sitting at 0. — [demon/demon.py lines 125-131, 425-438, _hand_end](/Users/armaanmediratta/Desktop/datathon/heads-up-bundle/demon/demon.py)
- **Measured expert usage** in one 1000-hand half, seed h0 (switches; share of hands):
  - vs agent.py: 87 switches; grinder 252, aggressor 476, sheriff 265, trapper 7.
  - vs jammer: 33 switches; trapper 630, aggressor 305.
  - vs nit: 18 switches; aggressor 926.
  - vs mc_grinder: 26 switches; sheriff 538, grinder 338.

  — [demon_meta.py output](/private/tmp/claude-501/-Users-armaanmediratta-Desktop-datathon-heads-up-bundle/2424e626-b048-4c5c-b38d-bbae1d4a40ae/scratchpad/ssw/demon_meta.py)
- **The data file.** demon/data/demon_q.npz contains only `expert_keys` and `expert_params` (grinder tuned by CEM). It has no theta_* or meta_q arrays, so the Q residual is 0 and the meta prior is 0. — [demon/data/demon_q.npz](/Users/armaanmediratta/Desktop/datathon/heads-up-bundle/demon/data/demon_q.npz)
- **Lens table sizes.** The lenses partition decisions into tabular cells: core is 4x2x10x4 = 320 cells, texture 4x10x2x2x2x4 = 1280, profile 4x3x3x3x5x4 = 2160, each with 4 actions. Each is fit on clipped (±30 bb) Monte Carlo returns minus the expert EV. — [demon/demon.py lines 137-147, _hand_end](/Users/armaanmediratta/Desktop/datathon/heads-up-bundle/demon/demon.py)
- **What demon_lab.py provides.** It has CEM tuning of one expert on common seeds, offline Q training from hand logs, and a meta prior built from dedicated per-expert matches, shrunk toward each expert's overall mean (k = 300). — [dev/demon_lab.py](/Users/armaanmediratta/Desktop/datathon/heads-up-bundle/dev/demon_lab.py)
- **Demon against default agent.py.** -0.06 [-0.47, +0.35] bb/deal over 4 seeds (agent 1-3-0), then -0.12 [-0.52, +0.28] (0-4-0) on seeds h4-h7. Effectively a chop. — [base.jsonl](/private/tmp/claude-501/-Users-armaanmediratta-Desktop-datathon-heads-up-bundle/2424e626-b048-4c5c-b38d-bbae1d4a40ae/scratchpad/ssw/base.jsonl); [confirm.jsonl](/private/tmp/claude-501/-Users-armaanmediratta-Desktop-datathon-heads-up-bundle/2424e626-b048-4c5c-b38d-bbae1d4a40ae/scratchpad/ssw/confirm.jsonl)

### Inferences
- **What is sound:**
  - Experts as parameter bundles over one shared EV model.
  - Profile features taken from running frequencies.
  - Offline CEM and meta-prior tooling that uses duplicate matches on common seeds.
- **What is not sound:**
  - Online meta learning from chip results: σ is about 15 bb/hand against arm gaps of about 0.2 (Q3), so the online meta table mostly reflects noise.
  - Spreading the meta table over 27 cells fragments the evidence further.
  - With a zero prior and greedy argmax, the rule mechanically chases losses.
  - The thousands of Q-lens cells cannot be learned online in about 2000 decisions. Even offline they need very large hand logs, and fitting them on noisy Monte Carlo returns risks overfitting to the zoo.
- **Minimal robust version (recommended):**
  1. Fix the opponent-stat counting (count unseen folds) first.
  2. Play default params until hand about 75.
  3. Classify with explicit thresholds into a small set of profiles, defaulting to default when uncertain:
     - jammer-like: pf ≥ 0.8 and postflop actions/hand < 0.15 → passive, or better a structural all-in fix.
     - solid grinder: pf 0.5-0.65, post 0.2-0.35, fold-to-raise 0.38-0.48 → aggr.
     - station: pf, post < 0.1 → passive/rhi (needs confirming).
     - default for everything else, including nits, where aggr and rhi hurt.
  4. Switch only when the same profile has been returned at checks 25 hands apart for 2 to 3 checks in a row (hysteresis), and re-check only every 100 hands.
  5. Optional guardrail: revert to default if the chosen profile's cumulative result falls more than about 3 standard errors below 0. This is a safety net, not a learner.

  Every profile-to-parameter mapping must be confirmed on fresh seeds before it ships.
- **Thompson sampling over 3 experts** using chip results (even with EV as a control variate) is unlikely to beat chance within 1000 hands, given the sample sizes in Q3. If used, it should start from a strong offline prior, such as demon_lab's meta prior, and explore very little. At that point it is close to the rule-based lookup anyway.
- **Expected value of building this:** about +1 to +1.5 W-C-L points over a 16-opponent zoo, against perfect-oracle upper bounds of +0.3 to +0.4 bb/deal on about 2 to 4 opponents. That is comparable to or smaller than the structural jammer fix reported by the concurrent experiment, which should come first.

### Gaps
- I did not run demon with `DEMON_EXPERT=grinder` pinned, so I cannot say whether its noisy switching costs it chips compared with grinder alone.
- I did not test a rule-based switching implementation end to end. Gains are inferred from fixed-config results on each opponent, assuming a correct switch by about hand 75 and that the first 75 hands are played at default.
