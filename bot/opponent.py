"""
opponent.py - running frequencies of the opponent's play this half.

Everything is counted from what we can see: the opponent's entries in
obs.action_history (seen when it is our turn) and how hands end. Beta
priors shrink the estimates so the first few hands don't swing them.
"""

from game import RAISE_ACTIONS, Action, HandResult, Observation, Street

# (prior successes, prior failures) for each frequency
PRIOR_PF_RAISE = (3.0, 5.0)      # opponent raises when acting preflop
PRIOR_POST_RAISE = (2.0, 5.0)    # opponent bets/raises when acting postflop
PRIOR_FOLD_TO_RAISE = (3.0, 5.0)  # opponent folds when facing our raise


def init(memory: dict) -> None:
    memory["opp"] = {
        "pf_acts": 0, "pf_raises": 0,
        "post_acts": 0, "post_raises": 0,
        "faced_raise": 0, "folded_to_raise": 0,
        "hand": -1, "seen": 0, "we_raised_last": False,
    }


def _freq(hits: float, total: float, prior: tuple[float, float]) -> float:
    return (hits + prior[0]) / (total + prior[0] + prior[1])


def pf_raise_freq(memory: dict) -> float:
    o = memory["opp"]
    return _freq(o["pf_raises"], o["pf_acts"], PRIOR_PF_RAISE)


def post_raise_freq(memory: dict) -> float:
    o = memory["opp"]
    return _freq(o["post_raises"], o["post_acts"], PRIOR_POST_RAISE)


def fold_to_raise(memory: dict) -> float:
    o = memory["opp"]
    return _freq(o["folded_to_raise"], o["faced_raise"], PRIOR_FOLD_TO_RAISE)


def observe(obs: Observation, memory: dict) -> None:
    """Count opponent actions we haven't seen yet in this hand's history."""
    o = memory["opp"]
    if o["hand"] != obs.hand_index:
        o["hand"], o["seen"], o["we_raised_last"] = obs.hand_index, 0, False
    history = obs.action_history
    for i in range(o["seen"], len(history)):
        act = history[i]
        if act.is_me:
            continue
        raised = act.action in RAISE_ACTIONS
        if act.street == Street.PREFLOP:
            o["pf_acts"] += 1
            o["pf_raises"] += raised
        else:
            o["post_acts"] += 1
            o["post_raises"] += raised
        if i > 0 and history[i - 1].is_me and history[i - 1].action in RAISE_ACTIONS:
            o["faced_raise"] += 1  # answered our raise without folding
    o["seen"] = len(history)


def note_our_action(action: Action, memory: dict) -> None:
    memory["opp"]["we_raised_last"] = action in RAISE_ACTIONS


def hand_end(result: HandResult, memory: dict) -> None:
    o = memory["opp"]
    if (o["hand"] == result.hand_index and o["we_raised_last"]
            and not result.went_to_showdown and result.my_net > 0):
        o["faced_raise"] += 1
        o["folded_to_raise"] += 1
    o["we_raised_last"] = False
