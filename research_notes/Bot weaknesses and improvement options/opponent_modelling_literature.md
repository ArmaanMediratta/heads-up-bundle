# Opponent modelling, exploitation and online strategy switching for a lightweight heads-up poker bot

Context for the writer: the game is Heads-Up Short Deck 5-card PLO, 40bb stacks (80 chips, BB=2) reset every hand, 4 actions (FOLD, CHECK_CALL, RAISE_HALF, RAISE_POT), raise cap of 4 per street, match = 2000 hands as 1000 duplicate deals, played as two 1000-hand halves with memory wiped between them ([repo README](file:///Users/armaanmediratta/Desktop/datathon/heads-up-bundle/README.md), `game.py`). Budget is about 2-4 ms per decision on 1 CPU. Per-hand std is about 25-30 bb (caller's figure). Most published results are for heads-up **limit Texas hold'em** (HULHE) or toy games, so transfer to PLO5 needs inference. Those inferences are labelled.

Source quality: everything cited as AAMAS, AISTATS, NIPS/NeurIPS, AAAI, UAI or ICML is peer reviewed. University of Alberta theses are reviewed by a committee, not by a venue. Poker-strategy sites and forums are non-academic and marked as such.

## Q1. Which strategy-selection approaches worked in the ACPC (implicit modelling, RNR, DBR, DBBR, safe exploitation), and what were the measured gains?

### Takeaway
The best-documented ACPC-level result is the University of Alberta's **implicit modelling** setup (Bard, Johanson, Burch, Bowling, AAMAS 2013). They built a small portfolio of robust responses (DBR) offline, then chose among them online with a modified **Exp4** that plays a *mixture* of the responses, plus importance-sampling variance reduction. Over 3000-hand matches it won about 65-100% more than a fixed equilibrium, and on the benchmark server it would have won the 2011 ACPC total-bankroll event (317 mbb/h vs 277 for the actual winner). UCB-style selection of a single strategy did worse and had higher variance. Explicit modelling online (Bayesian, DBBR) is cheap in toy games but less proven at scale.

### Cited Findings
- **Implicit modelling framework.** Instead of estimating the opponent's strategy, the agent estimates the *utility of each strategy in a fixed portfolio of pre-computed strategies*. Tested in HULHE. It "would have won the heads-up limit opponent exploitation event in the 2011 ACPC" — [Bard et al., AAMAS 2013, abstract page](https://webdocs.cs.ualberta.ca/~bowling/publications/b2hd-13aamas-implicitmodelling.html); full text [IFAAMAS PDF](https://www.ifaamas.org/Proceedings/aamas2013/docs/p255.pdf)
- **How the portfolio was built (AAMAS 2013).** They used 2010 ACPC logs for 13 agents, each with ≥8.4M full-information hands. They computed a DBR response to each agent, with DBR parameters tuned so each response was exploitable by only **about 100 mbb/h**, "kept relatively low to ensure that any of the responses could be used without substantial risk". Greedy submodular optimisation pruned the portfolio to a **4-response "Small-Portfolio"** — [Bard et al. 2013 PDF](https://poker.cs.ualberta.ca/publications/AAMAS13-modelling.pdf)
- **Bandit details.** This is a modified Exp4: it plays a softmax-weighted *mixture* of experts, and each expert's weight has a floor, so the acting strategy gives non-zero probability to every action sequence any expert would play. That floor is what makes unbiased off-policy importance-sampling estimates of *every* expert's value possible from each hand. Parameters were temperature η = 0.025 and minimum probability 2%. Performance was "largely insensitive to these parameter choices" — [Bard et al. 2013 PDF](https://poker.cs.ualberta.ca/publications/AAMAS13-modelling.pdf)
- **Variance reduction used.** They used Bowling et al.'s "imaginary observations". For each hand, they evaluated every possible opponent private holding and every early-fold opportunity consistent with the observed actions, combined with importance sampling for off-policy estimates. Early-fold imaginary observations are provably unbiased. The all-cards version has a small bias from card-removal effects but gives "substantial variance reduction" — [Bard et al. 2013 PDF](https://poker.cs.ualberta.ca/publications/AAMAS13-modelling.pdf)
- **Results against the 4 mimics (3000-hand matches, 95% CI ≤ ±7 mbb/h):**
  - Equilibrium: 368.7 mbb/h. Best single static response: 606.3. Small-Static (one DBR against an aggregate model of all four): 478.6. UCB-on-policy: 682.6. Big-Portfolio: 660.0. **Small-Portfolio: 732.5**.
  - Small-Portfolio is "nearly double" the equilibrium and beats every individual response by at least 19.9%.
  - Aggregating the opponents into one model hurt: Small-Static scored below the portfolio — [Bard et al. 2013 PDF](https://poker.cs.ualberta.ca/publications/AAMAS13-modelling.pdf)
- **UCB vs Exp4.** The UCB agent's 95% CI was about ±13 mbb/h, against ±7 for Exp4. Because UCB acts with *one* strategy at a time, it cannot evaluate the other arms off-policy without bias. The authors also argue that UCB1's regret bounds assume stochastic arms, which "may be inappropriate" in an adversarial game. Earlier work that used UCB1 over RNR portfolios or expert imitators got results that were "negative or statistically insignificant relative to a single expert" — [Bard et al. 2013 PDF](https://poker.cs.ualberta.ca/publications/AAMAS13-modelling.pdf)
- **Larger field of mimics.** Small-Portfolio beats the equilibrium by about 65%. Small-Portfolio and Big-Portfolio are within noise of each other, and both beat UCB and Small-Static — [Bard et al. 2013 PDF](https://poker.cs.ualberta.ca/publications/AAMAS13-modelling.pdf)
- **2011 ACPC benchmark server, total bankroll (mbb/h ± 95% CI).** Small-Portfolio **317 ± 5**, Big-Portfolio 290 ± 11, actual winner Calamari about 275-277 ± 4-5, Sartre about 268-272, original Hyperborean entry 224 ± 6 (3rd). Small-Portfolio won by more than the 95% margin, even though *none* of its responses were built against 2011 opponents — [Bard et al. 2013 PDF](https://poker.cs.ualberta.ca/publications/AAMAS13-modelling.pdf)
- **Restricted Nash Response (RNR).** RNR computes an equilibrium in a modified game where the opponent must play the model with probability p and is free with probability 1−p. This trades exploitation of the model against robustness when the model is wrong, and the responses are "significantly more robust" than best responses — [Johanson, Zinkevich, Bowling, NIPS 2007](https://webdocs.cs.ualberta.ca/~bowling/publications/b2hd-07nips-rnash.html). RNR is described as Pareto-optimal for the safety/exploitation trade-off but with no explicit bound, and it must be recomputed whenever the model or p changes — [Liu et al., NeurIPS 2022 (Safe Exploitation Search)](https://proceedings.neurips.cc/paper_files/paper/2022/file/b12a1d1014e952e676f5d6931d03241a-Paper-Conference.pdf)
- **Data Biased Response (DBR).** DBR fixes two weaknesses of RNR: the model is inaccurate in states never observed, and its accuracy varies across states. It trusts the model at each information set only in proportion to how much data was observed there — [Johanson & Bowling, AISTATS 2009](https://proceedings.mlr.press/v5/johanson09a.html); [slides](https://api.sambuz.com/doc/data-biased-robust-counter-strategies-ppt-presentation-159289)
- **DBBR (Ganzfried & Sandholm, AAMAS 2011).** DBBR builds an opponent model from the *deviations* between observed action frequencies and a precomputed approximate equilibrium, then best-responds in real time. The abstract reports significantly higher win rates than the equilibrium against several opponents in limit hold'em, and says the method can exploit "after only a small number of interactions" — [Ganzfried & Sandholm, AAMAS 2011 PDF](https://www.cs.huji.ac.il/~jeff/aamas11/papers/B4_R56.pdf); [DBLP](https://dblp.uni-trier.de/rec/html/conf/atal/GanzfriedS11). The text extracted from the PDF was not readable, so specific numbers were not verified.
- **Safe opponent exploitation (Ganzfried & Sandholm, 2015).** In a repeated game, an agent stays safe by risking exploitability only up to what it has already won *above the game value* in earlier rounds, so its total expected value is never below equilibrium. It computes ε-safe best responses by LP, which limits scalability — [summarised in Liu et al., NeurIPS 2022](https://proceedings.neurips.cc/paper_files/paper/2022/file/b12a1d1014e952e676f5d6931d03241a-Paper-Conference.pdf)
- **Safe Exploitation Search (NeurIPS 2022).** On Flop Hold'em, at estimation error 0.1, it was compared with a plain exploit-the-model strategy at exploitation level 1.0:
  - The plain strategy's exploitability rose from 29 to 981, and its payoff against the true opponent fell to −88.9.
  - SES kept exploitability at about 55, with payoff +3.3.
  - Lesson: naive exploitation of a slightly wrong model is catastrophic. Restricted or safe exploitation degrades gracefully — [Liu et al., NeurIPS 2022](https://proceedings.neurips.cc/paper_files/paper/2022/file/b12a1d1014e952e676f5d6931d03241a-Paper-Conference.pdf)
- **Bayesian explicit modelling.** "Bayes' Bluff" (UAI 2005) maintains a posterior over opponent strategies and approximates the required integrals by importance sampling from the prior — [Southey et al., UAI 2005](https://poker.cs.ualberta.ca/publications/UAI05.pdf)
- **Exp3 in simplified poker.** Exp3 over six pure strategies plus Nash has been used for short-term exploitation in simplified poker, framed as implicit modelling — [Hoehn et al., "Effective Short-Term Opponent Exploitation in Simplified Poker"](https://www.researchgate.net/publication/221605456_Effective_Short-Term_Opponent_Exploitation_in_Simplified_Poker); [Hoehn MSc thesis](https://poker.cs.ualberta.ca/publications/hoehn.msc.pdf)
- **Recent work (2026, preprint, not peer reviewed).** It argues that safe-exploitation guarantees "degrade exactly when the opponent model is wrong", and identifies "confirmation starvation" as a data-dependent limit of safe exploitation — [alphaXiv 2607.28520](https://www.alphaxiv.org/abs/2607.28520)

### Inferences
- **The template that transfers best:**
  - Offline, build 3-6 robust counter-strategies (e.g. anti-jammer, anti-calling-station, anti-nit, plus our base strategy), each only mildly exploitable.
  - Online, choose among them with an Exp3/Exp4-style or Bayesian rule over *opponent type*.
  - This fits a 2-4 ms budget easily: choosing the arm is O(#arms) per hand, and the arms are lookup or heuristic policies.
- Bard's gains were measured over 3000-hand matches. Our halves are 1000 hands, so expect a smaller share of the asymptotic gain, because a larger fraction of the half is spent identifying the opponent.
- The 4-arm portfolio beat the 13-arm one. Keep the portfolio small, and make each arm cover a *distinct* exploit direction.
- Robustness matters as much as exploitation. Each arm should be capped in how exploitable it is (Bard used about 100 mbb/h in HULHE, where the equilibrium earned about 370 mbb/h against the mimics). Our analogue: no arm should lose badly to a balanced or tricky opponent.

### Gaps
- Exact DBR/RNR trade-off numbers (e.g. "X% of best-response gain for Y% exploitability") could not be extracted: the AISTATS/NIPS PDFs were not text-readable through the tools.
- DBBR's numeric results and per-hand learning curves were not verified.
- No published ACPC results were found for PLO, or for any pot-limit game.

## Q2. Bandits over a portfolio: with ~1000 hands and std ~28 bb/hand, can chip results tell strategies apart, and what variance reduction helps?

### Takeaway
Raw chip results almost cannot separate strategies within 1000 hands unless the gap is several bb/hand. Over a full half, the standard error of the mean is about 0.9 bb/hand, and splitting the half across arms makes it worse. Variance reduction cuts sample needs by roughly 10-44x in published poker work. The useful forms here are AIVAT-style control variates, all-in EV adjustment, and evaluating all arms off-policy every hand. In practice, switch on fast-converging *action-frequency* signals and treat chip results only as a slow, variance-reduced sanity check.

### Cited Findings
- **AIVAT (Burch, Schmid, Moravčík, Morrill, Bowling, AAAI 2018)** is a provably unbiased, low-variance estimator. It reduces variance from chance events *and* from actions of players with a known strategy (i.e. our own).
  - In a HUNL man-machine match it cut the **standard deviation by 85%**, so the match needed **44x fewer games** for the same statistical conclusion.
  - It enabled the first statistically significant AI win over professionals in no-limit hold'em — [AIVAT, AAAI 2018](https://ojs.aaai.org/index.php/AAAI/article/view/11481); [arXiv 1612.06915](https://www.arxiv.org/pdf/1612.06915)
  - The arXiv version claims the reduction cuts hands needed by "more than a factor of 10" in no-limit poker — [arXiv 1612.06915](https://www.arxiv.org/pdf/1612.06915)
- **Imaginary observations plus importance sampling (Bowling et al.)** give low-variance on-policy and off-policy estimates. They are what let Bard's Exp4 update *every* portfolio arm from every hand — [Bard et al. 2013](https://poker.cs.ualberta.ca/publications/AAMAS13-modelling.pdf)
- **Off-policy evaluation needs a mixture.** It requires the behaviour policy to have support over every arm's actions, which is why Bard mixes experts and puts a 2% floor on each one. UCB acting with a single arm cannot do this without bias — [Bard et al. 2013](https://poker.cs.ualberta.ca/publications/AAMAS13-modelling.pdf)
- **Exp3 vs UCB.** In the stochastic setting, Exp3's short-run regret can match or beat UCB's but gets worse in the long run — [as summarised in arXiv 1110.6755](https://arxiv.org/pdf/1110.6755). UCB1 has logarithmic regret for stochastic arms; Exp3/Exp4 are built for adversarial reward sequences — [Auer et al. via Wikipedia summary](https://en.wikipedia.org/wiki/Upper_Confidence_Bound)

### Inferences
These are back-of-envelope calculations with σ = 28 bb/hand.
- **One arm for a whole 1000-hand half:** SE = 28/√1000 ≈ 0.89 bb/hand, so the 95% CI is about ±1.7 bb/hand.
- **Two arms with 500 hands each:** the SE of the difference is 28·√(2/500) ≈ 1.77 bb/hand. Only gaps of **about 3.5 bb/hand or more** reach 95% significance by the end of the half.
- **Five arms with about 200 hands each:** SE per arm ≈ 2 bb/hand. Chip-based UCB would mostly be chasing noise.
- **Where large gaps exist:** against a pure jammer, the gap between a "call wide" arm and a "fold-heavy" arm can be large (several bb/hand to 10+), so chip results *can* show it within a few hundred hands. Between subtle variations of our main strategy, they cannot.
- **Effect of variance reduction:** an 85% SD cut (σ_eff ≈ 4.2) would bring the two-arm separable gap down to about 0.5 bb/hand. Our game has no exact AIVAT, but cheap approximations exist:
  - **(a) All-in luck adjustment.** When chips go in before the river, score the hand with equity × pot instead of the realised result. Our evaluator can compute this exactly by enumerating the remaining board cards.
  - **(b) Control variate.** Use our own EV estimate at each decision as a baseline, i.e. reward = realised − (EV_at_decision − EV_prior).
  - **(c) Fold-equity imaginary observations.** Where both arms take the same action, credit both arms equally. Only the decision points where they diverge carry information.
  - Running (a) for each all-in hand is a small Monte Carlo or enumeration. It fits in the time budget only if it is limited to hands where the stacks went all-in, or computed after the hand.
- **Duplicate deals:** the match format cancels card luck *across* halves, but it gives no variance reduction for adapting *within* a half, because memory is wiped between halves.
- **Recommended structure:**
  - A Bayesian or Exp3-style selector over 3-5 arms. Its *prior* comes from fast action-frequency classification (Q4), and its update is a variance-reduced chip signal.
  - The default arm is the robust base strategy. Switch only on strong evidence: Bard's softmax had η small, and the 2% floor keeps every arm in play.

### Gaps
- No published measurement of per-hand std for short-deck PLO5 at 40bb was found; the caller's 25-30 bb is the working figure.
- No published AIVAT variant for PLO was found.

## Q3. Is online per-state Q-learning viable within 1000 hands, or should learning be offline with only opponent-type selection online?

### Takeaway
Learn offline and select online. The successful ACPC adaptive agent did all heavy computation (DBR responses, portfolio pruning) offline and adapted online only over a handful of portfolio weights. Per-state online learning faces the same σ ≈ 28 noise, spread across many states.

### Cited Findings
- Bard et al. built responses offline from millions of hands per opponent, "without the typically tight time constraints" of real-time play. Online, the problem reduces to "a utility estimation problem" over the portfolio — [Bard et al. 2013](https://poker.cs.ualberta.ca/publications/AAMAS13-modelling.pdf)
- They rejected explicit online modelling followed by a robust response as impractical at human scale. RNR must be recomputed for the whole game whenever the model changes: RNR limited to 10 CPU seconds per round failed to converge in Flop Hold'em, while the "big" version used about 190 CPU seconds per round — [Bard et al. 2013](https://poker.cs.ualberta.ca/publications/AAMAS13-modelling.pdf); [Liu et al., NeurIPS 2022](https://proceedings.neurips.cc/paper_files/paper/2022/file/b12a1d1014e952e676f5d6931d03241a-Paper-Conference.pdf)
- DBR's motivation was that frequentist models are inaccurate in states that were rarely or never observed — [Johanson & Bowling, AISTATS 2009](https://proceedings.mlr.press/v5/johanson09a.html)

### Inferences
- With the decisions in a half spread over many abstract states, most states get few visits, and each visit's chip reward has σ ≈ 28. Per-state Q-values after 1000 hands will be dominated by noise except in the 2-3 most frequent preflop nodes.
- **Viable online learning:**
  - (i) Bandit or Bayesian weights over a few offline-trained experts (the existing demon.py expert ensemble fits this).
  - (ii) Low-dimensional parameter adjustments driven by action frequencies, e.g. calling-threshold shifts against observed raise frequency.
  - (iii) A Q-learner whose state is coarse (street × facing-raise), whose actions are "which expert", and whose initial values come from a zoo trained offline.
- **Offline zoo:** self-play against a zoo of archetypes (jammer, station, nit, TAG, randomised mixtures) to pre-train each expert and the type → expert mapping. Online, only the type posterior is inferred.

### Gaps
- No peer-reviewed study was found that measures online tabular Q-learning convergence in poker within 1000 hands; the conclusion above is inferred from variance arithmetic and the ACPC design choices.

## Q4. Classifying opponents from action frequencies: how many hands, Beta priors, change-point detection

### Takeaway
Action frequencies converge far faster than chip results. A binomial frequency has SE ≤ √(0.25/n), i.e. ±5 percentage points after about 100 opportunities. Extreme styles (raise ≥ 90%) can be identified with high confidence in roughly 10-30 opportunities. Use Beta priors centred on the population or equilibrium frequencies (the DBBR idea of modelling *deviations* from equilibrium), and add a sliding-window or discounted check to catch strategy switches.

### Cited Findings
- DBBR builds the opponent model from observed action frequencies at public histories, *combined with* a precomputed equilibrium, and claims exploitation after "a small number of interactions" — [Ganzfried & Sandholm, AAMAS 2011](https://www.cs.huji.ac.il/~jeff/aamas11/papers/B4_R56.pdf)
- A Bayesian posterior over opponent strategies works in small poker games (Bayes' Bluff) — [Southey et al., UAI 2005](https://poker.cs.ualberta.ca/publications/UAI05.pdf)
- DBR's confidence weighting by observation counts is the principled way to blend a frequency model with a default — [Johanson & Bowling, AISTATS 2009](https://proceedings.mlr.press/v5/johanson09a.html)

### Inferences
- **Sample sizes** (binomial, two-sided 95%):

  | Opportunities (n) | 95% CI at p = 0.5 | 95% CI at p = 0.9 |
  |---|---|---|
  | 25 | ±0.20 | ±0.12 |
  | 100 | ±0.10 | ±0.06 |
  | 400 | ±0.05 | ±0.03 |

- **Preflop vs postflop:** preflop stats (VPIP, PFR, 3-bet) get one opportunity per hand (~1000 per half), so they become reliable by hand 50-150. Postflop node stats (fold-to-cbet, river aggression) get far fewer opportunities and need several hundred hands.
- **Priors:** Beta(α, β) with α + β ≈ 10-20 pseudo-counts, centred on the base strategy's or population frequency. This stops early-hand overreaction, and each count update is O(1).
- **Switching opponents:** in addition to the full-half count, keep an exponentially discounted count (e.g. half-life about 100 hands). Flag a change when the two disagree by more than about 2.5 SE, then reset the bandit or posterior. Discounted or sliding-window UCB are the standard non-stationary bandit variants; I did not fetch a primary source for them, so treat this as a gap.
- **Signal ranking, fastest to slowest:**
  1. Preflop action frequencies (one per hand, binary).
  2. Postflop action frequencies.
  3. Bet-sizing distributions.
  4. Showdown hand strength given an action (sparse: only hands reaching showdown).
  5. Variance-reduced chips.
  6. Raw chips (slowest, σ ≈ 28).

### Gaps
- No peer-reviewed source was found that gives specific "hands needed per HUD stat" figures. The numbers above are standard binomial arithmetic.
- No primary source was fetched for change-point detection in poker opponent modelling.

## Q5. Exploiting always-raise / jam opponents in shallow pot-limit heads-up: optimal calling vs a known wide range, without being exploited back

### Takeaway
Against a known range, the best response is simple pot-odds arithmetic: call or re-raise exactly when our equity against the opponent's *actual* range exceeds the price. A maniac's range is wide, so the profitable calling range is much wider than equilibrium. In PLO5 equities are compressed, which pushes it wider still. To stay safe, widen only as far as the evidence supports, through Beta-posterior estimates of the opponent's raise frequency, and keep the change restricted (an RNR/SES-style mix with the base strategy). The cost of being wrong is then bounded.

### Cited Findings
- In Hold'em push/fold, Nash calling ranges against an any-two-cards shover are much tighter than ATC. One (non-academic) source quotes a BB Nash call of about 2.3% (TT+) in some setting, with stack depth not stated — [ICMIZER blog](https://icmizer.com/en/blog/nash-calculator-and-nash-equilibrium-strategy-in-poker). Practical calls against a 10bb push run about 35% — [PokerStrategy forum (non-academic)](https://www.pokerstrategy.com/forum/postid/540972/). These figures are inconsistent and context-dependent; treat them as illustrative only.
- Nash ranges are unexploitable only against a Nash opponent. If one side deviates (e.g. calls too tight), the other side should widen — [PokerStrategy forum (non-academic)](https://www.pokerstrategy.com/forum/topicid/148635/)
- Naive full exploitation of a slightly mis-estimated model can raise exploitability by over 30x and turn a win into a loss. A restricted exploitation level keeps most of the gain with bounded risk — [Liu et al., NeurIPS 2022, Table 1](https://proceedings.neurips.cc/paper_files/paper/2022/file/b12a1d1014e952e676f5d6931d03241a-Paper-Conference.pdf)
- RNR gives a tunable p parameter between exploiting the model and staying robust — [Johanson et al., NIPS 2007](https://webdocs.cs.ualberta.ca/~bowling/publications/b2hd-07nips-rnash.html)

### Inferences
- **Calling rule.** Facing a bet B into a pot P (P includes the bet), calling costs C to win P + C. Call iff equity_vs_range ≥ C / (P + C).
  - Against an all-in for the remaining 40bb, the threshold is usually 40-50%, depending on how much is already in.
  - Against a 100%-raise preflop maniac, the "range" is all hands. In short-deck PLO5 most hands have 35-65% equity against a random hand, so the best-response calling or 3-betting range is roughly the top half of hands, or more.
  - Compute equity against the maniac's range (approximately a random range), not against an equilibrium jamming range.
- **Preflop sizing is fixed by the game.** In pot-limit, SB opens to 6 chips (pot), BB re-pots to 18, SB to 54, and then the 80-chip all-in. With a cap of 4 raises per street, stacks are typically in by the 3rd-4th raise. Against a maniac, the main choices are: (a) flat and play post-flop in position or out of position; (b) re-pot with the top ~40-60% to get stacks in while ahead of a random range. Option (b) cuts the opponent's post-flop fold equity and realisation edge.
- **Don't fold to aggression just because it is aggression.** Against an opponent raising about 95% of opportunities, every fold forfeits the pot. Folding equity-positive hands is the main leak.
- **Avoid being exploited back:**
  - Scale the widening by the posterior on raise frequency, e.g. use the lower 95% bound of a Beta posterior.
  - Recheck through the discounted counts (Q4) in case the opponent tightens.
  - Never widen past the threshold implied by a *mixed* range (e.g. 80% maniac / 20% value).
  - Because the arm switch is reversible, the downside is bounded by the hands it takes to detect a switch, roughly 50-100 hands by the frequency arithmetic in Q4.
- **Value over bluffs.** Against a station-maniac, bet thinly for value and stop bluffing: maniacs call too. Fold equity is low, so the exploit comes from calling down and value-raising.

### Gaps
- No peer-reviewed or solver-published equilibrium push/fold or call charts were found for short-deck PLO5 (or standard PLO). Equity percentages for PLO5 short deck in the inferences above are rough. They should be measured with the repo's `evaluator.py` by Monte Carlo.
- No academic paper specifically on countering "jammer/maniac" bots in computer poker competitions was found, beyond the general RNR/DBR/SES framework.
