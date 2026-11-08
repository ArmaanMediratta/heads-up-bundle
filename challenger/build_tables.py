"""
build_tables.py - offline precomputation for challenger.py.

Writes challenger/tables.npz with:
    rank5   uint16[376992]  dense strength rank of every 5-card hand, indexed by
                            the colex index of its sorted cards (bigger = better)
    pf      uint16[376992]  preflop equity (x 65535) of every 5-card holding vs a
                            uniformly random opponent holding, same indexing

    python3 challenger/build_tables.py [--samples 2000]

Takes a few minutes. Only uses evaluator.py from the repo root.
"""

import argparse
import os
import sys
import time
from itertools import combinations
from math import comb

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from evaluator import get_table  # noqa: E402

COMB = np.array([[comb(n, k) for k in range(6)] for n in range(37)], dtype=np.int64)


def colex(sorted_cards: np.ndarray) -> np.ndarray:
    """colex index of rows of ascending cards (last axis has length 5)."""
    idx = np.zeros(sorted_cards.shape[:-1], dtype=np.int64)
    for i in range(5):
        idx += COMB[sorted_cards[..., i], i + 1]
    return idx


def build_rank5() -> np.ndarray:
    table = get_table()
    hands = np.array(list(combinations(range(36), 5)), dtype=np.int64)
    masks = (np.left_shift(1, hands)).sum(axis=1)
    scores = np.array([table[int(m)] for m in masks], dtype=np.int64)
    idx = colex(hands)
    _, dense = np.unique(scores, return_inverse=True)
    out = np.zeros(len(hands), dtype=np.uint16)
    out[idx] = dense + 1  # 0 is reserved for "impossible"
    return out


def build_T(rank5: np.ndarray):
    pairs = np.array(list(combinations(range(36), 2)), dtype=np.int8)
    triples = np.array(list(combinations(range(36), 3)), dtype=np.int8)
    T = np.zeros((len(pairs), len(triples)), dtype=np.uint16)
    for p, (a, b) in enumerate(pairs):
        cards = np.empty((len(triples), 5), dtype=np.int64)
        cards[:, 0] = a
        cards[:, 1] = b
        cards[:, 2:] = triples
        cards.sort(axis=1)
        bad = (np.diff(cards, axis=1) == 0).any(axis=1)
        v = rank5[np.minimum(colex(cards), len(rank5) - 1)]
        v[bad] = 0
        T[p] = v
    pidx = -np.ones((36, 36), dtype=np.int64)
    for p, (a, b) in enumerate(pairs):
        pidx[a, b] = pidx[b, a] = p
    tidx = -np.ones((36, 36, 36), dtype=np.int64)
    for t, (a, b, c) in enumerate(triples):
        for x, y, z in ((a, b, c), (a, c, b), (b, a, c), (b, c, a), (c, a, b), (c, b, a)):
            tidx[x, y, z] = t
    return T.ravel(), pidx, tidx


PAIRS5 = np.array(list(combinations(range(5), 2)))
TRIP5 = np.array(list(combinations(range(5), 3)))


def build_pf(Tf, pidx, tidx, samples: int, seed: int = 1) -> np.ndarray:
    hands = np.array(list(combinations(range(36), 5)), dtype=np.int64)
    ranks, suits = hands >> 2, hands & 3
    # canonical class under suit permutation
    perms = np.array(list(__import__("itertools").permutations(range(4))), dtype=np.int64)
    best = None
    for perm in perms:
        mapped = np.sort(ranks * 4 + perm[suits], axis=1)
        ci = colex(mapped)
        best = ci if best is None else np.minimum(best, ci)
    classes, inverse = np.unique(best, return_inverse=True)
    print(f"{len(classes)} preflop classes", flush=True)
    hidx = colex(hands)
    # decode colex index -> cards (canonical hand is a real hand)
    by_idx = dict(zip(hidx.tolist(), range(len(hands))))
    rng = np.random.default_rng(seed)
    eq = np.zeros(len(classes))
    t0 = time.time()
    for k, c in enumerate(classes):
        hero = hands[by_idx[int(c)]]
        rest = np.setdiff1d(np.arange(36), hero)
        keys = rng.random((samples, len(rest)))
        pick = rest[np.argpartition(keys, 10, axis=1)[:, :10]]
        opp, board = pick[:, :5], pick[:, 5:]
        bt = tidx[board[:, TRIP5[:, 0]], board[:, TRIP5[:, 1]], board[:, TRIP5[:, 2]]]  # (S,10)
        hp = pidx[hero[PAIRS5[:, 0]], hero[PAIRS5[:, 1]]]  # (10,)
        op = pidx[opp[:, PAIRS5[:, 0]], opp[:, PAIRS5[:, 1]]]  # (S,10)
        hs = Tf[hp[None, :, None] * 7140 + bt[:, None, :]].max(axis=(1, 2))
        os_ = Tf[op[:, :, None] * 7140 + bt[:, None, :]].max(axis=(1, 2))
        eq[k] = ((hs > os_) + 0.5 * (hs == os_)).mean()
        if k % 2000 == 0:
            print(k, f"{time.time() - t0:.0f}s", flush=True)
    out = np.zeros(len(hands), dtype=np.uint16)
    out[hidx] = np.round(eq[inverse] * 65535).astype(np.uint16)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=2000)
    args = ap.parse_args()
    t0 = time.time()
    rank5 = build_rank5()
    print(f"rank5 built ({rank5.max()} classes) {time.time() - t0:.1f}s", flush=True)
    Tf, pidx, tidx = build_T(rank5)
    print(f"T built {time.time() - t0:.1f}s", flush=True)
    pf = build_pf(Tf, pidx, tidx, args.samples)
    np.savez_compressed(os.path.join(HERE, "tables.npz"), rank5=rank5, pf=pf)
    print(f"done {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
