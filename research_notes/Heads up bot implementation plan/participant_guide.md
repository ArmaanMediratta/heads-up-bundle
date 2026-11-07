# Participant Guide Extraction: TAMU Datathon Poker Bot Challenge (Heads-Up Short Deck 5-Card PLO)

Source for every citation below: the 15-page PDF "Heads Up Participant Guide - Google Docs.pdf" (distributed by the organizers; not stored in this repo, cited as [Guide p.N]). The text was extracted in full with pypdf; every page (1-15) was read. Text in quotation marks is copied exactly from the guide (whitespace normalised). Text without quotes is a close paraphrase. Anything under "Inferences" is my own interpretation, not the guide's.

Guide table of contents [Guide p.2]: 1 Challenge at a glance; 2 Getting started; 3 The game; 4 Writing your bot; 5 Time limits, errors and forfeits; 6 Scoring; 7 Where your bot runs; 8 Testing locally; 9 Submitting; 10 Strategy ideas; 11 FAQ; 12 Quick reference.

## Q1. Competition purpose and the exact game (variant, format, stacks, blinds, hand count, betting, rule changes)

### Takeaway
You write a Python bot (a small web server) that plays heads-up Short Deck (36-card) 5-card Pot-Limit Omaha against every other team's bot in a round robin. Each match is 2,000 hands in duplicate format. Stacks are 80 chips (40 bb) and reset every hand. Blinds are 1/2, there are only 4 discrete actions (fold, check/call, half-pot raise, pot raise), raises are capped at 4 per street, and hand rankings are the Short Deck ones: flush beats full house, trips beat a straight, and A-6-7-8-9 is the lowest straight.

### Cited Findings
**Purpose / framing**
- "Write a program that plays poker. Your Python bot will play every other team's bot in a round-robin tournament, thousands of hands per match, and the best bot wins." [Guide p.1]
- The bot is "a small Python web server that receives a description of the game, decides what to do, and answers with an action. A referee program (the judge) deals the cards, asks each bot for its move, enforces the rules, and keeps score." [Guide p.3]
- "Any approach is allowed: hand-written rules, simulations, statistics, or machine learning. You choose the libraries." [Guide p.3]
- Event branding: "TAMU DATATHON / Poker Bot Challenge / Participant Guide: Heads-Up Short Deck 5-Card Pot-Limit Omaha" [Guide p.1]

**Deck and card encoding**
- "Short Deck uses only 36 cards: the ranks 6, 7, 8, 9, T (ten), J, Q, K, A in four suits (clubs c, diamonds d, hearts h, spades s). The 2s, 3s, 4s and 5s are removed." [Guide p.5]
- Integer encoding, 0 to 35: `rank = card >> 2  # 0 = six, 1 = seven, ..., 7 = king, 8 = ace` and `suit = card & 3  # 0 = clubs, 1 = diamonds, 2 = hearts, 3 = spades`. Helpers in evaluator.py: `card_rank(c)`, `card_suit(c)`, `cards_to_str(cards)`, for example "`cards_to_str([35, 0])` gives `"As 6c"`". [Guide p.5]

**Hand rankings (Short Deck)**, best to worst [Guide p.5]:
1. Straight flush
2. Four of a kind
3. Flush ("Beats a full house in Short Deck")
4. Full house
5. Three of a kind ("Beats a straight in Short Deck")
6. Straight
7. Two pair
8. One pair
9. High card
- "The ace is high and low. ... it can also act as the low card in the straight A-6-7-8-9 (the missing 2-5 are skipped). That is the lowest straight: it loses to 6-7-8-9-T. The same goes for straight flushes." [Guide p.5]
- "Ties inside the same category are broken by the usual card-by-card comparison ... Suits never break ties. Exactly equal hands split the pot." [Guide p.5]

