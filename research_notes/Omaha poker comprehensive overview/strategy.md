# Pot-Limit Omaha (and Omaha Hi-Lo) Strategy, with emphasis on Heads-Up

Source-quality note for the report writer: freely accessible, solver-derived PLO numbers mostly come from commercial tool sites (PLO.com, SolvePoker/SolvePLO, PLO Genius, ThinkGTO). Premium sources (GTO Wizard PLO, PLO Mastermind, Run It Once, Upswing PLO Lab) are paywalled and could not be read directly. The Two Plus Two HU PLO GTO thread returned HTTP 403. Treat the numbers below as one solve each (one specific rake, stack, and sizing setup), not as universal truths. Some of the newer tool-site blogs (ThinkGTO especially) read like marketing content and may be partly machine-written. Where a figure comes from such a source, it is flagged.

## Preflop strategy: hand quality, position, opening ranges, 3-betting/4-betting, SPR

### Takeaway
Strong PLO hands are nutty (high cards, an ace suited to another card), connected (rundowns with few gaps), and suited, ideally double-suited, with no danglers. Equities run close: even premium hands are rarely above about 65% against a random hand. In one 100bb solve, 6-max opening widens from about 22% (HJ) to about 50% (BTN). Pot-limit caps the open at roughly 3bb (or 3.5bb in strict tournament pot-limit), so SPR is set mostly by 3-bets.

