"""
challenger.py - a self-contained Short Deck PLO5 heads-up bot.

Run it:
    python challenger/challenger.py            # listens on $PORT (default 5008)

Design (all strategy code lives in this file; tables.npz holds two lookup
tables made offline by build_tables.py):

* Hand evaluation: a (630 hole-pair x 7140 board-triple) uint16 strength table
  built at start-up from the 5-card rank table, so the Omaha "exactly 2 + 3"
  score of a hand is a max over 100 numpy lookups and thousands of hands are
  scored at once.
* Equity: each street we sample N opponent holdings (plus a random runout per
  sample) and store win/tie/loss outcomes, plus a "quality" percentile of each
  sampled opponent hand on every street seen so far (preflop equity table,
  made hand + draw estimate on flop/turn, exact strength on the river).
* Opponent range: a Bayesian weight per sample. Every opponent action
  re-weights the samples with a soft threshold on the quality percentile; the
  threshold comes from how often THIS opponent takes that action in that spot
  (learned online with priors), and a showdown-calibrated "reliability" says
  how much their actions actually reveal.
* Decisions: EV of every legal action with a one-street lookahead: fold
  equity, the opponent's calling / re-raising ranges (weighted quantiles of the
  range) and our best reply to a re-raise or to a bet after we check, with
  equity-realisation adjustments for position and future streets.
* Time: per-decision sample counts adapt to the remaining time bank; the bot
  aims to spend well under half of the 8 s bank.
"""

import os
import sys
import time
import traceback
from itertools import combinations
from math import comb

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import numpy as np  # noqa: E402
import uvicorn  # noqa: E402
from fastapi import FastAPI, Request  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402

from game import Action, AgentConfig, HandResult, Observation, Street  # noqa: E402

PARTICIPANT = "Challenger"
AGENT_NAME = "Challenger"

FOLD, CALL, HALF, POT = Action.FOLD, Action.CHECK_CALL, Action.RAISE_HALF, Action.RAISE_POT

# ===========================================================================
# Lookup tables
# ===========================================================================

NT = 7140  # number of 3-card board subsets of 36 cards
_COMB = np.array([[comb(n, k) for k in range(6)] for n in range(37)], dtype=np.intp)
P5 = np.array(list(combinations(range(5), 2)), dtype=np.intp)   # (10, 2)
T5 = np.array(list(combinations(range(5), 3)), dtype=np.intp)   # (10, 3)
T4 = np.array(list(combinations(range(4), 3)), dtype=np.intp)   # (4, 3)
ALL_CARDS = np.arange(36, dtype=np.intp)

# Straights as rank sets (rank 0 = six ... 8 = ace); A-6-7-8-9 is the wheel.
_STRAIGHTS = [frozenset((8, 0, 1, 2, 3))] + [frozenset(range(lo, lo + 5)) for lo in range(5)]


def _colex(sorted_cards):
    idx = _COMB[sorted_cards[..., 0], 1]
    for i in range(1, 5):
        idx = idx + _COMB[sorted_cards[..., i], i + 1]
    return idx


