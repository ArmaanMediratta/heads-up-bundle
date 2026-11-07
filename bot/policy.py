"""
policy.py - choose among at most four actions by estimated chip EV.

Equity comes from Monte Carlo rollouts (equity.py), weighted toward the
hands the opponent's actions this hand suggest (soft percentile cut-offs
that loosen against opponents who raise a lot). EV per action:

    fold        0
    check/call  E * R * (pot + to_call) - to_call
    raise to T  f * pot + (1 - f) * (E_call * R' * called_pot - added)

R is an equity-realisation factor (1 when all-in or on the river), f the
opponent's estimated fold-to-raise rate, E_call our equity against the
hands that continue.
"""

import numpy as np

from bot import equity, opponent, preflop, timebank
from game import RAISE_ACTIONS, Action, Observation, Street

PARAMS = {
    "r_ip": 0.95,          # realisation in position (button)
    "r_oop": 0.85,         # realisation out of position
    "temp_pre": 0.08,      # softness of preflop range cut-offs
    "temp_post": 0.12,     # softness of postflop range cut-offs
    "max_cut": 0.9,        # never assume a range tighter than the top 10%
    "call_cut_scale": 0.6,  # how much calling our raise narrows their range
    "half_fold_scale": 0.85,  # fold rate vs a half-pot raise relative to pot
    "commit_spr": 0.6,     # stack left / pot below which a raise is a commitment
    "max_samples": 1536,
}


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def _weights(obs: Observation, memory: dict, opp_pct: np.ndarray, opp_now: np.ndarray) -> np.ndarray:
    p = memory["params"]
    w = np.ones(len(opp_pct))
    r_pf = opponent.pf_raise_freq(memory)
    r_post = opponent.post_raise_freq(memory)
    f = opponent.fold_to_raise(memory)
    n_pf = n_post = n_calls = 0
    prev = None
    for act in obs.action_history:
        if not act.is_me:
            if act.action in RAISE_ACTIONS:
                if act.street == Street.PREFLOP:
                    n_pf += 1
                    cut = min(1.0 - r_pf ** n_pf, p["max_cut"])
                    w *= _sigmoid((opp_pct - cut) / p["temp_pre"])
                else:
                    n_post += 1
                    cut = min(1.0 - r_post ** n_post, p["max_cut"])
                    w *= _sigmoid((opp_now - cut) / p["temp_post"])
            elif (act.action == Action.CHECK_CALL and act.street != Street.PREFLOP
                  and prev is not None and prev.is_me and prev.action in RAISE_ACTIONS):
                n_calls += 1
                cut = min(f * p["call_cut_scale"], p["max_cut"])
                w *= _sigmoid((opp_now - cut) / p["temp_post"])
        prev = act
    return w + 1e-9


def decide(obs: Observation, memory: dict, budget: float) -> Action:
    p = memory["params"]
    # Nearly out of bank: a single minimum batch (~0.3 ms) still fits in the judge's grace.
    deadline = timebank.now() + (0.0 if timebank.panic(memory) else budget)
    win, opp_pct, opp_now = equity.rollout(obs.hole_cards, obs.board, deadline, memory["np_rng"],
                                           pre_pct=preflop.PCT, batch=256, min_samples=256,
                                           max_samples=int(p["max_samples"]))
    w = _weights(obs, memory, opp_pct, opp_now)
    eq = float((w * win).sum() / w.sum())

    pot, to_call, stack = obs.pot, obs.to_call, obs.my_stack
    river = obs.street == Street.RIVER
    r_base = p["r_ip"] if obs.is_button else p["r_oop"]
    all_in_call = to_call >= stack or obs.opp_stack == 0
    r_call = 1.0 if (river or all_in_call) else r_base

    evs = {Action.CHECK_CALL: eq * r_call * (pot + to_call) - to_call}
    if Action.FOLD in obs.legal_actions:
        evs[Action.FOLD] = 0.0

    raises = [a for a in RAISE_ACTIONS if a in obs.legal_actions]
    if raises:
        # The opponent continues vs a raise with roughly the top (1 - f) of hands
        # overall, so their fold chance is the share of their CURRENT range below
        # that line: big against a wide range, near zero once they have shown strength.
        t = opponent.fold_to_raise(memory)
        cont = _sigmoid((opp_now - t) / p["temp_post"])
        w_call = w * cont
        f = float(1.0 - w_call.sum() / w.sum())
        eq_call = float((w_call * win).sum() / w_call.sum()) if w_call.sum() > 1e-6 else eq
        seen_totals = set()
        for a in sorted(raises, reverse=True):  # RAISE_POT first, so it wins ties
            total = obs.raise_to[a]
            if total in seen_totals:
                continue
            seen_totals.add(total)
            added = total - obs.my_bet
            opp_add = min(total - obs.opp_bet, obs.opp_stack)
            called_pot = pot + added + opp_add
            committed = added >= stack or (stack - added) < p["commit_spr"] * called_pot
            r_raise = 1.0 if (river or committed) else r_base
            fa = f if a == Action.RAISE_POT else f * p["half_fold_scale"]
            evs[a] = fa * pot + (1 - fa) * (eq_call * r_raise * called_pot - added)

    memory["last_eq"] = eq
    return max(evs, key=evs.get)
