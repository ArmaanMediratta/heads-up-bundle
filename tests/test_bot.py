"""
Tests for the bot/ package: legality, robustness, timing and memory shape.

    python -m pytest -q
"""

import os
import random
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import bot  # noqa: E402
from bot import fasteval, opponent, policy, safety  # noqa: E402
from evaluator import omaha_score  # noqa: E402
from game import RAISE_ACTIONS, Action, AgentConfig, Game, make_deal  # noqa: E402


def play(num_hands, opp_raise_rate, seed="fuzz", bot_seat_of=lambda d: d % 2):
    """Our bot vs a random opponent; returns (our actions, memory). Asserts legality."""
    memory, rng, chosen = {}, random.Random(seed), []
    bot.on_new_half(AgentConfig(num_hands=num_hands), memory)
    for d in range(num_hands):
        game, me = Game(make_deal(seed, d), d % 2, d), bot_seat_of(d)
        while not game.is_terminal:
            obs = game.observation(game.to_act)
            if game.to_act == me:
                action = bot.decide(obs, memory)
                assert action in obs.legal_actions, (action, obs.legal_actions)
                chosen.append(action)
            else:
                raises = [a for a in obs.legal_actions if a in RAISE_ACTIONS]
                action = rng.choice(raises) if raises and rng.random() < opp_raise_rate else Action.CHECK_CALL
            game.apply(action)
        bot.observe_result(game.hand_result(me), memory)
    return chosen, memory


def test_fasteval_matches_omaha_score():
    rng = random.Random(3)
    for _ in range(2000):
        cards = rng.sample(range(36), 10)
        hole, board = cards[:5], cards[5:]
        fast = fasteval.best_score(fasteval.hole_pairs(hole), fasteval.board_triples(board))[0]
        assert fast == omaha_score(hole, board)


@pytest.mark.parametrize("raise_rate", [0.0, 0.3, 1.0])
def test_legal_in_both_seats(raise_rate):
    chosen, memory = play(400, raise_rate, seed=f"legal{raise_rate}")
    assert chosen and memory["errors"] == []


def test_raises_with_strong_hands_and_folds_trash_to_pressure():
    chosen, _ = play(300, 0.5, seed="mix")
    assert Action.FOLD in chosen and any(a in RAISE_ACTIONS for a in chosen)


def test_policy_exception_falls_back_to_legal(monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(policy, "decide", broken)
    chosen, memory = play(30, 0.5, seed="broken")
    assert chosen and memory["errors"]  # logged, never raised


def test_legalize_maps_everything_to_legal():
    game = Game(make_deal("lg", 0), 0)
    obs = game.observation(game.to_act)
    for junk in (None, "RAISE", 99, Action.FOLD, Action.RAISE_HALF, Action.RAISE_POT, Action.CHECK_CALL):
        assert safety.legalize(junk, obs) in obs.legal_actions


def test_decisions_are_fast_and_bank_is_respected():
    start = time.perf_counter()
    chosen, memory = play(300, 0.3, seed="timing")
    per_decision = (time.perf_counter() - start) / len(chosen)
    assert per_decision < 0.02
    assert memory["tb_spent"] < memory["tb_bank"]


def test_new_half_memory_keys_are_fixed():
    a, b = {}, {}
    bot.on_new_half(AgentConfig(), a)
    play(20, 0.5, seed="keys")
    bot.on_new_half(AgentConfig(), b)
    assert a.keys() == b.keys()


def _play_vs(opp_policy, num_hands=200, seed="opp"):
    """Our bot (always seat 0) vs a scripted opponent; returns memory."""
    memory = {}
    bot.on_new_half(AgentConfig(num_hands=num_hands), memory)
    for d in range(num_hands):
        game = Game(make_deal(seed, d), d % 2, d)
        while not game.is_terminal:
            obs = game.observation(game.to_act)
            game.apply(bot.decide(obs, memory) if game.to_act == 0 else opp_policy(obs))
        bot.observe_result(game.hand_result(0), memory)
    return memory


def _folder(obs):
    """Folds to any bet, never raises."""
    return Action.FOLD if obs.to_call > 0 else Action.CHECK_CALL


def _jammer(obs):
    """Raises whenever it can, never folds."""
    for a in (Action.RAISE_POT, Action.RAISE_HALF):
        if a in obs.legal_actions:
            return a
    return Action.CHECK_CALL


def test_hand_ending_folds_are_counted():
    # The folder's folds always end the hand before our next turn; they must
    # still count as (non-raise) actions, or it would look like a raiser.
    memory = _play_vs(_folder)
    o = memory["opp"]
    assert opponent.pf_raise_freq(memory) < 0.1
    assert opponent.fold_to_raise(memory) > 0.8
    assert o["pf_acts"] > 150


def test_always_raiser_reads_as_raiser_that_never_folds_once_raised():
    memory = _play_vs(_jammer)
    assert opponent.pf_raise_freq(memory) > 0.9
    assert opponent.fold_to_raise(memory, ctx=1) < 0.15
    assert opponent.reraise_rate(memory, ctx=1) > 0.7


def test_fixcount_switch_restores_old_counting():
    memory = {}
    bot.on_new_half(AgentConfig(), memory)
    memory["params"]["fixcount"] = 0
    for d in range(100):
        game = Game(make_deal("old", d), d % 2, d)
        while not game.is_terminal:
            obs = game.observation(game.to_act)
            game.apply(bot.decide(obs, memory) if game.to_act == 0 else _folder(obs))
        bot.observe_result(game.hand_result(0), memory)
    assert memory["opp"]["pf_acts"] < 20  # the old bug: the folds are invisible