def _build_tables():
    data = np.load(os.path.join(HERE, "tables.npz"))
    rank5 = data["rank5"]
    pf = data["pf"].astype(np.float64) / 65535.0
    pairs = np.array(list(combinations(range(36), 2)), dtype=np.intp)
    triples = np.array(list(combinations(range(36), 3)), dtype=np.intp)
    T = np.zeros((len(pairs), len(triples)), dtype=np.uint16)
    cards = np.empty((len(triples), 5), dtype=np.intp)
    cards[:, 2:] = triples
    for p, (a, b) in enumerate(pairs):
        cards[:, 0] = a
        cards[:, 1] = b
        srt = np.sort(cards, axis=1)
        bad = (np.diff(srt, axis=1) == 0).any(axis=1)
        v = rank5[np.minimum(_colex(srt), len(rank5) - 1)]
        v[bad] = 0
        T[p] = v
    pidx = np.zeros((36, 36), dtype=np.intp)          # premultiplied by NT
    for p, (a, b) in enumerate(pairs):
        pidx[a, b] = pidx[b, a] = p * NT
    tidx = np.zeros((36, 36, 36), dtype=np.intp)
    for t, (a, b, c) in enumerate(triples):
        for x, y, z in ((a, b, c), (a, c, b), (b, a, c), (b, c, a), (c, a, b), (c, b, a)):
            tidx[x, y, z] = t
    # Straight-draw table: for hole ranks (r1, r2) and a board rank mask, the
    # bitmask of ranks that would complete a NEW straight (2 hole + 2 board +
    # the new card).
    sd = np.zeros((81, 512), dtype=np.intp)
    for r1 in range(9):
        for r2 in range(9):
            if r1 == r2:
                continue
            for s in _STRAIGHTS:
                if r1 not in s or r2 not in s:
                    continue
                rest = sorted(s - {r1, r2})
                for missing in rest:
                    need = [r for r in rest if r != missing]
                    bit_need = (1 << need[0]) | (1 << need[1])
                    for m in range(512):
                        if (m & bit_need) == bit_need and not (m >> missing) & 1:
                            sd[r1 * 9 + r2, m] |= 1 << missing
    pop = np.array([bin(i).count("1") for i in range(512)], dtype=np.float64)
    return T.ravel(), pidx, tidx, pf, sd, pop


TF, PIDX, TIDX, PF, SD, POP = _build_tables()


def _pct(v):
    """Percentile rank of every entry of v within v (ties share the mid rank)."""
    s = np.sort(v)
    return (np.searchsorted(s, v, "left") + np.searchsorted(s, v, "right")) * (0.5 / len(v))


def _board_triples(board):
    b = np.asarray(board, dtype=np.intp)
    if len(b) == 3:
        return np.array([TIDX[b[0], b[1], b[2]]], dtype=np.intp)
    combos = T4 if len(b) == 4 else T5
    return TIDX[b[combos[:, 0]], b[combos[:, 1]], b[combos[:, 2]]]


def _quality(opp, op, board):
    """Made-hand + draw strength percentile of each sampled opponent hand on a
    3- or 4-card board."""
    tb = _board_triples(board)
    made = TF[op[:, :, None] + tb[None, None, :]].max(axis=(1, 2))
    made_pct = _pct(made)
    b = np.asarray(board, dtype=np.intp)
    bmask = int(np.bitwise_or.reduce(1 << (b >> 2)))
    ranks = opp >> 2
    rp = ranks[:, P5[:, 0]] * 9 + ranks[:, P5[:, 1]]
    sd = np.bitwise_or.reduce(SD[rp, bmask], axis=1)
    outs = POP[sd] * 3.0
    bsuit = np.bincount(b & 3, minlength=4)
    two = np.nonzero(bsuit == 2)[0]
    if len(two):
        suits = opp & 3
        fd = np.zeros(len(opp), dtype=bool)
        for s in two:
            fd |= (suits == s).sum(axis=1) >= 2
        outs = outs + 5.0 * fd
    outs = np.minimum(outs, 15.0)
    unseen = 31.0 - len(b)
    if len(b) == 3:
        hit = 1.0 - (1.0 - outs / unseen) * (1.0 - outs / (unseen - 1.0))
    else:
        hit = outs / unseen
    raw = made_pct + hit * np.maximum(0.0, 0.92 - made_pct)
    return _pct(raw)


