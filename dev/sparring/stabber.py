"""Stabber: bets the full pot every time it is checked to after the flop,
otherwise plays honestly. Probes: does our bot fold too much / give up pots?"""

from _spar_common import (FULL_HOUSE, TWO_PAIR, Action, Street, check_or_fold, flush_draw,
                          hand_pct, made_category, pot_odds, raise_or_call)


def new_half(config, memory):
    pass


def choose_action(obs, memory):
    if obs.street == Street.PREFLOP:
        pct = hand_pct(obs.hole_cards)
        if pct > 0.6:
            return raise_or_call(obs, Action.RAISE_HALF)
        if pct > 0.3 and pot_odds(obs) < 0.4:
            return Action.CHECK_CALL
        return check_or_fold(obs)
    if obs.to_call == 0:
        return raise_or_call(obs, Action.RAISE_POT)        # the stab
    cat = made_category(obs)
    if cat >= FULL_HOUSE:
        return raise_or_call(obs, Action.RAISE_POT)
    if cat >= TWO_PAIR or (flush_draw(obs.hole_cards, obs.board) and pot_odds(obs) < 0.35):
        return Action.CHECK_CALL
    return Action.FOLD


def on_hand_end(result, memory):
    pass
