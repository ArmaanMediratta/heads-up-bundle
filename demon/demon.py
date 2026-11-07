"""
demon.py - an ensemble poker bot built to beat agent.py.

Same contract as agent.py: one file, a FastAPI server, and the three hooks
new_half / choose_action / on_hand_end (so dev/harness.py can also load it
in-process).

    python demon/demon.py            # listens on port 5008 (PORT=... to change)

Architecture
------------
1. Perception (once per decision)
   Monte Carlo rollouts against sampled opponent hands (bot/equity.py),
   weighted into a range-aware equity using a model of the opponent's
   frequencies this half. Preflop raise ranges are also calibrated from the
   hands the opponent actually shows down.

2. Strategy experts
   Each expert is a parameterised chip-EV model over the four actions
   (fold / call / half-pot / pot). The experts differ in how they read the
   opponent's range, how much fold equity they expect, how much equity they
   realise, and whether they trap or call down light:
       grinder    balanced range-weighted EV (agent.py's model, re-tuned)
       aggressor  more fold equity, prefers betting
       trapper    slow-plays monsters against aggressive opponents
       sheriff    widens aggressive opponents' ranges and calls them down

3. Q-learning ensemble (residual Q)
   Q(s, a) = EV_expert(s, a) + sum_i theta_i[lens_i(s), a]
   Six tabular Q-learners each see the state through their own lens (core
   equity, betting line, board texture, stack depth, opponent profile, and a
   bias term). They are fit jointly on Monte Carlo returns offline
   (`dev/demon_lab.py train`, saved to demon/data/demon_q.npz) and can keep
   learning online during a half (DEMON_ONLINE=1).

4. Meta Q-learner
   At the start of each hand it picks which expert plays it, from a
   Q-table over (opponent-profile bucket, expert) that starts from an
   offline prior (`dev/demon_lab.py meta`) and learns from hand results.

5. Time management
   Plans to use ~62% of the 8 s bank, reserves the cost of a minimum decision
   for every decision left, caps each decision at 9 ms, and decides without a
   rollout if the bank ever gets critically low. It never runs the bank out.

Status
------
Only the grinder expert has been tuned so far, and the Q tables and meta prior
are untrained (all zero), so the bot currently plays the grinder expert with
online learning off: the configuration every reported result was measured on.
Run `python dev/demon_lab.py --help` to tune, train and evaluate.

Everything that changes during a half lives in `memory`, so the bot behaves
the same in the tournament (fresh process per half) and locally.
"""

import os
import sys
import traceback

# This file lives in demon/, so look one folder up for game.py, evaluator.py and bot/.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from evaluator import category_of, warmup
from game import RAISE_ACTIONS, Action, AgentConfig, HandResult, Observation, Street

warmup()

from bot import equity, preflop, safety, timebank  # noqa: E402
from bot import fasteval as F  # noqa: E402

PARTICIPANT = "TotallyAwesomeDatathonParticipant"
AGENT_NAME = "Demon"

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.environ.get("DEMON_DATA", os.path.join(HERE, "data", "demon_q.npz"))
TRAIN = os.environ.get("DEMON_TRAIN", "") not in ("", "0")
TRAIN_EPS = float(os.environ.get("DEMON_EPS", "0.06"))
FORCE_EXPERT = os.environ.get("DEMON_EXPERT", "")  # pin one expert (for tuning)
# Online Q updates during a half. Off by default: without trained offline tables
# they only add noise (measured), so turn on once demon/data has a trained prior.
ONLINE = os.environ.get("DEMON_ONLINE", "0") not in ("", "0")

ACTIONS = (Action.FOLD, Action.CHECK_CALL, Action.RAISE_HALF, Action.RAISE_POT)
A_IDX = {a: i for i, a in enumerate(ACTIONS)}
NA = len(ACTIONS)

# ---------------------------------------------------------------------------
# Strategy experts (parameter sets of one EV model). Tuned by `dev/demon_lab.py tune`;
# tuned values are stored in demon/data/demon_q.npz and override these defaults.
# ---------------------------------------------------------------------------