def build_set(hero, board, n, rng):
    """Sample n opponent holdings + runouts; return outcomes and qualities."""
    hero = np.asarray(hero, dtype=np.intp)
    board = np.asarray(board, dtype=np.intp)
    k = len(board)
    dead = np.zeros(36, dtype=bool)
    dead[hero] = True
    dead[board] = True
    rest = ALL_CARDS[~dead]
    need = 10 - k
    keys = rng.random((n, len(rest)))
    cards = rest[np.argpartition(keys, need - 1, axis=1)[:, :need]]
    opp = cards[:, :5]
    op = PIDX[opp[:, P5[:, 0]], opp[:, P5[:, 1]]]
    hp = PIDX[hero[P5[:, 0]], hero[P5[:, 1]]]
    if k == 5:
        bt = _board_triples(board)
        hs = TF[hp[:, None] + bt[None, :]].max()
        os_ = TF[op[:, :, None] + bt[None, None, :]].max(axis=(1, 2))
    else:
        fb = np.empty((n, 5), dtype=np.intp)
        fb[:, :k] = board
        fb[:, k:] = cards[:, 5:]
        bt = TIDX[fb[:, T5[:, 0]], fb[:, T5[:, 1]], fb[:, T5[:, 2]]]
        hs = TF[hp[None, :, None] + bt[:, None, :]].max(axis=(1, 2))
        os_ = TF[op[:, :, None] + bt[:, None, :]].max(axis=(1, 2))
    o = (hs > os_) + 0.5 * (hs == os_)
    q = [_pct(PF[_colex(np.sort(opp, axis=1))])]
    if k >= 3:
        q.append(_quality(opp, op, board[:3]))
    if k >= 4:
        q.append(_quality(opp, op, board[:4]))
    if k == 5:
        q.append(_pct(os_))
    delta = 0.0
    if k == 0:  # control variate: exact equity vs a random hand from the table
        delta = float(PF[_colex(np.sort(hero))]) - float(o.mean())
    return {"o": o.astype(np.float64), "q": q, "n": n, "delta": delta}


# ===========================================================================
# Opponent model
# ===========================================================================

# Prior action frequencies [fold, check/call, raise] per context.
PRIORS = {
    "pf_open": (0.15, 0.30, 0.55),
    "pf_check": (0.0, 0.65, 0.35),
    "pf_vs_raise": (0.30, 0.50, 0.20),
    "po_open": (0.0, 0.55, 0.45),
    "po_vs_bet": (0.40, 0.45, 0.15),
}
PRIOR_N = 6.0      # pseudo-counts behind the pooled priors
STREET_N = 8.0     # pseudo-counts tying a per-street context to its pooled one

DEFAULT_PARAMS = {
    "tau": 0.07,        # softness of range thresholds (percentile units)
    "eps_raise": 0.12,  # share of a raising range that is not value
    "trap": 0.30,       # share of strong hands that check / flat instead of raising
    "pol": 0.10,        # future-street polarisation of equity
    "pos_ip": 0.02,     # equity realisation bonus in position
    "pos_oop": -0.04,   # ... and penalty out of position
    # style biases (pot fractions) - zero for the real bot; used to build
    # sparring variants (maniac / station / nit) for testing
    "b_call": 0.0,
    "b_raise": 0.0,
    "b_fold": 0.0,
    "learn": 1.0,       # 0 = never update the opponent model (static bot)
}
PARAMS = dict(DEFAULT_PARAMS)   # the active set (memory["params"] of the current half)


def ctx_keys(street, facing, raises, last_kind, actor_was_aggr):
    """Context keys for an action, from the pooled context to the most specific
    one (street, raise level, size of the bet faced, previous aggressor)."""
    sz = "p" if last_kind == 3 else "h"
    if street == 0:
        if not facing:
            return ("pf_check",)
        if raises == 0:
            return ("pf_open",)
        lvl = min(raises, 3)
        return ("pf_vs_raise", f"pfr{lvl}", f"pfr{lvl}{sz}")
    if facing:
        return ("po_vs_bet", f"pvb{street}", f"pvb{street}" + ("r" if raises >= 2 else sz))
    return ("po_open", f"po{street}", f"po{street}" + ("a" if actor_was_aggr else "n"))


