"""MC grinder: honest equity-vs-pot-odds player. Monte-Carlo equity against a
random hand (time-capped), discounted when the opponent shows aggression.
Probes: overall soundness against a solid, straightforward opponent."""

import random

from _spar_common import (Action, Street, check_or_fold, hand_pct, mc_equity, opp_raised_this_street,
                          pot_odds, raise_or_call)


def new_half(config, memory):
    memory["rng"] = random.Random(7)


def choose_action(obs, memory):
    po = pot_odds(obs)
    if obs.street == Street.PREFLOP:
        pct = hand_pct(obs.hole_cards)
        if pct > 0.8 and obs.raises_this_street < 3:
            return raise_or_call(obs, Action.RAISE_POT)
        if pct > 0.55 and obs.raises_this_street == 0:
            return raise_or_call(obs, Action.RAISE_HALF)
        if pct > 0.3 + po:
            return Action.CHECK_CALL
        return check_or_fold(obs)
    eq = mc_equity(obs.hole_cards, obs.board, iters=60, budget_s=0.002, rng=memory["rng"])
    if opp_raised_this_street(obs):
        eq -= 0.08 * obs.raises_this_street                 # their range beats a random hand
    if eq > 0.8:
        return raise_or_call(obs, Action.RAISE_POT)
    if eq > 0.65 and obs.raises_this_street < 2:
        return raise_or_call(obs, Action.RAISE_HALF)
    if obs.to_call and eq > po + 0.05:
        return Action.CHECK_CALL
    return check_or_fold(obs)


def on_hand_end(result, memory):
    pass
