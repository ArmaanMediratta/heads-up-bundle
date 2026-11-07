"""Shared helpers for the practice opponents in dev/zoo (not part of the bot)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from bot import preflop  # noqa: E402,F401
from evaluator import category_of, omaha_score  # noqa: E402,F401
from game import RAISE_ACTIONS, Action, Street  # noqa: E402,F401


def made_category(obs) -> int:
    """Made-hand category on the river, -1 before (no full board yet)."""
    return category_of(omaha_score(obs.hole_cards, obs.board)) if len(obs.board) == 5 else -1


def raise_if_legal(obs, action=Action.RAISE_POT):
    if action in obs.legal_actions:
        return action
    for a in RAISE_ACTIONS:
        if a in obs.legal_actions:
            return a
    return Action.CHECK_CALL
