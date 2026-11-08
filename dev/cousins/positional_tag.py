"""Cousin: thresholds shifted by position (looser on the button), half-pot
sizing preferred, a small margin required over pot odds to call."""

from _cousin_common import Action, Street, equity_vs_random, fold_or_check, new_rng, pot_odds, raise_or


def new_half(config, memory):
    new_rng(memory, 12)


def choose_action(obs, memory):
    eq = equity_vs_random(obs, memory["rng"])
    shift = -0.03 if obs.is_button else 0.03
    if obs.street == Street.PREFLOP and obs.to_call <= 1 and obs.is_button and eq > 0.47:
        return raise_or(obs, Action.RAISE_HALF)
    if eq > 0.62 + shift:
        return raise_or(obs, Action.RAISE_HALF)
    if eq >= pot_odds(obs) + 0.04 + shift:
        return Action.CHECK_CALL
    return fold_or_check(obs)


def on_hand_end(result, memory):
    pass
