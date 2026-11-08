# Mirror-opponent detection and exploitation: theory, landscape and rules (HU Short Deck PLO5, 40bb, duplicate, round robin)

Context for the writer: the game is heads-up Short Deck 5-card PLO with 80-chip (40 bb) stacks that reset every hand. There are four actions (fold, check/call, half-pot raise, pot raise). A match is 1,000 duplicate deals: two 1,000-hand halves with seats swapped, each half in a fresh process with no shared memory. A team scores 1 for a win and 0 for a loss when the 95% CI of mean bb per deal lies entirely above or below 0, and 0.5 for a chop otherwise. The format is a round robin ([participant guide extraction](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/research_notes/Heads%20up%20bot%20implementation%20plan/participant_guide.md); [repo README](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/README.md)).

Source quality labels: **[PR]** is peer reviewed (AAMAS, AAAI, UAI, NIPS/NeurIPS, AISTATS, MLJ, EC/TEAC). **[Preprint]** is arXiv only. **[Informal]** covers news, blogs, GitHub and course pages. **[Repo]** means a file in this repository. Search ran 2026-11-07. Two full texts could not be fetched: Husky Hold'em's OpenReview PDF (behind a bot check) and the ACPC rules page (bad TLS certificate). Those details are listed under Gaps.

## Q1. What do AI-assistant/LLM-built poker bots typically look like, and what weaknesses recur?

### Takeaway
No one has published an audit of how Claude- or ChatGPT-written poker *bot code* is structured. The nearest evidence comes from three places:
- the starter guide's own suggested recipe, which assistants are likely to follow closely: Monte Carlo equity against a *random* opponent hand, a pot-odds comparison, simple preflop features, and frequency-count opponent stats;
- hobby repositories that implement exactly that recipe;
- studies showing that LLM-assisted code clusters around a few canonical solutions.

Bots that play directly as LLMs show systematic frequency biases: too tight preflop, over-aggressive postflop, and donk-betting. A Claude model topped the one benchmark where LLMs *write* poker bots. So in this hackathon, expect many entrants to be close cousins of each other and possibly of our own bot.

