"""
opponent.py - running frequencies of the opponent's play this half.

Everything is counted from what we can see: the opponent's entries in
obs.action_history (seen when it is our turn) and how hands end. Beta
priors shrink the estimates so the first few hands don't swing them.

Two things are easy to miss and matter a lot:
  * The opponent's LAST action of a hand is never in a history we see:
    a fold, or a call that ends the hand, closes it before our next turn.
    hand_end() counts those, otherwise a bot that folds 70% preflop looks
    like it raises every time it acts.
  * Responses to our raises are split by context: whether the opponent had
    already raised this hand. A player who folds a lot to opens may never
    fold once it has raised (and may always re-raise).

Showdowns also record the preflop strength of hands the opponent raised
with, which policy.py blends into its preflop range cut-offs.
"""

import numpy as np

from bot import preflop
from game import RAISE_ACTIONS, Action, HandResult, Observation, Street

# (prior successes, prior failures) for each frequency
PRIOR_PF_RAISE = (3.0, 5.0)       # opponent raises when acting preflop
PRIOR_POST_RAISE = (2.0, 5.0)     # opponent bets/raises when acting postflop
PRIOR_FOLD_TO_RAISE = (3.0, 5.0)  # opponent folds when facing our raise
PRIOR_RERAISE = (2.0, 6.0)        # opponent re-raises when it continues vs our raise

SD_QUANTILE = 0.2   # showdown hands are biased strong: use a low quantile as the range floor
SD_TRUST = 8.0      # showdowns needed before the observed floor gets half the weight


def init(memory: dict) -> None:
    memory["opp"] = {
        "pf_acts": 0, "pf_raises": 0,
        "post_acts": 0, "post_raises": 0,
        # responses to our raises, indexed by context (0: opponent hadn't raised
        # this hand yet, 1: it had)
        "faced": [0, 0], "folded": [0, 0], "reraised": [0, 0],
        "rr_chances": [0, 0],  # continues where re-raising was possible
        "rr_possible": False,  # could the opponent re-raise our last raise?
        "hand": -1, "seen": 0, "raised_hand": False, "pf_r_hand": 0,
        "we_raised_last": False, "raise_street": 0, "raise_ctx": 0,
        # preflop percentiles of hands shown down, by opponent preflop raises (1, 2, 3+)
        "sd_pcts": {1: [], 2: [], 3: []}, "sd_cut": {},
    }


def _freq(hits: float, total: float, prior: tuple[float, float]) -> float:
    return (hits + prior[0]) / (total + prior[0] + prior[1])


def pf_raise_freq(memory: dict) -> float:
    o = memory["opp"]
    return _freq(o["pf_raises"], o["pf_acts"], PRIOR_PF_RAISE)


def post_raise_freq(memory: dict) -> float:
    o = memory["opp"]
    return _freq(o["post_raises"], o["post_acts"], PRIOR_POST_RAISE)


def fold_to_raise(memory: dict, ctx: int | None = None) -> float:
    """Fold rate vs our raise; ctx=1 when the opponent has already raised this hand."""
    o = memory["opp"]
    if ctx is None or not memory["params"].get("split_ctx", 1):
        return _freq(sum(o["folded"]), sum(o["faced"]), PRIOR_FOLD_TO_RAISE)
    return _freq(o["folded"][ctx], o["faced"][ctx], PRIOR_FOLD_TO_RAISE)


def reraise_rate(memory: dict, ctx: int) -> float:
    """Share of the opponent's continues vs our raise that are re-raises."""
    o = memory["opp"]
    return _freq(o["reraised"][ctx], o["rr_chances"][ctx], PRIOR_RERAISE)


def opp_raised_this_hand(obs: Observation) -> int:
    return int(any(not a.is_me and a.action in RAISE_ACTIONS for a in obs.action_history))


def observe(obs: Observation, memory: dict) -> None:
    """Count opponent actions we haven't seen yet in this hand's history."""
    o = memory["opp"]
    if o["hand"] != obs.hand_index:
        o["hand"], o["seen"], o["we_raised_last"] = obs.hand_index, 0, False
        o["raised_hand"], o["pf_r_hand"] = False, 0
    history = obs.action_history
    for i in range(o["seen"], len(history)):
        act = history[i]
        if act.is_me:
            continue
        raised = act.action in RAISE_ACTIONS
        if act.street == Street.PREFLOP:
            o["pf_acts"] += 1
            o["pf_raises"] += raised
            o["pf_r_hand"] += raised
        else:
            o["post_acts"] += 1
            o["post_raises"] += raised
        if i > 0 and history[i - 1].is_me and history[i - 1].action in RAISE_ACTIONS:
            ctx = int(o["raised_hand"])  # context when our raise was made
            o["faced"][ctx] += 1         # answered our raise without folding
            if o["rr_possible"]:
                o["rr_chances"][ctx] += 1
                o["reraised"][ctx] += raised
        o["raised_hand"] = o["raised_hand"] or raised
    o["seen"] = len(history)


def note_our_action(action: Action, obs: Observation, memory: dict) -> None:
    o = memory["opp"]
    o["we_raised_last"] = action in RAISE_ACTIONS
    if o["we_raised_last"]:
        o["raise_street"] = int(obs.street)
        o["raise_ctx"] = int(o["raised_hand"])
        total = obs.raise_to.get(action, obs.min_raise_to)
        o["rr_possible"] = (obs.raises_this_street + 1 < memory.get("raise_cap", 4)
                            and total - obs.opp_bet < obs.opp_stack
                            and total - obs.my_bet < obs.my_stack)


def _count_unseen(o: dict, street: int) -> None:
    """The opponent's hand-ending action (never a raise) on `street`."""
    if street == Street.PREFLOP:
        o["pf_acts"] += 1
    else:
        o["post_acts"] += 1


def hand_end(result: HandResult, memory: dict) -> None:
    o = memory["opp"]
    if o["hand"] != result.hand_index:
        # We never got a turn: the opponent (button) folded its first action preflop.
        if memory["params"].get("fixcount", 1) and not result.went_to_showdown and result.my_net > 0:
            o["pf_acts"] += 1
    else:
        fixcount = memory["params"].get("fixcount", 1)
        ctx = o["raise_ctx"]
        if not result.went_to_showdown and result.my_net > 0:
            # The opponent folded: to our raise, or (as button) to the big blind.
            if fixcount:
                _count_unseen(o, o["raise_street"] if o["we_raised_last"] else Street.PREFLOP)
            if o["we_raised_last"]:
                o["faced"][ctx] += 1
                o["folded"][ctx] += 1
        elif result.went_to_showdown and o["we_raised_last"] and fixcount:
            # Our raise was called and that call ended the hand (river or all-in).
            _count_unseen(o, o["raise_street"])
            o["faced"][ctx] += 1
            o["rr_chances"][ctx] += o["rr_possible"]
        if result.opp_hole and o["pf_r_hand"] > 0:
            n = min(o["pf_r_hand"], 3)
            pcts = o["sd_pcts"][n]
            pcts.append(preflop.strength(result.opp_hole)[1])
            o["sd_cut"][n] = (float(np.quantile(pcts, SD_QUANTILE)), len(pcts))
    o["we_raised_last"] = False


def sd_blend(memory: dict, n_raises: int, cut: float) -> float:
    """Move a frequency-based preflop range cut toward the floor seen at showdown."""
    seen = memory["opp"]["sd_cut"].get(min(n_raises, 3))
    if not seen:
        return cut
    floor, k = seen
    t = k / (k + SD_TRUST)
    return (1.0 - t) * cut + t * floor
