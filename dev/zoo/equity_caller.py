"""Equity caller: this bot's own equity engine but never raises (tests our value betting)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import bot  # noqa: E402
from game import Action  # noqa: E402


def new_half(config, memory):
    bot.on_new_half(config, memory)


def choose_action(obs, memory):
    action = bot.decide(obs, memory)
    if action in (Action.RAISE_HALF, Action.RAISE_POT):
        return Action.CHECK_CALL
    return action


def on_hand_end(result, memory):
    bot.observe_result(result, memory)
