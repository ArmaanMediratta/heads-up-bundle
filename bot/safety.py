"""
safety.py - never return an illegal action, never let an exception escape.

Five errors in a half forfeit the whole match, so every hook goes through
these helpers.
"""

import traceback

from game import Action, Observation


def fallback(obs: Observation) -> Action:
    """Check when free, otherwise call cheaply-safe: CHECK_CALL is always legal,
    so fold only when there is something to call."""
    if Action.FOLD in obs.legal_actions and obs.to_call > 0:
        return Action.FOLD
    return Action.CHECK_CALL


def legalize(action, obs: Observation) -> Action:
    """Map anything the policy returned onto a legal Action."""
    try:
        action = Action(action)
    except (ValueError, TypeError):
        return fallback(obs)
    if action in obs.legal_actions:
        return action
    if action in (Action.RAISE_HALF, Action.RAISE_POT):
        other = Action.RAISE_POT if action == Action.RAISE_HALF else Action.RAISE_HALF
        if other in obs.legal_actions:
            return other
        return Action.CHECK_CALL
    if action == Action.FOLD:  # fold with nothing to call: check instead
        return Action.CHECK_CALL
    return fallback(obs)


def log_exception(memory: dict, where: str) -> None:
    """Keep the last few tracebacks for local debugging (cheap, bounded)."""
    try:
        errs = memory.setdefault("errors", [])
        if len(errs) < 20:
            errs.append(f"{where}: {traceback.format_exc(limit=4)}")
    except Exception:
        pass
