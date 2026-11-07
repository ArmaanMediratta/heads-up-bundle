"""Trapper: slowplays strong made hands, check-raises the flop and turn, and
raises the river for value. Probes: does our bot bet into strength and call
down too thin?"""

from _spar_common import (THREE_OF_A_KIND, TWO_PAIR, Action, Street, check_or_fold, hand_pct,
                          made_category, opp_raised_this_street, pot_odds, raise_or_call)


def new_half(config, memory):
    pass


def choose_action(obs, memory):
    if obs.street == Street.PREFLOP:
        if hand_pct(obs.hole_cards) > 0.4 and pot_odds(obs) < 0.4:
            return Action.CHECK_CALL                        # never raise preflop: hide strength
        return check_or_fold(obs)
    cat = made_category(obs)
    if cat >= THREE_OF_A_KIND:
        if obs.street == Street.RIVER:
            return raise_or_call(obs, Action.RAISE_POT)
        if obs.to_call == 0:
            return Action.CHECK_CALL                        # set the trap
        return raise_or_call(obs, Action.RAISE_POT)         # spring it: check-raise
    if cat >= TWO_PAIR and pot_odds(obs) < 0.3 and not opp_raised_this_street(obs):
        return Action.CHECK_CALL
    return check_or_fold(obs)


def on_hand_end(result, memory):
    pass
