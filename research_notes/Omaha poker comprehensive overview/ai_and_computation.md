# Omaha Poker: AI, Solvers, Hand Evaluation, and Game-Theoretic Complexity

Notes compiled 2026-11-07. Labels used throughout: **[peer-reviewed]**, **[preprint]**, **[vendor claim]**, **[affiliate/marketing]**, **[open-source repo README]**. A few canonical papers are cited with URLs from background knowledge. I did not re-fetch them in this session, and they are marked "(canonical, not re-fetched)".

---

## 1. Game size and complexity: heads-up PLO vs heads-up NLHE; card and action abstraction

### Takeaway
Exact sizes are published for heads-up limit and no-limit hold'em: HUNL (ACPC 200bb, 2010+ rules) has about 6.4×10^161 information sets. I found **no published exact count for heads-up PLO**. The structure still points one way. Each player has 270,725 private hands instead of 1,326 (about 204x more per player, and about 16,432 classes vs 169 after suit isomorphism). Pot-limit betting has a smaller action space than no-limit, but nowhere near enough to make up for that. So PLO is handled entirely with lossy card abstraction plus coarse bet abstraction, or with subgame/neural methods.

### Cited Findings
- **Heads-up limit hold'em (ACPC):** 3.162×10^17 game states and 3.194×10^14 information sets. Lossless suit isomorphism cuts this to 1.380×10^13 canonical infosets and 3.589×10^13 canonical infoset-actions. Exact solving with standard CFR would need about 523 TB of RAM (two 8-byte doubles per infoset-action). — [Johanson 2013, "Measuring the Size of Large No-Limit Poker Games", tech report](https://arxiv.org/abs/1302.7008) [tech report]
- **HUNL, 2010-present ACPC game** ($50/$100 blinds, $20,000 = 200bb stacks, any integer bet): about 6.31×10^164 game states and about 6.38×10^161 information sets. Standard CFR would need about 1.09×10^138 yottabytes of RAM. — [Johanson 2013](https://arxiv.org/abs/1302.7008)
- **HUNL, 2009 ACPC game** ($1/$2, $400 = 200bb): about 1.38×10^51 game states and about 1.39×10^48 infosets; CFR would need about 2.38×10^24 yottabytes. The 2007-08 game ($1/$2, 500bb) has 7.16×10^75 states. — [Johanson 2013](https://arxiv.org/abs/1302.7008). (The "1.39×10^48 infosets" figure that later papers cite for NLHE, e.g. [arXiv 1807.00900](https://arxiv.org/pdf/1807.00900), comes from this 200bb/$2-blind version.)
- **CFR memory model:** CFR's convergence bound is linear in the number of (canonical) information sets, and memory is about 2 doubles per infoset-action. This is the key scaling fact for PLO: memory grows with the private-hand count at every public node. — [Johanson 2013](https://arxiv.org/abs/1302.7008)
- **PLO private-hand space:** C(52,4) = 270,725 raw four-card hands, reduced to 16,432 suit-isomorphic preflop classes. By suit pattern: double-suited 3,081, single-suited 7,098, triple-suited 3,718, rainbow 1,820, monotone 715. — [Li & Huang, "Abstraction Agent", arXiv 2609.04303](https://arxiv.org/html/2609.04303v1) [preprint]
- One 2026 CFR paper uses PLO's 270,725 hands as its example of a game where "lossy abstraction becomes necessary". It has no PLO experiments. — [Li & Huang, "Real-Time Parallel CFR", arXiv 2605.19928](https://arxiv.org/html/2605.19928) [preprint]
- **Comparison with NLHE:** hold'em has 1,326 two-card combos and PLO4 more than 270,000 starting combos, before position, stack depth or runouts. — [pokerfuse solver guide](https://pokerfuse.com/learn-poker/tools/poker-solvers/) [industry guide]
- **PLO5/PLO6 classes:** PLO5 has 2,598,960 raw hands and 134,459 classes. PLO6 has 20,358,520 raw hands and 962,988 classes. — [ploadvisor PLO6 methodology page](https://ploadvisor.pages.dev/en/plo6-methodology) [low-quality site; the PLO5 raw count C(52,5)=2,598,960 is correct arithmetic, but I did not check the class counts independently]
- **Flop isomorphism:** there are 1,755 strategically distinct flops, used by GTO Wizard and SolvePLO to cover all flops. — [PokerNews / GTO Wizard PLO coverage](https://www.pokernews.com/poker-tools/gto-wizard/plo-solver.htm) [vendor claim]
- **Practitioner view:** a full PLO preflop solve without abstraction "will require several machines". — [Two Plus Two software forum](https://forumserver.twoplustwo.com/167/poker-software/piosolver-postflop-equilibrium-solver-holdem-1516187/index121.html) [forum, anecdotal]
- **MonkerSolver's approach:** it advertises "state of the art abstraction techniques to reduce game size". Solvable tree size scales with RAM (minimum 8 GB) and solve time with CPU speed. — [MonkerWare](https://monkerware.com/solver.html) [vendor]
- **Learned or semantic card abstraction for PLO (experimental):** an LLM proposes features (rank/pair strength, suitedness/flush potential, straight connectivity, all-card coordination, nut potential), scores all 16,432 classes, and k-means groups them into K=30 buckets. Evaluation is qualitative only, with no exploitability measured. The authors argue that evaluator-based abstractions (EHS, potential-aware) get expensive at PLO scale because of rollouts. — [arXiv 2609.04303](https://arxiv.org/html/2609.04303v1) [preprint; cluster descriptions are partly inconsistent with their representatives]
- **Standard abstraction families in the hold'em literature:**
  - Clustering-based automated abstraction (Gilpin & Sandholm). — [AAMAS 2007](https://www.ifaamas.org/Proceedings/aamas07/html/pdf/AAMAS07_0450_49c46463f25ec41a547caddd3cd39006.pdf) [peer-reviewed]
  - Imperfect-recall abstractions with bounded loss. — [arXiv 1803.05392](https://arxiv.org/pdf/1803.05392)
  - Asymmetric abstractions. — [Bard et al., AAMAS 2014](https://www.cs.ualberta.ca/~games/poker/publications/2014-aamas-asymmetric-abstractions.pdf) [peer-reviewed]
  - Higher-resolution imperfect-recall abstractions. — [arXiv 2510.15094](https://arxiv.org/pdf/2510.15094) [preprint]
  - None of these report PLO experiments in what I read.
- **Omaha rule constraint:** a hand must use exactly 2 hole cards and exactly 3 board cards. — [Wikipedia: Omaha hold 'em](https://en.wikipedia.org/wiki/Omaha_hold_%27em)

### Inferences
- **Rough PLO vs NLHE scaling:** a public betting node in a solver holds one range vector per player. The vector has 1,326 entries in NLHE and 270,725 in PLO4, minus board-blocked combos (with a 5-card board, C(47,4)=178,365 live hands). Per-node strategy and regret memory is therefore about 135–204x larger in PLO. Hand-vs-hand showdown evaluation at a river node scales with the square of range size unless done with sort-based O(n log n) methods, so the gap there is much larger.
- **Pot-limit vs no-limit betting:** pot-limit caps every bet at pot size, so the betting tree per public state is smaller than NLHE's with the same stacks. NLHE's 10^161 infoset figure comes mostly from allowing every integer bet size. Practical solvers abstract both games to 1–4 sizes anyway, so in practice the gap comes almost entirely from cards.
- **Typical PLO bet abstraction:** preflop limp/raise-pot (plus 3-bet/4-bet pot); postflop check, 33–50% pot, 75–100% pot (pot = maximum). A full HU PLO tree at 100bb usually puts players all-in by the 4-bet or by turn/river, which keeps the tree shallow.
- **Lossless suit isomorphism matters more in PLO** because the card space is so large. Flop, turn and river classes for PLO can be built with a generic hand indexer (see section 4).

### Gaps
- I found no peer-reviewed or technical source giving an exact count of game states or infosets for heads-up PLO under any betting abstraction. The Johanson counting algorithm and code could be adapted to produce one, but nobody appears to have published it.
- I found no published exploitability results (mbb/g) for any PLO abstraction.

---

## 2. Algorithms (CFR family, DeepStack, ReBeL, Pluribus) and published Omaha applications

### Takeaway
Every algorithm behind superhuman hold'em play (CFR+/DCFR tabular solving, MCCFR blueprints, depth-limited re-solving with value networks, Deep CFR/ReBeL) carries over to Omaha in principle. **I found no peer-reviewed paper reporting a strong or superhuman PLO agent.** Public Omaha work consists of open-source projects (PokerRL-Omaha, PLOAI), a Harvard thesis on an Omaha Hi-Lo jam/fold endgame, and preprints that mention PLO only as a motivating example. The ACPC never ran an Omaha event (inference, see below). Commercial PLO solvers are where the practical progress is, but their methods are undisclosed.

### Cited Findings
- **CFR** (Zinkevich et al. 2007): iterative regret matching at every information set, with average-strategy convergence at a rate linear in the number of infosets. — [Johanson 2013 summary](https://arxiv.org/abs/1302.7008); [original NeurIPS 2007 paper](https://proceedings.neurips.cc/paper/2007/hash/08d98638c6fcd194a4b1e6992063e944-Abstract.html) (canonical, not re-fetched)
- **CFR+** (Tammelin 2014), which essentially solved heads-up limit hold'em (Cepheus, Bowling et al., Science 2015). — [CFR+ arXiv 1407.5042](https://arxiv.org/abs/1407.5042); [Science 2015](https://www.science.org/doi/10.1126/science.1259433) (canonical, not re-fetched)
- **Discounted CFR / Linear CFR** (Brown & Sandholm, AAAI 2019): the usual tabular solver core today. — [arXiv 1809.04040](https://arxiv.org/abs/1809.04040) (canonical, not re-fetched). Newer neural variant: Deep (Predictive) Discounted CFR. — [arXiv 2511.08174](https://arxiv.org/pdf/2511.08174) [preprint]
- **Deep CFR** (Brown, Lerer, Gross, Sandholm, ICML 2019): neural networks approximate tabular CFR on the unabstracted game. Experiments are on HU limit hold'em. — [arXiv 1811.00164](https://arxiv.org/pdf/1811.00164) [peer-reviewed]
- **Single Deep CFR** (Steinberger 2019), with public code at github.com/EricSteinberger/Deep-CFR. — [arXiv 1901.07621](https://arxiv.org/pdf/1901.07621)
- **DeepStack** (Moravčík et al., Science 2017): continual re-solving with deep counterfactual value networks; beat professionals at HUNL. — [arXiv 1701.01724](https://arxiv.org/abs/1701.01724) (canonical, not re-fetched). An analysis of DCFV networks and of the 1.39×10^48-infoset NLHE scale motivating them: — [arXiv 1807.00900](https://arxiv.org/pdf/1807.00900); [KI 2018 paper](https://ke-tud.github.io/publications/papers/KI18-PokerDCVNN.pdf)
- **Libratus** (Brown & Sandholm, Science 2018): blueprint plus nested safe subgame solving for HUNL. — [Science](https://www.science.org/doi/10.1126/science.aao1733) (canonical, not re-fetched). Endgame solving background: — [Ganzfried & Sandholm, AAMAS 2015](https://www.ifaamas.org/Proceedings/aamas2015/aamas/p37.pdf) [peer-reviewed]
- **Pluribus** (Brown & Sandholm, Science 2019): 6-max NLHE, MCCFR blueprint plus depth-limited search. — [Science](https://www.science.org/doi/10.1126/science.aay2400) (canonical, not re-fetched)
- **ReBeL** (Brown et al., NeurIPS 2020): RL plus search over public belief states. — [arXiv 2007.13544](https://arxiv.org/abs/2007.13544) (canonical, not re-fetched)
- **Real-Time Parallel CFR (2026):** a 3.3–3.4x postflop speedup over single-threaded CFR, about 47–54 ms per iteration on a tree with more than 1.08 billion histories (HUNL), and about 7x lower river-subgame exploitability than PokerRL at equal wall-clock time, on an NVIDIA DGX Spark. Cites PLO as needing lossy abstraction. — [arXiv 2605.19928](https://arxiv.org/html/2605.19928) [preprint]
- **GPU-CFR (2026)** claims 80x faster CFR by compiling the game to static dataflow and CUDA Graph replay. I could not confirm Omaha coverage. — [arXiv 2609.11923](https://arxiv.org/pdf/2609.11923) [preprint; title-level only]
- **PokerRL-Omaha** (GitHub fork of PokerRL):
  - Adds PLO with Deep CFR and SD-CFR for 2–6 players.
  - The Omaha evaluator is "naive and slow": the 2+3 combo logic sits on top of the hold'em evaluator.
  - Training uses a GPU/CPU distributed scheme, with a claimed 2–3x cycle-time cut. A dense residual network "significantly outperforms" the original network head-to-head.
  - Preflop hand bucketing is handcrafted.
  - No exploitability numbers.
  - The author says the internet lacked open-source Omaha RL code.
  - [github.com/diditforlulz273/PokerRL-Omaha](https://github.com/diditforlulz273/PokerRL-Omaha) [repo README]
- **PLOAI** (robb17): a PLO agent built from two rounds of abstraction, then CFR or MCCFR. Its stated goal is "at least as good as a decent human player". — [github.com/robb17/PLOAI](https://github.com/robb17/PLOAI) [repo README]
- **Omaha Hi-Lo thesis (Harvard):** "A No-Limit Omaha Hi-Lo Poker Jam/Fold Endgame Equilibrium", which uses CFR+ to compute a two-player tournament jam/fold equilibrium. — [Harvard DASH](https://dash.harvard.edu/server/api/core/bitstreams/7312037d-b83c-6bd4-e053-0100007fdf3b/content) [undergraduate thesis]
- **Other research and tooling repos:**
  - jimmy-sim/poker-ai: a from-first-principles CFR/MCCFR research repo. — [GitHub](https://github.com/jimmy-sim/poker-ai)
  - Multiplayer CFR in non-zero-sum games (Risk & Szafron). — [arXiv 1305.0034](https://arxiv.org/pdf/1305.0034)
  - Neither is Omaha-specific.
- **Survey of CFR-family dominance in poker AI:** — [arXiv 1906.04439](https://arxiv.org/pdf/1906.04439)

### Inferences
- The ACPC (2006–2018) ran heads-up limit, heads-up no-limit and 3-player hold'em only, with no Omaha track (background knowledge; I did not verify it against ACPC pages this session). No Omaha agent has ever had a public benchmark like Slumbot or ACPC results.
- **Recommended stack for a compute-limited HU PLO bot:**
  - (a) Preflop: a precomputed blueprint over the 16,432 classes, or a bucketed version of them.
  - (b) Postflop: real-time re-solving of the current street, as in DeepStack/Libratus, with a small bet abstraction, over isomorphic flops (1,755).
  - (c) Depth limit at turn/river roots: equity or value-network leaf estimates.
- PLO's large ranges strain DeepStack-style value networks, whose input is the range vector (about 270k vs 1,326 entries). Practical neural approaches would encode hands with features or embeddings rather than one-hot range vectors.
- MCCFR (external or outcome sampling) helps PLO more than NLHE, because full chance-node enumeration is far more expensive.

### Gaps
- I found no peer-reviewed PLO agent with measured exploitability or head-to-head results against humans or other bots.
- Commercial engines (GTO Wizard, Vision, PLO Genius/Deepsolver) do not publish their algorithms. Whether any uses neural nets or "AI" solving for PLO is unconfirmed.

---

## 3. Commercial and public PLO solvers and tools (as of November 2026); bots and bot detection

### Takeaway
As of late 2026 the main PLO tools are:
- **MonkerSolver**: local desktop CFR with abstraction, multiway, RAM-bound, €499.
- **GTO Wizard PLO**: cloud; launched spring 2026, with heads-up custom solves, nodelocking and opponent profiles added by July 2026; PLO5 promised.
- **Vision**: a precomputed-solution browser and trainer, built on a Monker-derived workflow.
- **PLO Genius** (Deepsolver): a cloud solver and trainer.
- **PLO Mastermind**: an education platform whose solver sits on its higher tiers.

PioSOLVER is a hold'em solver. Nearly all capability statements come from vendors or affiliates. I found no independent accuracy benchmark. Bot activity in PLO is documented historically (a 2015 PokerStars mid-stakes PLO ring), but reliable 2025–26 PLO-specific reports are thin.

### Cited Findings
- **MonkerSolver** (MonkerWare): solves "Omaha and Hold'em from any street with any number of players", using abstraction. Requires Windows 64-bit or macOS and at least 8 GB RAM; tree size scales with RAM. The free version is limited to turn and river; the full version costs €499. — [monkerware.com/solver.html](https://monkerware.com/solver.html) [vendor]. Affiliate sites describe it as needing workstation hardware and being strong for PLO and multiway spots. — [SolvePLO "best PLO solver 2026"](https://solveplo.pages.dev/best-plo-solver) [affiliate/competitor]
- **GTO Wizard PLO:**
  - PLO4 for cash and MTT, preflop to river, covering all 1,755 flops and every turn and river, with custom sizings, ranges and boards. Standalone subscription with a free basic tier. — [PokerNews tool page](https://www.pokernews.com/poker-tools/gto-wizard/plo-solver.htm); [PokerListings launch](https://www.pokerlistings.com/news/gto-wizard-launches-plo-solver) [vendor claims via affiliate press]
  - **July 28, 2026 update:** fully customizable heads-up PLO strategies preflop to river; nodelocking (the engine finds the least-exploitable strategy consistent with locked frequencies); 8 default player profiles (GTO-savvy, fish, calling station, maniac, TAG, LAG, nit, "Glass Cannon") applied on every street, plus custom profiles; postflop ICM including bounties; river spots solving about 2x faster than at launch at 0.1% pot exploitability; larger maximum tree size for deeper stacks. The PLO engine work also made NLHE solves 3–6x faster.
  - PLO5 and mobile are "in the pipeline" with no date. The algorithm is not disclosed. — [PokerNews, Jul 2026](https://www.pokernews.com/news/2026/07/gto-wizard-launches-major-updates-to-its-plo-solver-52006.htm) [vendor claims via press]
  - The exact launch date is inconsistent across sources ("a couple of months" before July 2026).
- **Vision:** created by Matthias Pum (Austria), started in 2018 after he had used Monker since 2017; Run It Once became a full partner in 2020. Features include a Hand Categorization view, a Flop Overview, a Preflop RFI trainer and Streak Mode. The article is labeled an advertisement and gives no generation method. — [PokerNews](https://www.pokernews.com/strategy/vision-a-user-friendly-revolution-in-plo-training-47342.htm) [advertorial]. Affiliate pages put its price at about $200–$250/month, with no free tier, and call it the strongest PLO/PLO5 option. — [SolvePLO vs Vision](https://solveplo.pages.dev/compare/vision); [DeucesCracked](https://www.deucescracked.com/tools/gto-solvers) [affiliate]
- **PLO Genius:** a browser-based cloud PLO solver and trainer by Deepsolver (Warsaw), at about $60–$99/month; board coverage depends on the package. — [SolvePLO vs PLO Genius](https://solveplo.pages.dev/compare/plo-genius) [competitor/affiliate]
- **PLO Mastermind:** an education platform with videos, courses and a community; the solver is on higher tiers at about $99–$199/month. — [SolvePLO vs PLO Mastermind](https://solveplo.pages.dev/compare/plo-mastermind) [competitor/affiliate]
- **SolvePLO** (competitor) says it sells a MonkerSolver-based tool at $60/month covering all 1,755 flops. — [solveplo.pages.dev](https://solveplo.pages.dev/best-plo-solver) [vendor claim]
- **PioSOLVER** is described as a "postflop equilibrium solver for Holdem". — [Two Plus Two thread](https://forumserver.twoplustwo.com/167/poker-software/piosolver-postflop-equilibrium-solver-holdem-1516187/index121.html). I found no evidence of PLO support.
- **Bots:**
  - In 2015 PokerStars investigated suspected bots in mid-stakes PLO cash games; the ring reportedly won about $1.5M. — [VIP-Grinders bot farm article](https://www.vip-grinders.com/massive-bot-farm-online-poker-sites/) [secondary]
  - PokerStars, April 2026: "Ban early, ban quickly has been our approach with these bot rings." — [pokerfuse](https://pokerfuse.com/the-rail/2026/4/?post=3892)
  - Claims of QQPK banning 893 bots in 2026 and an ACR real-time-assistance case in Sept 2026 appear only secondhand. — [VIP-Grinders](https://www.vip-grinders.com/massive-bot-farm-online-poker-sites/) [unverified]
  - Unconfirmed allegations link the "Deeplay" bot farm to WPT Global. — [poker.academy](https://poker.academy/blog/post/wpt-global-poker-bot-controversy-130-accounts-new-allegation) [allegation]
  - Operator integrity teams of about 60 people combine ex-pros and data scientists. — [European Business Magazine](https://europeanbusinessmagazine.com/how-poker-bot-detection-wars-are-saving-platform-integrity/) [low specificity]
  - Several 2026 "GGPoker bot detection" pages (dev.to/pokerhackorg, pokerbot-com, ggpokerbot-com) appear to be bot-vendor marketing and should not be trusted.

### Inferences
- **Two kinds of commercial products:** "solution browsers" (precomputed libraries: Vision, GTO Wizard preflop libraries) and "custom solvers" (Monker local; GTO Wizard and PLO Genius in the cloud). GTO Wizard's reported 0.1%-pot river target, together with nodelocking and profiles, means its PLO engine supports exploitative best-response-style solving, which matters for opponent modeling.
- For a research bot, MonkerSolver output (ranges and strategies) is the most practical source of a PLO preflop blueprint or a reference to validate against.

### Gaps
- I found no reliable source for Odin or ProPokerTools (Oracle/Odds Oracle PLO equity features) in this session, or for Vision's and PLO Genius's actual solving methods and abstraction granularity.
- I found no independent accuracy or speed benchmark across PLO solvers.
- I found no reputable 2025–26 report of a PLO-specific bot ring.

---

## 4. Hand evaluation for Omaha; equity; isomorphism; Hi-Lo

### Takeaway
A naive Omaha evaluation calls a 5-card evaluator 60 times: C(4,2)×C(5,3) = 6×10. HenryRLee's PokerHandEvaluator (PHEvaluator) avoids that with a perfect-hash table, at the cost of memory: about 30 MB for PLO4, 112 MB for PLO5 and 353 MB for PLO6. Hold'em evaluators (2+2 7-card table, OMPEval, Cactus Kev) do not apply directly because of the use-exactly-2-and-3 rule. Use them through 60-combo loops or rank-reduced tricks. Suit isomorphism (Waugh's hand indexer) gives 16,432 preflop classes and also indexes later streets.

### Cited Findings
- **PHEvaluator** (HenryRLee, Apache-2.0, C/C++ with Python `phevaluator` and ports in C#, Rust, TS, WASM):
  - Evaluates 5-, 6- and 7-card hands and PLO4/5/6 "without brute-force combination checking", using a perfect hash into a precomputed table. The method is a "slight modification" of the hold'em algorithm and is documented in `Documentation/Algorithm.md`.
  - Memory: phevalplo4 30,516 KB; phevalplo5 112,296 KB; phevalplo6 353,484 KB.
  - Benchmarks (2023, 12×2.6 GHz): random PLO4 3,054 ns, PLO5 3,300 ns, PLO6 3,441 ns. — [github.com/HenryRLee/PokerHandEvaluator](https://github.com/HenryRLee/PokerHandEvaluator); [PyPI phevaluator](https://pypi.org/project/phevaluator/0.5.3/) [repo]
  - **Caution:** the README also shows "~32 M/s", which conflicts with 3,054 ns per evaluation (that would be about 0.33 M/s). The benchmark may time a batch per iteration. Benchmark it yourself before relying on either figure.
- **OMPEval** (zekyll): a fast C++ Texas Hold'em evaluator and equity calculator for 0–7 card hands, giving a 16-bit rank, with Monte Carlo and full-enumeration equity. I found no documented native Omaha support. AyaPoker, a Rust derivative, ranks Omaha hands. — [github.com/zekyll/OMPEval](https://www.github.com/zekyll/OMPEval); [uoftcprg fork](https://github.com/uoftcprg/OMPEval); [aya-poker](https://awesome.ecosyste.ms/projects/github.com%2Fdtrifuno%2Faya-poker)
- **TwoPlusTwo 7-card evaluator** (state-machine lookup table): — [TwoPlusTwoHandEvaluator mirror](https://relatedrepos.com/gh/tangentforks/TwoPlusTwoHandEvaluator). It is hold'em-oriented; the 2+3 rule makes a direct 9-card walk invalid.
- **PokerRL-Omaha** layered the Omaha combo rule on a hold'em evaluator. The author calls it slow, and it slows LBR rollouts. — [GitHub](https://github.com/diditforlulz273/PokerRL-Omaha)
- **Waugh hand isomorphism** ("A Fast and Optimal Hand Isomorphism Algorithm", AAAI Computer Poker Symposium 2013): a C library mapping hands to a tight index under suit permutation and within-round reordering. It supports multi-round configurations, e.g. [4] then [4,3] then [4,3,1] then [4,3,1,1] for PLO, and has a Rust wrapper `hand_indexer` (MIT). — [docs.rs hand_indexer](https://docs.rs/crate/hand_indexer/latest/source/src/hand_indexer.rs); [lib.rs](https://lib.rs/crates/hand_indexer)
- **Preflop and flop counts:** 16,432 PLO4 classes, by suit pattern as in section 1. — [arXiv 2609.04303](https://arxiv.org/html/2609.04303v1). 1,755 distinct flops. — [GTO Wizard via PokerNews](https://www.pokernews.com/poker-tools/gto-wizard/plo-solver.htm)
- **Rule:** exactly 2 hole and 3 board cards for high (and for low in Hi-Lo). — [Wikipedia](https://en.wikipedia.org/wiki/Omaha_hold_%27em)

### Inferences (engineering guidance; not sourced in this session)
- **Fast Omaha high without giant tables:**
  - Precompute the 6 hole pairs and 10 board triples.
  - Flush is possible only if some hole pair is suited and the board has 3 or more of that suit. Handle that path separately.
  - Otherwise evaluate on ranks only, with a 5-rank lookup (about 6,175 distinct non-flush rank multisets for 5 cards). That gives 60 cheap rank-table lookups.
  - Evaluate the board-triple ranks once per board and reuse them across all hands in a range. This is the dominant trick for solver showdowns.
- **Range-vs-range showdown:** for each of the about 178k live hands, compute the best rank once per river, then sort. Compute equity or EV with a prefix-sum sweep that handles card removal (blockers) by inclusion–exclusion over shared cards. This is the standard O(n log n) river-evaluation approach from hold'em solvers, and it matters far more in PLO. With 4 hole cards, card removal has to subtract hands sharing any of 4 cards: subtract per-card sums, add back per-pair sums, and so on.
- **Equity calculation:**
  - Hand vs hand preflop: C(44,5) = 1,086,008 runouts, so full enumeration is feasible but slow per pair.
  - Hand vs range: Monte Carlo with about 10k–100k samples gives about 0.3–0.5% standard error.
  - On the flop, C(45,2) = 990 runouts for heads-up, so enumeration is cheap.
  - Equity tables over the 16,432 classes against a random hand are a cheap preflop feature.
- **Hi-Lo (8-or-better) low:**
  - Use exactly 2 hole and 3 board cards, all 5 with distinct ranks of 8 or lower (A counts low). Straights and flushes are ignored for low.
  - A qualifying low needs at least 3 distinct board cards of 8 or lower. Compute the best low as the lexicographically smallest sorted rank tuple, encoded as a 13-bit rank mask, from a small table.
  - Quartering and scooping make EV non-linear in rank. Showdown sweeps need separate high and low passes.

### Gaps
- I did not fetch the PHEvaluator `Algorithm.md`, so the exact Omaha hash construction is not described here. I also did not verify the Cactus Kev page or ProPokerTools' evaluator, and found no published Omaha Hi-Lo evaluator benchmarks.

---

## 5. Practical heuristics for a competitive heads-up PLO agent with limited compute

### Takeaway
With modest compute, the strongest feasible design is a hybrid:
1. Preflop: a small precomputed blueprint over isomorphic or bucketed hands.
2. Postflop: real-time, street-limited CFR re-solving with 2–3 pot-fraction sizes.
3. Leaves: equity- or rollout-based estimates.
4. Lightweight opponent modeling layered on through nodelock-style best responses.

Commercial tools show this works in practice: GTO Wizard's nodelocking and profiles, and Monker-based libraries.

### Cited Findings
- Re-solving or subgame solving on a blueprint is the proven path in large HU games. — [DeepStack](https://arxiv.org/abs/1701.01724); [Libratus](https://www.science.org/doi/10.1126/science.aao1733); [Endgame solving, AAMAS 2015](https://www.ifaamas.org/Proceedings/aamas2015/aamas/p37.pdf)
- Parallel CFR on commodity or GPU hardware can reach about 50 ms per iteration on billion-history trees, enough for real-time street re-solves (HUNL result). — [arXiv 2605.19928](https://arxiv.org/html/2605.19928)
- Nodelocking finds the least-exploitable strategy consistent with locked opponent frequencies, and profile-based exploit strategies are now standard in commercial PLO tools. — [PokerNews Jul 2026](https://www.pokernews.com/news/2026/07/gto-wizard-launches-major-updates-to-its-plo-solver-52006.htm)
- Strategic features that matter for PLO hand abstraction: nut potential, suitedness (double-suited being best, with the ace of a suit valuable), connectivity (rundowns), all-four-card coordination (danglers hurt), and domination risk. Four-flush and trips holdings are weak because of the must-use-two rule. — [arXiv 2609.04303](https://arxiv.org/html/2609.04303v1)
- A residual dense network outperformed a plain network in Deep CFR for PLO, and handcrafted preflop bucketing was used. — [PokerRL-Omaha](https://github.com/diditforlulz273/PokerRL-Omaha)

### Inferences (design recommendations)
- **Pot-limit action generation:**
  - Max raise-to = current bet faced + (pot after calling). For example, facing bet B into pot P (P includes B), max raise-to = B + (P + B) = P + 2B, which is 3B + P_before.
  - Min raise = previous raise increment.
  - The legal action set is always bounded, so encode actions as {fold, check/call, min-raise, 50% pot, pot}, plus all-in when stack ≤ pot-raise.
  - Preflop, the blinds count toward the pot: HU SB pot-raise to 3bb (SB 0.5 completes to 1, pot becomes 2, raise 2 more, so 3bb total).
- **Card abstraction:**
  - Preflop: all 16,432 classes, or 200–1,000 buckets by EHS plus suitedness/connectivity features.
  - Flop: potential-aware buckets (equity-distribution histograms over turn/river) via k-means with EMD, combined with lossless isomorphic flops (1,755).
  - Turn/river: bucket by EHS and EHS², or solve exactly in a street-limited re-solve, where the range is the only large dimension.
- **Compute-saving tricks:**
  - Prune hands with near-zero reach.
  - Re-solve only the current street with depth-limited leaves, estimating continuation values by equity times pot or by a few rollouts.
  - Use CFR+/DCFR with alternating updates.
  - Store regrets as float32 or int16.
  - Exploit card removal via suit isomorphism on the board.
- **Equity-based baseline policy:** PLO equities run closer than NLHE (top hands vs random are about 60–65% rather than 85%; from general knowledge, unverified here). Pure equity/pot-odds play is exploitable but a reasonable fallback. Combine equity with nut-potential and blocker features (holding the nut-flush blocker) for bluff selection.
- **Opponent modeling:** track VPIP/PFR/3-bet, c-bet and fold-to-pot-bet frequencies. Use Bayesian frequency estimates to nodelock the opponent in a subgame solve and compute a restricted best response, with a mixing weight toward equilibrium for safety. This mirrors the "safe exploitation" ideas.
- **Hand evaluation budget:** a 30 MB perfect-hash PLO4 table (PHEvaluator) or a rank-only 60-combo evaluator with board-triple caching. Precompute per-river hand ranks for every live hand once, then reuse across all CFR iterations.

### Gaps
- I found no published PLO-specific results on which abstraction granularities or bet sets minimize exploitability per unit of compute. Recommendations above are extrapolated from hold'em literature and solver practice.
- I found no head-to-head data on equity-heuristic PLO bots vs solver-based bots.
