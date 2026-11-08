"""Cousin: the textbook recipe. Equity vs random; raise pot above 0.65,
half-pot above 0.58, call when equity beats pot odds, else fold/check."""

from _cousin_common import Action, equity_vs_random, fold_or_check, new_rng, pot_odds, raise_or


def new_half(config, memory):
    new_rng(memory, 11)


def choose_action(obs, memory):
    eq = equity_vs_random(obs, memory["rng"])
    if eq > 0.65:
        return raise_or(obs, Action.RAISE_POT)
    if eq > 0.58:
        return raise_or(obs, Action.RAISE_HALF)
    if eq >= pot_odds(obs):
        return Action.CHECK_CALL
    return fold_or_check(obs)


def on_hand_end(result, memory):
    pass
