"""Cousin with a typical assistant-written opponent counter: tracks how often
the opponent raises (only counting actions seen on its own turn, the common
bug) and calls wider against aggressive opponents."""

from _cousin_common import RAISE_ACTIONS, Action, equity_vs_random, fold_or_check, new_rng, pot_odds, raise_or


def new_half(config, memory):
    new_rng(memory, 13)
    memory.update(acts=0, raises=0, hand=-1, seen=0)


def choose_action(obs, memory):
    if memory["hand"] != obs.hand_index:
        memory["hand"], memory["seen"] = obs.hand_index, 0
    for a in obs.action_history[memory["seen"]:]:
        if not a.is_me:
            memory["acts"] += 1
            memory["raises"] += a.action in RAISE_ACTIONS
    memory["seen"] = len(obs.action_history)
    aggression = (memory["raises"] + 2) / (memory["acts"] + 6)
    eq = equity_vs_random(obs, memory["rng"])
    discount = 0.08 * max(0.0, aggression - 0.35)  # vs maniacs, call lighter
    if eq > 0.64:
        return raise_or(obs, Action.RAISE_POT)
    if eq >= pot_odds(obs) - discount:
        return Action.CHECK_CALL
    return fold_or_check(obs)


def on_hand_end(result, memory):
    pass
