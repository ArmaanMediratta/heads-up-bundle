"""
Run test_agent.py's judge-compatibility suite against demon.py, plus a few
demon-specific checks (online Q-learning, expert selection, time use).
"""

import importlib.util
import os
import sys

import numpy as np
import pytest
from fastapi.testclient import TestClient

HERE = os.path.dirname(os.path.abspath(__file__))
BUNDLE = os.path.dirname(HERE)
sys.path.insert(0, BUNDLE)

import test_agent  # noqa: E402
from test_agent import (TOKEN, play_hands, start_half,  # noqa: E402,F401
                        test_act_before_new_half_is_refused, test_bad_token_is_refused_before_the_body_is_read,
                        test_crashes_are_reported_to_the_judge, test_every_decision_is_legal,
                        test_handles_aggressive_opponent, test_malformed_body_is_rejected,
                        test_memory_is_fresh_each_half, test_names_are_set, test_new_half_works,
                        test_token_is_checked, test_works_in_both_seats_and_both_halves)
from game import AgentConfig  # noqa: E402


def load_demon():
    spec = importlib.util.spec_from_file_location("demon_under_test", os.path.join(BUNDLE, "demon.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def _use_demon(monkeypatch):
    monkeypatch.setattr(test_agent, "load_agent", load_demon)


@pytest.fixture
def bot():
    module = load_demon()
    module.TOKEN = TOKEN
    return module, TestClient(module.app)


def test_demon_reads_port_from_environment():
    source = open(os.path.join(BUNDLE, "demon.py"), encoding="utf-8").read()
    assert 'os.environ.get("PORT"' in source and "0.0.0.0" in source


def test_online_q_learning_updates_without_errors(bot):
    module, client = bot
    module.ONLINE = True  # off by default until trained tables exist
    start_half(client)
    before = [t.copy() for t in module.MEMORY["theta"]]
    play_hands(client, 120, seed="qlearn", raise_rate=0.5)
    after = module.MEMORY["theta"]
    assert module.MEMORY["errors"] == [], module.MEMORY["errors"]
    assert any(not np.allclose(a, b) for a, b in zip(after, before)), "Q tables never updated"
    assert module.MEMORY["meta_n"].sum() == 120


def test_prior_tables_have_expected_shapes():
    module = load_demon()
    for t, c, n in zip(module.PRIOR_THETA, module.PRIOR_COUNT, module.LENS_SIZE):
        assert t.shape == (n, module.NA) and c.shape == (n, module.NA)
        assert np.isfinite(t).all()
    assert module.PRIOR_META.shape == (27, module.NE)


def test_time_bank_respected(bot):
    module, client = bot
    start_half(client)
    play_hands(client, 150, seed="bank", raise_rate=0.4)
    mem = module.MEMORY
    assert mem["tb_spent"] < AgentConfig().time_bank_seconds
    # the per-decision budget shrinks once part of the bank is gone
    from bot import timebank
    early = timebank.budget({**mem, "tb_spent": 0.0, "tb_decisions": 10}, 4)
    late = timebank.budget({**mem, "tb_spent": 7.0, "tb_decisions": 1500}, 600)
    assert late < early