BASE = {
    "r_ip": 0.95, "r_oop": 0.85,          # equity realisation in / out of position
    "temp_pre": 0.08, "temp_post": 0.12,  # softness of range cut-offs
    "max_cut": 0.9,                       # tightest range we ever assume (top 10%)
    "widen": 1.0,                         # >1 assumes the opponent raises wider
    "call_cut_scale": 0.6,                # how much calling our raise narrows them
    "half_fold_scale": 0.85,              # fold rate vs half pot relative to pot
    "commit_spr": 0.6,
    "fe_scale": 1.0,                      # multiplier on estimated fold equity
    "call_bonus": 0.0,                    # extra call EV, as a fraction of the pot
    "raise_bonus": 0.0,                   # extra raise EV, as a fraction of the pot
    "trap": 0.0,                          # check bonus (x pot) with a monster, vs aggression
    "trap_eq": 0.8,
    "pf_open": 0.0,                       # extra preflop raise EV (x pot) on the button
    "defend": 0.15,                       # preflop call bonus (x pot) scaled by opp raise rate above 35%
    "sd_use": 1.0,                        # how much showdown-observed ranges move the cut-offs
}

EXPERTS = {
    "grinder": dict(BASE),
    "aggressor": dict(BASE, fe_scale=1.25, raise_bonus=0.03, r_oop=0.82, pf_open=0.04),
    "trapper": dict(BASE, trap=0.12, trap_eq=0.78, half_fold_scale=0.8),
    "sheriff": dict(BASE, widen=1.6, max_cut=0.8, call_bonus=0.04, temp_pre=0.12,
                    call_cut_scale=0.45),
}
EXPERT_NAMES = list(EXPERTS)
NE = len(EXPERT_NAMES)

# Q-learning hyper-parameters
ONLINE_PRIOR_CAP = 60.0   # offline evidence counts as at most this many samples per cell
ONLINE_RIDGE = 8.0        # shrinkage of online updates toward the prior
RESID_CLIP = 30.0         # bb; clip residual targets so one cooler can't wreck a cell
META_PRIOR_N = 150.0      # pseudo-hands behind each meta prior value
META_EXPLORE = 0.0        # online meta exploration (0: greedy)

# ---------------------------------------------------------------------------
# Lenses: each maps a decision to one cell of its own Q-table
# ---------------------------------------------------------------------------

LENS_DIMS = {
    "bias": (4, 2, 4),                    # street, button, facing
    "core": (4, 2, 10, 4),                # street, button, equity10, facing
    "line": (4, 4, 4, 5, 4),              # street, opp raises this hand, raises this street, eq5, facing
    "texture": (4, 10, 2, 2, 2, 4),       # street, made category+1, flush draw, 3-flush board, paired board, facing
    "stack": (4, 4, 4, 5, 4),             # street, spr4, pot4, eq5, facing
    "profile": (4, 3, 3, 3, 5, 4),        # street, opp aggression, opp fold-to-raise, opp pf raise, eq5, facing
}
LENS_NAMES = list(LENS_DIMS)
NL = len(LENS_NAMES)
LENS_SIZE = [int(np.prod(d)) for d in LENS_DIMS.values()]


def _ravel(vals, dims) -> int:
    k = 0
    for v, d in zip(vals, dims):
        k = k * d + min(max(int(v), 0), d - 1)
    return k


# ---------------------------------------------------------------------------
# Offline knowledge
# ---------------------------------------------------------------------------

def _load_prior():
    theta = [np.zeros((n, NA)) for n in LENS_SIZE]
    count = [np.zeros((n, NA)) for n in LENS_SIZE]
    meta_q = np.zeros((27, NE))
    experts = {k: dict(v) for k, v in EXPERTS.items()}
    try:
        if os.path.exists(DATA_PATH):
            z = np.load(DATA_PATH, allow_pickle=False)
            for i, name in enumerate(LENS_NAMES):
                if f"theta_{name}" in z.files and z[f"theta_{name}"].shape == theta[i].shape:
                    theta[i] = z[f"theta_{name}"].astype(np.float64)
                    count[i] = z[f"count_{name}"].astype(np.float64)
            if "meta_q" in z.files and z["meta_q"].shape == meta_q.shape:
                meta_q = z["meta_q"].astype(np.float64)
            if "expert_params" in z.files:
                keys = [str(k) for k in z["expert_keys"]]
                vals = z["expert_params"]
                for e, name in enumerate(EXPERT_NAMES):
                    if e < len(vals):
                        experts[name].update({k: float(v) for k, v in zip(keys, vals[e])})
    except Exception:
        pass
    return theta, count, meta_q, experts


