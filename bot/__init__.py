"""
bot - the strategy behind agent.py.

agent.py's three hooks call on_new_half / decide / observe_result. Each one
measures its own time for the time bank and never lets an exception escape:
any failure falls back to a legal action.
"""

import os

import numpy as np

from bot import opponent, policy, safety, timebank
from game import AgentConfig, HandResult, Observation


def on_new_half(config: AgentConfig, memory: dict) -> None:
    start = timebank.now()
    seed = os.environ.get("BOT_SEED")
    memory["np_rng"] = np.random.default_rng(int(seed) if seed else None)
    memory["params"] = dict(policy.PARAMS)  # per-half copy, so dev/harness.py can A/B tweaks
    memory["last_eq"] = 0.5
    memory["raise_cap"] = config.raise_cap
    memory["errors"] = []
    timebank.init(memory, config.time_bank_seconds, config.num_hands)
    opponent.init(memory)
    timebank.charge(memory, timebank.now() - start)


def decide(obs: Observation, memory: dict):
    start = timebank.now()
    try:
        if "tb_bank" not in memory:  # new_half never ran (shouldn't happen): set up now
            on_new_half(AgentConfig(), memory)
        opponent.observe(obs, memory)
        action = policy.decide(obs, memory, timebank.budget(memory, obs.hand_index))
    except Exception:
        safety.log_exception(memory, "decide")
        action = safety.fallback(obs)
    action = safety.legalize(action, obs)
    try:
        opponent.note_our_action(action, obs, memory)
        timebank.charge(memory, timebank.now() - start)
    except Exception:
        safety.log_exception(memory, "decide/bookkeeping")
    return action


def observe_result(result: HandResult, memory: dict) -> None:
    start = timebank.now()
    try:
        if "opp" in memory:
            opponent.hand_end(result, memory)
            timebank.charge(memory, timebank.now() - start)
    except Exception:
        safety.log_exception(memory, "observe_result")
