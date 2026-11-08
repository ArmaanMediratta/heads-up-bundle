"""
policy.py - choose among at most four actions by estimated chip EV.

Equity comes from Monte Carlo rollouts (equity.py), weighted toward the
hands the opponent's actions this hand suggest (soft percentile cut-offs
that loosen against opponents who raise a lot, and move toward the hands it
actually showed down). EV per action, in chips relative to now:

    fold        0
    check/call  E * R * (pot + to_call) - to_call
                (when the call leaves too little behind to fold later, it is
                priced as getting all the chips in)
    raise to T  f * pot
                + (1 - f) * [(1 - q) * (E_flat * R' * called_pot - added)
                             + q * max(-added, E_rr * allin_pot - stack)]

f is the chance the opponent folds and q the chance it re-raises when it
continues, both read from its responses to our raises in the same context
(had it already raised this hand?). E_flat / E_rr are our equity against
the hands that call / re-raise. R is an equity-realisation factor (1 when
all-in or on the river).

Every refinement has a switch in PARAMS so dev/harness.py can A/B it, e.g.
    python dev/harness.py --bot "agent.py@lookahead=0" --opp agent.py
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
    "commit_spr": 0.6,     # stack left / pot below which chips put in are a commitment
    "max_samples": 1024,   # more showed no measurable gain, and costs time bank
    # switches (1 = on); see bot/opponent.py for fixcount / split_ctx
    "fixcount": 1,         # count the opponent's hand-ending folds and calls
    "split_ctx": 1,        # fold/re-raise rates split by "opponent already raised"
    "lookahead": 1,        # model the opponent re-raising our raise
    "lookahead_qmax": 0.5,  # ...only vs selective re-raisers: above this re-raise rate
                            # their re-raises carry little strength (maniacs, always-raisers)
    "commit_call": 0,      # price low-SPR calls as all-in (neutral in A/B tests: off)
    "sd_use": 1.0,         # weight of showdown-observed preflop ranges
    "defend": 0.0,         # preflop call bonus (x pot) per unit of opp raise rate above 35%
                           # (helped only while folds went uncounted; neutral since: off)
    "draw_weight": 0.0,    # weight of draw-aware opponent strength postflop (0 = made hand only;
                           # neutral in A/B tests and ~2x the thinking time, so off)
    "draw_runouts": 4,
    "mix_eps": 0.0,        # pick randomly among actions within this x pot of the best
    "mirror": 0,           # detect a copy of ourselves and switch to bot/mirror.py MIRROR_COUNTER (off until validated)
}


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def _weights(obs: Observation, memory: dict, opp_pct: np.ndarray, opp_now: np.ndarray) -> np.ndarray:
    p = memory["params"]
    w = np.ones(len(opp_pct))
    r_pf = opponent.pf_raise_freq(memory)
    r_post = opponent.post_raise_freq(memory)
    f = opponent.fold_to_raise(memory)
    n_pf = n_post = 0
    prev = None
    for act in obs.action_history:
        if not act.is_me:
            if act.action in RAISE_ACTIONS:
                if act.street == Street.PREFLOP:
                    n_pf += 1
                    cut = min(1.0 - r_pf ** n_pf, p["max_cut"])
                    if p["sd_use"] > 0:
                        cut += p["sd_use"] * (opponent.sd_blend(memory, n_pf, cut) - cut)
                    w *= _sigmoid((opp_pct - cut) / p["temp_pre"])
                else:
                    n_post += 1
                    cut = min(1.0 - r_post ** n_post, p["max_cut"])
                    w *= _sigmoid((opp_now - cut) / p["temp_post"])
            elif (act.action == Action.CHECK_CALL and act.street != Street.PREFLOP
                  and prev is not None and prev.is_me and prev.action in RAISE_ACTIONS):
                cut = min(f * p["call_cut_scale"], p["max_cut"])
                w *= _sigmoid((opp_now - cut) / p["temp_post"])
        prev = act
    return w + 1e-9


def _mean(w: np.ndarray, win: np.ndarray, default: float) -> float:
    s = w.sum()
    return float((w * win).sum() / s) if s > 1e-6 else default


def decide(obs: Observation, memory: dict, budget: float) -> Action:
    p = memory["params"]
    # Nearly out of bank: a single minimum batch (~0.3 ms) still fits in the judge's grace.
    deadline = timebank.now() + (0.0 if timebank.panic(memory) else budget)
    win, opp_pct, opp_now = equity.rollout(obs.hole_cards, obs.board, deadline, memory["np_rng"],
                                           pre_pct=preflop.PCT, batch=256, min_samples=256,
                                           max_samples=int(p["max_samples"]),
                                           draw_runouts=int(p["draw_runouts"]),
                                           draw_weight=float(p["draw_weight"]))
    w = _weights(obs, memory, opp_pct, opp_now)
    eq = _mean(w, win, 0.5)

    pot, to_call, stack, opp_stack = obs.pot, obs.to_call, obs.my_stack, obs.opp_stack
    river = obs.street == Street.RIVER
    r_base = p["r_ip"] if obs.is_button else p["r_oop"]
    all_in_call = to_call >= stack or opp_stack == 0
    r_call = 1.0 if (river or all_in_call) else r_base

    # check / call
    call_ev = eq * r_call * (pot + to_call) - to_call
    if (p["commit_call"] and to_call > 0 and not all_in_call and not river
            and stack - to_call < p["commit_spr"] * (pot + to_call)):
        eff = min(stack - to_call, opp_stack)  # the rest goes in on a later street
        call_ev = eq * (pot + to_call + 2 * eff) - (to_call + eff)
    if to_call > 0 and obs.street == Street.PREFLOP and p["defend"] > 0:
        call_ev += p["defend"] * pot * max(0.0, opponent.pf_raise_freq(memory) - 0.35)
    evs = {Action.CHECK_CALL: call_ev}
    if Action.FOLD in obs.legal_actions:
        evs[Action.FOLD] = 0.0

    raises = [a for a in RAISE_ACTIONS if a in obs.legal_actions]
    if raises:
        ctx = opponent.opp_raised_this_hand(obs)
        # The opponent continues vs a raise with roughly the top (1 - t) of hands
        # overall, so its fold chance is the share of its CURRENT range below that
        # line: big against a wide range, near zero once it has shown strength.
        t = opponent.fold_to_raise(memory, ctx)
        w_cont = w * _sigmoid((opp_now - t) / p["temp_post"])
        f = float(1.0 - w_cont.sum() / w.sum())
        eq_cont = _mean(w_cont, win, eq)
        q = opponent.reraise_rate(memory, ctx) if p["lookahead"] else 0.0
        if q > p["lookahead_qmax"]:
            q = 0.0
        # re-raisers are the top q of the continuing hands
        w_rr = w_cont * _sigmoid((opp_now - (1.0 - q * (1.0 - t))) / p["temp_post"])
        can_reraise = obs.raises_this_street + 1 < memory.get("raise_cap", 4)
        seen_totals = set()
        for a in sorted(raises, reverse=True):  # RAISE_POT first, so it wins ties
            total = obs.raise_to[a]
            if total in seen_totals:
                continue
            seen_totals.add(total)
            added = total - obs.my_bet
            opp_add = min(total - obs.opp_bet, opp_stack)
            called_pot = pot + added + opp_add
            committed = added >= stack or (stack - added) < p["commit_spr"] * called_pot
            r_raise = 1.0 if (river or committed) else r_base
            fa = f if a == Action.RAISE_POT else f * p["half_fold_scale"]
            q_eff = q if (can_reraise and added < stack and opp_add < opp_stack) else 0.0
            if q_eff > 0 and w_cont.sum() > 1e-6:
                # q_eff is the measured re-raise rate itself: the soft cut-off only picks
                # WHICH hands re-raise (their equity), never how often (it inflated q).
                eq_rr = _mean(w_rr, win, eq_cont)
                eq_flat = min(1.0, max(0.0, (eq_cont - q_eff * eq_rr) / (1.0 - q_eff)))
                # facing the re-raise we fold or get it all in (pot-limit at 40bb
                # commits within one more raise)
                rr_ev = max(-added, eq_rr * (pot + stack + opp_stack) - stack)
                cont_ev = (1 - q_eff) * (eq_flat * r_raise * called_pot - added) + q_eff * rr_ev
            else:
                cont_ev = eq_cont * r_raise * called_pot - added
            evs[a] = fa * pot + (1 - fa) * cont_ev

    memory["last_eq"] = eq
    best = max(evs, key=evs.get)
    if p["mix_eps"] > 0:
        near = [a for a, v in evs.items() if v >= evs[best] - p["mix_eps"] * pot]
        if len(near) > 1:
            best = near[int(memory["np_rng"].integers(len(near)))]
    return best