**Omaha rule**
- "each player makes their best five-card hand using exactly two of their five hole cards and exactly three of the five board cards. ... That gives 10 × 10 = 100 possible hands, and the best one counts." [Guide p.5]
- Worked example: Board Ah Kh Qh Jh 6c, hand Th 7s 7d 8c 9c. You do not have a royal flush, and you have no flush. Best hand is a king-high straight using Th 9c + Kh Qh Jh. "lots of one suit on the board doesn't give you a flush unless two of your hole cards are that suit." [Guide p.6]
- "`omaha_score(hole_cards, board)` applies this rule for you and returns a number: higher is better, equal is a tie. It needs the full five-card board." [Guide p.6]

**Hand flow**
- "Both players start with 80 chips (stacks reset every hand, so a bad hand never carries over). The button posts the small blind (1), the other player the big blind (2). Each player gets 5 hole cards." [Guide p.6]
- "Preflop. The button acts first." On the flop, turn and river, "the non-button player acts first." [Guide p.6]
- "After a preflop call of the big blind, the big blind still gets to act (check or raise) before the flop. This is called the big blind's option." [Guide p.6]
- "If a player goes all-in and the bets are matched, there is no more betting: the rest of the board is dealt and the hand goes to showdown." [Guide p.6]
- Glossary: "Results are measured in bb, so +1 bb means you won 2 chips. Each player starts every hand with 40 bb." "Button: The player who posts the small blind. The button alternates every hand." [Guide p.4]

**Actions and their legality** [Guide p.6-7]
- FOLD: legal "Only when you owe chips (to_call > 0). You can't fold when checking is free."
- CHECK_CALL: legal "Always". "If you can't afford the full call, you go all-in with what you have."
- RAISE_HALF: "Raise by about half the pot".
- RAISE_POT: "Raise by the size of the pot, the most allowed ("pot-limit")".
- Both raises are legal only if all of these hold: "Fewer than 4 raises have happened on this street (blinds don't count). After 4, players can only call or fold."; "You have more chips behind than you need to call (my_stack > to_call)."; "Your opponent is not already all-in."
- "Always pick from obs.legal_actions. It lists exactly what you may do right now."

**Raise sizing** (exact formulas) [Guide p.7]
```
pot_raise_to  = opp_bet + pot + to_call             # the pot-limit maximum
half_raise_to = opp_bet + (pot + to_call) // 2
min_raise_to  = opp_bet + max(last raise size, 2)    # a raise must be at least this big
raise_to = min( max(target, min_raise_to), pot_raise_to, my_bet + my_stack )
```
- "'Raise to' means your total bet on this street afterwards." Amounts are precomputed: "obs.raise_to[Action.RAISE_HALF] and obs.raise_to[Action.RAISE_POT] already hold the exact totals." "You never choose an amount." [Guide p.7]
- Worked example [Guide p.7]: preflop pot 3, A (button) to call 1: half to 4, pot to 6. A pots to 6. B: to_call 4, pot 8, half to 12, pot to 18. B pots to 18. A calls, so the pot is 36 and each player has 62 left. Flop, B first: half 18, pot 36. B bets 36. A: to_call 36, pot 72, a pot raise would be 144, so both raise options become all-in for 62. B: to_call 26 with exactly 26 left, so B "can't raise" and may only FOLD or CHECK_CALL. "two players can be all-in on the flop."

**Match length**
- "Each match is 2,000 hands, played so that both bots get exactly the same cards" [Guide p.3]. Quick reference: "2,000 (1,000 deals × 2 halves, seats swapped)" [Guide p.15]

### Inferences
- I checked the worked example against the formulas and every step matches (for example, preflop pot raise = 2+3+1 = 6). The formulas are consistent.
- With 40 bb stacks and pot-sized raises, a 3-bet pot preflop (18 each) already commits 45% of the stack. The game is therefore effectively very shallow, and push/fold-style and commitment logic will matter.
- Because stacks reset every hand, there is no tournament or ICM dynamic. Every hand is an independent chip-EV problem.
- The extra preflop raises allowed by the 4-raise cap are mostly moot, since stacks are exhausted after about 3 pot raises.

