"""
Tests for bot/mirror.py: the detector flags agent.py playing itself, leaves
other bots alone, never errors, and keeps memory's shape fixed.

    python -m pytest -q tests/test_mirror.py
"""

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "dev"))

import bot  # noqa: E402
from bot import mirror  # noqa: E402
from game import AgentConfig, HandResult  # noqa: E402
from harness import GROUPS, _load, play_half  # noqa: E402

ON = {"mirror": 1.0}
DEALS = 400


def _half(opp_path, seed, deals=DEALS, opp_overrides=None):
    me = _load(os.path.join(ROOT, "agent.py"), "mirror_me")
    opp = _load(os.path.join(ROOT, opp_path), "mirror_opp")
    _, a, b = play_half(me, ON, opp, opp_overrides or {}, seed, 1, deals, AgentConfig(num_hands=deals))
    return a, b


def test_flags_a_copy_of_itself():
    flagged = 0
    for seed in ("m1", "m2"):
        a, b = _half("agent.py", seed, opp_overrides=ON)
        for p in (a, b):
            st = mirror.status(p.memory)
            assert p.errors == 0 and p.memory["errors"] == []
            flagged += st["state"] == "mirror"
            assert st["spent"] < mirror.BUDGET_SECONDS + 0.05
    assert flagged >= 3  # of 4 detectors (both seats, two halves)


def _rel(paths):
    return [os.path.relpath(p, ROOT) for p in paths]


EQUITY = _rel(GROUPS["equity"])
FALSE_POSITIVE_SET = [p for p in _rel(GROUPS["zoo"] + GROUPS["sparring"] + GROUPS["baselines"])
                      if p not in EQUITY]
REPORT_ONLY = ["demon/demon.py"] + EQUITY + [
    p for p in ["challenger/challenger.py"] if os.path.exists(os.path.join(ROOT, p))]


@pytest.mark.parametrize("opp", FALSE_POSITIVE_SET)
def test_does_not_flag_non_equity_bots(opp):
    a, _ = _half(opp, "fp1")
    st = mirror.status(a.memory)
    assert st["state"] != "mirror", st
    assert a.errors == 0 and a.memory["errors"] == []


@pytest.mark.parametrize("opp", REPORT_ONLY)
def test_relatives_cousins_and_challenger_never_error(opp):
    # Flagging these is desired for close relatives but not required; report it.
    a, _ = _half(opp, "rel1")
    st = mirror.status(a.memory)
    print(f"{opp}: {st}")
    assert a.errors == 0 and a.memory["errors"] == []
    assert st["state"] in ("watch", "mirror", "clear", "stopped", "reverted")


def test_memory_keys_fixed_with_detector_on():
    a, b = {}, {}
    bot.on_new_half(AgentConfig(), a)
    p, _ = _half("agent.py", "keys", deals=60, opp_overrides=ON)
    bot.on_new_half(AgentConfig(), b)
    assert a.keys() == b.keys() == p.memory.keys()
    assert a["mirror"].keys() == b["mirror"].keys() == p.memory["mirror"].keys()


def test_off_by_default_costs_nothing():
    me = _load(os.path.join(ROOT, "agent.py"), "mirror_off")
    _, a, _ = play_half(me, {}, me, {}, "off", 1, 100, AgentConfig(num_hands=100))
    st = mirror.status(a.memory)
    assert st["state"] == "watch" and st["decisions"] == 0 and st["spent"] == 0.0


def test_broken_detector_never_escapes(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("replay broke")
    monkeypatch.setattr(mirror, "_replay", boom)
    a, _ = _half("agent.py", "broken", deals=80, opp_overrides=ON)
    assert a.errors == 0                      # nothing reached the judge
    assert any("mirror" in e for e in a.memory["errors"])
    assert mirror.status(a.memory)["state"] == "stopped"


def test_guardrail_reverts_after_clear_losses():
    memory = {}
    bot.on_new_half(AgentConfig(), memory)
    memory["params"]["mirror"] = 1
    before = dict(memory["params"])
    monkey_counter = {"r_ip": 0.5}
    saved = dict(mirror.MIRROR_COUNTER)
    mirror.MIRROR_COUNTER.clear()
    mirror.MIRROR_COUNTER.update(monkey_counter)
    try:
        r = HandResult(0, 0, 0, False, (), None, "opp")
        mirror._switch(r, memory)
        assert memory["params"]["r_ip"] == 0.5
        for i in range(mirror.REVERT_MIN + 5):
            mirror.hand_end(HandResult(i, -10 + (i % 3), 20, False, (), None, "opp"), memory)
        assert mirror.status(memory)["state"] == "reverted"
        assert memory["params"] == before
        # hysteresis: never switches again this half
        mirror.hand_end(HandResult(999, 5, 10, False, (), None, "me"), memory)
        assert mirror.status(memory)["state"] == "reverted"
    finally:
        mirror.MIRROR_COUNTER.clear()
        mirror.MIRROR_COUNTER.update(saved)
