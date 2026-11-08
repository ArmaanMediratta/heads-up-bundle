"""
Shared helpers for the "template cousin" practice bots in dev/cousins/.

These imitate the bot most teams will likely build with an AI assistant:
Monte Carlo equity against a RANDOM hand (no range reading), compared with
pot odds and fixed thresholds. Each cousin varies the recipe a little.
They are opponents for testing only, never part of our bot.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np  # noqa: E402

from bot import equity  # noqa: E402  (only the fast evaluator/sampler; no strategy)
from game import RAISE_ACTIONS, Action, Street  # noqa: E402,F401

SAMPLES = 256


def equity_vs_random(obs, rng) -> float:
    """Plain equity vs a uniformly random opponent hand (the template's mistake:
    it ignores what the opponent's betting says about its hand)."""
    win, _, _ = equity.rollout(obs.hole_cards, obs.board, time.perf_counter(), rng,
                               batch=SAMPLES, min_samples=SAMPLES, max_samples=SAMPLES)
    return float(win.mean())


def pot_odds(obs) -> float:
    return obs.to_call / (obs.pot + obs.to_call) if obs.to_call > 0 else 0.0


def raise_or(obs, prefer=Action.RAISE_POT, otherwise=Action.CHECK_CALL):
    if prefer in obs.legal_actions:
        return prefer
    for a in RAISE_ACTIONS:
        if a in obs.legal_actions:
            return a
    return otherwise


def fold_or_check(obs):
    return Action.FOLD if obs.to_call > 0 and Action.FOLD in obs.legal_actions else Action.CHECK_CALL


def new_rng(memory, seed):
    memory["rng"] = np.random.default_rng(seed)