### Cited Findings
**The template LLM assistants are handed (the guide's "Strategy ideas")**
- The guide suggests these ideas [Informal/organiser doc] ([participant guide extraction, Q5](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/research_notes/Heads%20up%20bot%20implementation%20plan/participant_guide.md)):
  - "Beat the baselines first. A bot that folds weak hands, calls with decent ones and raises strong ones…";
  - "deal the missing board cards (and a random opponent hand) many times and count how often you win… Monte Carlo equity";
  - "Compare price and chances… you need to win more than 25%";
  - "Precompute simple features of your five hole cards (pairs, suited cards, connected ranks, high cards)";
  - "Position matters";
  - "track how often your opponent raises, folds or bluffs… then adapt".
- The baseline opponents shipped with the repo are `baseline_random`, `baseline_always_half`, `baseline_always_pot` and `baseline_calling_station`. Any bot tuned mainly against these learns to value-bet thin and rarely fold [Repo] (`baseline-bots/`).

**Public hobby and student bots follow the same recipe**
- The Bonobo791/Poker GitHub bot's decisions "depend on equity… calculated by a montecarlo simulation" [Informal] — [GitHub Bonobo791/Poker](https://github.com/Bonobo791/Poker)
- A developer guide for a Telegram poker bot computes hand-vs-hand Monte Carlo equity and claims about 1% accuracy at 10,000 iterations [Informal] — [DEV Community guide](https://dev.to/strazi_weekey_9d6671e9aae/building-your-own-telegram-poker-bot-a-practical-developers-guide-4b10)
- LucasColas/Poker-AI lists "Stochastic probability, Monte Carlo / Monte Carlo Tree Search, and Outs" as its agent strategies [Informal] — [GitHub LucasColas/Poker-AI](https://github.com/LucasColas/Poker-AI)
- **MIT Pokerbots 2016 MADbot (HU PLO).** Early versions ignored opponent bets and history and were "possibly too aggressive". A later version fixed a bug in the max-equity computation and swapped the evaluator for a neural net [Informal] — [GitHub suryabhupa/MADbot](https://github.com/suryabhupa/MADbot)
- **Jeremy Rubin's MIT Pokerbots IAP entry** (2nd in the new-team bracket). Equity precision "was not their bottleneck" after about 10k Monte Carlo rounds. The edge came from tracking opponent stats and adjusting aggression and looseness [Informal] — [mit.edu/~jlrubin](https://www.mit.edu/~jlrubin/projects/pokerbots)

**When LLMs write competition bots**
- Husky Hold'em Bench (NeurIPS 2025) asked frontier LLMs, through a 5-stage iterative refinement scaffold, to write Python poker bots that play a 6-player round robin. "Claude 4 Sonnet tops the leaderboard". Top models produced "balanced or aggressive" styles, and lower-ranked models produced more defensive ones [PR, NeurIPS 2025 listing] — [NeurIPS virtual page](https://neurips.cc/virtual/2025/122372); [OpenReview](https://openreview.net/forum?id=jARUSddVIB). The bots' internal structure could not be retrieved (see Gaps).
- CodeClash reuses the Husky Hold'em engine for a "write a bot that earns the most" task [Preprint] — [arXiv 2511.00839](https://arxiv.org/pdf/2511.00839)

**Homogenisation: why many entrants may look alike**
- Among correct solutions, LLM-assisted programming solutions were more semantically similar to each other than unassisted ones. They clustered around "a smaller number of canonical approaches". The sample is small, about 40 solutions [Preprint] — [arXiv 2605.13776](https://arxiv.org/pdf/2605.13776)
- Human-written solutions are more algorithmically diverse than correct LLM-generated ones [Preprint] — [arXiv 2503.00691](https://ar5iv.labs.arxiv.org/html/2503.00691)
- LLMs show a strong shared preference for Python and well-known libraries [Preprint] — [arXiv 2503.17181](https://arxiv.org/html/2503.17181v1)
- In a 36-person study, ChatGPT-assisted ideation was more homogeneous at the group level than ideation with other tools [Preprint] — [arXiv 2402.01536](https://arxiv.org/html/2402.01536v2)

**LLMs playing poker directly: frequency biases**
- PokerBench (AAAI 2025) tested 11,000 spots (1k preflop, 10k postflop). The best pre-trained model, GPT-4, scored 53.55% exact match. Pre-trained LLMs "significantly lack in their ability to play game theory optimal poker" [PR] — [PokerBench arXiv/AAAI](https://arxiv.org/html/2501.08328v2)
- GPT-4's measured biases in PokerBench's gameplay study [PR] ([PokerBench](https://arxiv.org/html/2501.08328v2)):
  - it open-raised only 15.3% preflop;
  - it 3-bet only AA, KK and AKs, with no bluffs;
  - it bet or raised 0.823 times per street on flop and turn, against 0.312 for the fine-tuned model;
  - it donk-bet in 25% of flop and turn spots.
  These come from a single 1,000-hand match, so they are directional only.
- PokerBattle.ai (Oct-Nov 2025) was nine LLMs playing $10/$20 NLHE. o3 won, Claude Sonnet 4.5 was 2nd and Grok 3rd. Reporters described the models as generally "too aggressive", calling or raising rather than folding when unsure. Llama 4 had a VPIP above 60% and busted [Informal, press] — [PokerNews](https://www.pokernews.com/news/2025/11/poker-bot-battle-results-49971.htm); [PokerListings](https://www.pokerlistings.com/news/results-of-the-first-ever-pokerbattle-ai)

**Our own bot (to judge what a mirror of it might look like)**
- `bot/policy.py` picks the action with the best estimated chip EV. Equity comes from Monte Carlo rollouts weighted toward hands consistent with the opponent's actions (soft percentile cut-offs). A raise's EV uses an estimated fold probability f and re-raise probability q, both read from the opponent's past responses. It applies equity-realisation factors (0.95 in position, 0.85 out of position) [Repo] (`bot/policy.py` docstring and PARAMS).
- `dev/zoo/` contains `equity_caller`, `maniac`, `nit` and `tag`, which are archetypes close to typical LLM bots [Repo].

### Inferences
- The modal LLM-built entrant probably looks like this:
  1. a preflop heuristic score from pairs, suits, connectedness and high cards;
  2. postflop Monte Carlo equity against a *uniformly random* 5-card hand;
  3. thresholds such as "raise if equity above X, call if equity above pot odds, else fold";
  4. possibly a VPIP/aggression counter that nudges the thresholds.
  This follows from the guide's text plus the homogenisation evidence. No direct audit exists.
- **Recurring exploitable weaknesses, inferred from that structure:**
  - *Equity vs a random hand overstates equity once the opponent has shown strength.* Such bots over-call big raises and over-stack medium hands. In PLO5 equities run close, so the "random hand" bias is large on wet Short Deck boards. Counter: value-bet larger and more often, and bluff less.
  - *Static thresholds give fixed, learnable fold frequencies.* If the bot folds whenever equity is below pot odds, its fold rate against a pot raise is predictable. Counter: probe which bet size makes it over-fold and size there.
  - *Position is often ignored.* The bot uses the same thresholds in and out of position.
  - *Postflop over-aggression and preflop tightness are likely* if the LLM's poker intuitions leak into its hand-coded thresholds. This is extrapolated from PokerBench and PokerBattle and is unverified for code-writing.
  - *Raise sizes collapse to RAISE_POT,* since many LLM templates "raise strong hands" with the maximum.
  - *Robustness bugs* such as an exception path or a time-bank overrun can hand you free forfeits. That is not something to exploit actively.
- A mirror of *our* bot would be an equity-vs-range EV maximiser. It is far less exploitable than the template bot, so mirror-detection mainly matters against *template* cousins (see Q2 and Q4).

### Gaps
- No published audit of Claude- or ChatGPT-generated poker bot source code exists. The Husky Hold'em PDF and its open-sourced bots could not be retrieved because of OpenReview's bot check. The NousResearch `huskyholdem-bench` repo is worth inspecting by hand for the actual code structure.
- No public write-up of a hackathon where most entrants used Claude to write a poker bot was found.
- Evidence that LLM *gameplay* biases carry over into LLM-*written* code thresholds is indirect only.

## Q2. Mirror and self-play matches, opponent identification, and best-responding to a known or approximately known policy

### Takeaway
In a duplicate match two identical deterministic bots score exactly 0 per deal, which under these rules is a guaranteed chop. Stochastic near-mirrors give a mean of about 0 with a CI that straddles 0, which is also a chop. Three things break the symmetry: (i) exploiting the opponent's *fixed, known* policy, (ii) asymmetric adaptation (one bot models and the other doesn't), and (iii) a strength difference. The literature says identifying an opponent from a small portfolio of known strategies, and choosing a response online, is far more sample-efficient than modelling it explicitly. Bard et al. 2013 is the key example, with Southey et al. 2005 and Hoehn et al. 2005 alongside it. Against an exactly known policy, a best response maximises winnings but is brittle. Robust or safe responses trade a little exploitation for a large cut in downside: RNR, DBR, and Ganzfried and Sandholm's safe exploitation.

### Cited Findings
**Duplicate and mirror mechanics**
- In duplicate poker, agents play a set of hands, swap seats and replay the same cards. It is used in the ACPC to cancel luck. AIVAT adds control variates and cuts the required sample size by more than 10x (about 3x lower SD) [PR, AAAI 2018] — [AIVAT, Burch et al.](https://ojs.aaai.org/index.php/AAAI/article/view/11481)
- In this event, half 2 replays "the same 1,000 deals again, with the seats swapped". The score sums both halves per deal, then takes the mean ± 1.96·SE. A CI that "includes or touches 0" is a chop [Repo/organiser] ([participant guide extraction, Q3](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/research_notes/Heads%20up%20bot%20implementation%20plan/participant_guide.md))

**Implicit modelling: identify, then pick the response from a portfolio**
- Bard, Johanson, Burch and Bowling (AAMAS 2013), "Online Implicit Agent Modelling" [PR] — [abstract page](https://webdocs.cs.ualberta.ca/~bowling/publications/b2hd-13aamas-implicitmodelling.html); [PDF](https://poker.cs.ualberta.ca/publications/AAMAS13-modelling.pdf):
  - Instead of inferring "the explicit parameters of another agent's strategy", the agent estimates the utility of a fixed portfolio of precomputed responses.
  - The portfolio was DBR responses to 13 agents from 2010 ACPC logs, pruned to 4.
  - Responses were selected with an Exp4 variant (η = 0.025, 2% probability floor) plus importance sampling, so every expert could be evaluated off-policy on every hand.
  - In 3,000-hand matches the portfolio won 732.5 mbb/h, against 368.7 for an equilibrium and 606.3 for the best single static response.
  - It would have won the 2011 ACPC total bankroll with 317 ± 5 mbb/h, against about 277 for the actual winner.
  These details are as extracted in this repo's [opponent_modelling_literature.md](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/research_notes/Bot%20weaknesses%20and%20improvement%20options/opponent_modelling_literature.md), Q1.
- In the same paper, UCB over single strategies had higher variance (CI about ±13 against ±7 mbb/h). Aggregating all opponents into one model ("Small-Static", 478.6) underperformed the portfolio [PR] — same source.
- Bard et al. (AAMAS 2015), "Decision-theoretic Clustering of Strategies", clusters opponent strategies *by the utility of responding to them*, not by raw distance. Response utility was "dramatically improved" over distance-based clustering in toy poker [PR] — [Bowling publications page](https://webdocs.cs.ualberta.ca/~bowling/publications/b2hd-15aamas-clustering.html). This is directly relevant to fingerprinting: group opponents by which counter works, not by how their statistics look.

**Bayesian opponent modelling**
- Southey et al. (UAI 2005), "Bayes' Bluff", keeps a posterior over opponent strategies using Dirichlet priors in a small poker game and an expert-informed prior in hold'em. It responds with Bayesian best response and related methods. It explicitly handles partial observability: cards are only seen at showdown [PR] — [arXiv 1207.1411](https://arxiv.org/abs/1207.1411)
- Hoehn, Southey, Holte and Bulitko (AAAI 2005; MLJ 2009 journal version) found that converging to a *maximally* exploitive strategy within a few hundred hands is impractical even in Kuhn poker. "Better than Nash or breakeven" play, however, can be reached quickly with parameter estimation or expert algorithms [PR] — [AAAI05 PDF](https://cdn.aaai.org/AAAI/2005/AAAI05-123.pdf); [MLJ 2009](https://mlanthology.org/mlj/2009/southey2009mlj-effective)

**Best response versus robust or safe response**
- Restricted Nash Response (Johanson, Zinkevich and Bowling, NIPS 2007) solves a modified game in which the opponent plays the model with probability p. p = 1 gives the best response and p = 0 gives Nash. This traces a frontier of exploitation against exploitability [PR] — [NIPS07 PDF](https://www.cs.ualberta.ca/~games/poker/publications/NIPS07-rnash.pdf)
- Data Biased Response (Johanson and Bowling, AISTATS 2009) handles incomplete or inaccurate models better than RNR. RNR "can perform poorly" when the model is wrong or missing in unobserved states [PR] — [AISTATS 2009](https://webdocs.cs.ualberta.ca/~bowling/publications/b2hd-09aistats.html)
- Ganzfried and Sandholm, "Safe Opponent Exploitation" (EC 2012; ACM TEAC 2015), characterises when deviating from equilibrium to exploit is *safe*: expected loss stays bounded relative to the equilibrium value. Roughly, you risk only what you have already won or what the opponent has gifted through mistakes [PR] — [dblp EC'12](https://dblp1.uni-trier.de/rec/conf/sigecom/GanzfriedS12.html). Later work describes it as LP-based, whole-game and limited in scale [PR, NeurIPS 2022] — [Liu et al., Safe Exploitation Search](https://proceedings.neurips.cc/paper_files/paper/2022/file/b12a1d1014e952e676f5d6931d03241a-Paper-Conference.pdf)
- Ge et al. (ICML 2024) propose safe and robust *subgame* exploitation [PR] — [PDF](https://personal.ntu.edu.sg/boan/papers/ICML24_Subgame.pdf)
- 2026 preprints on safe exploitation under showdown censoring and on confidence-scheduled restricted responses cite Ganzfried and Sandholm as the prior theory. They are unvetted [Preprint] — [arXiv 2608.09954](https://arxiv.org/pdf/2608.09954); [alphaxiv 2607.28520](https://www.alphaxiv.org/abs/2607.28520)

### Inferences
- **Why mirror results are exactly 0 here.** Suppose both bots are deterministic functions of the observation, and any RNG is seeded from the observation. Then half 2 replays half 1 with the roles swapped, and every per-deal sum is exactly 0. SE = 0 and the CI "touches 0", so the result is a chop. If the bots use unseeded Monte Carlo, the per-deal sums are small noise around 0, which is again almost surely a chop. A pure mirror therefore yields 0.5 points without any intervention.
- **What breaks symmetry:**
  1. *Adaptation asymmetry.* If we detect "this is a known template" and switch to a precomputed counter while the opponent keeps static thresholds, we gain. If the opponent is a copy of *our own* adaptive bot, both sides adapt symmetrically and the expectation stays about 0.
  2. *Information asymmetry.* Only we know our own policy exactly. Against an exact copy, a best response to ourselves is computable offline (in self-play, a best response to a fixed policy). But the copy adapts to our deviation through its own opponent model, so the gain decays.
  3. *Stochastic variance.* This only widens the CI and does not create an edge.
- **Fingerprinting from actions.** Each half is only 1,000 hands with cards seen only at showdown. The cheapest discriminating features are therefore action-frequency signatures by context, as in Bard 2015's utility-based clustering:
  - preflop open frequency on the button;
  - which raise size is used (HALF vs POT);
  - fold rate to a pot raise by street;
  - check-raise frequency;
  - response time is *not* observable.
  Showdown hands let you check "did it reach the river with a hand that equity-vs-random would play, but equity-vs-range would fold?"
- **The recommended form is a Bard-style implicit-modelling portfolio, not a hard classifier.** Keep the default strategy plus 2-4 precomputed counters (for example "vs equity-vs-random template", "vs over-folder", "vs maniac"). Mix or select them online with Exp3/Exp4-style weights and a probability floor. This degrades gracefully when identification is wrong. A related experiment file exists in this repo ([strategy_switching_experiments.md](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/research_notes/Bot%20weaknesses%20and%20improvement%20options/strategy_switching_experiments.md)).
- **Use bounded counters (RNR/DBR spirit).** For example, only loosen value-betting and tighten bluffing against a suspected template, rather than switching to a full best response that becomes very exploitable if the guess is wrong.

### Gaps
- No literature found specifically on "mirror matches" between near-identical *heuristic* poker bots, and no published fingerprinting accuracy figures for poker bots from action sequences.
- No PLO, or Short Deck PLO, specific results for implicit modelling. All the evidence is from limit hold'em or toy games.

## Q3. Risks: misidentification, opponents adapting back, arms races

### Takeaway
The main risks are three. (1) A false-positive identification makes us play a brittle counter against the wrong opponent. (2) Adaptive opponents, including copies of our own bot, re-exploit the counter. (3) The extra code paths add forfeit risk, where one exception loop loses the whole match. The literature's answers are robust or safe responses, portfolios with probability floors, and the observation that full exploitation needs far more hands than are available. In-match evidence must therefore be strong before deviating much.

### Cited Findings
- RNR overfits to the opponent model, needs a lot of data, and performs poorly where the model is inaccurate or has unobserved states. DBR was designed to fix this [PR] — [Johanson and Bowling, AISTATS 2009](https://webdocs.cs.ualberta.ca/~bowling/publications/b2hd-09aistats.html); [DBR slides](https://api.sambuz.com/doc/data-biased-robust-counter-strategies-ppt-presentation-159289)
- Bard et al. tuned their portfolio responses to be exploitable by only about 100 mbb/h, "to ensure that any of the responses could be used without substantial risk" [PR] — [Bard et al. 2013 PDF](https://poker.cs.ualberta.ca/publications/AAMAS13-modelling.pdf) (via [repo notes](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/research_notes/Bot%20weaknesses%20and%20improvement%20options/opponent_modelling_literature.md))
- Maximal exploitation within a few hundred hands is impractical even in Kuhn poker [PR] — [Hoehn et al. AAAI 2005](https://cdn.aaai.org/AAAI/2005/AAAI05-123.pdf)
- Safe exploitation bounds losses relative to equilibrium, so deviations are funded only by the opponent's observed mistakes [PR] — [Ganzfried and Sandholm EC'12](https://dblp1.uni-trier.de/rec/conf/sigecom/GanzfriedS12.html); [Liu et al. NeurIPS 2022](https://proceedings.neurips.cc/paper_files/paper/2022/file/b12a1d1014e952e676f5d6931d03241a-Paper-Conference.pdf)
- Five errors in a half cause a forfeit, and a forfeit loses the match "however many chips you were winning by". Crashes in `on_hand_end` are counted per hand, and hands arrive in batches [Repo] — [README §8](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/README.md)
- Memory is wiped each half, so any identification must be re-learned within each 1,000-hand half [Repo] — [README §7](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/README.md)

### Inferences
- **The misidentification cost is asymmetric under CI scoring.** Against an opponent we would otherwise beat clearly, a wrong counter can drag the mean into the chop band, losing 0.5 points. Against an opponent we would chop anyway, a correct counter can turn the chop into a win, gaining 0.5. Weight the decision threshold by how often each case occurs.
- **The duplicate format adds its own mirror wrinkle.** Our detector runs independently in both halves. If it fires in one half and not the other, the per-deal sums gain variance, which widens the CI and pushes results toward a chop. Detection rules should be stable, triggering at consistent hand counts.
- **Adapting back.** If the opponent is a copy of our bot, it also models f and q (fold and re-raise rates) from our responses. Any counter that changes our frequencies gets partly re-exploited. The result is a symmetric arms race with expectation about 0, so mirror-detection against a *true* copy is likely worthless. Its value is against *static* cousins.
- **Arms race in the codebase.** Every counter is another code path inside the 1 s/request and 8 s/half time limits. Keep counters as parameter overrides of the same policy, which is how `bot/policy.py` PARAMS already works, rather than as separate engines.
- **Keep an always-on fallback.** If the opponent's observed statistics leave the template's predicted envelope, revert to default play. This is a "safe exploitation" stop-loss.
- **Recommended guardrail settings for the switch/revert design.** Each setting is mapped to its literature basis. The numbers are starting points to tune locally, since the papers give no PLO-specific values.
  - *Bounded counter.* The counter bundle should be a modest PARAMS deviation, with its own exploitability bounded when it faces our default bot or the zoo, rather than a full best response. Basis: Bard 2013 kept each response exploitable by only about 100 mbb/h "to ensure that any of the responses could be used without substantial risk", and RNR/DBR tune exactly this exploitation-vs-exploitability trade-off ([Bard 2013](https://poker.cs.ualberta.ca/publications/AAMAS13-modelling.pdf); [Johanson et al. NIPS 2007](https://www.cs.ualberta.ca/~games/poker/publications/NIPS07-rnash.pdf)).
  - *Confidence threshold before switching.* Require at least two independent evidence types (action statistics and showdown-replay agreement) and a minimum sample size before switching. For example, at least 150-200 hands and at least 15-20 replayable showdown decisions, with replay agreement clearly above what a non-mirror template achieves on the same decisions. Calibrate the agreement threshold so the false-positive rate is at most about 5% against every `dev/zoo` and `dev/sparring` bot. Basis: Hoehn et al. show that even in Kuhn poker reliable inference takes hundreds of hands, while modest gains are possible early ([AAAI 2005](https://cdn.aaai.org/AAAI/2005/AAAI05-123.pdf)). The exact counts are my inference.
  - *Soft rather than hard switching (optional).* An alternative to a binary switch is Bard-style weighting: blend the default and counter PARAMS by an Exp3/Exp4 weight, with a floor (Bard used η = 0.025 and a 2% minimum probability) so that both stay evaluable ([Bard 2013](https://poker.cs.ualberta.ca/publications/AAMAS13-modelling.pdf)). If you keep a hard switch, add hysteresis: once reverted, do not re-switch within the same half, or only re-switch after a much higher evidence bar, to avoid flapping.
  - *Revert criterion (stop-loss).* Track bb won since the switch. Revert when the cumulative result is below about −1.5 to −2 times its own standard error (SE ≈ per-hand SD·√n), and after at least about 100 hands, so that card noise alone does not trigger it. Also revert immediately if the identifying statistics drift outside the mirror envelope. Basis: Ganzfried and Sandholm's safe exploitation risks only what the opponent's observed mistakes have "paid for" ([EC'12](https://dblp1.uni-trier.de/rec/conf/sigecom/GanzfriedS12.html)). A simple practical proxy is: never let post-switch losses exceed the pre-switch winnings plus a small margin. The thresholds are my inference.
  - *Consistency across halves.* Use deterministic trigger rules, with the same thresholds in both halves, so that the duplicate pairing is not destabilised (see the variance point above).

### Gaps
- No empirical numbers exist for false-positive rates of poker-bot fingerprinting at a 1,000-hand horizon. It would need to be measured locally against `dev/zoo` and `dev/sparring` variants.

## Q4. Competition rules on detection and exploitation vs collusion and signalling

### Takeaway
The rules explicitly allow, and even encourage, in-game opponent modelling and adaptation, so recognising and exploiting an opponent from its observed play is permitted. They prohibit interfering with "the judge, the other bot, or the machine" (disqualification). They contain no explicit clause on collusion between teams. Signalling or soft-play arrangements with other teams nonetheless fall under standard anti-collusion norms and very plausibly under "interfere with... the other bot". **Treat any deliberate cross-team signalling, handshake sequences, chip-dumping or soft-play as MUST-NOT-DO.**

### Cited Findings
- "Any approach is allowed: hand-written rules, simulations, statistics, or machine learning." [Organiser guide p.3] — [participant guide extraction](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/research_notes/Heads%20up%20bot%20implementation%20plan/participant_guide.md)
- "Model your opponent. Use on_hand_end and action_history to track how often your opponent raises, folds or bluffs (cards revealed at showdown are gold), then adapt." [Organiser guide p.13-14] — same source
- "Don't try to interfere with the judge, the other bot, or the machine. Bots that do will be disqualified." [Organiser guide p.9] — same source
- "Registering the same person on multiple teams will result in invalid registration for the whole team!" [Organiser guide p.1] — same source
- No network access during a match, and nothing carries over between halves [Repo] — [README §7-8](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/README.md)
- The guide has "no explicit statement on code sharing between teams, plagiarism… or LLM use" [Repo notes] — [participant guide extraction, Q6 Gaps](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/research_notes/Heads%20up%20bot%20implementation%20plan/participant_guide.md)
- The README's rules section (§8) covers time, startup, errors, port, plumbing, network, files, libraries and threads. A grep for collusion, signalling or soft-play wording found none [Repo] — [README](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/README.md)

### Inferences
- **Allowed:** detecting a template or mirror opponent purely from legally observed game data (`action_history`, showdown `opp_hole`, result stats) and adjusting play. This is exactly the "model your opponent… then adapt" the organisers suggest.
- **MUST NOT DO:**
  1. Agree with another team that bots will recognise each other through an action "handshake" (for example a fixed raise pattern in the first hands) and then soft-play or check down, or dump chips to boost either team's points or tie-breaker. In a round robin this changes third parties' standings. It is collusion by any poker or tournament norm and very likely "interfering with the other bot".
  2. Anything that attacks the opponent's server, timing or judge. That is explicit grounds for disqualification.
  3. Registering one person on multiple teams in order to run "sibling" bots.
- **A grey area to avoid:** deliberately embedding a *unilateral* recognition signature in our own play, meant for another team's bot to read. Even without explicit agreement, this functions as signalling. If the team wants mirror-detection, it should only *read* opponents, never *broadcast*.
- **Rules check of the design now being implemented.** The design: detect a mirror or near-mirror during a half from action stats, plus replaying the opponent's revealed showdown decisions through our own policy; switch to a counter-strategy PARAMS bundle; revert if results turn clearly negative.
  - *Inputs.* The design uses only `obs.action_history`, `HandResult.opp_hole` (given "only after a showdown") and our own results. These are exactly the sources the organisers suggest ("Use on_hand_end and action_history… cards revealed at showdown are gold, then adapt"). It is pure in-game observation, with no channel to the other bot beyond legal poker actions. **Compliant.**
  - *Output.* The switch changes only our own poker decisions, so no rule is engaged. **Compliant**, subject to the three risk flags below.
  - **RISK FLAG 1: the counter must stay competitive.** The counter bundle must be an *exploitative* strategy that tries to win chips: larger value bets, fewer bluffs into a caller, attacking fixed fold frequencies. It must never be passive or "friendly" when a mirror is detected (checking down, folding more, avoiding big pots). If the opponent is a copy running the same detector, two mutually passive counters would play like soft-play by design. That is indistinguishable from collusion and could be read as such even without any agreement. Test counter-vs-counter (our bot against a copy of itself with the detector on): both sides should still play full-strength poker, with an expected result near 0 and no drop in pot sizes or aggression.
  - **RISK FLAG 2: no broadcasting.** The detector must only *read*. Do not add deliberate probing patterns whose purpose is to be recognisable to another bot, such as a fixed raise sequence in the first N hands. Ordinary exploratory variation is fine. A designed signature is signalling. Do not share the detector's features, or the bundle, with other teams.
  - **RISK FLAG 3: robustness rather than rules.** The showdown-replay step calls our policy inside `on_hand_end`. Every exception there counts as one error, hands arrive in batches, and 5 errors forfeit the match. The replay time is also charged to the 8 s bank and the 1 s per-request limit ([README §8](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/README.md)). Wrap the replay in try/except, cap how many replays run per request, and use few or no Monte Carlo samples in the replay. Otherwise the feature can lose matches through forfeits or an empty time bank, which is far worse than any exploitation gain.
  - *Grey area, not used by this design.* Building counters offline from other teams' *public* repositories (the rules require repos to be public) is not addressed by the guide. It is not part of the current design. If considered, ask the organisers first.
- **When in doubt, ask the organisers in writing.** Note that the guide's deadline and form fields still contain placeholders, so the rules may be updated (README and game.py are the stated sources of truth).

### Gaps
- The ACPC rules page could not be fetched (TLS certificate error), so its exact wording on collusion and entries per team is not quoted here. This repo found no organiser statement specific to collusion.
- Whether organisers would view passive mirror detection as "interfering" was not addressed. Nothing in the text suggests it would be, since it uses only legal observations.

## Q5. How much is a mirror-detection feature worth vs improving general strength? ACPC analogues

### Takeaway
Under win/chop/loss CI scoring, a feature only pays where it moves a matchup across a CI boundary. Against true copies of our bot, detection is worth about 0, because the match chops by symmetry and the copy adapts back. Against *static template cousins* that we already beat, it adds tiebreak bb but few points. It only gains points against near-equal opponents where a counter raises the edge above about 0.06·SD per deal. In the ACPC, generic strength (equilibrium quality) dominated, but portfolio exploitation beat the winner by a significant margin. Exploitation therefore matters most when the field contains many exploitable, similar bots, which is plausible in an LLM-assisted hackathon.

### Cited Findings
- ACPC total-bankroll scoring ranks by average winnings against the whole field. Instant-runoff eliminates the lowest-bankroll bot each round, so it rewards not losing rather than exploiting. Being closer to Nash did not always mean winning instant-runoff events [Informal/organiser announcements and press] — [computer-poker Google group, 2017 results](https://groups.google.com/g/computer-poker/c/_f-c1ZJwK5w); [IEEE Spectrum](https://spectrum.ieee.org/champions-declared-in-ai-poker-tournament); [PokerNews 2016 ACPC report](https://www.pokernews.com/strategy/poker-ai-2016-annual-computer-poker-competition-24246.htm)
- A portfolio of exploitive responses would have won the 2011 total-bankroll event (317 ± 5 vs about 277 mbb/h), even though none of its responses were built against 2011 entrants [PR] — [Bard et al. 2013](https://poker.cs.ualberta.ca/publications/AAMAS13-modelling.pdf)
- MIT Pokerbots experience is that equity precision was not the bottleneck, and gains came from opponent-stat-driven adjustment [Informal] — [Rubin, MIT Pokerbots](https://www.mit.edu/~jlrubin/projects/pokerbots)
- The win threshold here is a mean above 1.96·SD/√1000 ≈ 0.062·SD per deal [Repo notes] — [participant guide extraction, Q3 Inferences](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/research_notes/Heads%20up%20bot%20implementation%20plan/participant_guide.md)

### Inferences
- **A worked threshold example.** Assume a per-deal duplicate-sum SD of about 10 bb (unmeasured; measure it with `dev/harness.py`). A win then needs at least +0.62 bb/deal. Against a template that our general bot already beats by several bb per deal, the counter adds no points. Against a strong cousin at +0.3 bb/deal, a counter worth +0.4 turns the chop into a win and gains 0.5 points.
- **Rough expected-value comparison.** Let N = number of opponents and p = the fraction that are "near-equal and statically exploitable by a known counter". Detection gains about 0.5·p·N·(true-positive rate) points, minus the losses from false positives. General-strength improvements raise *every* close matchup. Unless p is substantial (many near-copies of a strong shared template), general strength is the better investment.
- **The ACPC analogue.** Many ACPC entrants were variants of public CFR-style baselines. The equilibrium-like ones mostly drew against each other, and margins came from exploiting the weaker ones. The parallel in this hackathon is that LLM-built cousins are probably the "weaker ones". A modest, robust exploitation portfolio aimed at the *template archetype* is likely worth more than a detector aimed at an exact mirror of our bot. This is inference only: no source documents how many ACPC entrants were baseline variants.
- **Priority order:** (1) robustness, with zero forfeits; (2) general strength vs the zoo; (3) a bounded counter for the "equity-vs-random threshold" archetype; (4) exact-mirror detection, which is lowest value because mirrors chop by symmetry.

### Gaps
- The per-deal SD of duplicate sums for our bot is not measured in any source. It should be measured locally.
- The number of entrants, and how many are LLM-template cousins, is unknown. The guide does not state the field size.
- No public data on how many ACPC entries were baseline variants, or on how they scored against each other.
