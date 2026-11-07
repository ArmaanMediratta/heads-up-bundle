# Omaha Poker: Mathematics, Combinatorics and Probability

Method note: few rigorous Omaha math sources are on the open web, and many search hits were low-quality SEO or mirror pages, which I discarded. To fill the gaps I checked many figures by exact enumeration or Monte Carlo in Python, using my own 5-card evaluator with the Omaha rule of exactly 2 hole cards plus 3 board cards. Sanity check: the same evaluator gives Hold'em AA vs random = 84.7% over 6k trials, against the accepted 85.2%, so it agrees within Monte Carlo error. The scripts were in a temporary scratch directory (not committed) (comb.py, low.py, ev.py, pre.py, post.py, post2.py, fin.py). Below, "[Own computation]" refers to these scripts. Exact (enumerated) results are labeled "exact". Monte Carlo (MC) results are labeled with their trial counts. At 8k trials the standard error is about ±0.5 percentage points (pp); at 30k it is about ±0.3pp.

## Q1. How many starting hands are there (PLO4, PLO5, PLO6), and how many 5-card hands does each player make at showdown?

### Takeaway
PLO4 has C(52,4) = 270,725 starting combos, which reduce to 16,432 suit-isomorphic classes. PLO5 has 2,598,960 combos and 134,459 classes. PLO6 has 20,358,520 combos and 962,988 classes. Hold'em has 1,326 combos and 169 classes. At showdown an Omaha player must use exactly 2 hole cards and 3 board cards, so a 4-card hand makes C(4,2) x C(5,3) = 6 x 10 = 60 five-card hands. PLO5 makes 10 x 10 = 100 and PLO6 makes 15 x 10 = 150. A Hold'em player makes C(7,5) = 21.