### Gaps
- "last raise size" in min_raise_to is not defined in the guide (for example, what it equals preflop, or after a short all-in). The guide says game.py is the source of truth [Guide p.14].
- The guide does not say whether a short all-in raise reopens raising for the opponent. It also doesn't say how `min_raise_to` interacts when RAISE_HALF is below the minimum. The formula clamps it up, so RAISE_HALF and RAISE_POT may produce equal amounts. This can be checked in game.py.

## Q2. Required bot interface (functions, observation, actions, return values, limits, libraries)

### Takeaway
You edit only the `# ===== YOUR CODE HERE =====` section of `agent.py`. It holds three functions: `new_half(config, memory)`, `choose_action(obs, memory) -> Action` and `on_hand_end(result, memory)`. Your code must return a member of `obs.legal_actions`. You get an 8-second thinking budget per 1,000-hand half and at most 1 second per request. The machine has 1 CPU, 4 GB of RAM and no internet, and only `/tmp` is writable. Python 3.10+ is required, any library is allowed, and PyTorch CPU is preinstalled.

### Cited Findings
**Files and what you may edit** [Guide p.3-4]
- agent.py: "Your bot. A complete web server with three empty functions for your strategy." Edit "Yes, between the YOUR CODE HERE markers".
- game.py: "The rules: dealing, betting, legal actions, raise sizes, showdown. Read it to settle any rules question." Do not edit.
- evaluator.py: "Card helpers and a fast hand evaluator (omaha_score)." Do not edit.
- judge_engine.py: "The referee. Run it locally to play your bot against another bot." Do not edit.
- baseline-bots/: "Simple opponents to test against, e.g. baseline_random.py." "No (copy them freely)".
- test_agent.py: "Checks that the tournament can run your bot." Do not edit.
- "The tournament uses its own copies of game.py, evaluator.py and the judge, so changes you make to those files have no effect there. Only agent.py (and any files it imports) is yours." [Guide p.4]
- "The bottom half of the file (marked SERVER PLUMBING) is the web server that talks to the judge. Don't change it" [Guide p.7]
- First edits: set `PARTICIPANT` to your team name and `AGENT_NAME` to a bot name, then replace the example strategy in `choose_action()` [Guide p.4]

**The three functions** [Guide p.8]
- `new_half(config, memory)`: called "Once at the start of each half-match (1,000 hands)." Use it to set up tracking, e.g. `memory["opp_raises"] = 0`.
- `choose_action(obs, memory)`: called "Every time it's your turn." "Look at obs and return one of `obs.legal_actions`."
- `on_hand_end(result, memory)`: called "Once after every finished hand." "Optional: learn from what happened".
- The example signature is `def choose_action(obs: Observation, memory: dict) -> Action:`. The example needs `from evaluator import FLUSH` and `from game import Street`. The guide says this example "loses to the random baseline bot". [Guide p.8]
- Score encoding: "Hand scores keep the hand category in their top bits, so score >> 20 gives the category from 0 = high card to 8 = straight flush. category_name(score) turns it into text like "flush"." The example uses `score >= (FLUSH << 20)`. [Guide p.8]

**Observation fields** ("All chip amounts are whole numbers") [Guide p.8-9]
- `hand_index`: 0..999 within the half
- `street`: Street.PREFLOP / FLOP / TURN / RIVER
- `hole_cards`: "Your 5 cards as integers, sorted from low to high."
- `board`: 0/3/4/5 cards
- `pot`: "All chips both players have put in this hand, blinds included."
- `to_call`: "0 means you can check."
- `my_bet`, `opp_bet`: chips put in "on this street (blinds count preflop)"
- `my_stack`, `opp_stack`: "Chips each player still has behind (not yet bet)."
- `is_button`: True if you are the button (small blind)
- `legal_actions`
- `raise_to`: for each legal raise, the total street bet after it, e.g. `{RAISE_HALF: 12, RAISE_POT: 18}`
- `min_raise_to`: "The smallest normal raise total (an all-in can be smaller)."
- `raises_this_street`: maximum 4
- `action_history`: "Every action this hand so far, oldest first. Each has street, is_me (True if it was yours), action, amount (chips that action added) and street_total. Blinds are not listed."
- `big_blind`: 2

