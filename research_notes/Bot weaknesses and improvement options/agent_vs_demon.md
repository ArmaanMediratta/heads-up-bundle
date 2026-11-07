# agent.py vs demon/demon.py: head-to-head, per-opponent edges, and which demon features to port

Sources are local result files. `SP` = `/private/tmp/claude-501/-Users-armaanmediratta-Desktop-datathon-heads-up-bundle/2424e626-b048-4c5c-b38d-bbae1d4a40ae/scratchpad`. New paired experiments from this session are in `SP/avd/results_paired.txt`, `SP/avd/results2.txt` and `SP/avd/results3.txt`. They were produced by `SP/avd/paired.py`, which plays every config on the same duplicate deals (seeds `pz0..`) and gives a per-deal paired-difference 95% CI, so it is much tighter than comparing two separate CIs. The port of demon's features into agent is `SP/avd/agent_sd.py`. It monkeypatches `bot.policy` in the scratch process only, and no tracked file was changed. With `sd_use=0,defend=0` it behaves exactly like agent.py.

Config labels:
- `ab`: agent.py.
- `aboth`: agent plus sd_use=1 and defend=0.15, ported.
- `asd`: agent plus sd_use only.
- `adef`: agent plus defend only.
- `a512`: agent with max_samples=512.
- `dd`: demon default.
- `dg`: demon pinned to grinder.
- `d0`: demon with sd_use=0 and defend=0.
- `dnosd`, `dnodef`: demon with one of those two features off.
- `dclone`: demon pinned to grinder, with every parameter reset to agent's values and sd_use=defend=0.
- `dgnew`: grinder with widen=1 and fe_scale=1.
- `d256`: DEMON_SAMPLES=256.

## Head-to-head result and per-opponent edges

### Takeaway
The head-to-head is a statistical tie in every run (point estimates -0.14 to +0.30 bb/deal, all CIs include 0). Across the field demon scored 43/48 against agent's 41/48. Its edge is concentrated on jammer, flush_hunter, nit and the raise-heavy baselines. Elsewhere the two are within noise.

