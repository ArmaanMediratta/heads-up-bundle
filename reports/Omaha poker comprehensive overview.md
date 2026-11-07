# Four hole cards reshape poker's math

Omaha is Texas Hold'em with four hole cards and one strict rule: every hand is built from **exactly two hole cards plus exactly three board cards**. That rule, together with the pot-limit betting that most Omaha uses, accounts for nearly everything distinctive about the game. Equities run close together (the best starting hand wins only about 65–70% against a random hand, where Hold'em aces win about 85%). Draws can have up to 20 outs and are often favorites over sets. Showdowns need much stronger hands, and variance is roughly 1.5–2x that of No-Limit Hold'em. Pot-Limit Omaha (PLO) began at the Golden Nugget in Las Vegas in 1982–83, became the main "action" game in Britain and Ireland, hosted the biggest online pots ever recorded in 2009, and is now the second pillar of high-roller poker, with $2M+ first prizes at the 2026 WSOP and on the Triton circuit. Computationally it is a much harder game than Hold'em. Each player has **270,725 possible starting hands instead of 1,326**, no peer-reviewed superhuman PLO agent has been published, and the practical state of the art sits in commercial solvers (MonkerSolver, GTO Wizard PLO, Vision, PLO Genius) whose methods are undisclosed. For heads-up play the solver picture is unusually clear and unusually loose: the button plays about 87% of hands, and almost all of them are pot-sized raises.

## The "two-plus-three" rule drives every Omaha hand

The structure is the same as Hold'em: blinds, a button, four betting rounds, and a five-card board. Each player gets four hole cards and must use "exactly two of them, plus exactly three of the five community cards" ([Wikipedia](https://en.wikipedia.org/wiki/Omaha_hold_%27em)). The rule causes most beginner misreads. A flush needs two suited cards in hand, so four hearts on the board with only one heart in hand is no flush. Four hearts in hand with two on the board is no flush either ([PokerSkill](https://www.pokerskill.com/blog/pot-limit-omaha/)). A straight cannot be made from one hole card and four board cards, and two pair on the board is not a full house unless you hold a matching pair ([Wikipedia](https://en.wikipedia.org/wiki/Omaha_hold_%27em)). Players also cannot "play the board" ([DeucesCracked](https://www.deucescracked.com/learn/omaha)). Two more consequences follow from the same rule: three aces in hand with one ace on the board is only trips, and a single ten on an A-K-Q-J-x board makes no straight. Tournament rules reflect how easily Omaha hands are misread. **TDA Rule 14-A requires an Omaha player to table all four hole cards at showdown**, and Rule 13 ("cards speak") makes verbal declarations non-binding ([Poker TDA Rules 2026 v1.1](https://www.pokertda.com/view-poker-tda-rules/)).

### Pot-limit caps raises at "three times the bet plus the pot"