def replay(history, hero_is_button):
    """Walk a hand's action list. Yields (is_me, street, keys, kind, raises_before,
    action) with kind 0 fold / 1 check-call / 2 raise."""
    street = 0
    tot = {True: 1 if hero_is_button else 2, False: 2 if hero_is_button else 1}
    raises = 0
    last_kind = 0
    cur_aggr = prev_aggr = None
    for a in history:
        s = int(a.street)
        if s != street:
            prev_aggr = cur_aggr if s == street + 1 else None
            cur_aggr = None
            street = s
            tot = {True: 0, False: 0}
            raises = 0
            last_kind = 0
        me = bool(a.is_me)
        facing = tot[not me] > tot[me]
        act = int(a.action)
        kind = 2 if act >= 2 else act
        yield me, street, ctx_keys(street, facing, raises, last_kind, prev_aggr is me), kind, raises, act
        tot[me] = int(a.street_total)
        if kind == 2:
            raises += 1
            last_kind = act
            cur_aggr = me


def prev_aggressor(history, street):
    """True if we, False if the opponent made the last raise of the previous
    street, None if nobody raised there."""
    last = None
    for a in history:
        if int(a.street) == street - 1 and int(a.action) >= 2:
            last = bool(a.is_me)
    return last


def final_state(history, hero_is_button):
    """(street, street totals, acted flags, raises) after a list of actions."""
    street = 0
    tot = {True: 1 if hero_is_button else 2, False: 2 if hero_is_button else 1}
    acted = {True: False, False: False}
    raises = 0
    for a in history:
        s = int(a.street)
        if s != street:
            street, raises = s, 0
            tot = {True: 0, False: 0}
            acted = {True: False, False: False}
        me = bool(a.is_me)
        tot[me] = int(a.street_total)
        acted[me] = True
        if int(a.action) >= 2:
            raises += 1
            acted[not me] = False
    return street, tot, acted, raises


def new_model():
    return {"cnt": {}, "mine": {}, "size": [1.0, 1.0], "rho": [3.2, 4.0], "rho_c": [3.2, 4.0]}


def freqs(model, keys):
    """[fold, call, raise] frequencies with hierarchical shrinkage."""
    cnt = model["cnt"]
    pri = PRIORS[keys[0]]
    c = cnt.get(keys[0], (0.0, 0.0, 0.0))
    n = c[0] + c[1] + c[2]
    f = [(c[i] + PRIOR_N * pri[i]) / (n + PRIOR_N) for i in range(3)]
    for k in keys[1:]:
        c = cnt.get(k)
        if c is None:
            continue
        n = c[0] + c[1] + c[2]
        f = [(c[i] + STREET_N * f[i]) / (n + STREET_N) for i in range(3)]
    return f


def _count(model, key, kind):
    c = model["cnt"].get(key)
    if c is None:
        c = model["cnt"][key] = [0.0, 0.0, 0.0]
    c[kind] += 1.0


def _sig(x):
    return 1.0 / (1.0 + np.exp(-x))


def _wquant(q, w, level):
    """Weighted quantile of q at `level` (0..1)."""
    order = np.argsort(q, kind="stable")
    cw = np.cumsum(w[order])
    i = int(np.searchsorted(cw, level * cw[-1]))
    return float(q[order[min(i, len(q) - 1)]])