PRIOR_THETA, PRIOR_COUNT, PRIOR_META, EXPERT_PARAMS = _load_prior()

# ---------------------------------------------------------------------------
# Opponent model
# ---------------------------------------------------------------------------

PRIORS = {"pf": (3.0, 5.0), "post": (2.0, 5.0), "fold": (3.0, 5.0)}  # Beta priors (hits, misses)


def _opp_init(memory):
    memory["opp"] = {"pf_acts": 0, "pf_raises": 0, "post_acts": 0, "post_raises": 0,
                     "faced": 0, "folded": 0, "hand": -1, "seen": 0, "we_raised_last": False,
                     "hands": 0, "pf_r_hand": 0,
                     # preflop strength percentiles of hands the opponent showed down,
                     # by how many times it raised preflop in that hand (1, 2, 3+)
                     "sd_pcts": {1: [], 2: [], 3: []}, "sd_cut": {}}

SD_QUANTILE = 0.2   # showdown hands are biased strong: use a low quantile as the range floor
SD_TRUST = 8.0      # showdowns needed before the observed floor gets half the weight


def _freq(h, n, prior):
    return (h + prior[0]) / (n + prior[0] + prior[1])


def _opp_rates(memory):
    o = memory["opp"]
    return (_freq(o["pf_raises"], o["pf_acts"], PRIORS["pf"]),
            _freq(o["post_raises"], o["post_acts"], PRIORS["post"]),
            _freq(o["folded"], o["faced"], PRIORS["fold"]))


def _opp_observe(obs, memory):
    o = memory["opp"]
    if o["hand"] != obs.hand_index:
        o["hand"], o["seen"], o["we_raised_last"] = obs.hand_index, 0, False
        o["pf_r_hand"] = 0
    hist = obs.action_history
    for i in range(o["seen"], len(hist)):
        act = hist[i]
        if act.is_me:
            continue
        raised = act.action in RAISE_ACTIONS
        if act.street == Street.PREFLOP:
            o["pf_acts"] += 1
            o["pf_raises"] += raised
            o["pf_r_hand"] += raised
        else:
            o["post_acts"] += 1
            o["post_raises"] += raised
        if i > 0 and hist[i - 1].is_me and hist[i - 1].action in RAISE_ACTIONS:
            o["faced"] += 1
    o["seen"] = len(hist)


def _opp_hand_end(result, memory):
    o = memory["opp"]
    o["hands"] += 1
    if (o["hand"] == result.hand_index and o["we_raised_last"]
            and not result.went_to_showdown and result.my_net > 0):
        o["faced"] += 1
        o["folded"] += 1
    o["we_raised_last"] = False
    if result.opp_hole and o["hand"] == result.hand_index and o["pf_r_hand"] > 0:
        n = min(o["pf_r_hand"], 3)
        pcts = o["sd_pcts"][n]
        pcts.append(preflop.strength(result.opp_hole)[1])
        o["sd_cut"][n] = (float(np.quantile(pcts, SD_QUANTILE)), len(pcts))


def _sd_blend(memory, n, cut):
    """Blend a frequency-based range cut with the floor seen at showdown."""
    seen = memory["opp"]["sd_cut"].get(min(n, 3))
    if not seen:
        return cut
    floor, k = seen
    t = k / (k + SD_TRUST)
    return (1.0 - t) * cut + t * floor


def _profile_bucket(memory) -> tuple[int, int, int]:
    r_pf, r_post, fold = _opp_rates(memory)
    aggr = 0 if r_post < 0.25 else 1 if r_post < 0.45 else 2
    fb = 0 if fold < 0.3 else 1 if fold < 0.5 else 2
    pb = 0 if r_pf < 0.3 else 1 if r_pf < 0.6 else 2
    return aggr, fb, pb


# ---------------------------------------------------------------------------
# EV model shared by the experts
# ---------------------------------------------------------------------------

def _sig(x):
    return 1.0 / (1.0 + np.exp(-x))