**HandResult fields** [Guide p.9]
- `hand_index`, `my_net` (chips won or lost), `pot` (final), `went_to_showdown`, `board` (only the cards shown by the time of a fold), `opp_hole` ("only after a showdown; otherwise None"), `winner` ("me", "opp" or "split").
- "finished hands are delivered together with your next decision, so on_hand_end always runs before choose_action sees the next hand. The last few hands of a half are delivered when the half ends." [Guide p.9]

**Memory / state** [Guide p.9]
- memory "is wiped clean at the start of each half. In the tournament, each half also runs in a brand-new copy of your server, so nothing at all (not memory, not global variables, not files) carries over from one half to the other."
- "Reading files that are part of your repository (for example a trained model loaded when the file starts) is fine."

**Rules for your code** [Guide p.9]
- "Always return a value from obs.legal_actions. Anything else counts as an error"
- "Your server answers one request at a time, so your functions never run twice at once."
- The guide recommends wrapping your strategy in try/except with a fallback to CHECK_CALL.
- "Don't try to interfere with the judge, the other bot, or the machine. Bots that do will be disqualified."

**Time limits** [Guide p.10]
- "time bank of 8 seconds of thinking time per half (1,000 hands). Every request the judge sends you is timed, and the time is taken from your bank. The first millisecond of each request is free, to cover network delay."
- "A single request may take at most 1 second. Taking longer counts as an error."
- When the bank is empty: "for the rest of the half it automatically checks when that's free and folds otherwise. That's not an error, but it will lose you a lot of chips."
- Guidance: "roughly 2 to 4 milliseconds per decision on average". "A full board evaluation with omaha_score takes a few microseconds, so you can afford some simulation, but not thousands of full simulations on every decision."

**Runtime environment** [Guide p.11-12]
- CPU: "1 CPU core". Memory: "4 GB". Internet: "None". Files: "Read-only, except /tmp", with "(512 MB limit), which is empty at the start of each half". User: not root. Image size: "3 GB added on top of the base image". Build time: "30 minutes". Fresh start: "New server process every half".
- "There are no restrictions on which libraries you use. The base image already includes Python, the packages the starter bot needs, and PyTorch (CPU version). GPUs are not available".
- "Declare your additional requirements in the requirements.txt. Ensure this file is in the root of your repository."
- Local setup: "Python 3.10 or newer"; `pip install fastapi uvicorn`; the bot runs on port 5008 and the opponent on 5009 [Guide p.4]
- Multiple files are allowed: "agent.py can import your own modules and load data files from your repository." [Guide p.14]

### Inferences
- `on_hand_end` runs inside the same HTTP request as the next `choose_action`. The time it uses is therefore almost certainly charged to the bank and counts toward the 1-second-per-request limit. The guide says "Every request ... is timed".
- Model loading at import or startup time does not seem to be charged to the bank, since the bank only times requests. However, "A bot also forfeits if it fails to start or doesn't answer at the beginning of a half" [Guide p.10]. Startup must therefore be reasonably fast, and any work in `new_half` is charged.
- 8 s / 1,000 hands = 8 ms per hand. Spend it unevenly: use cheap lookups preflop and heavier Monte Carlo on big flop or turn decisions.
- The 1 ms free allowance per request covers network delay. Micro-decisions under 1 ms are effectively free.

### Gaps
- The contents of the `config` argument to `new_half` are not described.
- The exact type of the `action` field inside `action_history` entries, and the meaning of `street_total`, are not specified precisely. Check game.py or agent.py.
- The Python version in the base image is not stated. The guide only says Python 3.10+ locally.
- It is not stated whether startup time (imports, model load) has a timeout, or how long "doesn't answer at the beginning of a half" allows.

## Q3. Evaluation (matchmaking, hands, metric, leaderboard, tie-breaks, variance reduction)