def range_weights(S, history, hero_is_button, model):
    tau = PARAMS["tau"]
    eps = PARAMS["eps_raise"]
    trap = PARAMS["trap"]
    rho = model["rho"][0] / model["rho"][1]
    rho_c = model["rho_c"][0] / model["rho_c"][1]
    w = np.ones(S["n"])
    nq = len(S["q"])
    for me, street, keys, kind, raises, _act in replay(history, hero_is_button):
        if me or street >= nq:
            continue
        q = S["q"][street]
        ff, fc, fr = freqs(model, keys)
        base = keys[0]
        if kind == 2:
            if fr > 0.97:
                continue
            thr = _wquant(q, w, 1.0 - fr)
            f = eps + (1.0 - eps) * _sig((q - thr) / tau)
            w *= (1.0 - rho) + rho * f
        elif kind == 1:
            facing = base in ("pf_open", "pf_vs_raise", "po_vs_bet")
            hi = _wquant(q, w, 1.0 - fr) if fr > 0.03 else 2.0
            capf = 1.0 - (1.0 - trap) * _sig((q - hi) / tau)
            if facing and ff > 0.03:
                lo = _wquant(q, w, ff)
                f = _sig((q - lo) / tau) * capf
                w *= (1.0 - rho_c) + rho_c * f
            else:
                w *= (1.0 - rho) + rho * capf
        w = np.maximum(w, 1e-9)
    return w


# ===========================================================================
# EV engine
# ===========================================================================

def _raise_to(pot, actor_bet, other_bet, actor_stack, kind):
    """Engine raise formula (min-raise approximated by the last bet step)."""
    to_call = other_bet - actor_bet
    pot_to = other_bet + pot + to_call
    half_to = other_bet + (pot + to_call) // 2
    min_to = other_bet + max(to_call, 2)
    target = pot_to if kind == POT else half_to
    return min(max(target, min_to), pot_to, actor_bet + actor_stack)


def _eff(e, future, street, ip):
    if not future:
        return e
    k = 0.5 if street == 2 else 1.0
    e2 = e + k * (PARAMS["pol"] * (e - 0.5) + (PARAMS["pos_ip"] if ip else PARAMS["pos_oop"]))
    return min(1.0, max(0.0, e2))


def _split(q, w, o, ff, fr, rho_c, rho, delta):
    """Opponent response to a bet/raise: probabilities of fold / call / raise and
    our equity against the calling and raising parts of the range."""
    W = w.sum()
    if ff > 0.0:
        thr_f = _wquant(q, w, ff)
        pfold = rho_c * (q < thr_f) + (1.0 - rho_c) * ff
    else:
        pfold = np.zeros_like(q)
    if fr > 0.0:
        thr_r = _wquant(q, w, 1.0 - fr)
        prai = rho * (q >= thr_r) + (1.0 - rho) * fr
        prai = np.minimum(prai, 1.0 - pfold)
    else:
        prai = np.zeros_like(q)
    pcall = np.maximum(0.0, 1.0 - pfold - prai)
    wf, wc, wr = (w * pfold).sum(), w * pcall, w * prai
    wcs, wrs = wc.sum(), wr.sum()
    e_c = (wc @ o) / wcs + delta if wcs > 1e-12 else 0.5
    e_r = (wr @ o) / wrs + delta if wrs > 1e-12 else 0.5
    return wf / W, wcs / W, wrs / W, min(1.0, max(0.0, e_c)), min(1.0, max(0.0, e_r))