def _weights(obs, p, memory, opp_pct, opp_now):
    r_pf, r_post, fold = _opp_rates(memory)
    widen = p["widen"]
    r_pf = min(0.97, r_pf ** (1.0 / widen))
    r_post = min(0.97, r_post ** (1.0 / widen))
    w = np.ones(len(opp_pct))
    n_pf = n_post = 0
    prev = None
    for act in obs.action_history:
        if not act.is_me:
            if act.action in RAISE_ACTIONS:
                if act.street == Street.PREFLOP:
                    n_pf += 1
                    cut = min(1.0 - r_pf ** n_pf, p["max_cut"])
                    if p["sd_use"] > 0:
                        cut += p["sd_use"] * (_sd_blend(memory, n_pf, cut) - cut)
                    w *= _sig((opp_pct - cut) / p["temp_pre"])
                else:
                    n_post += 1
                    cut = min(1.0 - r_post ** n_post, p["max_cut"])
                    w *= _sig((opp_now - cut) / p["temp_post"])
            elif (act.action == Action.CHECK_CALL and act.street != Street.PREFLOP
                  and prev is not None and prev.is_me and prev.action in RAISE_ACTIONS):
                cut = min(fold * p["call_cut_scale"], p["max_cut"])
                w *= _sig((opp_now - cut) / p["temp_post"])
        prev = act
    return w + 1e-9, fold


def _expert_evs(obs, p, memory, win, opp_pct, opp_now):
    """Chip EV of each legal action (relative to our stack before acting), plus equity."""
    w, fold_rate = _weights(obs, p, memory, opp_pct, opp_now)
    ws = w.sum()
    eq = float((w * win).sum() / ws)
    pot, to_call, stack = obs.pot, obs.to_call, obs.my_stack
    river = obs.street == Street.RIVER
    r_base = p["r_ip"] if obs.is_button else p["r_oop"]
    all_in_call = to_call >= stack or obs.opp_stack == 0
    r_call = 1.0 if (river or all_in_call) else r_base

    evs = {}
    call_ev = eq * r_call * (pot + to_call) - to_call
    if to_call > 0:
        call_ev += p["call_bonus"] * pot
        if obs.street == Street.PREFLOP and p["defend"] > 0:
            r_pf, _, _ = _opp_rates(memory)   # defend wider vs frequent raisers
            call_ev += p["defend"] * pot * max(0.0, r_pf - 0.35)
    elif p["trap"] > 0 and eq >= p["trap_eq"] and not river:
        _, r_post, _ = _opp_rates(memory)
        call_ev += p["trap"] * pot * min(1.0, r_post / 0.35)
    evs[Action.CHECK_CALL] = call_ev
    if Action.FOLD in obs.legal_actions:
        evs[Action.FOLD] = 0.0

    raises = [a for a in RAISE_ACTIONS if a in obs.legal_actions]
    if raises:
        cont = _sig((opp_now - fold_rate) / p["temp_post"])
        w_call = w * cont
        wc = w_call.sum()
        f = float(1.0 - wc / ws)
        f = min(0.95, f * p["fe_scale"])
        eq_call = float((w_call * win).sum() / wc) if wc > 1e-6 else eq
        bonus = p["raise_bonus"] * pot
        if obs.street == Street.PREFLOP and obs.is_button and obs.raises_this_street == 0:
            bonus += p["pf_open"] * pot
        seen = set()
        for a in sorted(raises, reverse=True):
            total = obs.raise_to[a]
            if total in seen:
                continue
            seen.add(total)
            added = total - obs.my_bet
            opp_add = min(total - obs.opp_bet, obs.opp_stack)
            called_pot = pot + added + opp_add
            committed = added >= stack or (stack - added) < p["commit_spr"] * called_pot
            r_raise = 1.0 if (river or committed) else r_base
            fa = f if a == Action.RAISE_POT else f * p["half_fold_scale"]
            evs[a] = fa * pot + (1 - fa) * (eq_call * r_raise * called_pot - added) + bonus
    return evs, eq


# ---------------------------------------------------------------------------
# Lens keys
# ---------------------------------------------------------------------------

def _facing(obs) -> int:
    if obs.to_call <= 0:
        return 0
    r = obs.to_call / max(obs.pot, 1)
    return 1 if r < 0.25 else 2 if r < 0.45 else 3


