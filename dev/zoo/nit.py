"""Nit: plays only the top 25% of hands, raises the top 10%, folds to river aggression without trips+."""

from _common import Action, Street, made_category, preflop, raise_if_legal


def new_half(config, memory):
    pass


def choose_action(obs, memory):
    _, pct = preflop.strength(obs.hole_cards)
    if obs.street == Street.PREFLOP:
        if pct > 0.9:
            return raise_if_legal(obs)
        if pct > 0.75 or obs.to_call == 0:
            return Action.CHECK_CALL
        return Action.FOLD
    cat = made_category(obs)
    if cat >= 4:
        return raise_if_legal(obs)
    if obs.to_call == 0 or (cat < 0 and pct > 0.85) or obs.to_call <= obs.pot // 4:
        return Action.CHECK_CALL
    return Action.FOLD


def on_hand_end(result, memory):
    pass