### Cited Findings
**Hand quality**
- Double-suited hands are the most valuable starters because they can make two different flushes. Examples of the top tier include AAKK double-suited and KKQJ double-suited. Big double-suited rundowns such as KQJT and JT98 are strong, while small ones like 8765 are more speculative — [DeucesCracked PLO basics](https://www.deucescracked.com/poker/strategy/plo-basics); [PokerNews: Evaluating Starting Hands](https://www.pokernews.com/strategy/cant-play-them-all-evaluating-starting-hands-pot-limit-omaha-29959.htm)
- A dangler is a card that doesn't work with the other three (example: AKQ7, where the 7 is the dangler). Danglers lower a hand's value — [DeucesCracked](https://www.deucescracked.com/poker/strategy/plo-basics); [PokerTraining: hands to avoid in PLO](https://www.pokertraining.com/poker/blog/hands-to-avoid-in-pot-limit-omaha/)
- Low, disconnected double-suited hands play poorly because they make non-nut flushes. Avoid weak, low rundowns — [PokerListings: why avoid weak rundowns](https://www.pokerlistings.com/sidebar-post/why-avoid-weak-rundowns-in-plo)
- PLO has 270,725 starting hands versus 1,326 in NLHE. Double-suited and rainbow versions of the same hand differ by about 3-6% equity. Premium hands are rarely above 65% against a random hand. One gap in a rundown is acceptable, while two gaps make it "marginal at best." A dangler is defined there as a card below 6 that shares no suit with the rest of the hand. (Jan 2026; source of unclear rigor) — [ThinkGTO PLO preflop](https://thinkgto.com/blog/plo-preflop-strategy-from-theory-to-practice)
- Don't overrate pocket two pair: if the bigger pair isn't worth playing on its own, fold the hand, especially out of position — [PokerNews: Eight Common Mistakes](https://www.pokernews.com/strategy/eight-common-mistakes-beginners-make-in-pot-limit-omaha-32220.htm)

**6-max opening ranges (solved 100bb cash; solver not named)**
- HJ opens 22% / folds 78%; CO opens 30%; BTN opens 50%; SB raises 33%, limps 7%, folds 60%. UTG was not given. SolvePLO describes UTG as "roughly one in five hands" — [ThinkGTO](https://thinkgto.com/blog/plo-preflop-strategy-from-theory-to-practice); [SolvePLO preflop charts (MonkerSolver, 100bb 6-max)](https://solveplo.pages.dev/plo-preflop-charts)
- A separate MonkerSolver-based dataset gives the 6-max button open as 48.6%. Facing it, the BB folds 60.2% and 3-bets 9.4% — [PLO.com HU ranges (6-max comparison)](https://plo.com/plo-heads-up-ranges)
- Button open width depends heavily on stack depth: about 26% at 20bb and about 52% at 150bb. At 20bb the open is a min-raise to 2bb; from 30bb up it is a pot-sized raise — [SolvePoker: PLO by stack depth](https://solvepoker.app/plo-stack-depth)

**Small blind (6-max, PLO Genius, Dec 2024, Jakub Szczotka)**
- The SB strategy depends on rake. At low stakes it is pure raise/fold: raise 37.4%, fold 62.6%. At mid stakes it raises 38.9% with no limping. At the highest stakes (around PLO5000 rake) it limps 24.3%, raises 28.5%, and folds 47.2% — [PLO Genius: SB preflop](https://plogenius.com/blog/taking-a-closer-look-at-small-blind)
- Because the SB has already posted 0.5bb, the solver opens some hands with negative EV that still lose less than folding. Example: QT86 single-suited open is about -0.41bb versus -0.5bb for folding. The theoretical BB 3-bet frequency against the SB is about 13%. If BB folds to a steal more than about 63%, any-two-style opening becomes profitable. Raise all AA and KK and most QQ and double-paired hands. Avoid trips except aces. Be cautious with 2s, 3s, 4s, and 5s — [PLO Genius](https://plogenius.com/blog/taking-a-closer-look-at-small-blind)
- In pot-limit play the maximum open is 3bb in cash games where the SB counts as a fraction, about 3.5x in strict tournament pot-limit, and about 4x where the SB is treated as a full blind — [PLO Genius](https://plogenius.com/blog/taking-a-closer-look-at-small-blind); [VIP-Grinders PLO guide](https://vip-grinders.com/poker-strategy/omaha/beginners)
- Heuristic advice from one source: from the SB, 3-bet or fold against raises, with roughly 15-20% 3-betting, plus a small flat range of hands that play well multiway — [VIP-Grinders](https://vip-grinders.com/poker-strategy/omaha/beginners). The *Mastering Small Stakes PLO* book recommends over-limping around 30% from the SB, which conflicts with the solver-style figures — [dokumen.pub extract](https://dokumen.pub/mastering-small-stakes-pot-limit-omaha-1nbsped.html)

**BB defense, 3-betting**
- Solver BB defense against a 2.5bb open in 6-max cash is about 36.5% versus UTG and about 41.9% versus MP. These figures come from a PLO4-vs-cash comparison article of questionable provenance — [QuintAce PLO4 article](https://quintace-external.github.io/articles/ad-hoc/books/book-5/)
- Against a button open, the BB defends wide by calling and 3-bets selectively with AAxx, strong suited rundowns, and double-suited broadways. It tightens considerably against UTG — [SolvePLO preflop ranges explained](https://solveplo.pages.dev/articles/plo-preflop-ranges-explained)
- Preflop fold equity is much lower in PLO than in NLHE. 3-betting suited aces without connectivity, or low rundowns from the blinds, leads to trouble on every street. Out-of-position 3-bet ranges should be tighter and more nut-heavy — [SolvePLO 3-betting in PLO](https://solveplo.pages.dev/articles/3-betting-in-plo)

**SPR**
- SPR is arguably more useful in PLO than in NLHE because pot-limit caps bet sizes. At SPR around 1 or below you are virtually committed once you catch any piece. Deeper stacks make it a bigger mistake to commit with hands like bare two pair — [Card Player: PLO SPR Part I](https://cardplayer.com/cardplayer-poker-magazines/66224-poker-year-in-review-26-1/articles/21011-pot-limit-omaha-the-stack-to-pot-ratio-spr-part-i); [Card Player: PLO SPR Part II](https://www.cardplayer.com/cardplayer-poker-magazines/66227-greg-raymer-26-3/articles/21056-pot-limit-omaha-the-stack-to-pot-ratio-spr-part-ii)
- Sources disagree on where the "commit zone" starts: SPR 0-3, under 3, or 4 or below for PLO. PLO commitment thresholds are stricter than NLHE because ranges are stronger — [DeucesCracked SPR guide](https://www.deucescracked.com/blog/poker-spr-stack-to-pot-ratio-strategy-guide-2026); [Pokerology SPR](https://www.pokerology.com/poker/strategy/spr/)

### Inferences
- Pot-sized 3-bets with AAxx put 100bb pots at a low SPR (roughly 3-4 at 100bb when called heads-up). This explains the classic heuristic of 3-betting aces to set up stack-offs, but no retrieved source confirmed a specific SPR number for this.
- The SB raise/limp mix is driven by rake, so a "GTO chart" that ignores rake structure can be misleading.

### Gaps
- No reliable free source gave full solver UTG/LJ ranges, 4-bet frequencies, or SB 4-bet/call/fold versus a 3-bet.
- No source quantified the heuristic that AAxx should "always 3-bet pot." The PLO.com HU data (next section) shows the BB 3-betting AAxx 96.7% heads-up, which is the closest evidence.

## Heads-up PLO specifically

### Takeaway
In a 100bb heads-up MonkerSolver solve (5% rake, 1bb cap), the button/SB plays 87.5% of hands: 84.9% as a pot-sized raise, 2.6% as a limp, and 12.5% folded. The BB continues 61.4% (43.3% call, 18.1% 3-bet). That is far wider than 6-max (BTN 48.6% open; BB folds 60.2%, 3-bets 9.4%). Big pairs and high-card hands gain value heads-up, small rundowns lose value, and position matters even more.

### Cited Findings
- **HU solve (PLO.com, data generated July 8, 2026, MonkerSolver, 100bb, 5% rake with 1bb cap):**
  - Button raises 84.9% (pot), limps 2.6%, folds 12.5%. BB versus the open calls 43.3%, 3-bets 18.1%, folds 38.6%. BB versus a limp raises 43.6% and checks 56.4% — [PLO.com HU ranges](https://plo.com/plo-heads-up-ranges)
  - Button raise/limp/fold by hand class: AAxx 98.9/1.1/0; KKxx 99/1/0; QQxx 98.5/1.3/0.2; JJ-TTxx 98.1/1.9/0; trips 14.7/2.1/83.2; one-pair 86.7/2.9/10.4; rundowns 94.6/1.7/3.7; one-gap 94.2/0.5/5.3; wheel hands 93.4/2.6/4; "junk" (48.6% of all hands) 78.2/2.9/18.9 — [PLO.com](https://plo.com/plo-heads-up-ranges)
  - BB 3-bet/call/fold by hand class: AAxx 96.7/3.3/0; KKxx 67.5/31.8/0.7; QQxx 50.8/47.1/2.1; JJ-TTxx 35.3/63.8/0.8; double-paired 89.2/10.8/0; broadway rundowns 89.6/10.4/0; rundowns 40.6/46.7/12.8; one-gap 42.4/40.3/17.3; wheel 13.9/57.8/28.3; pair 12/52.1/35.9; junk 9.4/36.9/53.7; trips 0/0.6/99.4 — [PLO.com](https://plo.com/plo-heads-up-ranges)
  - The site explains the width by two facts: the button posts a blind every hand, and PLO equities run close against one opponent. "The solver barely selects hands"; the skill lies in postflop play with wide ranges — [PLO.com](https://plo.com/plo-heads-up-ranges)
- GTO Wizard launched fully customizable heads-up PLO solving, from preflop to river, plus nodelocking, in July 2026 — [PokerNews, July 2026](https://www.pokernews.com/news/2026/07/gto-wizard-launches-major-updates-to-its-plo-solver-52006.htm)
- PLO Genius's free plan includes 100bb heads-up preflop solutions for PLO4 and PLO5 — [PLO Genius](https://plogenius.com/blog/taking-a-closer-look-at-small-blind)
- **Older heuristic (OmahaPlanet, around 2009-2018):** position matters more heads-up than in full ring. Big pairs and high-card hands gain value, smaller rundowns lose value, and overpairs and top two pair win more often. Monsters on ragged low flops get paid less. Opponent profiling matters most: how they play non-nut flush draws, whether they lead with trips, what their bet sizes mean, whether they bluff busted draws, and what their check-raises represent — [OmahaPlanet HU PLO intro](https://www.omahaplanet.com/pot-limit-omaha/strategy/heads-up-introduction/)
- A NLHE comparison, for context only: HU NLHE button min-raise ranges are about 70-91%. PLO HU opens are pot-sized, not min-raises, except at around 20bb — [Upswing HUNL button opens](https://upswingpoker.com/heads-up-button-open-strategy-no-limit-hunl/); [SolvePoker stack depth](https://solvepoker.app/plo-stack-depth)

### Inferences
- Heads-up, the BB 3-bets nearly twice as often as in 6-max (18.1% vs 9.4%) and folds far less (38.6% vs 60.2%). Expect more 3-bet pots, more low-SPR play, and more value from the high pairs (AA/KK/QQ) that dominate the 3-bet range.
- The solve limps only 2.6% and does not fold to limps, so a near-pure pot-raise strategy is a reasonable simplification for humans at typical rake.
- Because ranges are wide, postflop hand values shift up: one pair, top two, and non-nut draws gain value relative to 6-max multiway pots. This is consistent with OmahaPlanet's heuristic, but no free solver postflop HU data was found to confirm it.

### Gaps
- No free source gave HU postflop solver data (c-bet frequencies, sizing in HU SRPs and 3-bet pots) or SB-vs-3-bet (4-bet) frequencies. The 2+2 thread "Heads-up PLO, what does GTO preflop play look like?" exists but was blocked (403): https://forumserver.twoplustwo.com/38/omaha/heads-up-plo-what-does-gto-preflop-play-look-like-1803662/
- The PLO.com numbers come from one MonkerSolver solve with one sizing tree. Other trees and rakes will differ.

## Postflop: draws vs made hands, nuttiness, blockers, board textures, c-betting, OOP play

### Takeaway
Draw to the nuts. Non-nut flushes, bottom sets, and non-nut straights lose big pots. In a 6-max 100bb BTN-vs-BB SRP solve, the overall button c-bet rate was 52.3% (37.0% at 33% pot, 15.4% pot-sized). Betting is highest on ace-high paired two-tone and dry paired boards (75-84%), mostly small, and lowest on connected or monotone middle boards (about 19-44%). Overbets on the flop are nearly absent.

### Cited Findings
- **SolvePoker solve (6-max, 100bb, BTN open / BB call, flop checked to BTN, 1,755 flops; published Oct 2025, updated Sep 2026):**
  - Overall c-bet 52.3% (37.0% small, 15.4% pot). By class: ace-high 58.3%; K/Q/J-high 50.2%; 8-T high 51.6%; 7-high or lower 50.6%; paired 52.0%; trips on board 33.6%; disconnected 53.8%; connected (span ≤2) 39.9%; monotone 40.9% — [SolvePoker highest c-bet boards](https://solvepoker.app/articles/highest-cbet-frequency-boards)
  - Top boards: A88 two-tone 84.4%; A99tt 82.8%; ATTtt 81.3%; A77tt 80.9%; AJJtt 79.4%; 993r 78.1%; 994r 77.8%; 883r 75.6%. The 33% size dominates (62-74 points of the 75-84). On ace-free paired boards, more than 92% of bets are small — [SolvePoker](https://solvepoker.app/articles/highest-cbet-frequency-boards)
  - Specific boards: AK4r 64.5% (slight preference for pot); A64r 67.6%; QJTr 33.4%; QJT monotone 18.8%; 765tt 43.8%; AAAr checked back 73.5%. Pot-sized bets concentrate on boards that split the range into value and air. The BB's donk-lead rate is 19.3% on 765tt and 3.5% on ace-high boards — [SolvePoker](https://solvepoker.app/articles/highest-cbet-frequency-boards)
  - Principles: the BB's calling range (rundowns, suited middle cards, pairs) holds few aces, so the preflop raiser bets A-high and paired boards. The BB "finally has the advantage" on low connected boards. Draw density is the main factor governing c-bet frequency — [SolvePoker](https://solvepoker.app/articles/highest-cbet-frequency-boards); [SolvePLO board texture analysis](https://solveplo.pages.dev/articles/board-texture-analysis)
- In a CO-vs-BB 100bb SRP dataset: K72r c-bet 83.6% at about 2.4bb, KK5 79.3% at about 1.8bb, and flop overbets on only 0.0-0.3% of bets. (Unverified commercial source; tables partly garbled) — [QuintAce PLO4 article](https://quintace-external.github.io/articles/ad-hoc/books/book-5/)
- In 3-bet pots on ace-high dry boards, the IP 3-bettor c-bets at very high frequency with small sizing, and OOP frequencies are much lower on the same texture — [SolvePLO A-high flops in 3-bet pots](https://solveplo.pages.dev/articles/ace-high-flops-3bet-pots)
- "The critical question isn't 'do I have a flush draw?' but 'do I have the nut flush draw?'" Overvaluing non-nut hands (second-nut flushes, bottom sets, non-nut straights) is the main reason beginners lose big pots — [rec.poker PLO for beginners](https://rec.poker/announcements/blog/plo-for-beginners-tame-the-game-of-draws/); [PokerNews five common PLO mistakes](https://www.pokernews.com/strategy/do-not-make-these-five-common-plo-mistakes-42923.htm)
- An overpair, even aces, is often just a bluff catcher after the flop. Slow-playing is dangerous in PLO, especially multiway — [PokerNews Eight Common Mistakes](https://www.pokernews.com/strategy/eight-common-mistakes-beginners-make-in-pot-limit-omaha-32220.htm)
- Playing OOP is a structural disadvantage. Even the SB's goal is to "lose less" than other seats — [PLO Genius](https://plogenius.com/blog/taking-a-closer-look-at-small-blind); [SolvePLO playing OOP](https://solveplo.pages.dev/articles/playing-oop-in-plo)

### Inferences
- The c-bet pattern follows from range advantage: high-card and ace-high paired textures favor the opener, while low connected and draw-heavy boards favor the caller. Heads-up, both ranges are wider, so the same logic probably applies with larger magnitudes. This is unverified.
- Blocker bluffing (for example, holding the nut-flush blocker on a three-flush river) is widely taught, but no retrieved source gave solver frequencies for it.

### Gaps
- No free solver data was retrieved on turn/river play, blocker-driven bluff frequencies, check-raise frequencies (a SolvePLO check-raising article exists at https://solveplo.pages.dev/articles/check-raising-in-plo but was not fetched), wrap play, or HU postflop specifics.

## Common leaks and beginner mistakes

### Takeaway
The consensus leaks are: drawing to or stacking off with non-nut hands; overplaying aces, overpairs, and two pair; playing too many hands, especially out of position; set mining small pairs; slow-playing; and 3-betting badly constructed hands.

### Cited Findings
- Not drawing to the nuts, playing out of position too much, and set mining with mid or low pairs — [PokerNews five common mistakes](https://www.pokernews.com/strategy/do-not-make-these-five-common-plo-mistakes-42923.htm)
- Calling big bets with second-nut flushes, bottom sets, and non-nut straights; overplaying big overpairs, especially aces; slow-playing multiway; and weak starting-hand and position discipline — [PokerNews Eight Mistakes](https://www.pokernews.com/strategy/eight-common-mistakes-beginners-make-in-pot-limit-omaha-32220.htm); [rec.poker](https://rec.poker/announcements/blog/plo-for-beginners-tame-the-game-of-draws/)
- Overrating pocket two pair: fold it when the bigger pair isn't playable alone — [PokerNews Eight Mistakes](https://www.pokernews.com/strategy/eight-common-mistakes-beginners-make-in-pot-limit-omaha-32220.htm)
- 3-betting unconnected suited aces or low rundowns from the blinds — [SolvePLO 3-betting](https://solveplo.pages.dev/articles/3-betting-in-plo)
- Committing bare two pair deep, which is a bigger mistake as SPR rises — [Card Player SPR Part I](https://cardplayer.com/cardplayer-poker-magazines/66224-poker-year-in-review-26-1/articles/21011-pot-limit-omaha-the-stack-to-pot-ratio-spr-part-i)
- Tri "SuitedSuperman" Nguyen discussed avoiding beginner PLO mistakes in a Card Player interview — [Card Player](https://cardplayer.com/cardplayer-poker-magazines/66526-acr-poker-36-22/articles/24934-ky-suitedsuperman-nguyen-talks-how-to-avoid-beginner-plo-mistakes) (page content not fetched)

### Inferences
- Several "6-max" leaks become less severe heads-up, where the solver plays around 87% of hands from the button. Playing too many hands is mainly a leak in multiway and 6-max formats.

### Gaps
- Wrap misplays (for example, playing the low end of a wrap) were not covered in any fetched source.

## Tournaments vs cash, stack depth, ICM, multiway

### Takeaway
Shorter stacks shrink PLO opening ranges and shift sizing toward min-raises (around 20bb). PLO tournament advice traditionally favors tighter play. Some 2026 commentary argues that standard ICM fits PLO poorly because of close equities and the need for short stacks to re-accumulate.

### Cited Findings
- Stack depth: the button opens about 26% at 20bb (min-raise) and about 52% at 150bb (pot) — [SolvePoker stack depth](https://solvepoker.app/plo-stack-depth)
- Tournaments use strict pot-limit opens of up to about 3.5bb — [VIP-Grinders](https://vip-grinders.com/poker-strategy/omaha/beginners)
- "ICM is broken in PLO tournaments": short stacks may need to take more risk than ICM suggests in order to re-enter contention. The author calls this tentative (Aug 2026) — [PokerStrategy, Barry](https://www.pokerstrategy.com/news/content/ICM-is-broken-in-PLO-tournaments-l-Strategy-with-Barry_140474/)
- Older advice says correct PLO tournament play is usually tight on all streets, with the aim of waiting for others to bust. Stack management in PLO MTTs is difficult because chip stacks swing so much — [Card Player Piper "PLOnkaments" (2010)](https://cardplayer.com/poker-blogs/50-piper-on-pot-limit-omaha/entries/235441-plonkaments-part-ii); [Card Player: Stack Management in PLO tournaments](https://www.cardplayer.com/cardplayer-poker-magazines/66297-cppt-st-maarten-28-5/articles/22282-stack-management-in-pot-limit-omaha-tournaments-part-i-how-plo-tournaments-try-to-ruin-your-sanity)
- In general ICM, chip-EV-positive spots can become folds because busting costs more than the potential gain — [DeucesCracked ICM](https://www.deucescracked.com/learn/icm-final-table-strategy)
- Multiway: draw to the nuts and avoid slow-playing — [PokerNews Eight Mistakes](https://www.pokernews.com/strategy/eight-common-mistakes-beginners-make-in-pot-limit-omaha-32220.htm)

### Inferences
- Because PLO preflop all-ins are rarely worse than 35/65, ICM risk premiums interact differently than in NLHE. Close equities cut both ways: ICM can push you to avoid flips, and short stacks can't wait for spots with a big edge.

### Gaps
- No solver-based PLO ICM ranges or short-stack multiway PLO guidance was found.

## Omaha Hi-Lo principles

### Takeaway
The aim is to scoop. A2 is the most important low holding but is often quartered or counterfeited, so A2 plus a third low card (3 or 4) and high-side potential is much better. Freerolls (one half locked while drawing to the other) are the key edge.

### Cited Findings
- A2 is the most important low draw. A bare A2 has the nut low, alone or shared, about 25% of the time — [PokerSkill Omaha Hi-Lo](https://www.pokerskill.com/blog/omaha-hi-lo/); [DeucesCracked Omaha Hi-Lo](https://www.deucescracked.com/learn/omaha-hi-lo)
- Counterfeiting: the most common case is the board pairing your A or 2. A 3 or 4 alongside A2 protects the low (A-2-3-4 still plays low if either card pairs) — [Wikipedia Counterfeit](https://en.wikipedia.org/wiki/Counterfeit_(poker)); [PokerSkill](https://www.pokerskill.com/blog/omaha-hi-lo/)
- Don't overbet a bare nut low (A2 or A3 with a 2-3 low). It's often shared, and you end up quartered — [PokerSkill](https://www.pokerskill.com/blog/omaha-hi-lo/)
- Scoop means winning both halves. A freeroll means one half is locked and you're drawing at the other — [PokerStrategy glossary: Scoop](https://www.pokerstrategy.com/glossary/Scoop/); [DeucesCracked](https://www.deucescracked.com/learn/omaha-hi-lo)

### Gaps
- No solver-based Hi-Lo (PLO8/O8) data was retrieved. Hi-Lo sources are older heuristic articles.

## Strategy literature and training resources

### Takeaway
The classic texts are Jeff Hwang's *Pot-Limit Omaha Poker* (2008) and Bob Ciaffone's *Omaha Poker*, with *Mastering Small Stakes PLO* as a modern small-stakes book. The leading training is PLO Mastermind (solver-backed, expensive, less beginner-focused), plus Run It Once, PLO Quick Pro, and Upswing (mainly NLHE). The solver tools are GTO Wizard PLO (with HU added July 2026), PLO Genius, MonkerSolver, and Vision GTO.

### Cited Findings
- Hwang's *Pot-Limit Omaha Poker* (2008) is called a classic must-read focused on board texture and preflop selection. Ciaffone's *Omaha Poker* (2006, originally from the 1980s) is described as foundational — [PokerTraining: top 5 Omaha books](https://www.pokertraining.com/poker/blog/top-5-books-on-omaha-strategy/)
- *Mastering Small Stakes Pot-Limit Omaha*: key lessons summarized by D&B Poker — [D&B Poker](https://dandbpoker.com/blogs/news/key-lessons-from-mastering-small-stakes-pot-limit-omaha-and-a-special-offer); [Goodreads](https://www.goodreads.com/book/show/52882447)
- PLO Mastermind is PLO-specific, with solver-backed training and preflop ranges, but is expensive and less beginner-focused. Run It Once has a broad PLO library. PLO Quick Pro is high-level. Upswing covers PLO but is mostly NLHE — [Pokerfuse: best training sites for PLO (Aug 2026)](https://pokerfuse.com/latest-news/2026/8/best-poker-training-sites-teach-plo/); [PokerNews: PLO Mastermind](https://www.pokernews.com/poker-coaching/plo-mastermind/)
- GTO Wizard's PLO solver is sold as a separate subscription. A July 2026 update added HU PLO, nodelocking, and player profiles — [PokerNews](https://www.pokernews.com/news/2026/07/gto-wizard-launches-major-updates-to-its-plo-solver-52006.htm)
- The tool sites publishing free solver data include PLO.com (MonkerSolver-based), SolvePoker/SolvePLO, and PLO Genius — [PLO.com](https://plo.com/plo-heads-up-ranges); [SolvePoker docs](https://solvepoker.app/docs); [PLO Genius](https://plogenius.com/blog/taking-a-closer-look-at-small-blind)

### Gaps
- No retrieved source covered Rolf Slotboom's books (*Secrets of Professional Pot-Limit Omaha*, *Pot-Limit Omaha Poker*), Lasse Förster's *Pot-Limit Omaha Strategy*, Tri Nguyen's PLO content, Vision GTO, or Upswing PLO Lab in detail. Exact titles and descriptions should be verified before citing.