### Takeaway
Every match is a round-robin pairing, played in duplicate: 1,000 deals, then the same 1,000 deals with seats swapped, in a fresh bot process. The per-deal summed bb result is averaged with a 95% CI. A CI entirely above 0 is a win (1 point), entirely below 0 is a loss (0), and anything else is a chop (0.5 each). A forfeit in either half is an automatic loss. Standings are by total points, with ties broken by average bb per deal.

### Cited Findings
- "Half 1: 1,000 hands. Your bot sits in one seat, your opponent in the other." "Half 2: the same 1,000 deals again, with the seats swapped. You now get exactly the cards your opponent had, and the same boards." [Guide p.10-11]
- "Because each half runs in a fresh copy of your bot, you can't remember the cards from the first half." [Guide p.11]
- "For each of the 1,000 deals, the judge adds up your result from both halves, in big blinds. It then takes the average per deal and a 95% confidence interval around it (average ± 1.96 × standard error)." [Guide p.11]
- CI table: "Entirely above 0: You win (You 1, opponent 0)". "Entirely below 0: You lose (You 0, opponent 1)". "Includes or touches 0: Chop (draw): too close to call (0.5 each)". [Guide p.11]
- "Every bot plays every other bot exactly once (a round robin). Standings are ordered by total points. Ties on points are broken by average big blinds won per deal across all your matches." [Guide p.11]
- Forfeit: "After 5 errors in one half, your bot forfeits that half". "If your bot forfeits either half of a match, your team gets a loss (0 points) for that match, however many chips you were winning by. Your opponent gets the win. If both bots forfeit, both teams get a loss." "Running out of time bank is not a forfeit". [Guide p.10]
- Error definitions (each one error, and the default check/fold is played for you): an exception in any of the three functions; returning a non-action or an illegal action; a request taking more than 1 s; the server being unreachable or sending a malformed reply. [Guide p.10]
- FAQ: a chop despite winning chips happens because "Your winning margin wasn't big enough, compared with the randomness of the cards, for the judge to be 95% confident." [Guide p.14]

### Inferences
- Scoring rewards consistently beating each opponent by a statistically significant margin, rather than total chip winnings. The total only matters as a tie-break. Against weak bots, a large and low-variance edge secures a 1. Against strong ones, a chop (0.5) is likely.
- Because the duplicate pairing sums both seats for the same deal, card luck largely cancels. The remaining variance comes from divergent decisions, so lower-variance strategies tighten the CI.
- n = 1,000 paired deals. The standard error is computed over per-deal sums, so the win threshold is roughly mean > 1.96·sd/√1000 ≈ 0.062·sd.
- The match loss for any forfeit makes robustness the dominant priority. The guide states this repeatedly (p.3, p.14).

### Gaps
- The number of teams/bots, and whether there are multiple tournament rounds or a final, are not stated.
- It is not stated whether the tournament seeds and decks are fixed or published, or whether baseline bots are entered in the tournament.
- No tie-break is given beyond average bb per deal.

## Q4. Submission mechanics, deadlines, team rules, judging, presentations, prizes

### Takeaway
Register your team (this is mandatory), keep the repo public, and submit three things through the Google Form: team name, GitHub repo URL and the full 40-char commit SHA. Each submission is built into a container and smoke-tested. The latest successful build plays, and failed builds keep the previous one. The deadline is a placeholder in this version of the guide. The guide says nothing about team size, prizes, presentations or subjective judging.

### Cited Findings
- Starter code: "https://github.com/tamu-datathon-org/heads-up-bundle" [Guide p.1, p.3]
- "MANDATORY TEAM REGISTRATION": https://docs.google.com/forms/d/e/1FAIpQLSeVRUzERWDfrri24U6kA2tUbjT0530IwudYokp3ZpoxfXVAwA/viewform?usp=sharing&ouid=100967425964110292916 [Guide p.1]. The URL is reassembled from a line-wrapped PDF.
- Submission form: "https://forms.gle/Jx9RWE5VgR8dbbcj9" [Guide p.1]
- "NOTE: Your submission will not go through if you do not register! Registering the same person on multiple teams will result in invalid registration for the whole team!" [Guide p.1]
- "Copy it into a repository of your own team (for example with GitHub's Use this template or Fork button, or by cloning and pushing to a new repository). You will submit a link to your repository and a specific commit." [Guide p.3]
- Form fields [Guide p.13]:
  - Team name: "Use the same name every time you resubmit, so your new bot replaces the old one."
  - GitHub repository URL: "Your team's repository, in exactly this form. It must be public." The example is `https://github.com/jdoe/poker-bot`.
  - Commit SHA: "The full 40-character commit ID to build. Short IDs are rejected."
  - Use `git push` then `git rev-parse HEAD`. "The commit you submit must be pushed to GitHub, otherwise it can't be built."
