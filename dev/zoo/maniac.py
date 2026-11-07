"""Maniac: raises 70% of the time it can, never folds."""

import random

from _common import RAISE_ACTIONS, Action


def new_half(config, memory):
    memory["rng"] = random.Random(7)


def choose_action(obs, memory):
    raises = [a for a in RAISE_ACTIONS if a in obs.legal_actions]
    if raises and memory["rng"].random() < 0.7:
        return memory["rng"].choice(raises)
    return Action.CHECK_CALL


def on_hand_end(result, memory):
    pass