def evaluate(obs, S, w, model):
    """EV (in chips, future money only) of every legal action."""
    o, delta = S["o"], S["delta"]
    st = int(obs.street)
    q = S["q"][st]
    W = w.sum()
    e_all = min(1.0, max(0.0, (w @ o) / W + delta))
    P, C = obs.pot, obs.to_call
    mb, ob, ms, os_ = obs.my_bet, obs.opp_bet, obs.my_stack, obs.opp_stack
    river = st == 3
    ip = bool(obs.is_button)
    raises = obs.raises_this_street
    rho = model["rho"][0] / model["rho"][1]
    rho_c = model["rho_c"][0] / model["rho_c"][1]
    p_pot = model["size"][1] / (model["size"][0] + model["size"][1])
    opp_kind = POT if p_pot >= 0.5 else HALF
    ev = {}
    legal = obs.legal_actions
    if FOLD in legal:
        ev[FOLD] = 0.0

    # ---- check / call
    opp_acted = any((not a.is_me) and int(a.street) == st for a in obs.action_history)
    sb_limp = st == 0 and raises == 0 and C > 0 and mb < ob and not opp_acted
    closing = (C > 0 and not sb_limp) or (C == 0 and opp_acted)
    ms1 = ms - min(C, ms)
    if closing or os_ == 0 or ms1 == 0 or raises >= 4:
        fut = (not river) and ms1 > 0 and os_ > 0
        ev[CALL] = _eff(e_all, fut, st, ip) * (P + C) - C
    else:
        opp_aggr = st > 0 and prev_aggressor(obs.action_history, st) is False
        _, _, fb = freqs(model, ctx_keys(st, False, raises, 0, opp_aggr))
        P1, mb1 = P + C, mb + C
        thr = _wquant(q, w, 1.0 - fb)
        pb_i = rho * (q >= thr) + (1.0 - rho) * fb
        wb = w * pb_i
        wn = w - wb
        wbs, wns = wb.sum(), wn.sum()
        pb = wbs / W
        e_b = min(1.0, max(0.0, (wb @ o) / wbs + delta)) if wbs > 1e-12 else e_all
        e_n = min(1.0, max(0.0, (wn @ o) / wns + delta)) if wns > 1e-12 else e_all
        ev_n = _eff(e_n, not river, st, ip) * P1 - C
        b_to = _raise_to(P1, ob, mb1, os_, opp_kind)
        cost = min(b_to - mb1, ms1)
        final = P1 + (b_to - ob) + cost
        allin = cost >= ms1
        ev_bc = _eff(e_b, (not river) and not allin, st, ip) * final - C - cost
        ev[CALL] = (1.0 - pb) * ev_n + pb * max(ev_bc, -C)

    # ---- raises
    for a in (HALF, POT):
        if a not in legal:
            continue
        ff, fc, fr = freqs(model, ctx_keys(st, True, raises + 1, int(a), False))
        R = obs.raise_to[a]
        A, D = R - mb, R - ob
        hero_allin = A >= ms
        opp_allin = D >= os_
        can_rr = raises + 1 < 4 and not hero_allin and not opp_allin
        pfo, pca, pra, e_c, e_r = _split(q, w, o, ff, fr if can_rr else 0.0, rho_c, rho, delta)
        fut = (not river) and not hero_allin and not opp_allin
        ev_c = _eff(e_c, fut, st, ip) * (P + A + D) - A
        ev_r = 0.0
        if pra > 0.0:
            P2 = P + A
            R2 = _raise_to(P2, ob, R, os_, opp_kind)
            cost = min(R2 - R, ms - A)
            final2 = P2 + (R2 - ob) + cost
            fut2 = (not river) and cost < ms - A
            ev_r = max(_eff(e_r, fut2, st, ip) * final2 - A - cost, -A)
        ev[a] = pfo * P + pca * ev_c + pra * ev_r
    if PARAMS["b_call"] or PARAMS["b_raise"] or PARAMS["b_fold"]:
        for a in ev:
            if a == FOLD:
                ev[a] += PARAMS["b_fold"] * P
            elif a == CALL:
                ev[a] += PARAMS["b_call"] * P if C > 0 else 0.0
            else:
                ev[a] += PARAMS["b_raise"] * P
    return ev


# ===========================================================================
# Bot hooks
# ===========================================================================

DEBUG = bool(os.environ.get("CHALLENGER_DEBUG"))
N_MAX = 800
N_MIN = 48
BUDGET = 3.0        # seconds of our own compute we aim to spend per half


def new_half(config: AgentConfig, memory: dict) -> None:
    memory["params"] = dict(DEFAULT_PARAMS)
    memory["rng"] = np.random.default_rng(12345)
    memory["model"] = new_model()
    memory["n"] = 320
    memory["spent"] = 0.0
    memory["num_hands"] = int(getattr(config, "num_hands", 1000) or 1000)
    memory["bank"] = float(getattr(config, "time_bank_seconds", 8.0) or 8.0)
    memory["cache"] = {}
    memory["last"] = None
    memory["hand_t"] = [0.0, -1]   # time spent on the current hand, its index
    memory["ema"] = 1e-5     # seconds per hand per sample (running estimate)