### Cited Findings
- 270,725 four-card combinations reduce to 16,432 distinct starting hands — [PokerStrategy](https://www.pokerstrategy.com/strategy/1826); [Wikipedia 2006 mirror, "Poker probability (Omaha)"](https://wikipedia2006.classicistranieri.com/en/p/o/k/Poker_probability_%28Omaha%29_b06d.html)
- A Wikipedia user-page derivation breaks the 16,432 classes down by rank pattern. Four distinct ranks account for 10,725 classes and 183,040 combos. (Search snippet only; the page later returned 404.) — [wiki.riteme.site User:Valoem](https://wiki.riteme.site/wiki/User:Valoem/Poker_probability_(Omaha))
- PokerStrategy labels 10,725 as "starting hands with a pair". That conflicts with the Wikipedia derivation, where 10,725 is the number of classes with four *distinct* ranks. PokerStrategy also gives 234 for "two pair". Treat PokerStrategy's labels for these counts as unreliable — [PokerStrategy](https://www.pokerstrategy.com/strategy/1826) vs [wiki.riteme.site](https://wiki.riteme.site/wiki/User:Valoem/Poker_probability_(Omaha))
- Hand counts are 270,725 / 2,598,960 / 20,358,520 and class counts are 16,432 / 134,459 / 962,988 for PLO4 / PLO5 / PLO6, by exact combinatorics. One class covers up to 24 concrete hands — [PLOAdvisor AAxx equity page](https://ploadvisor.pages.dev/en/aaxx-equity); [PLOAdvisor PLO6 methodology](https://ploadvisor.pages.dev/en/plo6-methodology)
- I verified the counts independently. Brute-force canonicalisation over 24 suit permutations gives 16,432 (4 cards) and 134,459 (5 cards). A Burnside's-lemma orbit count gives 169 (2 cards), 16,432, 134,459 and **962,988** (6 cards), which confirms PLOAdvisor's PLO6 figure — [Own computation, comb.py / low.py]
- Hold'em comparison: 1,326 preflop combos and 169 distinct hands — [PLO Mastermind help article (search snippet)](https://intercom.help/plo-mastermind/en/articles/9895110-the-challenges-of-solving-plo)
- Exact rank-pattern distribution of PLO4 combos (out of 270,725) — [Own computation, comb.py]:
  - Four distinct ranks: 183,040 (67.61%)
  - One pair: 82,368 (30.42%)
  - Two pair: 2,808 (1.04%)
  - Trips: 2,496 (0.92%)
  - Quads: 13 (0.005%)
  - These match PokerStrategy's "pair 30.4%" and "two pair about 1%" — [PokerStrategy](https://www.pokerstrategy.com/strategy/1826)
- Exact suit-pattern distribution of PLO4 combos — [Own computation, comb.py]:
  - Single-suited (2-1-1): 158,184 (58.43%)
  - 3-1 (three of one suit): 44,616 (16.48%)
  - Double-suited (2-2): 36,504 (13.48%)
  - Rainbow (1-1-1-1): 28,561 (10.55%)
  - Monotone (4 of one suit): 2,860 (1.06%)
- PokerStrategy gives about 13.5% double-suited, which matches. It also gives "single-suited about 75%", which matches only if the 3-1 and 4-suited shapes are counted as "suited" (58.4 + 16.5 = 74.9%), and about 10% rainbow — [PokerStrategy](https://www.pokerstrategy.com/strategy/1826)
- Probability of being dealt aces in PLO4 (exact): exactly two aces 6,768/270,725 = 2.50%, at least two aces 2.57%, at least one ace 28.1%, three aces 0.071%, four aces 1 in 270,725 — [Own computation, comb.py]
- PLOAdvisor gives the share of hands with a pair of aces as 2.57% (PLO4), 4.17% (PLO5) and 6.08% (PLO6). Its share of hands with two aces plus four broadway cards is 0.266% / 0.129% / 0.054% — [PLOAdvisor](https://ploadvisor.pages.dev/en/aaxx-equity)
- The showdown rule of exactly two hole cards plus three board cards gives 60 five-card combinations per PLO4 player — [Own computation; standard rule, e.g. Wikipedia Omaha hold 'em](https://en.wikipedia.org/wiki/Omaha_hold_%27em)

### Inferences
- PLO4 has about 97x as many isomorphic classes as Hold'em (16,432 vs 169), and PLO6 has about 5,700x. This is one reason preflop charts in PLO are heuristic rather than memorised hand by hand.
- The forced "exactly 2 from hand" rule matters. A player holding one card of a suit with four of that suit on the board has no flush. A board of quads or trips plays differently too. The 60 combinations mean hands are far more connected to the board than in Hold'em.

### Gaps
- I could not retrieve the full Wikipedia table of the 16,432 classes broken down by shape (16 rank shapes x suit shapes); the mirror returned 404.

## Q2. What are the typical preflop equity matchups, and why do they run closer than in Hold'em?

### Takeaway
Preflop equities in PLO are much closer than in Hold'em. In Hold'em, AA is about 85% against a random hand. In PLO, the best hand (AAKK double-suited) is only about 65–71% against a random hand, depending on source, and only about 59–66% against good double-suited rundowns. Sources disagree here. PokerStrategy says 65.5% for AAKKds vs random. My simulation gives about 70.4–71.3%, and an unreliable stats page gives 72.5%. I believe the ~70% figure is correct (see below).

### Cited Findings
- PokerStrategy: AAKK double-suited vs a random hand is a 65.5% favourite (65.17% win plus 0.33% split), against about 85% for aces in Hold'em — [PokerStrategy](https://www.pokerstrategy.com/strategy/1826)
- A statistics roundup gives AAKKds vs random as 72.5%. It is unsourced and low quality — [Gitnux (search snippet)](https://gitnux.org/poker-hands-statistics/)
- A search snippet attributed to PLO.Academy/PLOAdvisor says AsAhKsQh vs random is about 68.92% in PLO4, 63.81% in PLO5 and 62.10% in PLO6. On fetch, the PLOAdvisor page showed percentile rankings rather than equities, so these figures are unverified — [PLOAdvisor (search snippet)](https://ploadvisor.pages.dev/en/aaxx-equity)
- **My preflop Monte Carlo results, heads-up all-in to the river.** The "same suits" or "different suits" note says whether the opponent's suits overlap with the AAKK hand's suits — [Own computation, pre.py / chk.py]:

| Matchup | Equity (hero / villain) | Trials |
|---|---|---|
| AsAhKsKh vs random | 70.4 / 29.6 (71.3 at 8k) | 30k |
| AsAhKdKc (rainbow) vs random | 65.3 / 34.7 | 10k |
| AsAhKsKh vs 2 random hands (3-way) | 54.2 / 22.7 / 23.2 | 8k |
| AsAhKsKh vs JsTh9s8h (same suits) | 65.6 / 34.4 | 8k |
| AsAhKsKh vs JdTc9d8c (different suits) | 61.3 / 38.7 | 8k |
| AsAhKsKh vs 7d6c5d4c (different suits) | 59.1 / 40.9 | 8k |
| AsAhKdQd vs JcTc9h8h (AA single-suited vs ds rundown) | 55.2 / 44.8 | 8k |
| AsAhJdTc vs KsKhQdJc (AA vs KK, ds both) | 73.9 / 26.1 | 8k |
| AsAhKdQc vs KsKh7d2c (AA blocking KK) | 83.1 / 16.9 | 8k |
| AsAdKcQh (rainbow AAKQ) vs random | 64.2 / 35.8 | 8k |
| AsKsAh2d (AA, single-suited A) vs random | 65.4 / 34.6 | 8k |
| AsAh2c2d (aces plus deuces, ds) vs random | 63.6 / 36.4 | 8k |
| AsAh7d2c (aces, ds, junk) vs random | 61.7 / 38.3 | 8k |
| KsKhQsQh vs random | 69.2 / 30.8 | 8k |
| JsTh9s8h vs random | 56.6 / 43.4 | 8k |
| 9s8h7s6h vs random | 51.2 / 48.8 | 8k |
| 2s2h2d7c (trips plus junk) vs random | 21.9 / 78.1 | 8k |

- Suit structure is worth about 5pp for AAKK vs random: 70.4% double-suited vs 65.3% rainbow — [Own computation]
- PokerStrategy's 65.5% sits very close to my AAKK *rainbow* result (65.3%) and to my AAKKds vs JT98ds same-suit result (65.6%). PokerStrategy may have mislabelled the matchup. The figure "AAKKds ~65% vs JT98ds" cited from Card Player's calculator supports this reading — [bandarpokeronline PLO guide (low-quality, search snippet)](https://bandarpokeronline-xyz.pages.dev/plo-strategy.html); [Own computation]
- AA is worth far less with more hole cards. AsAh with suited broadway (AAKQJT ds) ranks in the top 0.18% / 0.12% / 0.02% of hands in PLO4 / 5 / 6. AsAh7s2h34 (aces suited to junk) ranks top 0.53% / 2.19% / 6.14%. Rainbow aces with junk rank top 4.53% / 26.59% / 52%. These are 6-max playability rankings: the PLO4 and PLO5 orderings come from ProPokerTools files, and PLO6 is PLOAdvisor's own — [PLOAdvisor](https://ploadvisor.pages.dev/en/aaxx-equity)

### Inferences
- Equities converge because each hand makes 60 five-card hands, against 21 in Hold'em. "Random" four-card hands almost always hold some draw or pair potential, and domination is rare unless cards are blocked (as in the AA vs KK matchup where the AA hand holds a king: 83%).
- The worst hands are those with trips or quads, plus disconnected rainbow cards. Trips kill a hand's own outs (2s2h2d7c is only about 22% vs random).
- The often-repeated line "the best PLO hand is only about 65% vs random" is probably about 5pp low for AAKKds. The figure fits rainbow AAKK or the matchup against JT98ds better. The report should flag this conflict.

### Gaps
- I could not access ProPokerTools or OddsOracle output directly, so the canonical AAKKds-vs-random figure is not confirmed by a primary calculator source.
- I found no reliable PLO5 or PLO6 equity table beyond the unverified AAKQ snippet.

## Q3. What are the postflop equities for wraps, nut flush draws, sets vs wraps and combo draws, and how well do the rules of 4 and 2 work?

### Takeaway
A four-card hand can hold up to 20 clean straight outs (a "wrap") on a rainbow flop, such as JT76 on 9-8-2. Big wraps are *favourites* over sets on rainbow flops: a 20-out wrap is about 54% against top set, and about 60% against top set when the wrap also has a flush draw. Overpairs are crushed by big wraps: AA vs a 20-out wrap is 25.6 / 74.4. The rule of 4 overstates large draws in Omaha. With 20 outs the true chance of hitting by the river is 69.7%, against the rule's 80%.

### Cited Findings
- Straight-out counts on the flop (exact, counting turn cards that complete a straight) — [Own computation, post.py]:
  - JsTh7d6c on 9-8-2 rainbow: **20 outs**, from ranks Q, J, T, 7, 6, 5 (the classic 20-out wrap)
  - On 9-7-2, the maximum for any four-card rank set is **17 outs**, from T-8-6-x (here T-8-6-2)
  - On 8-6-2, the maximum is 20 outs, from 9-7-5-4
  - **13-out wraps**, for example QJT8 on 9-7-2, JT87 on 9-6-2, KQT9 on J-8-2, JT98 on 7-6-2, 9865 on 7-4-2 and QJ98 on T-7-2. For comparison, an open-ended straight draw in Hold'em has 8 outs.
- Exact flop equities, heads-up to the river (enumerating all 946 turn/river runouts) — [Own computation, post2.py]:

| Flop | Hand A | Hand B | A / B equity |
|---|---|---|---|
| 9h8c2d | 9s9dKc4h (top set) | JsTh7d6c (20-out wrap) | 45.6 / 54.4 |
| 9h8h2d (two-tone) | 9s9dKc4h (top set) | JhTh7d6c (20-out wrap plus flush draw) | 39.9 / 60.1 |
| 9c7h2d | 9s9dKc4h (top set) | QsJhTd8c (13-out wrap) | 57.9 / 42.1 |
| 9h8c2c | 2s2dKc4h (bottom set) | JsTh7d6c (20-out wrap) | 45.6 / 54.4 |
| 9h8h2d | 9s9dKc4h (top set) | AhQh5c3d (nut flush draw only) | 72.9 / 27.1 |
| 9h8c2d | AsAdKc4h (overpair) | JsTh7d6c (20-out wrap) | 25.6 / 74.4 |
| 9c7h2d | AsAdKc4h (overpair) | QsJhTd8c (13-out wrap) | 44.6 / 55.4 |
| 9hQc8d | JsTh5d4c (nut straight) | 9s9dKc3h (set) | 62.2 / 37.8 |
| 9h4h2s | AhKs5h3d (nut flush draw) | QhJh7c6d (lower flush draw) | 79.0 / 21.0 |
| KhQc2d | KsQd5c4h (top two pair) | 2s2dJc8h (bottom set) | 21.8 / 78.2 |

- A set needs redraws to hold against a made straight. A set facing the nut straight is still 37.8%, because it fills up on about 10 outs (7 board-pairing cards plus 1 card for quads, and more with runner-runner) — [Own computation]
- Exact hit probabilities from flop to river with 45 unseen cards, compared with the "rule of 4" — [Own computation, using 1 − C(45−outs,2)/C(45,2)]:
  - 9 outs: 36.4% (rule of 4 gives 36%)
  - 13 outs: 49.9% (rule gives 52%)
  - 17 outs: 61.8% (rule gives 68%)
  - 20 outs: 69.7% (rule gives 80%)
  - These are draw-completion odds, not equity. Many Omaha outs are "dirty", meaning they complete the draw but pair the board or make a better hand for an opponent.
- PokerStrategy gives a flop example (J987ds on K-Q-T) showing how equity varies by what the opponent holds: Axxx with a flush draw 46.92%, a set with any kickers 54.99%, AJxx 27.75%, a set plus a higher flush draw 26.54%. The extraction did not make clear which side each percentage belongs to — [PokerStrategy](https://www.pokerstrategy.com/strategy/1826)
- Exact flop probabilities — [Own computation, fin.py]:
  - One pocket pair in a four-card hand flops a set or better: 12.23%. In Hold'em the figure is 11.76%.
  - A two-pair hand (for example KKQQ) flops at least one set: **23.43%**. PokerStrategy says "21%", which conflicts with this — [PokerStrategy](https://www.pokerstrategy.com/strategy/1826)
  - A suited two-card subset flops a made flush: 0.95%. A double-suited hand flops one: 1.91%.
  - A suited two-card subset sees two or more of its suit on the flop (flush draw or better): 12.7%.

### Inferences
- Because draws routinely hold 13 to 20 outs and often combine with flush draws, the "made hand vs draw" calculation from Hold'em flips in PLO. Bottom or top set on a coordinated, rainbow flop can be an *underdog* to a wrap. This is the core reason for "draw to the nuts" thinking.
- Players should replace the rule of 4 with exact tables when they have 15 or more outs, and should discount outs that pair the board.

### Gaps
- I found no online source that publishes a canonical "wrap outs" table, such as the full 13/16/17/20-out wrap list (Hwang lists these in *Pot-Limit Omaha Poker: The Big Play Strategy*, which I could not access). I did not verify the 16-out wrap shape.

## Q4. How often is each hand type, including the nuts, needed to win at showdown?

### Takeaway
I found no published dataset. My simulation shows the winning hand is much stronger in Omaha than in Hold'em at the same number of players. With 6 random hands dealt to the river in PLO, the winner holds a straight or better 78% of the time, and a full house or better 31%. In 6-handed Hold'em the winner holds a straight or better about 40% of the time.

### Cited Findings
- I found no published breakdown of PLO showdown winners by hand class. An arXiv paper separates absolute frequency from showdown frequency for generalised poker, but it is not specific to PLO — [arXiv 2511.06145](https://arxiv.org/pdf/2511.06145v1)
- Practitioner sources note that PLO needs stronger hands to win at showdown than NLHE, and that the gap between the nuts and the second nuts can be large, but they give no figures — [PokerTraining.com](https://www.pokertraining.com/poker/blog/when-the-second-nuts-in-plo-is-a-river-fold/)
- Distribution of the best (winning) hand class, all hands to the river with no folding — [Own computation, fin.py]:
  - **PLO, 2 players (6k trials):** high card 0.1%, pair 10.6%, two pair 32.9%, trips 12.6%, straight 18.1%, flush 12.2%, full house 12.0%, quads 1.2%, straight flush 0.2%
  - **PLO, 6 players (3k trials):** pair 0.2%, two pair 11.0%, trips 10.9%, straight 25.0%, flush 21.9%, full house 27.4%, quads 3.0%, straight flush 0.6%
  - **NLHE, 6 players (4k trials):** pair 16.1%, two pair 30.4%, trips 13.7%, straight 17.5%, flush 10.6%, full house 10.4%, quads 1.0%, straight flush 0.2%
- Probability that a low is possible on a random 5-card board is about 60% (see Q6) — [Wikipedia](https://en.wikipedia.org/wiki/Omaha_hold_%27em); [Own computation]

### Inferences
- In multiway PLO pots, any straight or flush that is not the nuts is often beaten. The winning-hand distribution moves up by roughly two hand classes compared with Hold'em at the same player count.
- These are no-fold baselines and overstate showdown strength relative to real play, where weaker hands fold. Real-database "W$SD by hand class" data would be the primary source, and I found none.

### Gaps
- I found no hand-history-database statistics (for example from PokerTracker samples) on how often the nuts is shown down in PLO.

## Q5. What point systems and starting-hand rankings exist, and what are their limits?

### Takeaway
Edward Hutchison's point count (Canadian Poker Monthly, December 1997) is the best-known heuristic. Its total score is meant to approximate a hand's percent chance of winning a 10-handed showdown. The online versions I found are Omaha Hi-Lo variants that award points for low-card combinations. Modern rankings use simulated equity or solver play (ProPokerTools ranking files, PLOAdvisor) rather than additive scores.

### Cited Findings
- The Hutchison scoring module scores a hand as the sum of three components: suited cards, paired cards and straight cards. The total is "roughly equivalent to the percentage chance of this turning into a winning hand in a 10 player game, where each player plays until the end." The module points to the original rules at thepokerforum.com/omahasystem.htm — [CPAN Games::Poker::Omaha::Hutchison](https://metacpan.org/pod/Games::Poker::Omaha::Hutchison)
- A blog repost of the Hi-Lo version, "slightly modified from Dec 1997 Canadian Poker Monthly", gives these values — [Poker Coimbra blog repost](https://pokercoimbra.blogspot.com/2009/01/e-tb-o-omaha-hl.html):
  - Low combinations: A-2 = 20, A-3 = 17, A-4 = 13, A-5 = 10, 2-3 = 15, 2-4 = 12, 3-4 = 11, 4-5 = 8
  - Pairs: AA = 8, KK = 6, QQ = 5, JJ = 2, TT = 1, 44 = 1, 33 = 1, 22 = 3. Trips lose half their pair points.
  - Suited, by the highest suited card: A = 4, K = 3, Q or J = 2, 8 to T = 1
  - Range 0 to 45. Play hands with 20 or more points; consider raising with 30 or more. Designed for 10-handed, low-limit games.
- Modern ranking: PLOAdvisor ranks hands by 6-max playability. Its PLO4 and PLO5 orderings come from ProPokerTools reference files, and its percentiles are simulation-based ("deeper rankings are less precise") — [PLOAdvisor](https://ploadvisor.pages.dev/en/aaxx-equity)

### Inferences
- Limits of additive point systems: they ignore interactions such as dangler cards, blockers, nut versus non-nut flush potential, position and stack depth. They also measure "equity to showdown in a 10-handed, no-fold game", which differs from realised equity in 6-max play with raising. Hand-rankings in general are range- and context-dependent: AAxx rainbow with junk drops from top 4.5% in PLO4 to top 52% in PLO6.

### Gaps
- I could not verify the original high-only Hutchison point values from a primary source; the CPAN source code and thepokerforum.com page were not retrieved. Several low-quality sites quote conflicting values, so I left them out.
- I found no authoritative "top 30 PLO hands" list online. Jeff Hwang's and Tri Nguyen's books were not accessible.

## Q6. What is the Hi-Lo specific math: chance of a low, counterfeiting and quartering?

### Takeaway
A qualifying low (8 or better) is possible on about 60.1% of random 5-card boards (exact). An A2 hand makes a low by the river only about 36.5% of the time when its other two cards are high, 49.5% with A23x, and 53.1% with A234. Being quartered turns a winning low into a net loss in a three-way pot.

### Cited Findings
- About 60% of the time a low hand is possible. A low needs three unpaired board cards of 8 or lower — [Wikipedia Omaha hold 'em](https://en.wikipedia.org/wiki/Omaha_hold_%27em)
- Exact probabilities — [Own computation, low.py]:
  - A random 5-card board contains at least 3 distinct ranks from A to 8: 1,561,728 / 2,598,960 = **60.09%**. This confirms the Wikipedia figure.
  - Given that the hero holds A2KQ, a low is possible on the board 61.78% of the time.
  - A flop with 3 distinct low ranks: 16.2%. A flop with at least 2 distinct low ranks: 62.8%.
  - The hand makes a qualifying low by the river (5-card board): A2KQ 36.52%, A23K 49.52%, A234 53.08%. 78KQ also gives 36.52%, since any two distinct low cards need the same 3 other distinct low ranks on board.
  - Counterfeit risk: with A2xx on a 3-4-9 flop, the chance the turn or river brings an A or 2 (6 such cards among 45 unseen) is 25.2%.
  - Duplicate nut lows: if the hero holds A2, the chance a given opponent also holds at least one A and one 2 is 4.38%. Against 5 opponents it is about 20.1% (assuming independence), and against 8 opponents about 30.1%. A random hand contains both an A and a 2 6.40% of the time.
- Quartering definitions: being quartered means splitting the low half with another player while a third wins the high, which leaves you with one quarter of the total pot. It typically happens when two players hold A-2. If no low qualifies, the high hand wins the whole pot — [PokerSkill glossary](https://www.pokerskill.com/poker-glossary/quartered/); [PokerNews "Outdrawn and Quartered"](https://www.pokernews.com/strategy/horse-outdrawn-quartered-omaha-hi-lo-5593.htm)
- Players who compute pot odds as if every winning showdown takes half the pot "consistently overpay rivers" — [search summary of hi-lo sources; DeucesCracked Omaha Hi-Lo](https://www.deucescracked.com/learn/omaha-hi-lo)
- Quartering arithmetic, derived from the share rules above:
  - In a 3-way pot where each player puts in 1/3, a quartered player gets back 1/4. That is a net loss of 1/12 of the pot, or −25% on their own contribution.
  - In a 4-way pot each player puts in 1/4, so being quartered only breaks even.
  - Heads-up, a player who ties the low and loses the high gets 1/4 back of a pot they put half into, a loss of 50% of their investment.
  - [Own computation from share rules]

### Inferences
- Low draws are weaker than they look. Even the "best" low start, A2, completes a low only about 37% of the time with dead high cards, so scooping requires two-way hands such as A23K double-suited. Duplicate A2 holdings are common at full tables (20–30%), which makes quartering a central EV risk.

### Gaps
- I found no source with published Omaha Hi-Lo all-in equity tables, such as A2KK ds vs random. I did not compute Hi-Lo equities because my evaluator handles high hands only.

## Q7. How does variance in PLO compare with NLHE, and what bankroll does PLO need?

### Takeaway
The standard deviation (SD) in PLO is commonly put at about 1.5–2x that of NLHE. Typical figures are about 70–100 bb/100 for 6-max NLHE and about 120–160 bb/100 for 6-max PLO. Risk of ruin scales with SD², so bankroll needs roughly double or more. One simulation needed 40 buy-ins for Hold'em but 98 for Omaha at the same win rate and 5% risk of ruin. The sources are training and affiliate sites, not large datasets.

### Cited Findings
- Online 6-max NLHE SD is about 70–100 bb/100. Moving from 90 to 140 bb/100 SD raises the required bankroll by about 142%, not 56%, because risk of ruin scales with SD². At a 3 bb/100 win rate and a 5% ruin target, Hold'em needs about 40 buy-ins and Omaha about 98 — [DeucesCracked risk-of-ruin simulation](https://www.deucescracked.com/blog/poker-risk-of-ruin-variance-simulation-study)
- PLO 6-max SD is 120–160 bb/100 and PLO full ring 100–140 bb/100 — [Habwin "Poker Variance Part 2"](https://habwin.dinacode.com/en/post/poker-variance-part-2-its-influence-on-cash-games)
- Recommended bankrolls: 30–50 buy-ins for NLHE 6-max cash, 50–100 buy-ins for PLO 6-max — [VIP Grinders](https://www.vip-grinders.com/?p=144762)
- Another site recommends adding about 50% to a Hold'em bankroll for PLO (low-quality source) — [bandarpokeronline bankroll calculator](https://bandarpokeronline-xyz.pages.dev/bankroll-calculator.html)

### Inferences
- The equity convergence in Q2 and Q3 (most all-ins land between 40/60 and 65/35) plus pot-limit dynamics that build large multi-street pots are the mechanical cause of the higher SD. The 1.5–2x multiplier implies 2.25–4x the variance (SD²).
- The ruin arithmetic checks out: (140/90)² ≈ 2.42, a 142% increase. That supports DeucesCracked's internal consistency.

### Gaps
- I found no primary large-sample dataset, such as a published database of millions of hands, giving the PLO SD. All figures come from training or affiliate sites and should be presented as rules of thumb.
- I found no reliable PLO5 variance figures.