- Resubmitting: "Your latest successful build is the one that plays." "If a new submission fails to build or fails the smoke test, your previous working bot is kept." "Submitting the same commit twice changes nothing." [Guide p.13]
- Build check: "your bot is built and given a quick smoke test under exactly the limits above. If the build or smoke test fails, that submission is rejected" [Guide p.12]
- "Deadline: [[Date and time]]." This is an unfilled placeholder in the guide [Guide p.13].
- Section 9 says "Submit through the form: [[Submission form link]]", which is also a placeholder. Page 1 gives the forms.gle link [Guide p.13 vs p.1].
- Pre-submit checklist [Guide p.12-13]: test_agent.py passes; full 1,000-deal matches with 0 errors and no forfeits against several opponents and seeds; thinking time "comfortably under 8 s per half" ("the tournament machine may be slower than your laptop"); the bot beats the baselines; everything is committed and pushed.
- Common build failure causes: "a missing package, a file that wasn't committed, writing outside /tmp, using more than 4 GB of memory, or needing the internet." [Guide p.14]

### Inferences
- The winner is decided purely by tournament standings. The guide mentions no presentation or judging rubric.
- Since only the latest successful build plays, a late, risky submission that builds but plays worse would replace a good one. Build success, not bot quality, is the replacement criterion.

### Gaps
- The deadline date and time are not given (placeholder).
- Team size limits, prizes, presentation or demo requirements, judging criteria beyond the tournament, and when or how results are announced are not mentioned anywhere.
- The contents of the smoke test are not specified, beyond running "under exactly the limits above".
- Whether the requirements.txt install happens with internet at build time is implied (packages get installed within 30 min) but not stated.

## Q5. Hints, strategies, starter code references, FAQs

### Takeaway
The guide suggests a progression: beat the baselines with a fold/call/raise-by-strength bot, then use Monte Carlo equity with omaha_score (watch the time), pot-odds comparison, precomputed preflop features, positional awareness, opponent modelling via on_hand_end and action_history, and optionally offline-trained ML models shipped in the repo. Its main message is that robustness beats brilliance.

### Cited Findings
- Strategy ideas [Guide p.13-14]:
  - "Beat the baselines first. A bot that folds weak hands, calls with decent ones and raises strong ones already beats random play by a wide margin."
  - "Estimate your chances. Before the river, deal the missing board cards (and a random opponent hand) many times and count how often you win with omaha_score. This is called Monte Carlo equity. Watch your time budget!"
  - "Compare price and chances. If you must call 10 chips into a pot that will be 40, you need to win more than 25% of the time to profit."
  - "Preflop shortcuts. Precompute simple features of your five hole cards (pairs, suited cards, connected ranks, high cards) instead of simulating every preflop decision."
  - "Position matters. After the flop the button acts last and sees what the opponent did first."
  - "Model your opponent. Use on_hand_end and action_history to track how often your opponent raises, folds or bluffs (cards revealed at showdown are gold), then adapt."
  - "Machine learning. You can train offline (self-play or simulation) and ship the trained model in your repository. Remember the 1-CPU, 4 GB, no-internet limits, and keep inference fast."
  - "Robustness beats brilliance. One unhandled exception path, triggered 5 times, loses the whole match."