def _fallback(obs):
    legal = obs.legal_actions
    if obs.to_call == 0:
        return CALL
    return FOLD if FOLD in legal else CALL


def _adapt_n(memory, hand_index):
    """Pick the sample count from the remaining budget."""
    ht = memory["hand_t"]
    if ht[1] != hand_index:
        if ht[1] >= 0:
            memory["ema"] = 0.95 * memory["ema"] + 0.05 * ht[0] / max(memory["n"], 1)
        ht[0], ht[1] = 0.0, hand_index
    budget = min(BUDGET, 0.5 * memory["bank"]) * memory["bank"] / 8.0 if memory["bank"] < 8.0 else BUDGET
    left = max(1, memory["num_hands"] - hand_index)
    allow = (budget - memory["spent"]) / left       # seconds per hand still allowed
    n = int(allow / max(memory["ema"], 1e-7))
    memory["n"] = max(N_MIN, min(N_MAX, n))
    return memory["n"]


def choose_action(obs: Observation, memory: dict) -> Action:
    t0 = time.perf_counter()
    try:
        return _choose(obs, memory)
    except Exception:
        if DEBUG:
            raise
        return _fallback(obs)
    finally:
        dt = time.perf_counter() - t0
        memory["spent"] += dt
        memory["hand_t"][0] += dt


def _choose(obs, memory):
    global PARAMS
    PARAMS = memory["params"]
    legal = obs.legal_actions
    if len(legal) == 1:
        act = legal[0]
    elif memory["spent"] > 0.75 * memory["bank"]:
        act = _fallback(obs)
    else:
        n = _adapt_n(memory, obs.hand_index)
        key = (obs.hand_index, int(obs.street))
        cache = memory["cache"]
        S = cache.get(key)
        if S is None:
            if len(cache) > 8:
                cache.clear()
            S = build_set(obs.hole_cards, obs.board, n, memory["rng"])
            cache[key] = S
        w = range_weights(S, obs.action_history, obs.is_button, memory["model"])
        ev = evaluate(obs, S, w, memory["model"])
        act = max(ev, key=ev.get)
        if act not in legal:
            act = _fallback(obs)
    if act in (HALF, POT):
        total = obs.raise_to[act]
    elif act == CALL:
        total = obs.my_bet + min(obs.to_call, obs.my_stack)
    else:
        total = obs.my_bet
    memory["last"] = (obs.hand_index, obs.action_history, act, bool(obs.is_button), int(obs.street), total)
    return act


class _A:
    """A minimal ObservedAction stand-in for reconstructed history items."""
    __slots__ = ("street", "is_me", "action", "amount", "street_total")

    def __init__(self, street, is_me, action, street_total):
        self.street, self.is_me, self.action, self.amount, self.street_total = street, is_me, action, 0, street_total


def on_hand_end(result: HandResult, memory: dict) -> None:
    t0 = time.perf_counter()
    try:
        _learn(result, memory)
    except Exception:
        if DEBUG:
            raise
    finally:
        memory["spent"] += time.perf_counter() - t0


