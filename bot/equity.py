"""
equity.py - Monte Carlo rollouts against sampled opponent hands.

`rollout` deals N random (opponent hand, rest of board) completions and
returns per-sample arrays the policy weights into a range-aware equity:
    win      1 / 0.5 / 0 for hero at showdown
    opp_pct  preflop strength percentile of the opponent's hand (0..1)
    opp_now  opponent's strength on the board seen so far, as a percentile
             among the samples (0..1; preflop it equals opp_pct)
"""

import time

import numpy as np

from bot import fasteval as F
from evaluator import NUM_CARDS

ALL_CARDS = np.arange(NUM_CARDS, dtype=np.intp)


def _remaining(hole, board) -> np.ndarray:
    used = np.zeros(NUM_CARDS, dtype=bool)
    used[list(hole)] = True
    used[list(board)] = True
    return ALL_CARDS[~used]


def _rank_pct(x: np.ndarray) -> np.ndarray:
    """Percentile rank of each value among x (ties share the average rank)."""
    order = np.argsort(x, kind="stable")
    ranks = np.empty(len(x), dtype=np.float64)
    ranks[order] = np.arange(len(x))
    # average ties so equal hands get equal percentiles
    _, inv, counts = np.unique(x, return_inverse=True, return_counts=True)
    sums = np.bincount(inv, weights=ranks)
    return (sums / counts)[inv] / max(len(x) - 1, 1)


def _batch(hole, board, n, rng, pre_pct):
    rem = _remaining(hole, board)
    need = 5 + (5 - len(board))
    sel = rng.random((n, len(rem))).argpartition(need - 1, axis=1)[:, :need]
    cards = rem[sel]
    opp = cards[:, :5]
    if len(board) == 5:
        trips = F.board_triples(board)
        hero = F.best_score(F.hole_pairs(hole), trips)[0]
        opp_pairs = F.hole_pairs(opp)
        opp_final = F.best_score(opp_pairs, trips)
        hero_final = np.full(n, hero)
        opp_now_raw = opp_final
    else:
        boards = np.concatenate([np.broadcast_to(np.asarray(board, dtype=np.intp), (n, len(board))),
                                 cards[:, 5:]], axis=1)
        trips = F.board5_triples(boards)
        opp_pairs = F.hole_pairs(opp)
        hero_final = F.best_score(np.broadcast_to(F.hole_pairs(hole), (n, 10)), trips)
        opp_final = F.best_score(opp_pairs, trips)
        opp_now_raw = F.best_score(opp_pairs, F.board_triples(board)) if len(board) >= 3 else None
    win = (hero_final > opp_final) + 0.5 * (hero_final == opp_final)
    opp_pct = pre_pct[F.hand_index(np.sort(opp, axis=1))] if pre_pct is not None else np.full(n, 0.5)
    return win, opp_pct, opp_now_raw


def rollout(hole, board, deadline: float, rng: np.random.Generator, pre_pct=None,
            batch: int = 128, min_samples: int = 64, max_samples: int = 2048):
    """Sample until `deadline` (perf_counter time) or max_samples; always at least min_samples."""
    wins, pcts, nows = [], [], []
    total = 0
    while True:
        n = min(batch, max_samples - total)
        w, p, now = _batch(hole, board, max(n, min_samples if total == 0 else n), rng, pre_pct)
        wins.append(w)
        pcts.append(p)
        if now is not None:
            nows.append(now)
        total += len(w)
        if total >= max_samples or time.perf_counter() >= deadline:
            break
    win = np.concatenate(wins)
    opp_pct = np.concatenate(pcts)
    opp_now = _rank_pct(np.concatenate(nows)) if nows else opp_pct
    return win, opp_pct, opp_now