In pot-limit, the largest raise is the size of the pot after the raiser calls. That gives a simple formula: **raise to = 3 × the bet faced + the pot before that bet**. Facing a 50 bet into a 100 pot, a player can raise to 250 ([PokerSkill](https://www.pokerskill.com/blog/pot-limit-omaha/); [PLO Mastermind](https://intercom.help/plo-mastermind/en/articles/12529822-how-to-calculate-raise-sizes-in-pot-limit-omaha-plo)). Applying the formula preflop at $1/$2, the first player in can pot to $7 and the next player can re-pot to $24. Heads-up, the small blind's maximum open is 3bb, because its own blind is already part of the call. The TDA rules say preflop pot bets are calculated as if full blinds were posted, and only pot-limit games allow a player to ask for a pot count ([TDA Rule 56](https://www.pokertda.com/view-poker-tda-rules/)). One forum post gives a 60c pot raise at 10c/20c. That is an error; the formula gives 70c ([PokerChipForum](https://www.pokerchipforum.com/threads/how-to-calculate-plo-pot-sized-bets-from-the-blinds-preflop.113051/)).

Pot-limit is the default for a structural reason. Four-card hands are close in equity: aces with weak side cards are only about a 6-to-4 favorite over a T-9-8-7 rundown, against roughly 4-to-1 for aces over a suited connector in Hold'em ([PokerSkill](https://www.pokerskill.com/blog/pot-limit-omaha/)). In no-limit, that closeness would reduce the game to preflop near-coin-flips. History confirms it. The Stardust's January 1983 no-limit Omaha tournament switched to pot-limit within about a week because players were busting too fast ([Card Player, Ciaffone](https://cardplayer.com/cardplayer-poker-magazines/65671-erick-lindgren-20-12/articles/16829-all-about-omaha-origins)). Omaha Hi-Lo is usually played fixed-limit, and no-limit Omaha survives mainly in low-stakes online tournaments ([Wikipedia](https://en.wikipedia.org/wiki/Omaha_hold_%27em)).

### Hi-Lo splits the pot, and quartering punishes shared lows

In Omaha Hi-Lo (Omaha 8-or-better, the "O" in H.O.R.S.E.), the pot splits between the best high hand and the best qualifying low. A qualifying low is five unpaired ranks of 8 or lower, counted ace-to-five, with straights and flushes ignored, so the best low is 5-4-3-2-A. The 2+3 rule applies separately to each half, so a player may use different hole cards for high and low. If no low qualifies, the high hand scoops ([Wikipedia](https://en.wikipedia.org/wiki/Omaha_hold_%27em)). A few casinos use a nine-low qualifier. The TDA gives the odd chip to the high side ([TDA Rule 21-C](https://www.pokertda.com/view-poker-tda-rules/)). Being "quartered" means splitting the low half with another player while a third player wins the high, which leaves you a quarter of the pot. It usually happens when two players hold A-2 ([PokerSkill glossary](https://www.pokerskill.com/poker-glossary/quartered/)). The arithmetic is harsh. In a three-way pot where each player put in a third, being quartered returns a quarter of the pot, a **25% loss on your own contribution even though you "won"**.

### Variants change the card count, the dealing order, or the number of boards

Most variants keep the 2+3 rule and change one parameter.

| Variant | What changes | Status |
|---|---|---|
| PLO5 / Five-card Omaha | Five hole cards, still 2+3 | PokerStars from March 2013 ([Pokerfuse](https://pokerfuse.com/news/poker-room-news/pokerstars-to-debut-poker-variants-five-card-omaha-courchevel-21-03/)); GGPoker from 2021; 888poker added PLO5/PLO6 in Nov 2024 ([PokerNews](https://www.pokernews.com/news/2024/11/888poker-new-pot-limit-omaha-games-47335.htm)) |
| PLO6 / Six-card Omaha | Six hole cards; strategy less developed | Common in UK casinos ([Wikipedia](https://en.wikipedia.org/wiki/Omaha_hold_%27em); [PokerListings](https://www.pokerlistings.com/poker-games/6-card-omaha-poker)) |
| Big O | Five-card PLO played Hi-Lo 8-or-better | California and Southeastern US home games ([PokerNews](https://www.pokernews.com/poker-rules/big-o.htm)); the name is used inconsistently, and some sources apply it to any five-card Omaha |
| Courchevel | Five hole cards; first flop card shown before preflop betting | From the Aviation Club de France; on PokerStars since 2013 ([Wikipedia](https://en.wikipedia.org/wiki/Omaha_hold_%27em)) |
| Double-board bomb pot | Antes, no preflop betting, two boards, half the pot per board | Cash-game house rule ([Asian Poker Tour rulebook](https://www.theasianpokertour.com/info/pokerhandbook/omahadoubleboardbombpot)) |
| Fusion | Two hole cards preflop, a third after the flop, a fourth after the turn, then Omaha 2+3 | PokerStars, late 2018; reports conflict on whether it is still offered ([PokerNews](https://www.pokernews.com/news/2018/11/pokerstars-fusion-game-32556.htm)) |

Both Limit Omaha Hi-Lo and PLO are in the WSOP Eight-Game rotation ([SoMuchPoker](https://somuchpoker.com/events-calendar/wsop/2025/wsop-2025-las-vegas/73-eight-game-mix-6-handed-3-day-event-limit-holdem-limit-omaha-hi-lo-8-or-better-seven-card-stud-razz-seven-card-stud-hi-lo-8-or-better-no-limit-holdem-pot-limit-omaha-limit-2-7-lowball-triple-draw)). The notes found no authoritative ruleset for a Short Deck Omaha game.

### Heads-up and procedural rules mirror Hold'em, and running it twice is a PLO staple

Heads-up, **the button posts the small blind, acts first preflop and acts last on every later street**. The button may be adjusted when play becomes heads-up so that no one takes the big blind twice in a row ([TDA Rule 36-C](https://www.pokertda.com/view-poker-tda-rules/)). Tournaments use a dead button, and misdeals (two or more boxed cards, wrong card counts, and similar errors) cannot be called after substantial action ([TDA Rules 34, 37, 38](https://www.pokertda.com/view-poker-tda-rules/)). Running it twice is not in the TDA rules and is a cash-game convention. It requires an all-in with two live hands, the river not yet dealt, and agreement from both players ([PokerNews](https://www.pokernews.com/pokerterms/running-it-twice.htm)). It is "especially prevalent in Pot-Limit Omaha where the values of hands run so close together," and it cuts variance without changing expected value ([CardPlayer](https://www.cardplayer.com/cardplayer-poker-magazines/65600-max-pescatori-19-20/articles/15723-run-it-twice)).

## Sixty five-card hands per player compress every equity

A four-card hand forms **C(4,2) × C(5,3) = 6 × 10 = 60 five-card combinations** at showdown, compared with 21 in Hold'em. PLO5 forms 100 and PLO6 forms 150. The starting-hand space grows quickly. **PLO4 has 270,725 combinations that reduce to 16,432 suit-isomorphic classes** ([PokerStrategy](https://www.pokerstrategy.com/strategy/1826)). PLO5 has 2,598,960 combinations and 134,459 classes, and PLO6 has 20,358,520 and 962,988 ([PLOAdvisor](https://ploadvisor.pages.dev/en/plo6-methodology)). Hold'em has 1,326 and 169. The research team checked all of these class counts independently with a Burnside orbit count. PLO4 therefore has about 97 times as many distinct starting hands as Hold'em, which is why PLO preflop guidance is heuristic rather than memorized hand by hand. Double-suited hands, the most prized suit structure, are about 13.5% of deals, and rainbow hands about 10% ([PokerStrategy](https://www.pokerstrategy.com/strategy/1826)). Exact enumeration gives 13.48% and 10.55%, with single-suited hands at 58.4% and three-of-a-suit at 16.5%.

### The "65% best hand" figure is probably about five points low

The common claim is that AAKK double-suited, the best PLO hand, is only about a **65.5% favorite against a random hand** ([PokerStrategy](https://www.pokerstrategy.com/strategy/1826)). The research team's own Monte Carlo simulation (30,000 trials, evaluator checked against Hold'em AA's known 85%) gives a higher figure: about **70.4% for AAKK double-suited** against a random hand. The same simulation gives 65.3% for rainbow AAKK and 65.6% for AAKKds against JT98 double-suited. PokerStrategy's 65.5% matches those two matchups closely, which suggests it describes one of them rather than double-suited AAKK against a random hand. Other unpublished simulation results from the team show the same compression. JT98 double-suited is only about 57% against a random hand, and 9876 is about 51%. AA against a double-suited rundown is roughly 55–61%. Domination appears only through card removal: aces holding a king against KK are about 83%. Trips are a trap, with 222x at about 22% against a random hand, because the third card kills the hand's own outs. More hole cards make aces worth much less. Rainbow aces with junk rank in the top 4.5% of PLO4 hands but only the top 52% of PLO6 hands ([PLOAdvisor](https://ploadvisor.pages.dev/en/aaxx-equity)).

### Wraps beat sets, and the rule of 4 overstates big draws

Four hole cards allow straight draws with up to 20 outs. JT76 on a 9-8-2 rainbow flop is the classic **20-out wrap**, where a Hold'em open-ender has 8 outs ([Wikipedia](https://en.wikipedia.org/wiki/Omaha_hold_%27em)). The research team's exact enumeration of all turn and river cards shows what this does to "made hand beats draw" reasoning:

| Flop | Made hand | Draw | Made / draw equity |
|---|---|---|---|
| 9-8-2 rainbow | Top set (99) | 20-out wrap | 45.6 / 54.4 |
| 9-8-2 two-tone | Top set | 20-out wrap plus flush draw | 39.9 / 60.1 |
| 9-7-2 rainbow | Top set | 13-out wrap | 57.9 / 42.1 |
| 9-8-2 rainbow | Overpair (AA) | 20-out wrap | 25.6 / 74.4 |
| 9-8-2 two-tone | Top set | Nut flush draw only | 72.9 / 27.1 |
| Q-9-8 | Nut straight | Set | 62.2 / 37.8 |

Even a made nut straight is only about 62% against a set, because the set fills up when the board pairs. As CardPlayer puts it, "it's not uncommon for the nuts to be a significant underdog" in PLO ([CardPlayer](https://www.cardplayer.com/?p=1048628)). The Hold'em rule of 4 also breaks down. The exact chance of hitting from flop to river is 1 − C(45−outs, 2)/C(45, 2). That gives 36.4% for 9 outs, close to the rule's 36%, but **69.7% for 20 outs against the rule's 80%**. Many Omaha outs are also "dirty": they complete the draw but pair the board or give an opponent a better hand.

### Showdowns need roughly two hand classes more than Hold'em

The notes found no published breakdown of winning hands by class. Practitioners agree that PLO needs stronger hands at showdown and that the gap between the nuts and the second nuts can be large ([PokerTraining](https://www.pokertraining.com/poker/blog/when-the-second-nuts-in-plo-is-a-river-fold/)). The team's no-fold simulation gives a rough scale. With six players dealt to the river, the winning PLO hand is a straight or better about 78% of the time and a full house or better about 31%. In six-handed Hold'em the winner has a straight or better about 40% of the time. These baselines overstate real showdown strength, since weak hands fold in real games, but they explain why non-nut flushes lose so much money in multiway pots.

### Hi-Lo math: lows are less common than they look

A qualifying low is possible on about **60% of boards** ([Wikipedia](https://en.wikipedia.org/wiki/Omaha_hold_%27em)). Exact enumeration gives 60.09%. Holding a possible low is different from making one. By the team's calculation, A2 with two high cards completes a low only about 36.5% of the time, A23x about 49.5%, and A234 about 53%. A2xx on a 3-4-9 flop is counterfeited by an ace or deuce on the turn or river about 25% of the time. At a six-handed table, someone else also holds A-2 about 20% of the time, which is why quartering is a central EV risk.

### Variance roughly doubles bankroll requirements

Six-max PLO runs at about **120–160 bb/100 standard deviation**, against about 70–100 for 6-max NLHE ([Habwin](https://habwin.dinacode.com/en/post/poker-variance-part-2-its-influence-on-cash-games); [DeucesCracked](https://www.deucescracked.com/blog/poker-risk-of-ruin-variance-simulation-study)). Risk of ruin scales with the square of the standard deviation, so moving from 90 to 140 bb/100 raises the required bankroll by about 142%. In one simulation at a 3 bb/100 win rate and 5% risk of ruin, **Hold'em needed 40 buy-ins and Omaha 98** ([DeucesCracked](https://www.deucescracked.com/blog/poker-risk-of-ruin-variance-simulation-study)). Common advice is 50–100 buy-ins for 6-max PLO ([VIP Grinders](https://www.vip-grinders.com/?p=144762)). All of these figures come from training and affiliate sites rather than large published hand databases, so treat them as rules of thumb.

## Strategy rewards nut potential, and heads-up play is radically wide

### Preflop: nutty, connected, double-suited, no danglers

Good PLO starting hands are high, connected and suited, ideally double-suited, with no "dangler": a card that works with none of the others, like the 7 in AKQ7 ([DeucesCracked](https://www.deucescracked.com/poker/strategy/plo-basics)). Low double-suited hands make non-nut flushes and play badly ([PokerListings](https://www.pokerlistings.com/sidebar-post/why-avoid-weak-rundowns-in-plo)). Two pair in hand is overrated: if the bigger pair isn't worth playing alone, fold ([PokerNews](https://www.pokernews.com/strategy/eight-common-mistakes-beginners-make-in-pot-limit-omaha-32220.htm)). The old additive point systems, such as Edward Hutchison's 1997 count, aimed to approximate a hand's chance of winning a 10-handed no-fold showdown ([CPAN Hutchison module](https://metacpan.org/pod/Games::Poker::Omaha::Hutchison)). They have been replaced by simulation- and solver-based rankings, because additive scores miss interactions between cards, position and stack depth.

In one 100bb 6-max cash solve, opening ranges widen from about 22% in the hijack to 30% in the cutoff and **about 50% on the button** ([ThinkGTO](https://thinkgto.com/blog/plo-preflop-strategy-from-theory-to-practice)). A separate MonkerSolver dataset gives the button at 48.6%, with the big blind folding 60.2% and 3-betting 9.4% against it ([PLO.com](https://plo.com/plo-heads-up-ranges)). Stack depth matters a lot. The button opens about 26% at 20bb, using a min-raise, and about 52% at 150bb, using a pot-sized raise ([SolvePoker](https://solvepoker.app/plo-stack-depth)). Rake changes small-blind strategy completely. At low stakes the solved SB is pure raise-or-fold (37.4% raise). At the highest-stakes rake it limps 24.3% ([PLO Genius](https://plogenius.com/blog/taking-a-closer-look-at-small-blind)). A preflop chart that ignores the rake structure can therefore mislead. Because the pot cap keeps opens near 3bb, stack-to-pot ratio (SPR) is set mostly by 3-bets. SPR matters more in PLO than in NLHE: at SPR of about 1 or below, players are effectively committed once they connect with the flop ([Card Player](https://cardplayer.com/cardplayer-poker-magazines/66224-poker-year-in-review-26-1/articles/21011-pot-limit-omaha-the-stack-to-pot-ratio-spr-part-i)).

### Heads-up: the button plays 87.5% of hands

In a 100bb heads-up MonkerSolver solve (5% rake capped at 1bb, published July 2026), **the button pot-raises 84.9%, limps 2.6% and folds only 12.5%**. The big blind continues 61.4% of the time, calling 43.3% and 3-betting 18.1% ([PLO.com](https://plo.com/plo-heads-up-ranges)). Compared with 6-max, the BB 3-bets almost twice as often and folds much less. In the site's words, "the solver barely selects hands," so heads-up skill is almost entirely postflop. The breakdown by hand class sets clear priorities:

| Hand class | Button raise / limp / fold | BB 3-bet / call / fold |
|---|---|---|
| AAxx | 98.9 / 1.1 / 0 | 96.7 / 3.3 / 0 |
| KKxx | 99 / 1 / 0 | 67.5 / 31.8 / 0.7 |
| Double-paired | — | 89.2 / 10.8 / 0 |
| Broadway rundowns | — | 89.6 / 10.4 / 0 |
| Rundowns | 94.6 / 1.7 / 3.7 | 40.6 / 46.7 / 12.8 |
| "Junk" (48.6% of hands) | 78.2 / 2.9 / 18.9 | 9.4 / 36.9 / 53.7 |
| Trips | 14.7 / 2.1 / 83.2 | 0 / 0.6 / 99.4 |

Source: [PLO.com HU ranges](https://plo.com/plo-heads-up-ranges).

The near-pure pot-raise strategy with tiny limp frequencies is a reasonable simplification for human players at typical rake. Older heuristic advice agrees with the solve. Heads-up, position matters more, big pairs and high-card hands gain value, small rundowns lose value, overpairs and top two pair win more often, and profiling the opponent matters most: how they play non-nut flush draws, what their bet sizes mean, and whether they bluff busted draws ([OmahaPlanet](https://www.omahaplanet.com/pot-limit-omaha/strategy/heads-up-introduction/)). There is one important gap. **No free source publishes heads-up postflop solver data** (c-bet frequencies, sizings, 4-bet ranges). That data sits behind paywalls, including GTO Wizard's heads-up PLO solving, added in July 2026 ([PokerNews](https://www.pokernews.com/news/2026/07/gto-wizard-launches-major-updates-to-its-plo-solver-52006.htm)).

### Postflop: draw to the nuts and bet where the range advantage lies

The central postflop question is "not 'do I have a flush draw?' but 'do I have the nut flush draw?'" ([rec.poker](https://rec.poker/announcements/blog/plo-for-beginners-tame-the-game-of-draws/)). Overpairs, aces included, are often just bluff-catchers after the flop, and slow-playing is dangerous ([PokerNews](https://www.pokernews.com/strategy/eight-common-mistakes-beginners-make-in-pot-limit-omaha-32220.htm)). Across all 1,755 flops in a 100bb button-versus-big-blind single-raised pot, the button c-bets **52.3% overall: 37.0% at one-third pot and 15.4% at pot**. Frequency tracks range advantage. Ace-high paired two-tone boards such as A88 get bet 81–84% of the time, mostly small. Connected and monotone middle boards get bet much less: 33.4% on QJT rainbow and 18.8% on QJT monotone ([SolvePoker](https://solvepoker.app/articles/highest-cbet-frequency-boards)). The big blind's calling range has few aces, so the preflop raiser owns ace-high and paired boards, and the BB "finally has the advantage" on low connected boards. Draw density is the main factor setting c-bet frequency. Flop overbets are close to absent in the solves.

The consensus beginner leaks follow from the math above:

- stacking off with non-nut flushes, bottom sets or non-nut straights;
- overplaying aces and bare two pair, which gets worse as SPR rises;
- playing too many hands out of position;
- set-mining small pairs;
- 3-betting unconnected suited aces or low rundowns from the blinds.

Sources: [PokerNews](https://www.pokernews.com/strategy/do-not-make-these-five-common-plo-mistakes-42923.htm); [SolvePLO](https://solveplo.pages.dev/articles/3-betting-in-plo). Heads-up, the "too many hands" leak mostly goes away, since the solver itself plays about 87% from the button.

### Tournaments and Hi-Lo bend the rules further

Traditional PLO tournament advice favors tight play ([Card Player](https://cardplayer.com/poker-blogs/50-piper-on-pot-limit-omaha/entries/235441-plonkaments-part-ii)). A tentative 2026 argument holds that standard ICM fits PLO poorly, because close equities mean short stacks must take more risk to rebuild than ICM suggests ([PokerStrategy](https://www.pokerstrategy.com/news/content/ICM-is-broken-in-PLO-tournaments-l-Strategy-with-Barry_140474/)). In Hi-Lo the goal is to scoop. A2 is the key low holding, but a bare A2 holds the nut low, alone or shared, only about 25% of the time. Adding a 3 or 4 protects against counterfeiting, and the main edge comes from freerolls, where one half is locked up while you draw to the other ([PokerSkill](https://www.pokerskill.com/blog/omaha-hi-lo/); [DeucesCracked](https://www.deucescracked.com/learn/omaha-hi-lo)). The notes found no solver-based Hi-Lo data. Hi-Lo strategy still rests on older heuristic literature.

The classic books are Jeff Hwang's *Pot-Limit Omaha Poker* (2008) and Bob Ciaffone's *Omaha Poker* ([PokerTraining](https://www.pokertraining.com/poker/blog/top-5-books-on-omaha-strategy/)). PLO Mastermind and Run It Once lead PLO-specific training ([Pokerfuse](https://pokerfuse.com/latest-news/2026/8/best-poker-training-sites-teach-plo/)).

## From a Golden Nugget side game to $2M high-roller first prizes

Omaha reached casino play at the Golden Nugget in the early 1980s, although the year depends on the source. Bob Ciaffone, who was there, dates it to **spring 1982, just after the WSOP**. In his account, Robert "Chip Burner" Turner and a Seattle-area player called "Gwen" started a heads-up limit Omaha high game that soon filled up, with cardroom chief Bill Boyd's permission ([Card Player, Ciaffone 2007](https://cardplayer.com/cardplayer-poker-magazines/65671-erick-lindgren-20-12/articles/16829-all-about-omaha-origins)). PokerNews says Turner pitched the game to Boyd in 1983, and that Boyd named it "Nugget Hold'em" before it became "Omaha Hold'em" and then "Omaha" ([PokerNews 2009](https://www.pokernews.com/news/2009/06/from-the-poker-vaults-bill-boyd-6726.htm)). Similar games existed earlier: Ciaffone played "two by three" in 1970s Michigan. The notes found no sourced explanation for why the game is named after the city.

The game then moved from Las Vegas to Europe. After the 1983 Stardust switch to pot-limit, Jack Keller (the 1984 WSOP Main Event champion) promoted Omaha in England in 1984, and "the British and Irish quickly made it their favorite form of poker." London's Victoria Club ran a £1,000 buy-in half-razz, half-PLO game that was for a long time "likely the biggest sustained poker game in the world" ([Card Player 2007](https://cardplayer.com/cardplayer-poker-magazines/65671-erick-lindgren-20-12/articles/16829-all-about-omaha-origins)). In Europe, "Omaha" still means high-only PLO by default ([Wikipedia](https://en.wikipedia.org/wiki/Omaha_hold_%27em)).

Online PLO peaked at the Full Tilt $500/$1,000 tables in 2009. The **largest online pot ever, about $1,356,947**, was a PLO hand that Patrik Antonius won from Viktor "Isildur1" Blom in November 2009 ([PokerNews](https://www.pokernews.com/news/2009/11/patrik-antonius-and-isildur1-play-largest-ever-online-pot-at-7575.htm)). Blom and Phil Ivey played a $1,127,955 PLO pot in the same period, and nearly all of 2009's biggest pots came from those tables ([PokerNews](https://www.pokernews.com/news/2009/12/the-top-5-online-pots-of-2009-7691.htm)).

PLO is now a full second track on the high-roller circuit. At the 2026 WSOP:

- Michael Mizrachi won the $10K PLO Championship for $1,350,203. It was his ninth bracelet and his first in PLO ([PokerNews](https://www.pokernews.com/news/2026/06/michael-mizrachi-wins-ninth-wsop-bracelet-51714.htm)).
- Daniel Negreanu won the $100K PLO High Roller for $2,257,718 ([PokerNews](https://www.pokernews.com/news/2026/07/daniel-negreanu-wins-eighth-wsop-bracelet-51743.htm)).
- Eelis Pärssinen won the $25K PLO High Roller for $2,161,056 from a 451-entry field, and won a second bracelet the same summer ([PokerNews](https://www.pokernews.com/news/2026/07/wsop-statistician-picks-out-his-favorite-stats-from-2026-51969.htm)).
- Scott Clements won the $10K Omaha Hi-Lo Championship (same source).

On the Triton circuit, Daniel Dvoress won the $100K PLO Main Event in Montenegro in May 2026 for $2,018,000 ([Pokerology](https://www.pokerology.com/poker/news/dan-dvoress-wins-plo-main-event-at-triton-montenegro/)), and Triton Jeju 2025 drew record PLO fields ([PokerNews](https://www.pokernews.com/news/2025/03/another-record-field-triton-jeju-crowns-four-plo-champions-48169.htm)). Online, GGPoker's Omaholic series started in March 2021 with $7M guaranteed across 105 events ([PokerNews](https://www.pokernews.com/news/2021/03/omaholic-series-ggpoker-38815.htm)). A seat snapshot showed GGPoker with as many occupied mid-stakes PLO seats as the next three rooms combined. Typical rake was 4–5% with $2–$4 caps ([PokerListings](https://www.pokerlistings.com/blog/where-to-play-omaha-cash-games-online)).

**No reliable public figure exists for PLO's share of online traffic or rake.** Traffic trackers report totals by network, not by game, so any "PLO is X% of the market" claim is unverified.

## The computational frontier: 204x more hands and no published superhuman bot

### Game size grows with the card space, not the betting tree

Exact sizes are published for Hold'em. Heads-up limit Hold'em has about 3.19×10^14 information sets. Heads-up no-limit (200bb, ACPC rules) has **about 6.38×10^161**, mostly because any integer bet size is allowed ([Johanson 2013](https://arxiv.org/abs/1302.7008)). **No exact count has been published for heads-up PLO.** The structure still makes clear which way the comparison goes. Pot-limit betting shrinks the action tree compared with no-limit, but every player's private-hand dimension grows from 1,326 to 270,725 (178,365 live hands on a five-card board). Solvers abstract bet sizes in both games anyway, so in practice the extra difficulty comes almost entirely from the cards. A solver holds a range vector at every public node, so per-node memory is roughly 135–204x larger in PLO, and naive river showdown evaluation grows with the square of the range size. A 2026 CFR preprint uses PLO as its example of a game where "lossy abstraction becomes necessary" ([arXiv 2605.19928](https://arxiv.org/html/2605.19928)). Two exact reductions help: 16,432 isomorphic preflop classes and **1,755 strategically distinct flops** ([PokerNews/GTO Wizard](https://www.pokernews.com/poker-tools/gto-wizard/plo-solver.htm)).

### Hold'em algorithms transfer, but PLO results remain unpublished

All the algorithms behind superhuman Hold'em play carry over to Omaha in principle:

- CFR+, which essentially solved heads-up limit Hold'em ([Science 2015](https://www.science.org/doi/10.1126/science.1259433));
- Discounted CFR ([arXiv 1809.04040](https://arxiv.org/abs/1809.04040));
- DeepStack's continual re-solving with value networks ([arXiv 1701.01724](https://arxiv.org/abs/1701.01724));
- Libratus's blueprint plus safe subgame solving ([Science 2018](https://www.science.org/doi/10.1126/science.aao1733));
- Pluribus's MCCFR blueprint with depth-limited search ([Science 2019](https://www.science.org/doi/10.1126/science.aay2400));
- Deep CFR ([arXiv 1811.00164](https://arxiv.org/pdf/1811.00164));
- ReBeL ([arXiv 2007.13544](https://arxiv.org/abs/2007.13544)).

Even so, the notes found **no peer-reviewed paper reporting a strong or superhuman PLO agent, and no published exploitability figures for any PLO abstraction**. The public Omaha work is small:

- PokerRL-Omaha, a Deep CFR fork for 2–6 player PLO with handcrafted preflop buckets and an evaluator its author calls "naive and slow" ([GitHub](https://github.com/diditforlulz273/PokerRL-Omaha));
- PLOAI, which aims at "at least as good as a decent human player" ([GitHub](https://github.com/robb17/PLOAI));
- a Harvard thesis on a jam/fold Omaha Hi-Lo endgame ([Harvard DASH](https://dash.harvard.edu/server/api/core/bitstreams/7312037d-b83c-6bd4-e053-0100007fdf3b/content));
- a 2026 preprint in which an LLM proposes features to group the 16,432 classes into 30 buckets, evaluated only qualitatively ([arXiv 2609.04303](https://arxiv.org/html/2609.04303v1)).

The Annual Computer Poker Competition appears never to have run an Omaha event, so PLO has no public benchmark comparable to Slumbot. This is the researchers' background knowledge and was not checked against ACPC records.

### Commercial solvers hold the practical state of the art

| Tool | Model | Notable facts |
|---|---|---|
| MonkerSolver | Local desktop CFR with abstraction; any street, multiway | €499; tree size limited by RAM (8 GB minimum) ([MonkerWare](https://monkerware.com/solver.html)) |
| GTO Wizard PLO | Cloud | All 1,755 flops; July 2026 update added custom HU solves, nodelocking, 8 opponent profiles, about 2x faster river solves at 0.1% pot exploitability; PLO5 "in the pipeline" ([PokerNews](https://www.pokernews.com/news/2026/07/gto-wizard-launches-major-updates-to-its-plo-solver-52006.htm)) |
| Vision | Precomputed solution browser and trainer | Built from a Monker-based workflow since 2018; Run It Once partner ([PokerNews advertorial](https://www.pokernews.com/strategy/vision-a-user-friendly-revolution-in-plo-training-47342.htm)) |
| PLO Genius | Cloud solver and trainer (Deepsolver) | Free HU 100bb preflop for PLO4/PLO5 ([PLO Genius](https://plogenius.com/blog/taking-a-closer-look-at-small-blind)) |
| PioSOLVER | Hold'em only | No evidence of PLO support ([Two Plus Two](https://forumserver.twoplustwo.com/167/poker-software/piosolver-postflop-equilibrium-solver-holdem-1516187/index121.html)) |

None of these vendors discloses its algorithm, and no independent benchmark compares their accuracy or speed. Bot activity is real but thinly documented. PokerStars investigated a suspected mid-stakes PLO bot ring in 2015 that reportedly won about $1.5M ([VIP-Grinders](https://www.vip-grinders.com/massive-bot-farm-online-poker-sites/)), and in April 2026 it described its policy as "ban early, ban quickly" ([Pokerfuse](https://pokerfuse.com/the-rail/2026/4/?post=3892)). Many 2026 "bot detection" pages are marketing from bot vendors.

### Hand evaluation must respect the 2+3 rule

Hold'em evaluators such as the Two Plus Two 7-card table and OMPEval cannot evaluate Omaha hands directly, because walking all nine cards breaks the 2+3 rule. The naive method loops over the 60 combinations. **HenryRLee's PHEvaluator** uses a perfect hash to avoid that loop, with tables of about 30 MB for PLO4, 112 MB for PLO5 and 353 MB for PLO6. Its README benchmarks PLO4 at about 3 µs per random hand, though it also shows a conflicting throughput figure, so benchmark it yourself before relying on either number ([GitHub](https://github.com/HenryRLee/PokerHandEvaluator)). Waugh's hand-isomorphism indexer handles PLO's [4], [4,3], [4,3,1], [4,3,1,1] street layout ([hand_indexer](https://docs.rs/crate/hand_indexer/latest/source/src/hand_indexer.rs)).

For a compute-limited heads-up PLO bot, the notes' design recommendations are extrapolated from Hold'em practice, not from published PLO results:

- **Preflop:** a precomputed blueprint over the 16,432 classes or a few hundred buckets.
- **Postflop:** real-time re-solving of the current street with 2–3 pot-fraction sizes, over isomorphic flops, with equity- or rollout-based leaf values.
- **Showdowns:** rank every live hand once per river, sort, and sweep, correcting for blockers by inclusion–exclusion over the four hole cards.
- **Opponent modeling:** a nodelock-style restricted best response, mixed with equilibrium play for safety.

DeepStack's and Libratus's re-solving results support the approach in general ([Libratus](https://www.science.org/doi/10.1126/science.aao1733)). Parallel CFR has reached about 50 ms per iteration on billion-history Hold'em trees ([arXiv 2605.19928](https://arxiv.org/html/2605.19928)), which suggests street-limited PLO re-solves are feasible in real time.

## Conclusion

Omaha's defining features (close equities, big draws, high variance, its reputation as the action game, and its computational difficulty) all come from the requirement to use exactly two of four cards. The rule is simple and its effects are broad. The research also leaves a clear practical asymmetry. Heads-up preflop PLO is close to solved and simple to execute: pot-raise almost everything from the button, and 3-bet aces, double pairs and broadway rundowns from the big blind. Heads-up postflop play, where the solver says nearly all the skill lies, has no published free data and no peer-reviewed agent benchmark. Whoever builds a strong heads-up PLO agent is working in territory that academic poker AI has largely skipped, and evaluation speed and card abstraction will be the binding constraints.

Several common claims should be treated with suspicion. The "best hand is only 65% against random" figure is probably about five points low for AAKK double-suited. The rule of 4 overstates big wraps by up to ten points. Market-share claims about PLO traffic have no data behind them. Much of the freely available solver content comes from single solves on tool vendors' blogs, each tied to one rake and one bet-sizing setup, so it is best read as illustrating principles rather than as exact frequencies. Hi-Lo and PLO5/PLO6 remain the least studied areas, in both solver output and published math.