def _learn(result, memory):
    global PARAMS
    PARAMS = memory["params"]
    model = memory["model"]
    last = memory["last"]
    memory["cache"].clear()
    if not PARAMS["learn"]:
        return
    if last is None or last[0] != result.hand_index:
        # We never acted: as big blind the small blind folded at once.
        if not result.went_to_showdown and result.my_net > 0:
            _count(model, "pf_open", 0)
        return
    _, hist, my_act, is_btn, st, my_total = last
    hist = list(hist)
    hist.append(_A(st, True, my_act, my_total))  # our final action
    if my_act != FOLD:
        # Did the opponent still have to act after our last move? Then infer
        # its unseen reply (fold, or check/call to a showdown) and append it.
        street, tot, acted, raises = final_state(hist, is_btn)
        round_over = acted[True] and acted[False] and tot[True] == tot[False]
        if not round_over:
            facing = tot[True] > tot[False]
            if not result.went_to_showdown and result.my_net > 0 and facing:
                hist.append(_A(street, False, FOLD, tot[False]))
            elif result.went_to_showdown:
                hist.append(_A(street, False, CALL, tot[True]))
    events = list(replay(hist, is_btn))
    for me, s, keys, kind, raises, act in events:
        if me:
            c = model["mine"].setdefault(keys[-1], [0, 0, 0])
            c[kind] += 1
            continue
        for k in keys:
            _count(model, k, kind)
        if kind == 2:
            model["size"][1 if act == int(POT) else 0] += 1.0
    if result.went_to_showdown and result.opp_hole is not None:
        _calibrate(result, events, is_btn, memory)


def _calibrate(result, events, is_btn, memory):
    """Use the opponent's shown hand to learn how much their actions reveal:
    compare its quality percentile at each of their raises / calls with what an
    honest (strength-ordered) range would show."""
    model = memory["model"]
    opp = np.array(result.opp_hole, dtype=np.intp)
    board = list(result.board)
    rng = memory["rng"]
    qcache = {}
    for me, s, keys, kind, raises, act in events:
        if me or kind == 0:
            continue
        if s not in qcache:
            qcache[s] = _shown_quality(opp, board, s, rng)
        qv = qcache[s]
        ff, fc, fr = freqs(model, keys)
        base = keys[0]
        if kind == 2:
            if fr > 0.9:
                continue
            expect = 1.0 - 0.5 * fr          # mean percentile of an honest top-fr range
            r = model["rho"]
        else:
            facing = base in ("pf_open", "pf_vs_raise", "po_vs_bet")
            if not facing or ff < 0.1:
                continue
            expect = 0.5 + 0.5 * ff - 0.5 * fr
            r = model["rho_c"]
        if expect <= 0.55:
            continue
        val = (qv - 0.5) / (expect - 0.5)
        r[0] += min(1.2, max(-0.2, val))
        r[1] += 1.0
        r[0] = min(r[0], r[1])
        r[0] = max(r[0], 0.1 * r[1])


def _shown_quality(opp, board, street, rng, n=160):
    """Quality percentile of a shown opponent hand among random hands."""
    k = (0, 3, 4, 5)[street]
    b = np.array(board[:k], dtype=np.intp)
    dead = np.zeros(36, dtype=bool)
    dead[b] = True
    rest = ALL_CARDS[~dead]
    keys = rng.random((n, len(rest)))
    hands = rest[np.argpartition(keys, 4, axis=1)[:, :5]]
    hands[0] = opp
    op = PIDX[hands[:, P5[:, 0]], hands[:, P5[:, 1]]]
    if k == 0:
        q = _pct(PF[_colex(np.sort(hands, axis=1))])
    elif k == 5:
        bt = _board_triples(b)
        q = _pct(TF[op[:, :, None] + bt[None, None, :]].max(axis=(1, 2)))
    else:
        q = _quality(hands, op, b)
    return float(q[0])


def _warm():
    mem = {}
    new_half(AgentConfig(), mem)
    rng = np.random.default_rng(0)
    for k in (0, 3, 4, 5):
        cards = rng.permutation(36)
        build_set(cards[:5], cards[5:5 + k], 64, rng)


_warm()

# ===== SERVER PLUMBING (same as agent.py) =====

app = FastAPI()
MEMORY: dict = {}
STATUS = {"started": False}
TOKEN = os.environ.get("AGENT_TOKEN") or None


async def _read_request(request: Request, path: str):
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
