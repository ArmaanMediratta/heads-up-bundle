"""Blind stealer: raises almost every button, 3-bets light from the big blind,
then gives up postflop without a hand. Probes: our preflop / blind defense."""

from _spar_common import (TWO_PAIR, Action, Street, check_or_fold, flush_draw, hand_pct,
                          made_category, pot_odds, raise_or_call)


def new_half(config, memory):
    pass


def choose_action(obs, memory):
    pct = hand_pct(obs.hole_cards)
    if obs.street == Street.PREFLOP:
        if obs.is_button and obs.raises_this_street == 0:   # first in from the button
            return raise_or_call(obs, Action.RAISE_HALF) if pct > 0.1 else Action.FOLD
        if not obs.is_button and obs.raises_this_street == 1:  # facing a button open
            if pct > 0.45 or obs.hand_index % 4 == 1:       # plus a light 3-bet ~1 hand in 4
                return raise_or_call(obs, Action.RAISE_POT)
            return Action.CHECK_CALL if pct > 0.2 else Action.FOLD
        if not obs.is_button and obs.to_call == 0:           # opponent limped: attack it
            return raise_or_call(obs, Action.RAISE_POT)
        return Action.CHECK_CALL if pct > 0.55 else check_or_fold(obs)
    cat = made_category(obs)
    draw = flush_draw(obs.hole_cards, obs.board)
    if obs.to_call == 0:
        return raise_or_call(obs, Action.RAISE_HALF) if (cat >= TWO_PAIR or draw) else Action.CHECK_CALL
    if cat >= TWO_PAIR or (draw and pot_odds(obs) < 0.3):
        return Action.CHECK_CALL
    return Action.FOLD


def on_hand_end(result, memory):
    pass