### Cited Findings
- **Zoo runs (3 seeds x 1000 deals, -j 1):**
  - agent.py vs demon.py scored -0.138 [-0.591, +0.315], 0-3-0. The full field was 41/48 points, 36-10-2, at 3.94 s think/half. — [zoo_agent.txt](file://SP/zoo_agent.txt)
  - demon vs agent.py scored +0.023 [-0.437, +0.483], 1-1-1. The full field was 43/48, 40-6-2, at 1.88 s think/half. — [zoo_demon.txt](file://SP/zoo_demon.txt)
- **Other head-to-head runs** were also null:
  - Leak run, agent vs demon: +0.301 [-0.172, +0.775]. — [leaks_agent_vs_demon.txt](file://SP/avd/leaks_agent_vs_demon.txt)
  - demon_lab default demon vs agent: +0.006 [-0.364, +0.376]. — [ablate.txt](file://SP/avd/ablate.txt)
  - This session, agent vs demon over 4 seeds: -0.016 [-0.384, +0.353]. — [results_paired.txt](file://SP/avd/results_paired.txt)
- **Per-opponent bb/deal, demon minus agent, from the two zoo runs (same harness and seed offsets, but not paired):**

  | Opponent | demon - agent |
  |---|---|
  | jammer | +1.45 (agent -1.95, demon -0.50) |
  | baseline_random | +1.57 |
  | baseline_always_half | +1.29 |
  | baseline_always_pot | +1.21 |
  | flush_hunter | +1.14 |
  | exploiter | +0.71 |
  | baseline_calling_station | +0.64 |
  | nit | +0.43 |
  | blind_stealer | +0.40 |
  | stabber | +0.35 |
  | tag | +0.26 |
  | mc_grinder | +0.19 |
  | maniac | +0.09 |
  | equity_caller | +0.06 |
  | trapper | -0.12 |

  — [zoo_agent.txt](file://SP/zoo_agent.txt), [zoo_demon.txt](file://SP/zoo_demon.txt)
- **Paired check this session (dd - ab).** Each opponent is listed with its seed count.

  Significant:

  | Opponent (seeds) | dd - ab |
  |---|---|
  | jammer (6) | +1.253 [+0.988, +1.518] |
  | flush_hunter (2) | +1.279 [+0.938, +1.620] |
  | flush_hunter (3) | +0.987 [+0.735, +1.239] |
  | nit (2) | +0.555 [+0.228, +0.883] |
  | baseline_always_pot (3) | +1.026 [+0.361, +1.690] |

  Not significant:

  | Opponent (seeds) | dd - ab |
  |---|---|
  | mc_grinder (2) | +0.320 [-0.244, +0.883] |
  | tag | +0.161 [-0.234, +0.556] |
  | trapper | -0.097 [-0.299, +0.104] |
  | exploiter | +0.228 [-0.472, +0.928] |
  | equity_caller | -0.031 [-0.248, +0.186] |
  | stabber | -0.119 [-0.641, +0.403] |
  | baseline_random (3) | -0.386 [-1.492, +0.720] |

  — [results_paired.txt](file://SP/avd/results_paired.txt), [results2.txt](file://SP/avd/results2.txt)
- **mc_grinder over 3 fresh seeds:** demon +1.273 against agent +0.573. The paired ab - dd was -0.701 [-1.164, -0.237]. That is significant here, but with 2 seeds it was not. — [results_paired.txt](file://SP/avd/results_paired.txt)
- **Agent's leaks vs demon:** BB position -0.065 against button +0.366 bb/deal. Folding the flop to a pot-sized bet costs -0.971 bb/deal (939 hands, 53% fold rate vs a flop pot bet). — [leaks_agent_vs_demon.txt](file://SP/avd/leaks_agent_vs_demon.txt)

### Inferences
- There is no exploitable edge either way in the head-to-head. Demon's extra ~2 field points come from bigger wins against exploitable bots, mainly jammer (a chop instead of a loss in the zoo run) and better margins vs flush_hunter and nit.
- The zoo suggested demon was +1.6 vs baseline_random, but the paired test does not reproduce it (-0.39 [-1.49, +0.72]). Treat that zoo gap as noise. baseline_random has the noisiest results of all opponents (CI about ±1 bb).

### Gaps
- The paired test did not cover maniac or blind_stealer, so their zoo deltas (+0.09, +0.40) remain unconfirmed.

## Which demon feature explains the jammer (and other) gains: sd_use and defend

### Takeaway
All of demon's edge over agent vs jammer comes from sd_use (showdown-calibrated preflop range floor) and defend (wider preflop calls vs frequent raisers), and the two reinforce each other. With both turned off, demon equals agent (+0.015). Ported into agent, the pair gives +1.34 bb/deal vs jammer and averages about +0.44 bb/deal across 14 opponents. It is significantly positive on 5 and slightly negative on trapper (-0.13).

### Cited Findings
- **Jammer, 6 seeds, paired against agent (`ab` = -1.422):**

  | Config | Diff vs ab | 95% CI |
  |---|---|---|
  | dd | +1.253 | [+0.988, +1.518] |
  | dnosd | +0.409 | [+0.232, +0.585] |
  | dnodef | +0.698 | [+0.453, +0.943] |
  | d0 | +0.015 | [-0.085, +0.114] |
  | dg (pinned grinder) | +0.940 | [+0.707, +1.172] |

  — [results_paired.txt](file://SP/avd/results_paired.txt)
- **The same features ported into agent, jammer, same deals:**

  | Config | Diff vs ab | 95% CI | Absolute (all CIs include 0 except asd/adef) |
  |---|---|---|---|
  | asd (sd_use only) | +0.632 | [+0.367, +0.897] | |
  | adef (defend only) | +0.220 | [+0.083, +0.357] | |
  | aboth (both) | +1.342 | [+1.076, +1.608] | -0.080 [-0.687, +0.526] |

  This is a superadditive effect: 0.63 + 0.22 < 1.34. — [results_paired.txt](file://SP/avd/results_paired.txt)
- **Earlier demon_lab check on 3 seeds, vs jammer:** default +0.878, pinned grinder +0.391, sd_use=0 and defend=0 -0.511. — [field.txt](file://SP/avd/field.txt)
- **Port gain, aboth - ab, across the field.**

  Significantly positive:

  | Opponent (seeds) | aboth - ab |
  |---|---|
  | jammer (6) | +1.342 [+1.076, +1.608] |
  | baseline_always_half (2) | +1.742 [+1.031, +2.453] |
  | flush_hunter (2) | +0.910 [+0.586, +1.235] |
  | nit (2) | +0.575 [+0.302, +0.847] |

  Borderline:

  | Opponent (seeds) | aboth - ab |
  |---|---|
  | baseline_always_pot (2) | +0.747 [-0.063, +1.556] |

  Not significant:

  | Opponent | aboth - ab |
  |---|---|
  | baseline_random | +0.669 [-0.618, +1.956] |
  | exploiter | +0.251 [-0.414, +0.916] |
  | mc_grinder | +0.203 [-0.347, +0.754] |
  | calling_station | +0.133 [-0.088, +0.353] |
  | stabber | +0.053 |
  | demon | +0.046 [-0.427, +0.520] |
  | equity_caller | -0.056 |
  | tag | -0.278 [-0.659, +0.103] |

  Small significant loss:

  | Opponent | aboth - ab |
  |---|---|
  | trapper | -0.134 [-0.265, -0.002] |

  — [results_paired.txt](file://SP/avd/results_paired.txt), [results3.txt](file://SP/avd/results3.txt)
- **Mechanism, from the code.**
  - sd_use mixes the frequency-based preflop cut `1 - r_pf^n` with the 20th percentile of the preflop strength of hands the opponent showed down after n preflop raises. The weight is k/(k+8) for k such showdowns.
  - defend adds `0.15 * pot * max(0, r_pf - 0.35)` to the preflop call EV.
  - Both are in `_sd_blend` / `_weights` / `_expert_evs`. — [demon/demon.py](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/demon/demon.py) lines 232-262, 296-297, 326-328
- **Fold-to-raise counting:** both bots count an opponent fold to our raise in hand_end. agent does it through `note_our_action`, demon at line 577. The known fold-count bug applies to the raise-frequency denominators only (`pf_acts`/`post_acts`), and both bots share it. — [bot/opponent.py](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/bot/opponent.py), [demon/demon.py](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/demon/demon.py)

### Inferences
- The inflated r_pf estimate (about 0.99 vs a true 0.30 for jammer) makes agent assume jammer's preflop raises are top-tier hands. sd_use replaces that with the floor jammer actually shows down, so it is a data-driven workaround for the fold-count bug.
- defend has a perverse interaction with the bug. It fires harder the more r_pf is overestimated, which is why it helps a lot vs jammer and always-raise baselines and does little elsewhere.
- Once "fixcount" lands, the right r_pf will already loosen the ranges. Part of the sd_use and defend gain will then overlap with fixcount (fixcount alone took jammer from -1.38 to +0.37 per the other researcher). The combined gain is untested.
- sd_use is worth keeping after fixcount because it uses actual showdown evidence. defend's 0.35 threshold was set against biased r_pf values and should be re-tuned or dropped after fixcount.
- The trapper loss (-0.13) is small but real. Likely cause: trapper shows down strong hands, so sd_use tightens its range floor and agent over-folds. It is a fair price for +0.4 avg elsewhere.

### Gaps
- fixcount + sd_use + defend together was not tested within the 15-minute budget. That combination is the next experiment.
- Most field opponents got only 2 seeds. Effects under about 0.3 bb are unresolved.

## Demon's expert set, meta selector, tuned params, Q tables and online learning: help or noise?

### Takeaway
Expert switching is noise: pinned grinder and default demon are statistically indistinguishable across the field. The CEM-tuned grinder parameters alone add nothing in agent. The untrained Q tables contribute exactly zero. DEMON_ONLINE=1 Q-learning significantly hurts (-0.58).

### Cited Findings
- **Pinned experts vs agent (demon_lab, 4 seeds):** all are within noise.

  | Config | Result vs agent |
  |---|---|
  | grinder | +0.285 [-0.091, +0.660] |
  | aggressor | +0.322 [-0.086, +0.730] |
  | trapper | +0.052 [-0.284, +0.388] |
  | sheriff | -0.232 [-0.555, +0.091] |
  | default switching | +0.006 [-0.364, +0.376] |
  | defend=0, sd_use=0 | -0.236 [-0.564, +0.091] |

  — [ablate.txt](file://SP/avd/ablate.txt), [ablate2.txt](file://SP/avd/ablate2.txt)
- **Default minus pinned grinder (dd - dg)**, taken from the shared-baseline paired diffs: about +0.31 vs jammer, +0.23 vs nit, +0.15 vs flush_hunter (2 seeds) and -0.01 (3 seeds), +0.65 vs baseline_random, -0.49 vs baseline_always_pot. All others are within ±0.08. The signs are mixed and the mean is about 0. — [results_paired.txt](file://SP/avd/results_paired.txt), [results2.txt](file://SP/avd/results2.txt)
- **DEMON_ONLINE=1 vs agent:** -0.582 [-1.109, -0.054]. That is significant and worse than the default (+0.006). — [ablate.txt](file://SP/avd/ablate.txt)
- **Tuned grinder params ported into agent** (call_cut_scale 0.444, r_oop 0.889, r_ip 0.959, temp_post 0.1, max_cut 0.889, half_fold_scale 0.863), against the agent default:

  | Opponent | Tuned | Default |
  |---|---|---|
  | jammer | -1.871 | -1.865 |
  | flush_hunter | +3.443 | +3.576 |
  | baseline_random | +6.685 | +6.305 |
  | demon | +0.050 | -0.092 |

  All differences are within noise. — [port.txt](file://SP/avd/port.txt)
- **Stored data:** `demon_q.npz` holds only `expert_keys`/`expert_params`. The tuned grinder adds widen 1.08, fe_scale 1.08 and trap 0.028. The other three experts are untuned defaults. — `python3 -c "np.load('demon/data/demon_q.npz')"` on [demon_q.npz](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/demon/data/demon_q.npz)
- **dclone, a demon configured to play like agent** (agent's parameters and sd_use=defend=0, which leaves the Q residual and demon's time manager as the only differences), matches agent exactly: +0.000 [-0.109, +0.110] vs jammer (4 seeds) and -0.019 [-0.237, +0.198] vs flush_hunter (3 seeds). — [results2.txt](file://SP/avd/results2.txt)
- **widen/fe_scale:**
  - vs flush_hunter, dgnew (widen=1, fe_scale=1, with sd/defend) gives +0.957 against dg +0.994.
  - vs always_pot, it gives +1.085 against dg +1.519 and dclone +0.310 [-0.212, +0.832].
  - These are unpaired against each other, so they are indicative only. — [results2.txt](file://SP/avd/results2.txt)
- **Meta selector behaviour** (from the other researcher): greedy on an all-zero prior, no exploration, 18-87 switches per half. — task brief; counter script [meta_count.py](file://SP/avd/meta_count.py)

### Inferences
- With a zero prior and greedy argmax, the meta selector is essentially picking whichever expert's last few hands happened to win. That is noise-chasing, and the data show no consistent gain from it. Do not port it.
- If expert switching is wanted later, train the meta prior first (`demon_lab.py train`) and add exploration.
- Some of demon's flush_hunter edge without sd/defend (d0 - ab = +0.777 [+0.445, +1.109]) is not explained by tuned params (port.txt) or by the time manager (dclone ≈ agent). It probably comes from non-grinder experts being picked sometimes vs flush_hunter. sd/defend in agent (aboth +0.91) already captures most of the +1.0-1.3 total, so chasing the rest is low priority.
- widen 1.08 and fe_scale 1.08 may help vs always_pot (dg beats dgnew by about 0.4), but this is unconfirmed.

### Gaps
- There is no paired CI for dd - dg directly (only through the common baseline). Meta switch counts vs each opponent were not re-measured.
- widen/fe_scale were not tested inside agent.

## Time manager and sample count: does demon's ~1.9 s/half cost accuracy, or is agent wasting time?

### Takeaway
Agent is wasting time. A demon set up to play like agent, using demon's time manager (~1024 samples, 9 ms cap, about 0.8 s/half), plays exactly like agent (about 1.8 s/half). Agent capped at 512 samples is no worse, and it costs almost nothing against the bank because each decision then fits under the 1 ms grace. Below that there is a cost: demon at 256 samples lost 0.5 bb/deal vs mc_grinder.

### Cited Findings
- **dclone vs agent:** +0.000 [-0.109, +0.110] vs jammer, spending 0.78 s against 1.76 s. The flush_hunter run was -0.019 [-0.237, +0.198], 1.31 s against 3.07 s. — [results2.txt](file://SP/avd/results2.txt)
- **a512 vs ab:** -0.039 [-0.516, +0.437] vs demon. Vs mc_grinder (3 seeds), a512 - dd = -0.530 and ab - dd = -0.701, which makes a512 about +0.17 vs ab (noise).
  - Measured bank spend for a512 was 0.00-0.03 s/half, against 2.3-3.3 s/half for the default 1536.
  - A direct timing check over 300 hands vs mc_grinder gave a512 0.025 s charged (0.83 s wall), against 0.765 s charged (1.57 s wall) for the default. — [results_paired.txt](file://SP/avd/results_paired.txt); timing check run inline this session
- **d256 vs dd, mc_grinder, 3 seeds:** -0.507 [-0.956, -0.059]. — [results_paired.txt](file://SP/avd/results_paired.txt)
- **Budget settings:**
  - Agent: `MAX_DECISION=0.015`, `SAFETY_FRACTION=0.5` of the remaining bank, `max_samples=1536`. — [bot/timebank.py](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/bot/timebank.py), [bot/policy.py](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/bot/policy.py)
  - Demon: `TARGET_FRACTION=0.62`, `MAX_DECISION_S=0.009`, `MAX_SAMPLES=1024`, plus a no-rollout emergency path below 0.5 s. — [demon/demon.py](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/demon/demon.py) lines 463-506
- **Zoo spend:** agent averaged 3.94 s/half (max 5.66 s vs always_pot); demon 1.88 s/half (max 3.35 s). — [zoo_agent.txt](file://SP/zoo_agent.txt), [zoo_demon.txt](file://SP/zoo_demon.txt)

### Inferences
- Lowering agent's max_samples to 512-1024 costs no measurable EV and roughly halves or more its bank use. That gives a large safety margin on a slower or shared tournament CPU, where agent's 5.7 s peak out of 8 s is a real timeout risk.
- 256 samples is too few.
- The extra margin could instead fund features (for example opponent modelling) rather than more rollouts.

### Gaps
- 768 and 1024 were not swept in agent, and a512 had only about 3-4 seeds, so a cost under 0.3 bb cannot be ruled out.
- A slower-CPU run (`--bank 4`) was not done.

## Recommendations (port / drop)

### Takeaway
Port sd_use and defend into agent: about +0.44 bb/deal field average, +1.34 [+1.08, +1.61] vs jammer, and neutral head-to-head vs demon. Cut agent's sample cap to about 1024 (512 also looked free). Drop the meta selector, the extra experts, the untrained Q tables and online learning. Re-test defend once fixcount is in.

### Cited Findings
- **Port sd_use (SD_QUANTILE 0.2, SD_TRUST 8) and defend (0.15, threshold 0.35).**
  - Paired gains: jammer +1.342 [+1.076, +1.608], always_half +1.742 [+1.031, +2.453], flush_hunter +0.910 [+0.586, +1.235], nit +0.575 [+0.302, +0.847].
  - Costs: trapper -0.134 [-0.265, -0.002], tag -0.278 [-0.659, +0.103] (not significant).
  - vs demon: +0.046 [-0.427, +0.520].
  - The unweighted mean over 14 opponents is about +0.44 bb/deal. — [results_paired.txt](file://SP/avd/results_paired.txt), [results3.txt](file://SP/avd/results3.txt)
  - Of the two, sd_use is the bigger single feature (+0.632 [+0.367, +0.897] vs jammer); defend alone gives +0.220 [+0.083, +0.357]. — [results_paired.txt](file://SP/avd/results_paired.txt)
- **Reference implementation:** about 40 lines, wrapping `policy._weights`, the call EV and `hand_end` showdown logging, in [agent_sd.py](file://SP/avd/agent_sd.py). For production, put the showdown percentile list in `bot/opponent.py` and the blend and defend terms in `bot/policy.py` rather than using the scratch file's `max` shim.
- **Drop:**
  - the meta selector and the aggressor/trapper/sheriff experts (no significant gain; ablate2 pinned experts are all within ±0.33 with CIs spanning 0);
  - the Q-lens tables (zero effect, dclone = agent);
  - DEMON_ONLINE (-0.582 [-1.109, -0.054]);
  - the tuned grinder params (no gain in agent, per port.txt). — [ablate2.txt](file://SP/avd/ablate2.txt), [ablate.txt](file://SP/avd/ablate.txt), [results2.txt](file://SP/avd/results2.txt), [port.txt](file://SP/avd/port.txt)
- **Time:** set `max_samples` to about 1024, or 512, and optionally adopt demon's emergency no-rollout path. No accuracy loss was detected (dclone +0.000 [-0.109, +0.110]; a512 -0.04 [-0.52, +0.44]). — [results2.txt](file://SP/avd/results2.txt), [results_paired.txt](file://SP/avd/results_paired.txt)

### Inferences
- Suggested order:
  1. fixcount (other researcher: +1.75 vs jammer).
  2. sd_use. It still adds showdown evidence after fixcount.
  3. Re-tune or test defend under fixcount. Its benefit depends on an inflated r_pf, and it may become neutral or harmful once r_pf is correct.
  4. Lower max_samples.
- Expected combined field gain is roughly +0.3 to +0.5 bb/deal average. The gain on jammer is likely smaller than additive because fixcount and sd_use target the same range error.
- After porting, agent should match or exceed demon's field results (demon's edge was entirely explained by sd/defend, plus a small unexplained flush_hunter residual) while staying simpler.

### Gaps
- The fixcount + sd_use + defend combination is untested. Every port estimate above is measured against current agent.py, which still has the fold-count bug.
- No zoo-style W-C-L points tally was run for aboth, so the effect on tournament points (as opposed to bb/deal) is extrapolated.
