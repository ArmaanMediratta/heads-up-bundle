"""Cousin that plays push/fold: pot-raise everything with equity above 0.55,
otherwise check or fold (an all-in heavy recipe for shallow stacks)."""

from _cousin_common import Action, equity_vs_random, fold_or_check, new_rng, raise_or


def new_half(config, memory):
    new_rng(memory, 14)


def choose_action(obs, memory):
    eq = equity_vs_random(obs, memory["rng"])
    if eq > 0.55:
        return raise_or(obs, Action.RAISE_POT, Action.CHECK_CALL)
    return fold_or_check(obs)


def on_hand_end(result, memory):
    pass