def _lens_keys(obs, eq, memory) -> list[int]:
    st = int(obs.street)
    btn = int(obs.is_button)
    fac = _facing(obs)
    e10 = min(int(eq * 10), 9)
    e5 = min(int(eq * 5), 4)
    opp_r_hand = sum(1 for a in obs.action_history if not a.is_me and a.action in RAISE_ACTIONS)
    # texture
    board = obs.board
    if len(board) >= 3:
        score = int(F.best_score(F.hole_pairs(obs.hole_cards), F.board_triples(board))[0])
        cat = category_of(score) + 1
        bsuits = [c % 4 for c in board]  # card_suit(c) == c % 4
        hsuits = [c % 4 for c in obs.hole_cards]
        flush3 = int(max(bsuits.count(s) for s in range(4)) >= 3)
        fdraw = int(len(board) < 5 and any(bsuits.count(s) == 2 and hsuits.count(s) >= 2 for s in range(4)))
        branks = [c // 4 for c in board]
        paired = int(len(set(branks)) < len(branks))
    else:
        cat = 0
        hsuits = [c % 4 for c in obs.hole_cards]
        fdraw = int(max(hsuits.count(s) for s in range(4)) in (2, 3))
        flush3 = paired = 0
    pot = max(obs.pot, 1)
    spr = obs.my_stack / pot
    sprb = 0 if spr < 0.5 else 1 if spr < 1.0 else 2 if spr < 2.5 else 3
    potb = 0 if pot <= 6 else 1 if pot <= 20 else 2 if pot <= 60 else 3
    ag, fb, pb = _profile_bucket(memory)
    vals = (
        (st, btn, fac),
        (st, btn, e10, fac),
        (st, min(opp_r_hand, 3), min(obs.raises_this_street, 3), e5, fac),
        (st, cat, fdraw, flush3, paired, fac),
        (st, sprb, potb, e5, fac),
        (st, ag, fb, pb, e5, fac),
    )
    return [_ravel(v, d) for v, d in zip(vals, LENS_DIMS.values())]


# ---------------------------------------------------------------------------
# Hooks
# ---------------------------------------------------------------------------

def _q_residual(memory, keys) -> np.ndarray:
    th = memory["theta"]
    r = np.zeros(NA)
    for i, k in enumerate(keys):
        r += th[i][k]
    return r


def _pick_expert(memory) -> int:
    if FORCE_EXPERT in EXPERT_NAMES:
        return EXPERT_NAMES.index(FORCE_EXPERT)
    rng = memory["np_rng"]
    if TRAIN:
        return int(rng.integers(NE))
    ag, fb, pb = _profile_bucket(memory)
    cell = (ag * 3 + fb) * 3 + pb
    s = memory["meta_sum"][cell] + PRIOR_META[cell] * META_PRIOR_N
    n = memory["meta_n"][cell] + META_PRIOR_N
    q = s / n
    if META_EXPLORE > 0 and rng.random() < META_EXPLORE:
        return int(rng.integers(NE))
    return int(np.argmax(q))


def _new_half(config: AgentConfig, memory: dict) -> None:
    start = timebank.now()
    seed = os.environ.get("BOT_SEED")
    memory["np_rng"] = np.random.default_rng(int(seed) if seed else None)
    memory["stack0"] = config.starting_stack
    memory["bb"] = config.big_blind
    memory["errors"] = []
    # online Q tables start from the offline prior (counts capped so we can adapt)
    memory["theta"] = [t.copy() for t in PRIOR_THETA]
    memory["count"] = [np.minimum(c, ONLINE_PRIOR_CAP) for c in PRIOR_COUNT]
    memory["meta_sum"] = np.zeros((27, NE))
    memory["meta_n"] = np.zeros((27, NE))
    memory["hand"] = -1
    memory["expert"] = 0
    memory["trace"] = []      # this hand's decisions: (keys, action idx, base ev bb, stack before)
    memory["log"] = []        # training mode: every decision with its return
    memory["hand_log"] = []   # training mode: (profile cell, expert, net bb)
    timebank.init(memory, config.time_bank_seconds, config.num_hands)
    _opp_init(memory)
    timebank.charge(memory, timebank.now() - start)


# Time management. The judge's bank is 8 s per half and the tournament CPU may be
# slower or shared, so we plan to use only ~55% of it, cap every decision, and fall
# back to a tiny rollout (~0.3 ms) when the bank runs low instead of overrunning.
TARGET_FRACTION = 0.62       # plan to use ~62% of the bank (minimum costs reserved separately)
MAX_DECISION_S = 0.009       # rollout cap per decision
FLOOR_RESERVE_S = 0.0015     # charged cost of a minimum decision, reserved for every decision left
EMERGENCY_S = 0.5            # below this, decide without any rollout
MAX_SAMPLES = int(os.environ.get("DEMON_SAMPLES", 1024))


def _decisions_left(memory, hand_index):
    per_hand = max(memory["tb_decisions"] / max(hand_index, 1), 2.0)
    return max((memory["tb_hands"] - hand_index) * per_hand, 1.0)


def _time_budget(memory, hand_index):
    """(seconds for this decision's rollout, minimum samples)."""
    memory["tb_decisions"] += 1
    left = timebank.left(memory)
    d_left = _decisions_left(memory, hand_index)
    spendable = left - (1.0 - TARGET_FRACTION) * memory["tb_bank"] - d_left * FLOOR_RESERVE_S
    if spendable <= 0:
        return 0.0, 64
    return min(MAX_DECISION_S, spendable / d_left), 256


def _emergency_action(obs: Observation) -> Action:
    """No rollout: preflop table equity, or the made hand category postflop."""
    legal = obs.legal_actions
    if len(obs.board) < 3:
        eq, _ = preflop.strength(obs.hole_cards)
        strong, ok = eq > 0.58, eq > 0.5
    else:
        cat = category_of(int(F.best_score(F.hole_pairs(obs.hole_cards), F.board_triples(obs.board))[0]))
        strong, ok = cat >= 4, cat >= 2
    if strong and Action.RAISE_POT in legal:
        return Action.RAISE_POT
    if ok and obs.to_call <= 0.5 * obs.pot:
        return Action.CHECK_CALL
    return Action.FOLD if (obs.to_call > 0 and Action.FOLD in legal) else Action.CHECK_CALL


def _decide(obs: Observation, memory: dict) -> Action:
    if memory["hand"] != obs.hand_index:
        memory["hand"] = obs.hand_index
        memory["trace"] = []
        memory["expert"] = _pick_expert(memory)
        ag, fb, pb = _profile_bucket(memory)
        memory["cell"] = (ag * 3 + fb) * 3 + pb
    p = EXPERT_PARAMS[EXPERT_NAMES[memory["expert"]]]
    budget, min_samples = _time_budget(memory, obs.hand_index)
    deadline = timebank.now() + budget
    win, opp_pct, opp_now = equity.rollout(obs.hole_cards, obs.board, deadline, memory["np_rng"],
                                           pre_pct=preflop.PCT, batch=min(256, min_samples),
                                           min_samples=min_samples, max_samples=MAX_SAMPLES)
    evs, eq = _expert_evs(obs, p, memory, win, opp_pct, opp_now)
    keys = _lens_keys(obs, eq, memory)
    resid = _q_residual(memory, keys)
    bb = memory["bb"]
    q = {a: ev / bb + resid[A_IDX[a]] for a, ev in evs.items()}
    action = max(q, key=q.get)
    if TRAIN and memory["np_rng"].random() < TRAIN_EPS:
        legal = list(evs)
        action = legal[int(memory["np_rng"].integers(len(legal)))]
    memory["trace"].append((keys, A_IDX[action], evs[action] / bb, obs.my_stack))
    return action


def _hand_end(result: HandResult, memory: dict) -> None:
    _opp_hand_end(result, memory)
    if memory["hand"] != result.hand_index:
        return
    bb = memory["bb"]
    final_stack = memory["stack0"] + result.my_net
    th, cnt = memory["theta"], memory["count"]
    for keys, ai, base, stack_before in memory["trace"]:
        g = (final_stack - stack_before) / bb
        target = float(np.clip(g - base, -RESID_CLIP, RESID_CLIP))
        if ONLINE:
            pred = sum(th[i][k, ai] for i, k in enumerate(keys))
            err = target - pred
            for i, k in enumerate(keys):
                cnt[i][k, ai] += 1.0
                th[i][k, ai] += err / (NL * (cnt[i][k, ai] + ONLINE_RIDGE))
        if TRAIN:
            memory["log"].append((*keys, ai, base, g))
    net_bb = result.my_net / bb
    memory["meta_sum"][memory["cell"], memory["expert"]] += net_bb
    memory["meta_n"][memory["cell"], memory["expert"]] += 1.0
    if TRAIN:
        memory["hand_log"].append((memory["cell"], memory["expert"], net_bb))
    memory["trace"] = []


def new_half(config: AgentConfig, memory: dict) -> None:
    """Start of each 1000-hand half: reset opponent model and online Q tables."""
    _new_half(config, memory)


def choose_action(obs: Observation, memory: dict) -> Action:
    start = timebank.now()
    try:
        if "tb_bank" not in memory:
            _new_half(AgentConfig(), memory)
        _opp_observe(obs, memory)
        if timebank.left(memory) < EMERGENCY_S:
            action = _emergency_action(obs)
        else:
            action = _decide(obs, memory)
    except Exception:
        safety.log_exception(memory, "decide")
        action = safety.fallback(obs)
    action = safety.legalize(action, obs)
    try:
        memory["opp"]["we_raised_last"] = action in RAISE_ACTIONS
        timebank.charge(memory, timebank.now() - start)
    except Exception:
        safety.log_exception(memory, "bookkeeping")
    return action


def on_hand_end(result: HandResult, memory: dict) -> None:
    start = timebank.now()
    try:
        if "opp" in memory:
            _hand_end(result, memory)
            timebank.charge(memory, timebank.now() - start)
    except Exception:
        safety.log_exception(memory, "on_hand_end")


# ===== SERVER PLUMBING (same as agent.py) =====

app = FastAPI()
MEMORY: dict = {}
STATUS = {"started": False}
TOKEN = os.environ.get("AGENT_TOKEN") or None


async def _read_request(request: Request, path: str) -> tuple[dict, JSONResponse | None]:
    if TOKEN and request.headers.get("x-agent-token") != TOKEN:
        return {}, JSONResponse({"error": "bad or missing X-Agent-Token"}, status_code=401)
    if not STATUS["started"] and path != "/new-half":
        return {}, JSONResponse({"error": "call /new-half first"}, status_code=409)
    try:
        body = await request.json()
    except ValueError:
        body = None
    if not isinstance(body, dict):
        return {}, JSONResponse({"error": "the request body must be a JSON object"}, status_code=400)
    return body, None


def _error_info(exc: Exception) -> dict:
    return {"error": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc()}


def _crash(exc: Exception, hand_end_errors: list | None = None) -> JSONResponse:
    return JSONResponse({**_error_info(exc), "hand_end_errors": hand_end_errors or []},
                        status_code=500)


def _deliver_results(raw_results) -> list:
    errors = []
    for raw in raw_results or []:
        try:
            on_hand_end(HandResult.from_dict(raw), MEMORY)
        except Exception as exc:
            errors.append(_error_info(exc))
    return errors


@app.get("/")
async def info():
    return {"participant": PARTICIPANT, "agent_name": AGENT_NAME}


@app.post("/new-half")
async def route_new_half(request: Request):
    body, refused = await _read_request(request, "/new-half")
    if refused:
        return refused
    MEMORY.clear()
    STATUS["started"] = True
    try:
        new_half(AgentConfig.from_dict(body.get("config", {})), MEMORY)
    except Exception as exc:
        return _crash(exc)
    return {"ok": True}


@app.post("/act")
async def route_act(request: Request):
    body, refused = await _read_request(request, "/act")
    if refused:
        return refused
    hand_end_errors = _deliver_results(body.get("hand_results"))
    try:
        obs = Observation.from_dict(body["observation"])
        action = choose_action(obs, MEMORY)
    except Exception as exc:
        return _crash(exc, hand_end_errors)
    if isinstance(action, Action):
        answer = action.name
    elif action is None or isinstance(action, (str, int, float, bool)):
        answer = action
    else:
        answer = repr(action)
    return {"action": answer, "hand_end_errors": hand_end_errors}


@app.post("/hand-end")
async def route_hand_end(request: Request):
    body, refused = await _read_request(request, "/hand-end")
    if refused:
        return refused
    return {"ok": True, "hand_end_errors": _deliver_results(body.get("results"))}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5008"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info", access_log=False)