- Local testing commands [Guide p.4, p.12]: `python agent.py` (port 5008), `python baseline-bots/baseline_random.py` (port 5009), `python judge_engine.py` (1,000 deals, both halves). Judge options: `--deals 200`, `--seed 7` ("The same seed always deals the same cards"), `--json out.json --logs` (full per-hand result), `--agent1 5010 --agent2 5011`. To run a second bot: `PORT=5010 python agent.py` (PowerShell: `$env:PORT=5010; python agent.py`).
- Judge report [Guide p.12]: "agent1: +0.523 bb/deal" (agent1 = port 5008 by default); confidence interval and VERDICT; "Faults" lists thinking time out of 8 s, calls, errors and flags "FORFEITED" or "TIME BANK EMPTY", and prints the first error and traceback; the final line is "RESULT: AGENT1_WIN, AGENT2_WIN or CHOP".
- The starter bot "only checks or folds, so expect it to lose" [Guide p.4].
- FAQ highlights [Guide p.14]: stacks do not carry over, and "Your score is the sum of chips won or lost over all hands"; opponent cards are visible "Only after a showdown, in on_hand_end (result.opp_hole). Never during a hand"; the button alternates (check obs.is_button); there are no custom bet sizes; multiple files and folders are fine.
- "The settings in this guide (stacks, blinds, time bank and so on) may be tuned before the tournament. If they change, the updated game.py in the starter repository is the source of truth, and we'll announce it." [Guide p.14]

### Inferences
- An efficient plan: precompute a preflop hand-strength table offline (shipped as a data file), run small-sample Monte Carlo equity against a random or range-weighted opponent hand on later streets within a few ms, apply pot-odds thresholds, and add simple opponent frequency stats. Wrap everything in try/except returning CHECK_CALL, or FOLD/CHECK if appropriate, and choose only from legal_actions.
- Read settings such as stack, blind and limits from obs or config, or from game.py constants, rather than hard-coding them, because the numbers may be tuned.

### Gaps
- The guide names no baseline bots other than `baseline_random.py` ("e.g." implies there are more in the folder).
- No performance figures are given for omaha_score beyond "a few microseconds".

## Q6. Prohibited actions, and ambiguities to clarify with organizers

### Takeaway
Prohibited or penalised behaviour: interfering with the judge, the other bot or the machine (disqualification); editing the server plumbing (risks breaking the bot); illegal or non-action returns, exceptions, requests over 1 s and malformed replies (errors, with 5 per half causing a forfeit and match loss); registering one person on multiple teams (invalidates the whole team); writing outside /tmp; relying on internet or root. Several logistics items are unfilled placeholders or undefined.

### Cited Findings
- "Don't try to interfere with the judge, the other bot, or the machine. Bots that do will be disqualified." [Guide p.9]
- "Registering the same person on multiple teams will result in invalid registration for the whole team!" [Guide p.1]
- The SERVER PLUMBING section: "Don't change it: if it breaks, the judge can't talk to your bot." [Guide p.7]
- Error conditions and the 5-error forfeit rule [Guide p.10]. Environment restrictions (no internet, read-only FS except /tmp at 512 MB, non-root, 4 GB, 1 CPU) [Guide p.11].
- Placeholders "[[Submission form link]]" and "[[Date and time]]" [Guide p.13].

### Inferences
Items worth confirming with organizers:
1. The submission deadline (placeholder in the guide).
2. That the forms.gle link on p.1 is the submission form, since the section 9 link is a placeholder.
3. Whether any final changes to stacks, blinds or the time bank have been made (watch the starter repo's game.py and announcements).
4. Team size limits, prizes, and whether there is any presentation or judged component.
5. Whether time in `on_hand_end` and `new_half` counts against the bank, and whether startup and model-load time has a limit.
6. The definition of "last raise size" for min-raise, and the raise-reopening rules after a short all-in (or just read game.py).
7. The contents of `config` passed to `new_half`.
8. The number of entrants and the tournament schedule, and whether baselines are included in the round robin.
9. The base image's Python version, and whether pip installs at build time have internet access.

### Gaps
- The guide has no explicit statement on code sharing between teams, plagiarism, use of external pretrained poker solvers, or LLM use. "Any approach is allowed" [Guide p.3] is the only relevant line.
